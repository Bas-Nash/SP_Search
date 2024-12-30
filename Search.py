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
replace_input = None
count_display = None
replace_button = None
replace_all_button = None
current_index = -1
matched_layers = []

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
    print(f"[Python] Navigated to layer: {current_layer.get_name()}")
    update_button_states()

# Function to handle layer matching and selection
def handle_text_change(user_prompt):
    global matched_layers, current_index

    user_prompt = user_prompt.strip().lower()  # Convert input to lowercase
    if not user_prompt:  # Ignore empty or whitespace-only inputs
        substance_painter.layerstack.set_selected_nodes([])
        count_display.setText("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
        matched_layers = []
        current_index = -1
        update_button_states()
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
        fill_count = sum(1 for layer in matched_layers if layer.get_type() == substance_painter.layerstack.NodeType.FillLayer)
        paint_count = sum(1 for layer in matched_layers if layer.get_type() == substance_painter.layerstack.NodeType.PaintLayer)
        folder_count = sum(1 for layer in matched_layers if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer)

        count_display.setText(f"Fill Layers: {fill_count}, Paint Layers: {paint_count}, Group Folders: {folder_count}")
        substance_painter.layerstack.set_selected_nodes(matched_layers)  # Select all matched layers initially
        print(f"[Python] Selected all matching layers. Total: {len(matched_layers)}")
    else:
        substance_painter.layerstack.set_selected_nodes([])
        count_display.setText("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
        matched_layers = []
        current_index = -1

    update_button_states()

# Function to replace the name of the currently selected layer
def replace_current_layer():
    global current_index, matched_layers

    if not replace_input or current_index == -1 or not matched_layers:
        print("[Python] No active layer selected or replace field not initialized.")
        return

    replacement_text = replace_input.text().strip()
    if not replacement_text:
        print("[Python] Replacement field must be filled.")
        return

    current_layer = matched_layers[current_index]
    current_layer.set_name(replacement_text)
    print(f"[Python] Replaced current layer name with '{replacement_text}'.")

# Function to replace all matched layer names
def replace_name():
    if not prompt_input or not replace_input:
        print("[Python] Text inputs are not initialized.")
        return

    user_prompt = prompt_input.text().strip().lower()
    replacement_text = replace_input.text().strip()

    if not user_prompt or not replacement_text:
        print("[Python] Both find and replace fields must be filled.")
        return

    stack = substance_painter.textureset.get_active_stack()
    if not stack:
        print("No active texture set stack found.")
        return

    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    all_found = []

    for layer in all_layers:
        all_found.extend(find_layer(layer, user_prompt))

    if all_found:
        for layer in all_found:
            print(f"Replacing '{layer.get_name()}' with '{replacement_text}'.")
            layer.set_name(replacement_text)

        print(f"[Python] Replaced {len(all_found)} layer(s) with the new name '{replacement_text}'.")
    else:
        print(f"[Python] No layers found with the name starting with '{user_prompt}'.")

# Function to update the state of the Replace and Replace All buttons
def update_button_states():
    global matched_layers, replace_button, replace_all_button

    stack = substance_painter.textureset.get_active_stack()  # Get the active stack
    if not stack:
        print("[Python] No active texture set stack found.")
        return

    selected_nodes = substance_painter.layerstack.get_selected_nodes(stack)  # Pass the stack to get_selected_nodes()

    if len(selected_nodes) == 1:
        replace_button.setEnabled(True)
        replace_all_button.setEnabled(False)
    elif len(selected_nodes) > 1:
        replace_button.setEnabled(False)
        replace_all_button.setEnabled(True)
    else:
        replace_button.setEnabled(False)
        replace_all_button.setEnabled(False)

# Define the plugin's main functionality
def start_plugin():
    if not plugin_widgets:  # Check if the UI is already created
        create_ui()
    else:
        print("[Python] UI is already created.")

def create_ui():
    global prompt_input, replace_input, count_display, replace_button, replace_all_button  # Access the global variables

    if prompt_input is not None:
        print("[Python] UI is already created.")
        return

    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Name Search")
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # Top buttons layout
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

    # Main UI layout for Layers functionality
    text_fields_layout = QtWidgets.QHBoxLayout()

    find_layout = QtWidgets.QVBoxLayout()
    find_label = QtWidgets.QLabel("Find")
    find_label.setAlignment(QtCore.Qt.AlignLeft)
    find_layout.addWidget(find_label)

    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    prompt_input.textChanged.connect(handle_text_change)
    find_layout.addWidget(prompt_input)

    text_fields_layout.addLayout(find_layout)

    divider = QtWidgets.QFrame()
    divider.setFrameShape(QtWidgets.QFrame.VLine)
    divider.setFrameShadow(QtWidgets.QFrame.Sunken)
    text_fields_layout.addWidget(divider)

    replace_layout = QtWidgets.QVBoxLayout()
    replace_label = QtWidgets.QLabel("Replace")
    replace_label.setAlignment(QtCore.Qt.AlignLeft)
    replace_layout.addWidget(replace_label)

    replace_input = QtWidgets.QLineEdit()
    replace_input.setPlaceholderText("Enter replacement text...")
    replace_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    replace_layout.addWidget(replace_input)

    text_fields_layout.addLayout(replace_layout)
    main_layout.addLayout(text_fields_layout)

    navigation_layout = QtWidgets.QHBoxLayout()
    prev_button = QtWidgets.QPushButton("<")
    prev_button.clicked.connect(lambda: navigate_layers(-1))  # Navigate to previous layer
    navigation_layout.addWidget(prev_button)

    next_button = QtWidgets.QPushButton(">")
    next_button.clicked.connect(lambda: navigate_layers(1))  # Navigate to next layer
    navigation_layout.addWidget(next_button)
    main_layout.addLayout(navigation_layout)

    replace_buttons_layout = QtWidgets.QHBoxLayout()
    replace_button = QtWidgets.QPushButton("Replace")
    replace_button.clicked.connect(replace_current_layer)  # Replace current layer name
    replace_buttons_layout.addWidget(replace_button)

    replace_all_button = QtWidgets.QPushButton("Replace All")
    replace_all_button.clicked.connect(replace_name)  # Attach the replace_name function
    replace_buttons_layout.addWidget(replace_all_button)

    main_layout.addLayout(replace_buttons_layout)

    toggle_button = QtWidgets.QPushButton("Hide Stats")
    toggle_button.setCheckable(True)
    toggle_button.clicked.connect(lambda: toggle_counts_visibility(toggle_button))
    main_layout.addWidget(toggle_button)

    count_layout = QtWidgets.QVBoxLayout()
    count_display = QtWidgets.QLabel("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
    count_display.setAlignment(QtCore.Qt.AlignCenter)
    count_layout.addWidget(count_display)
    main_layout.addLayout(count_layout)
    main_layout.addStretch()

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)

    update_button_states()  # Ensure buttons are correctly initialized
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
        # Implement functionality for showing Effects-related UI elements

def toggle_counts_visibility(button):
    global count_display
    if count_display.isVisible():
        count_display.setVisible(False)
        button.setText("Show Stats")
    else:
        count_display.setVisible(True)
        button.setText("Hide Stats")

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
