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

# Lists to store the matching layers and effects(content effects and mask effects)
found_layers = []
found_content_effects = []
found_mask_effects = []

# Combined and sorted list used for navigating to the top and bottom of the stack 
combined_results = []  

#Global Variables
current_index = -1
replace_input = None
find_input = None
status_label = None
last_stack_key = None

# Specifically to track effects inside of fill layers workaround from how the API Navigates from effects > mask effects and vice versa
# uid effects of the parent layer
effect_parent_map = {}
mask_effect_parent_map = {}
node_category = {}     
last_item_category = None   

# Shorter Variables for each Module
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
    #Return a single combined list of all found items in top-to-bottom stack order.
    return combined_results

def _get_active_stack_key():
    #Returns a tuple uniquely identifying the currently active stack:
    try:
        stack = _TS.get_active_stack()
        if stack is None:
            return None
        # TextureSet name
        material = stack.material()
        mat_name = material.name() if hasattr(material, "name") else None
        # Stack name (empty string for non-layered materials)
        try:
            stack_name = stack.name()
        except Exception:
            stack_name = None
        return (mat_name, stack_name)
    except Exception:
        return None

def clear_search_state():
    # Clear all search results (Find and Replace), and resets navigation state. 
    # This is so when the user moves to a new stack it doesn't automatically select that layer/effect.
    global current_index, last_item_category
    global found_layers, found_content_effects, found_mask_effects, combined_results
    global node_category, effect_parent_map, mask_effect_parent_map
    global find_input, replace_input, status_label

    # Clear result lists and parent maps
    found_layers.clear()
    found_content_effects.clear()
    found_mask_effects.clear()
    combined_results.clear()
    node_category.clear()
    effect_parent_map.clear()
    mask_effect_parent_map.clear()
    current_index = -1
    last_item_category = None

    if find_input is not None:
        find_input.blockSignals(True)
        find_input.clear()
        find_input.blockSignals(False)

    if replace_input is not None:
        replace_input.blockSignals(True)
        replace_input.clear()
        replace_input.blockSignals(False)

    if status_label is not None:
        status_label.setText("0 out of 0")

def _name_contains(node, search_cf):
    # Check if the node name contains the search prompt
    try:
        return search_cf in node.get_name().casefold()
    except Exception:
        # ignores odd search types, if any node returns a non-string name
        name = str(node.get_name())
        return search_cf in name.casefold()

def collect_matches(layer, search_cf, layers_acc, content_acc, mask_acc, combined_acc):
    #Sorts Layer stack from top to bottom and collects matches in this exact order:-
    #Layers > Content Effects > Mask Effects > Groups (sub_layers)

    # 1. Layer itself
    if _name_contains(layer, search_cf):
        layers_acc.append(layer)
        combined_acc.append(layer)
        node_category[uid(layer)] = "layer"

    # 2. Content effects
    for effect in layer.content_effects():
        if _name_contains(effect, search_cf):
            content_acc.append(effect)
            combined_acc.append(effect)
            u = uid(effect)
            node_category[u] = "content_effect"
            effect_parent_map[u] = layer

    # 3. Mask effects
    if layer.has_mask():
        for effect in layer.mask_effects():
            if _name_contains(effect, search_cf):
                mask_acc.append(effect)
                combined_acc.append(effect)
                u = uid(effect)
                node_category[u] = "mask_effect"
                mask_effect_parent_map[u] = layer

    # 4. Groups
    if layer.get_type() == _NodeType.GroupLayer:
        for child in layer.sub_layers():  # assumed top -> bottom
            collect_matches(child, search_cf, layers_acc, content_acc, mask_acc, combined_acc)

def update_search_results(substring, status_display):
    # Updates the lists when it detects changes in the layer stack. This is different from recording the changes in stack because it records every change which is not helpful.
    # It returns the updated search results and updates the UI state
    global found_layers, found_content_effects, found_mask_effects, combined_results, current_index
    global node_category, effect_parent_map, mask_effect_parent_map, last_item_category

    if not _PR.is_open():
        return

    s = substring.strip()
    if not s:
        found_layers.clear()
        found_content_effects.clear()
        found_mask_effects.clear()
        combined_results.clear()
        node_category.clear()
        effect_parent_map.clear()
        mask_effect_parent_map.clear()
        last_item_category = None
        update_status_display(status_display)
        return

    # Capture previous size of lists
    old_sizes = (len(found_layers), len(found_content_effects), len(found_mask_effects))

    # New lists to slice and accumulate results
    new_layers = []
    new_content = []
    new_mask = []
    new_combined = []

    # Reset maps
    node_category.clear()
    effect_parent_map.clear()
    mask_effect_parent_map.clear()
    last_item_category = None

    # retrieves the active layer stack and its root layers
    stack = _TS.get_active_stack()
    root_layers = _LS.get_root_layer_nodes(stack)

    search_cf = s.casefold()
    # Sorts each root layer in order (top to bottom)
    for layer in root_layers:
        collect_matches(layer, search_cf, new_layers, new_content, new_mask, new_combined)

    # splicing and altering the found lists based on new results
    found_layers[:] = new_layers
    found_content_effects[:] = new_content
    found_mask_effects[:] = new_mask
    combined_results[:] = new_combined  # this drives navigation

    # retrieving the new sizes of each list
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

