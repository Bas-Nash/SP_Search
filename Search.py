import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
import substance_painter.event
from PySide2 import QtGui, QtWidgets, QtCore

plugin_widgets = []
current_view = "layers"
found_layers = []
found_content_effects = []
found_mask_effects = []
current_index = -1
replace_input = None

def uid(node):
    return node.uid() if hasattr(node, 'uid') else id(node)
def find_items(layer, substring):
    found_content_effects = []
    found_mask_effects = []
    found_layers = []

    if substring.lower() in layer.get_name().lower():
        found_layers.append(layer)

    for effect in layer.content_effects():
        if substring.lower() in effect.get_name().lower():
            found_content_effects.append(effect)

    if layer.has_mask():
        for effect in layer.mask_effects():
            if substring.lower() in effect.get_name().lower():
                found_mask_effects.append(effect)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            sub_content_effects, sub_mask_effects, sub_layers = find_items(sub_layer, substring)
            found_content_effects.extend(sub_content_effects)
            found_mask_effects.extend(sub_mask_effects)
            found_layers.extend(sub_layers)

    return found_content_effects, found_mask_effects, found_layers

def switch_view(view, layers_button, content_button, mask_button, status_display):
    global current_view, current_index
    current_view = view
    items = found_layers if view == "layers" else found_content_effects if view == "content_effects" else found_mask_effects
    current_index = 0 if items else -1

    def toggle(button, active):
        button.setChecked(active)
        button.setEnabled(not active)

    toggle(layers_button, view == "layers")
    toggle(content_button, view == "content_effects")
    toggle(mask_button, view == "mask_effects")

    select_current_item(status_display)

def update_search_results(substring, status_display):
    global found_layers, found_content_effects, found_mask_effects, current_index, current_view

    if not substance_painter.project.is_open():
        return

    if not substring.strip():
        found_layers.clear()
        found_content_effects.clear()
        found_mask_effects.clear()
        substance_painter.layerstack.set_selected_nodes([])
        update_status_display(status_display)
        return

    old_lengths = (len(found_layers), len(found_content_effects), len(found_mask_effects))

    new_layers = []
    new_content_effects = []
    new_mask_effects = []

    stack = substance_painter.textureset.get_active_stack()
    root_layers = substance_painter.layerstack.get_root_layer_nodes(stack)

    for layer in root_layers:
        content, mask, layers = find_items(layer, substring)
        new_content_effects.extend(content)
        new_mask_effects.extend(mask)
        new_layers.extend(layers)

    found_layers[:] = new_layers
    found_content_effects[:] = new_content_effects
    found_mask_effects[:] = new_mask_effects

    new_lengths = (len(found_layers), len(found_content_effects), len(found_mask_effects))
    items = found_layers if current_view == "layers" else found_content_effects if current_view == "content_effects" else found_mask_effects

    if new_lengths != old_lengths:
        current_index = 0 if items else -1
        select_current_item(status_display, should_select=True)
    else:
        if current_index >= len(items):
            current_index = len(items) - 1 if items else -1
        update_status_display(status_display)

def select_current_item(status_display, should_select=True):
    global current_index, current_view

    if not substance_painter.project.is_open():
        return

    selection = []
    if current_view == "layers" and found_layers:
        selection = [found_layers[current_index]]
    elif current_view == "content_effects" and found_content_effects:
        selection = [found_content_effects[current_index]]
    elif current_view == "mask_effects" and found_mask_effects:
        selection = [found_mask_effects[current_index]]

    if should_select:
        substance_painter.layerstack.set_selected_nodes(selection)
        
    update_status_display(status_display)

def update_status_display(status_display):
    global current_index, current_view
    total_items = len(found_layers if current_view == "layers" else found_content_effects if current_view == "content_effects" else found_mask_effects)
    if total_items > 0 and current_index >= 0:
        status_display.setText(f"{current_index + 1} out of {total_items}")
    else:
        status_display.setText("0 out of 0")

def navigate(direction, status_display):
    global current_index, current_view

    if not substance_painter.project.is_open():
        return

    items = found_layers if current_view == "layers" else found_content_effects if current_view == "content_effects" else found_mask_effects
    if items:
        current_index = (current_index + direction) % len(items)
    select_current_item(status_display, should_select=True)

