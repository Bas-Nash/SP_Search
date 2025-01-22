import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
import substance_painter.event
from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

# List to store plugin widgets
plugin_widgets = []

# Variables to store text input widgets
prompt_input = None
current_index = -1
matched_items = []
status_display = None
current_view = "layers"
manual_selection = False  # Track manual selections

# Function to search effects with substring match
def find_effects(layer, substring):
    found_effects = []
    effects = layer.content_effects() + (layer.mask_effects() if layer.has_mask() else [])

    for effect in effects:
        if substring.lower() in effect.get_name().lower():  # Match effect name with substring
            found_effects.append((effect, id(effect)))  # Store effect with its unique ID

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_effects.extend(find_effects(sub_layer, substring))
    return found_effects

# Function to search layers with substring match
def find_layer(layer, substring):
    found_layers = []
    if substring.lower() in layer.get_name().lower():
        found_layers.append(layer)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_layers.extend(find_layer(sub_layer, substring))

    return found_layers

# Function to handle input for layer or effect matching
def select_effect(effect):
    substance_painter.layerstack.set_selected_nodes([effect])
    print(f"[Python] Selected effect: {effect.get_name()} with ID: {id(effect)}")

# Function to navigate items (layers or effects)
def navigate_items(direction):
    global current_index, matched_items, manual_selection
    if not matched_items:
        print("[Python] No items to navigate.")
        return

    manual_selection = True  # Mark that navigation is manual
    current_index += direction

    # Wrap around if we go out of bounds
    if current_index < 0:
        current_index = len(matched_items) - 1
    elif current_index >= len(matched_items):
        current_index = 0

    # Select the current item
    current_item, _ = matched_items[current_index]
    if current_view == "effects":
        select_effect(current_item)
    else:
        substance_painter.layerstack.set_selected_nodes([current_item])
    update_status_display()
    if hasattr(current_item, "get_name"):
        print(f"[Python] Navigated to item: {current_item.get_name()}")

# Function to update the status display
def update_status_display():
    global status_display, current_index, matched_items

    if status_display is None:
        return

    if matched_items:
        status_display.setText(f"{current_index + 1} out of {len(matched_items)}")
    else:
        status_display.setText("0 out of 0")

# Function to handle text changes in the input box
def handle_text_change(user_prompt):
    global matched_items, current_index, current_view, manual_selection

    user_prompt = user_prompt.strip().lower()  # Convert input to lowercase
    if not user_prompt:  # Ignore empty or whitespace-only inputs
        substance_painter.layerstack.set_selected_nodes([])
        matched_items = []
        current_index = -1
        update_status_display()
        print("[Python] Empty prompt. Waiting for user input.")
        return

    stack = substance_painter.textureset.get_active_stack()
    if not stack:
        print("[Python] No active texture set stack found.")
        return

    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    matched_items = []

    if current_view == "layers":
        for layer in all_layers:
            matched_items.extend([(layer, id(layer)) for layer in find_layer(layer, user_prompt)])
    elif current_view == "effects":
        for layer in all_layers:
            matched_items.extend(find_effects(layer, user_prompt))

    if matched_items:
        if not manual_selection:  # Only auto-select if no manual selection
            current_index = 0  # Reset to the first match
            first_item, _ = matched_items[current_index]
            if current_view == "effects":
                select_effect(first_item)
            else:
                substance_painter.layerstack.set_selected_nodes([first_item])
        update_status_display()
    else:
        substance_painter.layerstack.set_selected_nodes([])
        matched_items = []
        current_index = -1
        update_status_display()

    # Reset manual selection for future inputs
    manual_selection = False
        
def update_layer_stack(event):
    global current_index, matched_items, manual_selection

    if manual_selection:
        print("[Python] Manual selection detected. Skipping update.")
        return

    print("[Python] Layer stack updated. Refreshing matched items.")
    
    if prompt_input:
        user_prompt = prompt_input.text().strip().lower()  # Get current user input
        if user_prompt:  # Only refresh if there's an active search prompt
            stack = substance_painter.textureset.get_active_stack()
            if not stack:
                print("[Python] No active texture set stack found during update.")
                return

            all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
            new_matched_items = []

            # Recalculate matched items based on the current view
            if current_view == "layers":
                for layer in all_layers:
                    new_matched_items.extend([(layer, id(layer)) for layer in find_layer(layer, user_prompt)])
            elif current_view == "effects":
                for layer in all_layers:
                    new_matched_items.extend(find_effects(layer, user_prompt))

            # Update matched items and auto-select the first match
            matched_items = new_matched_items
            if matched_items:
                current_index = 0
                first_item, _ = matched_items[current_index]
                if current_view == "effects":
                    select_effect(first_item)
                else:
                    substance_painter.layerstack.set_selected_nodes([first_item])
            else:
                matched_items = []
                current_index = -1

            # Trigger text change handling to update UI and logic
            handle_text_change(user_prompt)
        else:
            matched_items = []
            current_index = -1
            substance_painter.layerstack.set_selected_nodes([])
            update_status_display()
            print("[Python] No user input, cleared matched items.")


# Modified switch_view to trigger handle_text_change
def switch_view(view, layers_button, effects_button):
    global current_view
    current_view = view

    if view == "layers":
        layers_button.setChecked(True)
        layers_button.setEnabled(False)  # Grey out the Layers button
        effects_button.setChecked(False)
        effects_button.setEnabled(True)  # Enable the Effects button
        print("[Python] Switched to Layers view.")
    elif view == "effects":
        layers_button.setChecked(False)
        layers_button.setEnabled(True)  # Enable the Layers button
        effects_button.setChecked(True)
        effects_button.setEnabled(False)  # Grey out the Effects button
        print("[Python] Switched to Effects view.")

    # Trigger handle_text_change to refresh matched items
    if prompt_input:
        handle_text_change(prompt_input.text())

# Function to close the plugin
def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()

    # Disconnect the layer stack update event
    substance_painter.event.DISPATCHER.disconnect(substance_painter.event.LayerStacksModelDataChanged, update_layer_stack)

# Function to initialize the plugin
def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()
    print("[Python] Plugin initialized.")

# Function to start the plugin
def start_plugin():
    if not plugin_widgets:  # Check if the UI is already created
        create_ui()
    else:
        print("[Python] UI is already created.")

# Function to create the UI
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
    prev_button.clicked.connect(lambda: navigate_items(-1))  # Navigate to previous item
    navigation_layout.addWidget(prev_button)

    next_button = QtWidgets.QPushButton(">")
    next_button.clicked.connect(lambda: navigate_items(1))  # Navigate to next item
    navigation_layout.addWidget(next_button)
    main_layout.addLayout(navigation_layout)

    status_display = QtWidgets.QLabel("0 out of 0")
    status_display.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(status_display)

    main_layout.addStretch()

    substance_painter.ui.add_dock_widget(main_widget)
    plugin_widgets.append(main_widget)

    # Connect the layer stack update event
    substance_painter.event.DISPATCHER.connect(substance_painter.event.LayerStacksModelDataChanged, update_layer_stack)

    print("[Python] UI created successfully.")

if __name__ == "__main__":
    initialize_plugin()
