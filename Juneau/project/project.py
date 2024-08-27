import dearpygui.dearpygui as dpg

# used for filedialogs
import tkinter as tk
from tkinter import filedialog

import Juneau.config as consts

from Juneau.project.config_file import ConfigFile
from Juneau.project.object_aggregator import BNDLTree, get_bndl_tree
from Juneau.project.window_manager import WindowManager

from Juneau.formats.bndl.bndl import BNDL
from Juneau.format_parsing.parser.bndl_parser import fill_lazy_loaded_bndl
from Juneau.format_parsing.writer.bndl_writer import export_bndl_to_file

class Project():
    def __init__(self) -> None:
        self.config = ConfigFile(consts.CONFIG_FILEPATH, consts.CONFIG_FILENAME)

        self.root_window = None

        self.sidebar_window = None
        self.main_window = None

        self.popup = None

        self.window_manager : WindowManager = None

        self.is_hpr = False

        self.__init_app()


    def __init_app(self):
        dpg.create_context()
        dpg.configure_app(manual_callback_management=consts.DEBUGGING)

        with dpg.font_registry():
            default_font = dpg.add_font("data/NotoSansMono-SemiBold.ttf", 18)

        dpg.bind_font(default_font)

        self.__init_gui()

        dpg.create_viewport(title='Juneau', width=consts.WINDOW_WIDTH, height=consts.WINDOW_HEIGHT, small_icon=consts.ICON_FILENAME, large_icon=consts.ICON_FILENAME)
        dpg.set_viewport_vsync(False)
        dpg.setup_dearpygui()

        dpg.set_primary_window("Primary Window", True)
        dpg.show_viewport()

        if consts.DEBUGGING:
            # switch to loop to manually force dear py gui to running on a single thread, which allows proper debugging
            while dpg.is_dearpygui_running():
                jobs = dpg.get_callback_queue()
                dpg.run_callbacks(jobs)
                dpg.render_dearpygui_frame()
        else:
            dpg.start_dearpygui()

        dpg.destroy_context()

    def __dpg_startup_callback(self, _sender, _app_data, _user_data):
        if self.config.has_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH) \
             and self.config.has_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP) \
             and self.config.has_config_option(consts.CONFIG_OPTION_IS_HPR):

            if self.config.get_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP):
                self.__setup_sidebar(self.config.get_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH), self.config.get_config_option(consts.CONFIG_OPTION_IS_HPR), False)

    # --- Creating app GUI ---
    def __init_gui(self):
        with dpg.window(tag="Primary Window") as window:
            dpg.set_frame_callback(30, self.__dpg_startup_callback)

            self.root_window = window

            self.__init_menu_bar()

            with dpg.child_window(autosize_x=True, autosize_y=True):
                with dpg.group(horizontal=True, width=0):
                    self.sidebar_window = dpg.add_child_window(width=consts.SIDEBAR_WIDTH, height=-1)

                    self.main_window = dpg.add_child_window(autosize_x=True, height=-1, border=False)

                    self.window_manager = WindowManager(self.main_window)

    def __init_menu_bar(self):
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Open Game Directory", callback=self.__open_game_dir)

            with dpg.menu(label="Edit"):
                dpg.add_menu_item(label="Settings")

            with dpg.menu(label="View"):
                pass

            with dpg.menu(label="Debug Tools"):
                dpg.add_menu_item(label="Show Documentation", callback=lambda:dpg.show_tool(dpg.mvTool_Doc))
                dpg.add_menu_item(label="Show Debug", callback=lambda:dpg.show_tool(dpg.mvTool_Debug))
                dpg.add_menu_item(label="Show Style Editor", callback=lambda:dpg.show_tool(dpg.mvTool_Style))
                dpg.add_menu_item(label="Show Font Manager", callback=lambda:dpg.show_tool(dpg.mvTool_Font))
                dpg.add_menu_item(label="Show Item Registry", callback=lambda:dpg.show_tool(dpg.mvTool_ItemRegistry))

    # --- Menu bar function, open game directory and add files to the sidebar ---
    def __open_game_dir(self):
        # needed for file dialog popups
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        game_dir = filedialog.askdirectory(title="Select your Hot Pursuit directory")

        root.destroy()

        if game_dir is not None and not game_dir == "":
            self._game_dir_selection_confirmation(game_dir)

    def _game_dir_selection_confirmation(self, game_dir):
        self.popup = dpg.add_window(label="Confirmation", no_close=True, modal=False)

        dpg.add_text("Are you sure you want to use:", parent=self.popup)
        dpg.add_text(game_dir, bullet=True, parent=self.popup)
        dpg.add_text("as your game directory?", parent=self.popup)

        dpg.add_separator(parent=self.popup)
        open_on_startup_checkbox = dpg.add_checkbox(label="Open on Juneau startup", parent=self.popup)
        is_hpr_checkbox = dpg.add_checkbox(label="Is Hot Pursuit Remastered", parent=self.popup)

        def ok_callback():
            dpg.configure_item(self.popup, show=False)

            self.config.set_config_option(consts.CONFIG_OPTION_GAME_DIR_PATH, game_dir)
            self.config.set_config_option(consts.CONFIG_OPTION_OPEN_DIR_ON_STARTUP, dpg.get_value(open_on_startup_checkbox))
            self.config.set_config_option(consts.CONFIG_OPTION_IS_HPR, dpg.get_value(is_hpr_checkbox))

            self.__setup_sidebar(game_dir, dpg.get_value(is_hpr_checkbox), True)

        def browse_callback():
            dpg.configure_item(self.popup, show=False)

            self.__open_game_dir()

        with dpg.group(horizontal=True, parent=self.popup):
            dpg.add_button(label="OK", callback=ok_callback)
            dpg.add_button(label="Browse files", callback=browse_callback)

        root_window_width = dpg.get_item_width(self.root_window)
        root_window_height = dpg.get_item_height(self.root_window)
        # popup_width = dpg.get_item_width(self.popup)
        # popup_height = dpg.get_item_height(self.popup)
        # i dont like using constants here for spacing but this get item height/width aint working

        dpg.set_item_pos(self.popup, [int(root_window_width/2) - 150, int(root_window_height/2) - 100])


    # --- Sidebar directory setup ---
    def __setup_sidebar(self, game_dir : str, is_hpr, refresh_file_cache):
        self.is_hpr = is_hpr

        dpg.delete_item(self.popup)

        self.popup = dpg.add_window(modal=True, no_title_bar=True, no_close=True, show=True, width=1200, no_resize=True, no_scrollbar=True)
        dpg.add_text("Loading BNDL files from game directory", parent=self.popup)

        dpg.add_separator(parent=self.popup)

        progress_bar = dpg.add_progress_bar(parent=self.popup, user_data=[dpg.add_text(parent=self.popup)], width=-1)

        bndl_tree : BNDLTree = get_bndl_tree(game_dir, self.is_hpr, False, refresh_file_cache, progress_bar)

        dpg.hide_item(self.popup)

        dpg.delete_item(self.sidebar_window, children_only=True)

        with dpg.tree_node(label="Root", default_open=True, parent=self.sidebar_window) as root:
            self.__add_dir_to_sidebar(bndl_tree.root, root)

    def __add_dir_to_sidebar(self, bndl_node : BNDLTree.Node, parent_tag):
        # node is a directory
        if bndl_node.data == None:
            for directory in bndl_node.directories:
                with dpg.tree_node(label=directory, parent=parent_tag) as parent:
                    self.__add_dir_to_sidebar(bndl_node.directories[directory], parent)
        # node is a bndl
        for child_bndl_node in bndl_node.children:
            bndl = child_bndl_node.data

            bndl_tree_node = dpg.add_tree_node(label=bndl.file_name, parent=parent_tag)

            with dpg.item_handler_registry() as registry:
                dpg.add_item_toggled_open_handler(callback=self.__load_bndl_and_add_to_sidebar, user_data=[bndl, bndl_tree_node])

                dpg.bind_item_handler_registry(bndl_tree_node, registry)


    def __load_bndl_and_add_to_sidebar(self, _sender, _app_data, user_data):
        bndl : BNDL = user_data[0]
        bndl_tree_node = user_data[1]

        sidebar_needs_loading = bndl.lazy_loaded

        loading_popup = dpg.add_window(modal=True, no_title_bar=True)
        dpg.add_text("Unpacking and parsing resource entries", parent=loading_popup)

        fill_lazy_loaded_bndl(bndl)

        if sidebar_needs_loading:
            self.__add_items_to_bndl_tree_node(bndl, bndl_tree_node)

        dpg.hide_item(loading_popup)

    def __add_items_to_bndl_tree_node(self, bndl : BNDL, bndl_tree_node):
        for resource_type in bndl.objects:
            resource_type_name = bndl.objects[resource_type][0].get_resourse_type_name()

            with dpg.tree_node(label=resource_type_name, parent=bndl_tree_node):
                for res in bndl.objects[resource_type]:
                    if resource_type == consts.RESOURCE_ENTRY_TYPE_GENESYSINSTANCE:
                        label = f"{res.unpacked_object.obj_def.obj_name} (ID: {res.resource_id:16X})"

                    elif resource_type == consts.RESOURCE_ENTRY_TYPE_GENESYSDEFINITION:
                        label = f"{res.unpacked_object.obj_name} (ID: {res.resource_id:16X})"

                    else:
                        label = f"ID: {res.resource_id:16X}"

                    with dpg.group(horizontal=True):
                        open_button = dpg.add_button(label=label, callback=self.window_manager.add_window_callback, user_data=[bndl, res, bndl_tree_node])

                        with dpg.popup(open_button):
                            dpg.add_selectable(label="Open Resource Entry Data", callback=self.window_manager.add_resource_entry_window, user_data=[bndl, res])

        dpg.add_button(label="Open info tab", user_data=bndl, callback=lambda _, __, u : self.window_manager.add_bndl_window(u), parent=bndl_tree_node)
        dpg.add_button(label="Export bndl", user_data=bndl, callback=lambda _, __, u : export_bndl_to_file(u), parent=bndl_tree_node)
