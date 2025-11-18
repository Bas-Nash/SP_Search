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
current_view = "layers"
found_layers = []
found_content_effects = []
found_mask_effects = []
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
    #Returns node uid or fallback to id().
    return node.uid() if hasattr(node, "uid") else id(node)

def _active_results_list():
    #Return the currently active collection for the selected view
    if current_view == "layers":
        return found_layers
    elif current_view == "content_effects":
        return found_content_effects
    else:
        return found_mask_effects
    
def _set_toggle_state(layers_btn, content_btn, mask_btn, target_view):
    # Sets active for the selected view button, and disables the others
    for btn, is_active in (
        (layers_btn, target_view == "layers"),
        (content_btn, target_view == "content_effects"),
        (mask_btn, target_view == "mask_effects"),
    ):
        btn.setChecked(is_active)
        btn.setEnabled(not is_active) 

def _name_contains(node, search_cf):
    # Check if the node name contains the search prompt, 
    try:
        return search_cf in node.get_name().casefold()
    except Exception:
        #ignores odd search types, if any node returns a non-string name
        name = str(node.get_name())
        return search_cf in name.casefold()

def find_items_iter(root_layer, search_cf):
    #Iterating through the layer stack and adds matched content_effects, mask_effects, layers into their respective lists
    layers_acc = []
    content_acc = []
    mask_acc = []

    stack = [root_layer]
    pop = stack.pop
    extend = stack.extend
    #Loop through stack
    while stack:
        layer = pop()
        # Match layer name
        if _name_contains(layer, search_cf):
            layers_acc.append(layer)
        # Match content effects
        for effect in layer.content_effects():
            if _name_contains(effect, search_cf):
                content_acc.append(effect)
        # Match mask effects
        if layer.has_mask():
            for effect in layer.mask_effects():
                if _name_contains(effect, search_cf):
                    mask_acc.append(effect)
        # Dive into groups
        if layer.get_type() == _NodeType.GroupLayer:
            extend(layer.sub_layers())
    return content_acc, mask_acc, layers_acc

def update_search_results(substring, status_display): 
    #reruns the search and updates the UI state with new results
    global found_layers, found_content_effects, found_mask_effects, current_index

    if not _PR.is_open():
        return

    s = substring.strip()
    if not s:
        found_layers.clear()
        found_content_effects.clear()
        found_mask_effects.clear()
        update_status_display(status_display)
        return

    # Capture previous size of lists 
    old_sizes = (len(found_layers), len(found_content_effects), len(found_mask_effects))

    # New lists to slice and accumlate results 
    new_layers = []
    new_content = []
    new_mask = []
    # retrieves the active layer stack and its root layers
    stack = _TS.get_active_stack()
    root_layers = _LS.get_root_layer_nodes(stack)

    search_cf = s.casefold()
    for layer in root_layers:
        c, m, l = find_items_iter(layer, search_cf)
        new_content.extend(c)
        new_mask.extend(m)
        new_layers.extend(l)

    # splicing and altering the found lists based on new results 
    found_layers[:] = new_layers
    found_content_effects[:] = new_content
    found_mask_effects[:] = new_mask

    #retriving the new sizes of each list 
    new_sizes = (len(found_layers), len(found_content_effects), len(found_mask_effects))
    items = _active_results_list()

    if new_sizes != old_sizes:
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
    #Navigate up or down the active results list
    global current_index
    if not _PR.is_open():
        return
    items = _active_results_list()
    if items:
        # Mod in range with wrap
        current_index = (current_index + direction) % len(items)
    select_current_item(status_display, should_select=True)

def search_items(prompt_input, status_display):
    # Rerun search based on prompt initial input or change in the prompt field, and then select current item
    update_search_results(prompt_input.text().strip(), status_display)
    select_current_item(status_display, should_select=True)

def replace_substring_in_name(name, search, replacement, case_sensitive=False):
    #replaces the search prompt, not the whole name of the layer/effect but just the substring 
    if not search:
        return name
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(search)
    return re.sub(pattern, replacement, name, flags=flags)

def _get_current_item():
    #gets the currently selected item in the active results list
    items = _active_results_list()
    if items and 0 <= current_index < len(items):
        return items[current_index]
    return None

def _refresh_after_rename():
    # Applies search again after prompt name change
    if status_label is not None and find_input is not None:
        update_search_results(find_input.text().strip(), status_label)
        select_current_item(status_label, should_select=False)

def replace_current_item():
    #replaces the current selected item's name with the replace field
    global replace_input, find_input

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
    #replaces all found items' names with the replace field
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
    # Track changes in chase the UI selection Changes 
    changes = 0
    for item in list(items):
        old_name = item.get_name()
        new_name = replace_substring_in_name(old_name, search_text, replacement_text, case_sensitive=False)
        if old_name != new_name:
            item.set_name(new_name)
            changes += 1
    _refresh_after_rename()

def on_layer_stack_changed(*_args):
    if not _PR.is_open():
        return
    if plugin_widgets:
        if find_input and status_label:
            update_search_results(find_input.text().strip(), status_label)
            select_current_item(status_label, should_select=False)
        else:
            # Fallback: first dock's children
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

    # Main Window Header
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # View switch
    top_buttons_layout = QtWidgets.QHBoxLayout()
    def _make_view_btn(label, is_active):
        btn = QtWidgets.QPushButton(label)
        btn.setCheckable(True)
        btn.setChecked(is_active)
        btn.setEnabled(not is_active)
        return btn

    # View Buttons
    layers_button = _make_view_btn("Layers", True)
    layer_effects_button = _make_view_btn("Layer Effects", False)
    mask_effects_button = _make_view_btn("Mask Effects", False)

    # Status display
    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    status_label = status_display  # store globally for refresh after rename

    layers_button.clicked.connect(lambda: (globals().__setitem__("current_view", "layers"),
                                           _set_toggle_state(layers_button, layer_effects_button, mask_effects_button, "layers"),
                                           globals().__setitem__("current_index", 0 if found_layers else -1),
                                           select_current_item(status_display)))
    layer_effects_button.clicked.connect(lambda: (globals().__setitem__("current_view", "content_effects"),
                                                  _set_toggle_state(layers_button, layer_effects_button, mask_effects_button, "content_effects"),
                                                  globals().__setitem__("current_index", 0 if found_content_effects else -1),
                                                  select_current_item(status_display)))
    mask_effects_button.clicked.connect(lambda: (globals().__setitem__("current_view", "mask_effects"),
                                                 _set_toggle_state(layers_button, layer_effects_button, mask_effects_button, "mask_effects"),
                                                 globals().__setitem__("current_index", 0 if found_mask_effects else -1),
                                                 select_current_item(status_display)))

    top_buttons_layout.addWidget(layers_button)
    top_buttons_layout.addWidget(layer_effects_button)
    top_buttons_layout.addWidget(mask_effects_button)
    main_layout.addLayout(top_buttons_layout)

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
