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
found_effects = []
current_index = -1
search_term = ""
status_display = None  # Store status display globally

def uid(node):
    return node.uid() if hasattr(node, 'uid') else id(node)

def find_items(layer, substring):
    found_effects = []
    found_layers = []
    if substring.lower() in layer.get_name().lower():
        found_layers.append((layer.get_name(), uid(layer)))
    effects = layer.content_effects() + (layer.mask_effects() if layer.has_mask() else [])
    for effect in effects:
        if substring.lower() in effect.get_name().lower():
            found_effects.append((effect.get_name(), uid(effect)))
    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            sub_effects, sub_layers = find_items(sub_layer, substring)
            found_effects.extend(sub_effects)
            found_layers.extend(sub_layers)
    return found_effects, found_layers

def display_current_item():
    global current_index, found_layers, found_effects, current_view, status_display
    
    if not status_display:
        return  # Avoid errors if UI isn't initialized yet
    
    if current_view == "layers" and found_layers:
        item_name, item_id = found_layers[current_index]
        status_display.setText(f"{current_index + 1} out of {len(found_layers)}: {item_name} [UID: {item_id}]")
    elif current_view == "effects" and found_effects:
        item_name, item_id = found_effects[current_index]
        status_display.setText(f"{current_index + 1} out of {len(found_effects)}: {item_name} [UID: {item_id}]")
    else:
        status_display.setText("0 out of 0")

def navigate(direction):
    global current_index, found_layers, found_effects, current_view
    
    if current_view == "layers" and found_layers:
        current_index = (current_index + direction) % len(found_layers)
    elif current_view == "effects" and found_effects:
        current_index = (current_index + direction) % len(found_effects)
    display_current_item()

def search_layers(prompt_input=None):
    global found_layers, found_effects, current_index, search_term
    
    substring = prompt_input.text().strip() if prompt_input else search_term
    
    if not substring:  # If no input is provided, clear search results
        found_layers.clear()
        found_effects.clear()
        current_index = -1
        display_current_item()
        return
    
    search_term = substring  # Store for later updates
    found_layers.clear()
    found_effects.clear()
    current_index = -1
    
    stack = substance_painter.textureset.get_active_stack()
    root_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    for layer in root_layers:
        effects, layers = find_items(layer, substring)
        found_layers.extend(layers)
        found_effects.extend(effects)
    
    if found_layers or found_effects:
        current_index = 0
    display_current_item()

def switch_view(view, layers_button, effects_button):
    global current_view, current_index
    current_view = view
    current_index = 0 if (found_layers if view == "layers" else found_effects) else -1
    
    layers_button.setChecked(view == "layers")
    layers_button.setEnabled(view != "layers")
    effects_button.setChecked(view == "effects")
    effects_button.setEnabled(view != "effects")
    
    display_current_item()
    
def update_layer_stack(event):
    print("Updating Find functionality")
    search_layers()  # Refresh search with stored search term

def create_ui():
    global plugin_widgets, status_display

    if plugin_widgets:
        print("[Python] UI is already created.")
        return
    
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)
    
    top_buttons_layout = QtWidgets.QHBoxLayout()
    layers_button = QtWidgets.QPushButton("Layers")
    layers_button.setCheckable(True)
    layers_button.setChecked(True)
    layers_button.setEnabled(False)
    layers_button.clicked.connect(lambda: switch_view("layers", layers_button, effects_button))
    top_buttons_layout.addWidget(layers_button)
    
    effects_button = QtWidgets.QPushButton("Effects")
    effects_button.setCheckable(True)
    effects_button.setChecked(False)
    effects_button.clicked.connect(lambda: switch_view("effects", layers_button, effects_button))
    top_buttons_layout.addWidget(effects_button)
    main_layout.addLayout(top_buttons_layout)
    
    text_fields_layout = QtWidgets.QHBoxLayout()
    find_layout = QtWidgets.QVBoxLayout()
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    prompt_input.textChanged.connect(lambda: search_layers(prompt_input))  # Trigger search on text change
    find_layout.addWidget(prompt_input)
    text_fields_layout.addLayout(find_layout)
    main_layout.addLayout(text_fields_layout)

    navigation_layout = QtWidgets.QHBoxLayout()
    prev_button = QtWidgets.QPushButton("<")
    prev_button.clicked.connect(lambda: navigate(-1))  # Navigate to previous item
    navigation_layout.addWidget(prev_button)

    next_button = QtWidgets.QPushButton(">")
    next_button.clicked.connect(lambda: navigate(1))  # Navigate to next item
    navigation_layout.addWidget(next_button)
    main_layout.addLayout(navigation_layout)

    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(status_display)

    main_layout.addStretch()

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)
    
    substance_painter.event.DISPATCHER.connect(substance_painter.event.LayerStacksModelDataChanged, update_layer_stack)
    
    print("[Python] UI created successfully.")

def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()
    print("[Python] Plugin initialized.")

def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    print("[Python] Plugin closed.")
    
if __name__ == "__main__":
    initialize_plugin()