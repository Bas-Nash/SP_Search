import os
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset
import substance_painter.layerstack
from PySide2 import QtGui
from PySide2 import QtWidgets

plugin_widgets = []

def find_layer(layer, layer_name):
    found_layers = []

    if layer.get_name() == layer_name:
        found_layers.append(layer)

    if layer.get_type() == substance_painter.layerstack.NodeType.GroupLayer:
        for sub_layer in layer.sub_layers():
            found_layers.extend(find_layer(sub_layer, layer_name))

    return found_layers

def start_plugin():
    stack = substance_painter.textureset.get_active_stack()

    if not stack:
        print("No active texture set stack found.")
        return

    # Search for the layers named "test" in all layers recursively
    all_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    all_found = []

    for layer in all_layers:
        all_found.extend(find_layer(layer, "test"))

    if all_found:
        for layer in all_found:
            print(f"Found layer named 'test': {layer.get_name()}")
    else:
        print("Layer named 'test' not found.")

def close_plugin():
    """Cleans up the plugin by removing UI elements."""
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()

# Function to create the UI button
def create_ui():
    global plugin_widgets

    # Create a main window for the plugin
    window = substance_painter.ui.create_ui_element('Panel', "Layer Search Plugin", size=(200, 100))
    plugin_widgets.append(window)

    # Create a button inside the window
    button = substance_painter.ui.create_ui_element('Button', "Search Layers", parent=window)
    button.clicked.connect(start_plugin)

    # Add the panel to the Tools section of the UI
    substance_painter.ui.add_tool('Layer Search Plugin', window)

    return window

def start_plugin_with_ui():
    # Add the UI elements
    create_ui()

if __name__ == "__main__":
    start_plugin_with_ui()
