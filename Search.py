import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

# List to store plugin widgets
plugin_widgets = []

# Variables to store text input widgets
prompt_input = None
current_index = -1
matched_layers = []
status_display = None

# Function to search layers by prefix
def find_layer(layer, prefix):
    found_layers = []
    layer_name = layer.get_name().lower()  # Convert to lowercase
    if layer_name.startswith(prefix.lower()):  # Check if the name starts with the prefix
        found_layers.append(layer)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_layers.extend(find_layer(sub_layer, prefix))
    return found_layers

# Function to navigate layers
def navigate_layers(direction):
    global current_index, matched_layers

    if not matched_layers:
        print("[Python] No layers to navigate.")
        return

    current_index += direction

    # Wrap around if we go out of bounds
    if current_index < 0:
        current_index = len(matched_layers) - 1
    elif current_index >= len(matched_layers):
        current_index = 0

    # Select the current layer
    current_layer = matched_layers[current_index]
    substance_painter.layerstack.set_selected_nodes([current_layer])
    update_status_display()
    print(f"[Python] Navigated to layer: {current_layer.get_name()}")

# Function to handle layer matching and selection
def handle_text_change(user_prompt):
    global matched_layers, current_index

    user_prompt = user_prompt.strip().lower()  # Convert input to lowercase
    if not user_prompt:  # Ignore empty or whitespace-only inputs
        substance_painter.layerstack.set_selected_nodes([])
        matched_layers = []
        current_index = -1
        update_status_display()
        print("[Python] Empty prompt. Waiting for user input.")
        return

    stack = substance_painter.textureset.get_active_stack()
    if not stack:
        print("No active texture set stack found.")
        return

    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    matched_layers = []

    for layer in all_layers:
        matched_layers.extend(find_layer(layer, user_prompt))

    if matched_layers:
        current_index = 0  # Reset to the first match
        current_layer = matched_layers[current_index]
        substance_painter.layerstack.set_selected_nodes([current_layer])
        print(f"[Python] Selected first matching layer: {current_layer.get_name()}")
    else:
        substance_painter.layerstack.set_selected_nodes([])
        matched_layers = []
        current_index = -1

    update_status_display()

# Function to update the status display
def update_status_display():
    global status_display, current_index, matched_layers

    if status_display is None:
        return

    if matched_layers:
        status_display.setText(f"{current_index + 1} out of {len(matched_layers)}")
    else:
        status_display.setText("0 out of 0")

# Function to log effects from all layers, including layers in folders
def log_layer_effects_recursive(layer):
    effects = layer.content_effects()
    if effects:
        print(f"[Python] Layer: {layer.get_name()} has effects:")
        for effect in effects:
            print(f"    - {effect.get_name()}")
    else:
        print(f"[Python] Layer: {layer.get_name()} has no effects.")

    if layer.has_mask:
        mask_effects = layer.mask_effects()
        if mask_effects:
            print(f"[Python] Layer: {layer.get_name()} has mask effects:")
            for effect in mask_effects:
                print(f"    - {effect.get_name()}")

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            log_layer_effects_recursive(sub_layer)

def log_layer_effects():
    stack = substance_painter.textureset.get_active_stack()
    if not stack:
        print("[Python] No active texture set stack found.")
        return

    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    print("[Python] Listing effects in all layers:")

    for layer in all_layers:
        log_layer_effects_recursive(layer)

# Define the plugin's main functionality
def start_plugin():
    if not plugin_widgets:  # Check if the UI is already created
        create_ui()
    else:
        print("[Python] UI is already created.")

def create_ui():
    global prompt_input, status_display  # Access the global variables

    if prompt_input is not None:
        print("[Python] UI is already created.")
        return

    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Name Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    top_buttons_layout = QtWidgets.QHBoxLayout()

    layers_button = QtWidgets.QPushButton("Layers")
    layers_button.setCheckable(True)
    layers_button.setChecked(True)  # Default to Layers view
    layers_button.setEnabled(False)  # Grey out the Layers button by default
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
    prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    prompt_input.textChanged.connect(handle_text_change)
    find_layout.addWidget(prompt_input)

    text_fields_layout.addLayout(find_layout)
    main_layout.addLayout(text_fields_layout)

    navigation_layout = QtWidgets.QHBoxLayout()
    prev_button = QtWidgets.QPushButton("<")
    prev_button.clicked.connect(lambda: navigate_layers(-1))  # Navigate to previous layer
    navigation_layout.addWidget(prev_button)

    next_button = QtWidgets.QPushButton(">")
    next_button.clicked.connect(lambda: navigate_layers(1))  # Navigate to next layer
    navigation_layout.addWidget(next_button)
    main_layout.addLayout(navigation_layout)

    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(status_display)

    main_layout.addStretch()

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)

    print("[Python] UI created successfully.")

def switch_view(view, layers_button, effects_button):
    if view == "layers":
        layers_button.setChecked(True)
        layers_button.setEnabled(False)  # Grey out the Layers button
        effects_button.setChecked(False)
        effects_button.setEnabled(True)  # Enable the Effects button
        print("[Python] Switched to Layers view.")
        # Implement functionality for showing Layers-related UI elements
    elif view == "effects":
        layers_button.setChecked(False)
        layers_button.setEnabled(True)  # Enable the Layers button
        effects_button.setChecked(True)
        effects_button.setEnabled(False)  # Grey out the Effects button
        print("[Python] Switched to Effects view.")
        log_layer_effects()  # Call function to log effects

def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()

def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()
    print("[Python] Plugin initialized.")

if __name__ == "__main__":
    initialize_plugin()
