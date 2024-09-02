import dearpygui.dearpygui as dpg

from Juneau.project.config_file import ConfigFile

import Juneau.config as consts

class SettingsWindow:
    def __init__(self, config_file : ConfigFile) -> None:
        self.window = dpg.add_window(label="Settings")

        self.config : ConfigFile = config_file

        with dpg.group(horizontal=True, parent=self.window):
            dpg.add_text("Game Directory Path")
            dpg.add_input_text(
                default_value = self.config.get_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH) \
                    if self.config.has_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH) else None,
                callback = lambda _s, a, _u: self.config.set_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH, a)
            )

        with dpg.group(horizontal=True, parent=self.window):
            dpg.add_text("Open game directory on startup?")
            dpg.add_checkbox(
                default_value = self.config.get_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP) \
                    if self.config.has_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP) else None,
                callback = lambda _s, a, _u: self.config.set_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP, a)
            )

        with dpg.group(horizontal=True, parent=self.window):
            dpg.add_text("Is game directory HPR?")
            dpg.add_checkbox(
                default_value = self.config.get_config_option(consts.CONFIG_OPTION_IS_HPR) \
                    if self.config.has_config_option(consts.CONFIG_OPTION_IS_HPR) else None,
                callback = lambda _s, a, _u: self.config.set_config_option(consts.CONFIG_OPTION_IS_HPR, a)
            )

    def show(self):
        dpg.show_item(self.window)