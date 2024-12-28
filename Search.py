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


# Define the plugin's main functionality
def start_plugin():
    if not plugin_widgets:  # Check if the UI is already created
        create_ui()
    else:
        print("[Python] UI is already created.")

def handle_text_change(user_prompt):
    user_prompt = user_prompt.strip().lower()  # Convert input to lowercase
    if not user_prompt:  # Ignore empty or whitespace-only inputs
        substance_painter.layerstack.set_selected_nodes([])
        count_display.setText("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
        print("[Python] Empty prompt. Waiting for user input.")
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
        fill_count = sum(1 for layer in all_found if layer.get_type() == substance_painter.layerstack.NodeType.FillLayer)
        paint_count = sum(1 for layer in all_found if layer.get_type() == substance_painter.layerstack.NodeType.PaintLayer)
        folder_count = sum(1 for layer in all_found if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer)

        # Update the UI with the counts
        count_display.setText(f"Fill Layers: {fill_count}, Paint Layers: {paint_count}, Group Folders: {folder_count}")

        # Use set_selected_nodes to select the found layers
        substance_painter.layerstack.set_selected_nodes(all_found)
        for layer in all_found:
            print(f"Selected and marked layer named '{user_prompt}': {layer.get_name()}")
    else:
        substance_painter.layerstack.set_selected_nodes([])
        count_display.setText("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
        print(f"Layer named '{user_prompt}' not found.")

        # Deselect any currently selected layers
        

# Define the function to close the plugin UI

def create_ui():
    global prompt_input, count_display  # Access the global variables

    if prompt_input is not None:
        print("[Python] UI is already created.")
        return

    # Create a widget to serve as the main window
    main_widget = QtWidgets.QWidget()
    main_widget.setWindowTitle("Name Search")

    # Create a vertical layout for the window
    main_layout = QtWidgets.QVBoxLayout(main_widget)

    # Create a horizontal layout for the text fields and their labels
    text_fields_layout = QtWidgets.QHBoxLayout()

    # Create a vertical layout for the "Find" section
    find_layout = QtWidgets.QVBoxLayout()
    find_label = QtWidgets.QLabel("Find")
    find_label.setAlignment(QtCore.Qt.AlignLeft)  # Align the label to the left
    find_layout.addWidget(find_label)

    # Add the prompt input field
    prompt_input = QtWidgets.QLineEdit()
    prompt_input.setPlaceholderText("Type your prompt here...")
    prompt_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    prompt_input.textChanged.connect(handle_text_change)
    find_layout.addWidget(prompt_input)

    # Add the "Find" section to the horizontal layout
    text_fields_layout.addLayout(find_layout)

    # Add a vertical line divider
    divider = QtWidgets.QFrame()
    divider.setFrameShape(QtWidgets.QFrame.VLine)
    divider.setFrameShadow(QtWidgets.QFrame.Sunken)
    text_fields_layout.addWidget(divider)

    # Create a vertical layout for the "Replace" section
    replace_layout = QtWidgets.QVBoxLayout()
    replace_label = QtWidgets.QLabel("Replace")
    replace_label.setAlignment(QtCore.Qt.AlignLeft)  # Align the label to the left
    replace_layout.addWidget(replace_label)

    # Add the replacement input field
    replace_input = QtWidgets.QLineEdit()
    replace_input.setPlaceholderText("Enter replacement text...")
    replace_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    replace_layout.addWidget(replace_input)

    # Add the "Replace" section to the horizontal layout
    text_fields_layout.addLayout(replace_layout)

    # Add the text fields layout to the main layout
    main_layout.addLayout(text_fields_layout)

    # Create a horizontal layout for the navigation buttons ("<" and ">")
    navigation_layout = QtWidgets.QHBoxLayout()

    # Add "<" button
    prev_button = QtWidgets.QPushButton("<")
    navigation_layout.addWidget(prev_button)

    # Add ">" button
    next_button = QtWidgets.QPushButton(">")
    navigation_layout.addWidget(next_button)

    # Add the navigation layout to the main layout
    main_layout.addLayout(navigation_layout)

    # Create a horizontal layout for the replace buttons ("Replace" and "Replace All")
    replace_buttons_layout = QtWidgets.QHBoxLayout()

    # Add "Replace" button
    replace_button = QtWidgets.QPushButton("Replace")
    replace_buttons_layout.addWidget(replace_button)

    # Add "Replace All" button
    replace_all_button = QtWidgets.QPushButton("Replace All")
    replace_buttons_layout.addWidget(replace_all_button)

    # Add the replace buttons layout to the main layout
    main_layout.addLayout(replace_buttons_layout)


    # Create a toggle button to show/hide counts
    toggle_button = QtWidgets.QPushButton("Hide Stats")
    toggle_button.setCheckable(True)  # Enable toggling
    toggle_button.clicked.connect(lambda: toggle_counts_visibility(toggle_button))
    main_layout.addWidget(toggle_button)

    # Create a collapsible UI element for counts
    count_layout = QtWidgets.QVBoxLayout()

    # Display for counts
    count_display = QtWidgets.QLabel("Fill Layers: 0, Paint Layers: 0, Group Folders: 0")
    count_display.setAlignment(QtCore.Qt.AlignCenter)  # Center-align the label
    count_layout.addWidget(count_display)

    # Add the count display layout directly
    main_layout.addLayout(count_layout)

    # Add a spacer to push elements to the center of the window
    main_layout.addStretch()

    # Show the widget in Substance Painter
    substance_painter.ui.add_dock_widget(main_widget)

    # Keep track of the widget so it can be closed later
    plugin_widgets.append(main_widget)

    print("[Python] UI created successfully.")

def toggle_counts_visibility(button):
    """Toggle the visibility of count display."""
    # Toggle the visibility of the `count_display` only
    global count_display  # Access the global count_display widget
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
    

# Create the UI for the plugin

def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()  # Ensure the UI is created at plugin initialization
    print("[Python] Plugin initialized.")

if __name__ == "__main__":
    initialize_plugin()
