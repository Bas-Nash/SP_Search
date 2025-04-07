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

def uid(node):
    return node.uid() if hasattr(node, 'uid') else id(node)

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

def switch_view(view, layers_button, effects_button, status_display):
    global current_view, current_index
    current_view = view
    current_index = 0 if (found_layers if view == "layers" else found_effects) else -1
    
    layers_button.setChecked(view == "layers")
    layers_button.setEnabled(view != "layers")
    effects_button.setChecked(view == "effects")
    effects_button.setEnabled(view != "effects")
    
    select_current_item(status_display)

def update_search_results(substring, status_display):
    global found_layers, found_effects, current_index
    
    if not substring.strip():
        found_layers.clear()
        found_effects.clear()
        current_index = -1
        substance_painter.layerstack.set_selected_nodes([])  # Clear selection when empty
        update_status_display(status_display)
        return
    
    new_found_layers = []
    new_found_effects = []
    stack = substance_painter.textureset.get_active_stack()
    root_layers = substance_painter.layerstack.get_root_layer_nodes(stack)
    for layer in root_layers:
        effects, layers = find_items(layer, substring)
        new_found_layers.extend(layers)
        new_found_effects.extend(effects)
    
    if new_found_layers or new_found_effects:
        found_layers[:] = new_found_layers
        found_effects[:] = new_found_effects
        current_index = 0
        select_current_item(status_display, should_select=True)
        update_status_display(status_display)

def select_current_item(status_display, should_select=True):
    global current_index, found_layers, found_effects, current_view
    if should_select:
        if current_view == "layers" and found_layers:
            node = found_layers[current_index]
            substance_painter.layerstack.set_selected_nodes([node])
        elif current_view == "effects" and found_effects:
            node = found_effects[current_index]
            substance_painter.layerstack.set_selected_nodes([node])
        else:
            substance_painter.layerstack.set_selected_nodes([])  # Clear selection if nothing is found
    update_status_display(status_display)

def update_status_display(status_display):
    global current_index, found_layers, found_effects, current_view
    total_items = len(found_layers) if current_view == "layers" else len(found_effects)
    if total_items > 0 and current_index >= 0:
        status_display.setText(f"{current_index + 1} out of {total_items}")
    else:
        status_display.setText("0 out of 0")

def navigate(direction, status_display):
    global current_index, found_layers, found_effects, current_view
    if current_view == "layers" and found_layers:
        current_index = (current_index + direction) % len(found_layers)
    elif current_view == "effects" and found_effects:
        current_index = (current_index + direction) % len(found_effects)
    select_current_item(status_display, should_select=True)

def search_items(prompt_input, status_display):
    update_search_results(prompt_input.text().strip(), status_display)
    select_current_item(status_display, should_select=True)

def on_layer_stack_changed(*args):
    if plugin_widgets:
        prompt_input = plugin_widgets[0].findChild(QtWidgets.QLineEdit)
        status_display = plugin_widgets[0].findChild(QtWidgets.QLabel)
        if prompt_input and status_display:
            update_search_results(prompt_input.text().strip(), status_display)
            select_current_item(status_display, should_select=False)
    
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
