import os
import re
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
import substance_painter.event

IsQt5 = substance_painter.application.version_info() < (10, 1, 0)
if IsQt5:
    from PySide2 import QtGui, QtCore, QtWidgets
else:
    from PySide6 import QtGui, QtCore, QtWidgets

plugin_widgets = []
found_items = []
current_index = -1
replace_input = None
find_input = None
status_label = None

_LS = substance_painter.layerstack
_TS = substance_painter.textureset
_PR = substance_painter.project
_EV = substance_painter.event
_UI = substance_painter.ui
_NodeType = _LS.NodeType

def uid(node):
    # Returns node uid or fallback to id().
    return node.uid() if hasattr(node, "uid") else id(node)

def _active_results_list():
    # Return the unified search results list
    global found_items
    return found_items

def _name_contains(node, search_cf):
    # Check if the node name contains the search prompt
    try:
        return search_cf in node.get_name().casefold()
    except Exception:
        # Ignores odd search types, if any node returns a non-string name
        name = str(node.get_name())
        return search_cf in name.casefold()

def _sort_top_to_bottom(layers):
    # Sorts layers in a hierarchy-preserving order from top to bottom.
    for layer in layers:
        yield layer
        if layer.get_type() == _NodeType.GroupLayer:
            # Recurse into group sub-layers in their order
            for sub in _sort_top_to_bottom(layer.sub_layers()):
                yield sub

def update_search_results(substring, status_display):
    # Reruns the search and updates the UI state with new results
    global found_items, current_index

    if not _PR.is_open():
        return

    s = substring.strip()
    if not s:
        found_items.clear()
        update_status_display(status_display)
        return

    old_size = len(found_items)

    stack = _TS.get_active_stack()
    if stack is None:
        found_items.clear()
        update_status_display(status_display)
        return

    root_layers = _LS.get_root_layer_nodes(stack)
    search_cf = s.casefold()
    new_items = []

    # Sort the stack top → bottom, respecting hierarchy
    for layer in _sort_top_to_bottom(root_layers):
        # 1. The layer itself
        if _name_contains(layer, search_cf):
            new_items.append(layer)

        # 2. Its content effects, in their order
        for effect in layer.content_effects():
            if _name_contains(effect, search_cf):
                new_items.append(effect)

        # 3. Its mask effects, if any, in their order
        if layer.has_mask():
            for effect in layer.mask_effects():
                if _name_contains(effect, search_cf):
                    new_items.append(effect)

    # splice in-place so references stay valid
    found_items[:] = new_items
    new_size = len(found_items)
    items = _active_results_list()

    if new_size != old_size:
        current_index = 0 if items else -1
        select_current_item(status_display, should_select=True)
    else:
        if items:
            # Keep index within range
            if current_index >= len(items):
                current_index = len(items) - 1
        else:
            current_index = -1
        update_status_display(status_display)

def select_current_item(status_display, should_select=True):
    # Selects the current item in the stack and updates status display
    if not _PR.is_open():
        return

    items = _active_results_list()
    selection = [items[current_index]] if items and current_index >= 0 else []

    if should_select:
        _LS.set_selected_nodes(selection)

    update_status_display(status_display)

def update_status_display(status_display):
    # Updates the status display UI with current index and total results
    total = len(_active_results_list())
    if total > 0 and current_index >= 0:
        status_display.setText(f"{current_index + 1} out of {total}")
    else:
        status_display.setText("0 out of 0")

def navigate(direction, status_display):
    # Navigate up or down the unified results list in stack order
    global current_index
    if not _PR.is_open():
        return

    items = _active_results_list()
    if items:
        # Mod in range with wrap
        current_index = (current_index + direction) % len(items)

    select_current_item(status_display, should_select=True)

def search_items(prompt_input, status_display):
    # Rerun search based on prompt input, then select current item
    update_search_results(prompt_input.text().strip(), status_display)
    select_current_item(status_display, should_select=True)

def replace_substring_in_name(name, search, replacement, case_sensitive=False):
    # Replaces the search prompt substring (not the whole name)
    if not search:
        return name
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(search)
    return re.sub(pattern, replacement, name, flags=flags)

def _get_current_item():
    # Gets the currently selected item in the unified results list
    items = _active_results_list()
    if items and 0 <= current_index < len(items):
        return items[current_index]
    return None

def _refresh_after_rename():
    # Applies search again after name changes
    if status_label is not None and find_input is not None:
        update_search_results(find_input.text().strip(), status_label)
        select_current_item(status_label, should_select=False)

def replace_current_item():
    # Replaces the current selected item's name with the replace field
    global replace_input, find_input, current_index

    if replace_input is None or find_input is None:
        print("[Python] Replace or Find field not initialized.")
        return
    if current_index == -1:
        print("[Python] No active selection.")
        return

    search_text = find_input.text().strip()
    replacement_text = replace_input.text().strip()

    if not search_text:
        print("[Python] Find field is empty; nothing to replace.")
        return
    if not replacement_text:
        print("[Python] Replacement field must be filled.")
        return

    current_item = _get_current_item()
    if not current_item:
        print("[Python] No valid selection to replace.")
        return

    old_name = current_item.get_name()
    new_name = replace_substring_in_name(old_name, search_text, replacement_text, case_sensitive=False)

    if old_name != new_name:
        current_item.set_name(new_name)
        print(f"[Python] Renamed '{old_name}' → '{new_name}'.")
        _refresh_after_rename()
    else:
        print(f"[Python] No occurrences of '{search_text}' found in '{old_name}'.")

