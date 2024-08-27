import dearpygui.dearpygui as dpg

class SettingsWindow():
    def __init__(self) -> None:
        self.window = dpg.add_window(label="Settings")