def search_items(prompt_input, status_display):
    update_search_results(prompt_input.text().strip(), status_display)
    select_current_item(status_display, should_select=True)

def replace_current_item():
    global current_index, current_view, found_layers, found_content_effects, found_mask_effects, replace_input

    if replace_input is None or current_index == -1:
        print("[Python] No active selection or replace field not initialized.")
        return
    
    replacement_text = replace_input.text().strip()
    if not replacement_text:
        print("[Python] Replacement field must be filled.")
        return

    if current_view == "layers" and found_layers:
        current_item = found_layers[current_index]
    elif current_view == "content_effects" and found_content_effects:
        current_item = found_content_effects[current_index]
    elif current_view == "mask_effects" and found_mask_effects:
        current_item = found_mask_effects[current_index]
    else:
        print("[Python] No valid selection to replace.")
        return
    
    current_item.set_name(replacement_text)
    
    #print(f"[Python] Replaced current {current_view[:-1]} name with '{replacement_text}'.")
def replace_all_items():
    global current_view, found_layers, found_content_effects, found_mask_effects, replace_input

    if replace_input is None:
        print("[Python] Replace field not initialized.")
        return

    replacement_text = replace_input.text().strip()
    if not replacement_text:
        print("[Python] Replacement field must be filled.")
        return

    # Copy the list to iterate on a snapshot of the items.
    if current_view == "layers" and found_layers:
        items_to_replace = found_layers[:]  # Create a shallow copy
        for item in items_to_replace:
            item.set_name(replacement_text)
        print(f"[Python] Replaced all layer names with '{replacement_text}'.")
    elif current_view == "content_effects" and found_content_effects:
        items_to_replace = found_content_effects[:]
        for item in items_to_replace:
            item.set_name(replacement_text)
        print(f"[Python] Replaced all content effect names with '{replacement_text}'.")
    elif current_view == "mask_effects" and found_mask_effects:
        items_to_replace = found_mask_effects[:]
        for item in items_to_replace:
            item.set_name(replacement_text)
        print(f"[Python] Replaced all mask effect names with '{replacement_text}'.")
    else:
        print("[Python] No valid items to replace.")
        
def on_layer_stack_changed(*args):
    if not substance_painter.project.is_open():
        return
    if plugin_widgets:
        prompt_input = plugin_widgets[0].findChild(QtWidgets.QLineEdit)
        status_display = plugin_widgets[0].findChild(QtWidgets.QLabel)
        if prompt_input and status_display:
            update_search_results(prompt_input.text().strip(), status_display)
            select_current_item(status_display, should_select=False)

def create_collapsible_section(title, content_widget):
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
    global plugin_widgets, replace_input

    if plugin_widgets:
        print("[Python] UI is already created.")
        return

    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    top_buttons_layout = QtWidgets.QHBoxLayout()
    def create_view_switch_button(name):
        button = QtWidgets.QPushButton(name)
        button.setCheckable(True)
        button.setChecked(name == "Layers")
        button.setEnabled(name != "Layers")
        return button

    layers_button = create_view_switch_button("Layers")
    layer_effects_button = create_view_switch_button("Layer Effects")
    mask_effects_button = create_view_switch_button("Mask Effects")

    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)

    layers_button.clicked.connect(lambda: switch_view("layers", layers_button, layer_effects_button, mask_effects_button, status_display))
    layer_effects_button.clicked.connect(lambda: switch_view("content_effects", layers_button, layer_effects_button, mask_effects_button, status_display))
    mask_effects_button.clicked.connect(lambda: switch_view("mask_effects", layers_button, layer_effects_button, mask_effects_button, status_display))

    top_buttons_layout.addWidget(layers_button)
    top_buttons_layout.addWidget(layer_effects_button)
    top_buttons_layout.addWidget(mask_effects_button)
    main_layout.addLayout(top_buttons_layout)

    # Find section
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")

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

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)

    print("[Python] UI created successfully.")
    
def start_plugin():
    create_ui()
    substance_painter.event.DISPATCHER.connect(substance_painter.event.LayerStacksModelDataChanged, on_layer_stack_changed)
    print("Plugin started")

def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    substance_painter.event.DISPATCHER.disconnect(substance_painter.event.LayerStacksModelDataChanged, on_layer_stack_changed)
    print("[Python] Plugin closed.")
    
if __name__ == "__main__":
    start_plugin()