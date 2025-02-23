import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
import substance_painter.event
from PySide2 import QtGui, QtWidgets, QtCore

plugin_widgets = []
prompt_input = None
current_index = -1
matched_items = []
status_display = None
current_view = "layers"
manual_selection = True
root_layers = []

def update_root_layers():
    global root_layers
    stack = substance_painter.textureset.get_active_stack()
    if stack:
        root_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    else:
        root_layers = []

def find_effects(layer, substring):
    found_effects = []
    effects = layer.content_effects() + (layer.mask_effects() if layer.has_mask() else [])

    for effect in effects:
        if substring.lower() in effect.get_name().lower():
            found_effects.append((effect, id(effect)))

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_effects.extend(find_effects(sub_layer, substring))
    return found_effects

def find_layer(layer, substring):
    found_layers = []
    if substring.lower() in layer.get_name().lower():
        found_layers.append(layer)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_layers.extend(find_layer(sub_layer, substring))

    return found_layers

def select_effect(effect):
    substance_painter.layerstack.set_selected_nodes([effect])
    print(f"[Python] Selected effect: {effect.get_name()} with ID: {id(effect)}")

def navigate_items(direction):
    global current_index, matched_items, manual_selection

    print(f"[DEBUG] Navigating: Current Index = {current_index}, Matched Items = {len(matched_items)}")

    if not matched_items:
        print("[Python] No items to navigate.")
        return

    manual_selection = True
    current_index += direction

    # Ensure looping behavior
    if current_index < 0:
        current_index = len(matched_items) - 1
    elif current_index >= len(matched_items):
        current_index = 0

    current_uid, _ = matched_items[current_index]

    # Retrieve the actual node using UID
    current_item = substance_painter.layerstack.LayerNode(current_uid)

    # Debug print: Verify new current_index and selected item
    print(f"[DEBUG] New Index: {current_index}, Selected Item: {current_item.get_name()} (UID: {current_uid})")

    if current_view == "effects":
        select_effect(current_item)
    else:
        substance_painter.layerstack.set_selected_nodes([current_item])

    update_status_display()


def update_status_display():
    global status_display, current_index, matched_items

    if status_display is None:
        return

    if matched_items:
        status_display.setText(f"{current_index + 1} out of {len(matched_items)}")
    else:
        status_display.setText("0 out of 0")

def handle_text_change(user_prompt):
    global matched_items, current_index, current_view, manual_selection

    update_root_layers()

    user_prompt = user_prompt.strip().lower()
    if not user_prompt:
        substance_painter.layerstack.set_selected_nodes([])
        matched_items = []
        current_index = -1
        update_status_display()
        print("[Python] Empty prompt. Waiting for user input.")
        return

    previous_uid = None
    if current_index >= 0 and current_index < len(matched_items):
        previous_uid, _ = matched_items[current_index]  # Store previously selected UID

    matched_items = []

    if current_view == "layers":
        for layer in root_layers:
            found_layers = find_layer(layer, user_prompt)
            matched_items.extend([(layer.uid(), layer) for layer in found_layers])  # Store UID
    elif current_view == "effects":
        for layer in root_layers:
            found_effects = find_effects(layer, user_prompt)
            matched_items.extend([(effect.uid(), effect) for effect, _ in found_effects])  # Store UID

    print(f"[DEBUG] Matched Items ({len(matched_items)}): {[ (uid, item.get_name()) for uid, item in matched_items]}")

    if matched_items:
        # Try to restore the previous selection if it still exists in matched_items
        new_index = next((i for i, (uid, _) in enumerate(matched_items) if uid == previous_uid), 0)
        current_index = new_index

        selected_uid, selected_item = matched_items[current_index]
        if current_view == "effects":
            select_effect(selected_item)
        else:
            substance_painter.layerstack.set_selected_nodes([selected_item])

        update_status_display()
    else:
        substance_painter.layerstack.set_selected_nodes([])
        matched_items = []
        current_index = -1
        update_status_display()
        print("[Python] No matches found for input.")

def update_layer_stack(event):
    update_root_layers()
    print("[Python] Layer stack updated. Refreshing matched items.")
    if prompt_input:
        handle_text_change(prompt_input.text())

def switch_view(view, layers_button, effects_button):
    global current_view, current_index, matched_items
    current_view = view
    if view == "layers":
        layers_button.setChecked(True)
        layers_button.setEnabled(False)
        effects_button.setChecked(True)
        effects_button.setEnabled(True)
        print("[Python] Switched to Layers view.")
    elif view == "effects":
        layers_button.setChecked(True)
        layers_button.setEnabled(True)
        effects_button.setChecked(False)
        effects_button.setEnabled(False)
        print("[Python] Switched to Effects view.")
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
