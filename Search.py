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

def switch_view(view, layers_button, effects_button):
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
    global plugin_widgets  # Access the global variables

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
    #prompt_input.textChanged.connect()
    find_layout.addWidget(prompt_input)
    text_fields_layout.addLayout(find_layout)
    main_layout.addLayout(text_fields_layout)

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

# Function to initialize the plugin
def initialize_plugin():
    print("[Python] Initializing plugin...")
    create_ui()
    print("[Python] Plugin initialized.")

# Function to close the plugin
def close_plugin():
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    print("[Python] Plugin closed.")

if __name__ == "__main__":
    initialize_plugin()
