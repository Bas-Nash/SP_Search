import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtWidgets, QtCore

plugin_widgets = []
current_view = "layers"

def find_items(layer, substring):
    found_effects = []
    found_layers = []
    if substring.lower() in layer.get_name().lower():
        found_layers.append(layer)
    effects = layer.content_effects() + (layer.mask_effects() if layer.has_mask() else [])
    for effect in effects:
        if substring.lower() in effect.get_name().lower():
            found_effects.append(effect)
    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            sub_effects, sub_layers = find_items(sub_layer, substring)
            found_effects.extend(sub_effects)
            found_layers.extend(sub_layers)
    return found_effects, found_layers

def print_matched_items(layers, effects):
    global current_view
    print("[Python] Matched Items:")
    if current_view == "layers":
        for layer in layers:
            print(f" - {layer.get_name()} (Layer)")
    elif current_view == "effects":
        for effect in effects:
            print(f" - {effect.get_name()} (Effect)")

def search_layers(prompt_input):
    substring = prompt_input.text().strip()
    if not substring:
        print("[Python] No search term provided.")
        return
    
    found_layers = []
    found_effects = []
    stack = substance_painter.textureset.get_active_stack()
    root_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    
    for layer in root_layers:
        effects, layers = find_items(layer, substring)
        found_layers.extend(layers)
        found_effects.extend(effects)
    
    print_matched_items(found_layers, found_effects)

def switch_view(view, layers_button, effects_button):
    global current_view
    current_view = view
    if view == "layers":
        layers_button.setChecked(True)
        layers_button.setEnabled(False)
        effects_button.setChecked(True)
        effects_button.setEnabled(True)
    elif view == "effects":
        layers_button.setChecked(True)
        layers_button.setEnabled(True)
        effects_button.setChecked(False)
        effects_button.setEnabled(False)

def create_ui():
    global plugin_widgets

    if plugin_widgets:
        print("[Python] UI is already created.")
        return
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)
    
    text_fields_layout = QtWidgets.QHBoxLayout()
    find_layout = QtWidgets.QVBoxLayout()
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    find_layout.addWidget(prompt_input)
    
    search_button = QtWidgets.QPushButton("Search")
    search_button.clicked.connect(lambda: search_layers(prompt_input))
    find_layout.addWidget(search_button)
    
    text_fields_layout.addLayout(find_layout)
    main_layout.addLayout(text_fields_layout)

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

    navigation_layout = QtWidgets.QHBoxLayout()
    prev_button = QtWidgets.QPushButton("<")
    navigation_layout.addWidget(prev_button)
    next_button = QtWidgets.QPushButton(">")
    navigation_layout.addWidget(next_button)
    main_layout.addLayout(navigation_layout)

    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(status_display)

    main_layout.addStretch()

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)
    
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