def replace_all_items():
    # Replaces all found items' names with the replace field
    global replace_input, find_input

    if replace_input is None or find_input is None:
        print("[Python] Replace or Find field not initialized.")
        return

    search_text = find_input.text().strip()
    replacement_text = replace_input.text().strip()

    if not search_text:
        print("[Python] Find field is empty; nothing to replace.")
        return
    if not replacement_text:
        print("[Python] Replacement field must be filled.")
        return

    items = _active_results_list()
    if not items:
        print("[Python] No valid items to replace.")
        return

    changes = 0
    for item in list(items):
        old_name = item.get_name()
        new_name = replace_substring_in_name(old_name, search_text, replacement_text, case_sensitive=False)
        if old_name != new_name:
            item.set_name(new_name)
            changes += 1

    print(f"[Python] Renamed {changes} item(s).")
    _refresh_after_rename()

def on_layer_stack_changed(*_args):
    if not _PR.is_open():
        return
    if plugin_widgets:
        if find_input and status_label:
            update_search_results(find_input.text().strip(), status_label)
            select_current_item(status_label, should_select=False)
        else:
            prompt_input = plugin_widgets[0].findChild(QtWidgets.QLineEdit)
            status_display = plugin_widgets[0].findChild(QtWidgets.QLabel)
            if prompt_input and status_display:
                update_search_results(prompt_input.text().strip(), status_display)
                select_current_item(status_display, should_select=False)

def create_collapsible_section(title, content_widget):
    # Creates UI Element for collapsible section with drop down to reveal elements
    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    toggle_button = QtWidgets.QToolButton()
    toggle_button.setStyleSheet("QToolButton { border: none; }")
    toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    toggle_button.setArrowType(QtCore.Qt.RightArrow)
    toggle_button.setText(title)
    toggle_button.setCheckable(True)
    toggle_button.setChecked(False)
    toggle_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    collapsible_widget = QtWidgets.QWidget()
    collapsible_layout = QtWidgets.QVBoxLayout(collapsible_widget)
    collapsible_layout.setContentsMargins(15, 0, 0, 0)
    collapsible_layout.addWidget(content_widget)
    collapsible_widget.setVisible(False)

    def toggle_collapsible():
        visible = toggle_button.isChecked()
        collapsible_widget.setVisible(visible)
        toggle_button.setArrowType(QtCore.Qt.DownArrow if visible else QtCore.Qt.RightArrow)

    toggle_button.toggled.connect(toggle_collapsible)

    layout.addWidget(toggle_button)
    layout.addWidget(collapsible_widget)
    container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
    return container, collapsible_layout

def create_ui():
    global plugin_widgets, replace_input, find_input, status_label

    if plugin_widgets:
        print("[Python] UI is already created.")
        return

    # Main Window
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # Status display
    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    status_label = status_display  # store globally for refresh after rename

    # Find section
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    find_input = prompt_input  # store

    # Navigation buttons
    navigation_layout = QtWidgets.QHBoxLayout()
    prev_button = QtWidgets.QPushButton("<")
    prev_button.clicked.connect(lambda: navigate(-1, status_display))
    navigation_layout.addWidget(prev_button)
    next_button = QtWidgets.QPushButton(">")
    next_button.clicked.connect(lambda: navigate(1, status_display))
    navigation_layout.addWidget(next_button)

    find_widget = QtWidgets.QWidget()
    find_layout = QtWidgets.QVBoxLayout(find_widget)
    find_layout.setContentsMargins(0, 0, 0, 0)
    find_layout.addWidget(prompt_input)
    find_layout.addLayout(navigation_layout)

    find_section, _ = create_collapsible_section("Find", find_widget)
    main_layout.addWidget(find_section)

    # Replace section
    replace_input = QtWidgets.QLineEdit()
    replace_input.setPlaceholderText("Type replacement text...")

    replace_widget = QtWidgets.QWidget()
    replace_layout = QtWidgets.QVBoxLayout(replace_widget)
    replace_layout.setContentsMargins(0, 0, 0, 0)
    replace_layout.addWidget(replace_input)

    replace_buttons_layout = QtWidgets.QHBoxLayout()
    replace_button = QtWidgets.QPushButton("Replace")
    replace_button.clicked.connect(replace_current_item)
    replace_all_button = QtWidgets.QPushButton("Replace All")
    replace_all_button.clicked.connect(replace_all_items)
    replace_buttons_layout.addWidget(replace_button)
    replace_buttons_layout.addWidget(replace_all_button)
    replace_layout.addLayout(replace_buttons_layout)

    replace_section, _ = create_collapsible_section("Replace", replace_widget)
    main_layout.addWidget(replace_section)

    prompt_input.textChanged.connect(lambda: search_items(prompt_input, status_display))
    QtCore.QTimer.singleShot(0, lambda: search_items(prompt_input, status_display))

    main_layout.addWidget(status_display)
    main_layout.addStretch()

    _UI.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)

def start_plugin():
    create_ui()
    _EV.DISPATCHER.connect(_EV.LayerStacksModelDataChanged, on_layer_stack_changed)
    print("Plugin started")

def close_plugin():
    for widget in plugin_widgets:
        _UI.delete_ui_element(widget)
    plugin_widgets.clear()
    _EV.DISPATCHER.disconnect(_EV.LayerStacksModelDataChanged, on_layer_stack_changed)
    print("[Python] Plugin closed.")

if __name__ == "__main__":
    start_plugin()