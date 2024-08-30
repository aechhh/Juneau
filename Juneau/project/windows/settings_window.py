import dearpygui.dearpygui as dpg

from Juneau.project.config_file import ConfigFile

class SettingsWindow:
    def __init__(self, config_file : ConfigFile) -> None:
        self.window = dpg.add_window(label="Settings")

        self.config : ConfigFile = config_file

    def show(self):
        dpg.show_item(self.window)