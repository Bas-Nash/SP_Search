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

# Variable to store the text input widget
prompt_input = None

# Function to search layers by name
def find_layer(layer, layer_name):
    found_layers = []
    if layer.get_name() == layer_name:
        found_layers.append(layer)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_layers.extend(find_layer(sub_layer, layer_name))
    return found_layers

# Define the plugin's main functionality
def start_plugin():
    if not plugin_widgets:  # Check if the UI is already created
        create_ui()
    else:
        print("[Python] UI is already created.")

def handle_text_change(user_prompt):
    if not user_prompt.strip():  # Ignore empty or whitespace-only inputs
        print("[Python] Empty prompt. Waiting for user input.")
        return

    stack = substance_painter.textureset.get_active_stack()

    if not stack:
        print("No active texture set stack found.")
        return

    # Search for the layers named in the prompt
    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    all_found = []

    for layer in all_layers:
        all_found.extend(find_layer(layer, user_prompt))

    if all_found:
        for layer in all_found:
            print(f"Found layer named '{user_prompt}': {layer.get_name()}")
    else:
        print(f"Layer named '{user_prompt}' not found.")

# Define the function to close the plugin UI

def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    

# Create the UI for the plugin

def create_ui():
    global prompt_input  # Access the global prompt_input variable

    if prompt_input is not None:
        print("[Python] UI is already created.")
        return

    # Create a widget to serve as the main window
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Prompt Plugin")

    # Create a vertical layout for the window
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # Add a label
    label = QtWidgets.QLabel("Enter your prompt:")
    label.setAlignment(QtCore.Qt.AlignCenter)  # Center-align the label
    main_layout.addWidget(label)

    # Add a text input field
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    # Connect the textChanged signal to handle_text_change
    prompt_input.textChanged.connect(handle_text_change)
    main_layout.addWidget(prompt_input)

    # Add a spacer to push elements to the center of the window
    main_layout.addStretch()

    # Show the widget in Substance Painter
    substance_painter.ui.add_dock_widget(main_widget)

    # Keep track of the widget so it can be closed later
    plugin_widgets.append(main_widget)

    print("[Python] UI created successfully.")
# Initialize the plugin

def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()  # Ensure the UI is created at plugin initialization
    print("[Python] Plugin initialized.")

if __name__ == "__main__":
    initialize_plugin()