def _get_current_item():
    # gets the currently selected item in the combined_results list
    items = _active_results_list()
    if items and 0 <= current_index < len(items):
        return items[current_index]
    return None

def _get_parent_for_node(node, category):
    # gets the parent layer for an effect/mask effect, or None
    # as mentioned previously this is workaround from the how the API Navigates from effects > mask effects and vice versa
    u = uid(node)
    if category == "content_effect":
        return effect_parent_map.get(u)
    elif category == "mask_effect":
        return mask_effect_parent_map.get(u)
    return None

def select_current_item(status_display, should_select=True):
    # Selects the current item in the stack and updates status display
    global last_item_category

    if not _PR.is_open():
        return
    
    items = _active_results_list()
    current_item = items[current_index] if items and current_index >= 0 else None

    #Conditions to check for special condition
    if should_select and current_item is not None:
        u = uid(current_item)
        cat = node_category.get(u)

        # If navigating between effect <-> mask_effect, first select parent layer
        if (
            last_item_category in ("content_effect", "mask_effect") and
            cat in ("content_effect", "mask_effect") and
            last_item_category != cat
        ):
            parent = _get_parent_for_node(current_item, cat)
            if parent is not None:
                # First select the parent layer to ensure correct context,
                # then select the actual child node.
                _LS.set_selected_nodes([parent])

        # Now select the actual node
        _LS.set_selected_nodes([current_item])
        last_item_category = cat
    else:
        # If we're not actually selecting in the stack, don't change last_item_category
        pass
    update_status_display(status_display)

def update_status_display(status_display):
    # Updates the status display UI with current index and total results of matching layers/effects
    total = len(_active_results_list())
    if total > 0 and current_index >= 0:
        status_display.setText(f"{current_index + 1} out of {total}")
    else:
        status_display.setText("0 out of 0")

def navigate(direction, status_display):
    # Navigate up or down the combined results list
    global current_index
    if not _PR.is_open():
        return
    items = _active_results_list()
    if items:
        current_index = (current_index + direction) % len(items)
    select_current_item(status_display, should_select=True)

def search_items(prompt_input, status_display):
    # Calling search function based on prompt initial input or change in the prompt field, and then select current item
    update_search_results(prompt_input.text().strip(), status_display)
    select_current_item(status_display, should_select=True)

def replace_substring_in_name(name, search, replacement, case_sensitive=False):
    # replaces the search prompt, not the whole name of the layer/effect, just the substring
    if not search:
        return name
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.escape(search)
    return re.sub(pattern, replacement, name, flags=flags)

def _refresh_after_rename():
    # Applies search again after prompt name change
    if status_label is not None and find_input is not None:
        update_search_results(find_input.text().strip(), status_label)
        select_current_item(status_label, should_select=False)

def replace_current_item():
    # replaces the current selected item's name with the replace field
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
    # replaces all found items' names with the replace field
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

    # Track changes in case the UI selection changes
    changes = 0
    for item in list(items):
        old_name = item.get_name()
        new_name = replace_substring_in_name(old_name, search_text, replacement_text, case_sensitive=False)
        if old_name != new_name:
            item.set_name(new_name)
            changes += 1
    _refresh_after_rename()
    clear_search_state()

def on_layer_stack_changed(evt):
    #Called whenever the layer stack changes.
    global last_stack_key

    if not _PR.is_open():
        return
    
    current_key = _get_active_stack_key()

    #Condition to check if there is a change in the the stack layer
    if current_key != last_stack_key:
        last_stack_key = current_key
        clear_search_state()
        return

    #If the stack is the same as before: keep the existing live update functionality
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

    # Main Window Header
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # Status display (global)
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
    global last_stack_key

    for widget in plugin_widgets:
        _UI.delete_ui_element(widget)
    plugin_widgets.clear()

    _EV.DISPATCHER.disconnect(_EV.LayerStacksModelDataChanged, on_layer_stack_changed)

    # Reset stack tracking so next project/session resets
    last_stack_key = None

    print("[Python] Plugin closed.")

if __name__ == "__main__":
    start_plugin()
