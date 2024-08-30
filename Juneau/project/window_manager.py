import dearpygui.dearpygui as dpg

from Juneau.formats.bndl.bndl import ResourceEntry, BNDL

from Juneau.project.tabs import (GenesysInstanceWindow,
                                 GenesysDefinitionWindow,
                                 ResourceEntryWindow,
                                 TextfileWindow,
                                 LangFileWindow,
                                 TextureWindow)

import Juneau.config as consts

class WindowManager():
    def __init__(self, parent_window) -> None:
        self.dpg_parent_window = parent_window

        self.dpg_tab_bar = dpg.add_tab_bar(parent=self.dpg_parent_window, reorderable=True)

    def add_window_callback(self, _sender, _app_data, user_data):
        bndl : BNDL = user_data[0]
        resource_entry : ResourceEntry = user_data[1]

        self.add_window(bndl, resource_entry)

    def add_window(self, bndl : BNDL, resource_entry : ResourceEntry):
        title = f"{resource_entry.get_resourse_type_name()}: {resource_entry.resource_id:16X}"

        with self.__create_tab(title) as parent:
            if resource_entry.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSINSTANCE:
                self.__draw_genesys_instance_window(parent, bndl, resource_entry)

            elif resource_entry.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSDEFINITION:
                self.__draw_genesys_definition_window(parent, resource_entry)

            elif resource_entry.resource_type_id == consts.RESOURCE_ENTRY_TYPE_LANGUAGE:
                self.__draw_langfile_window(parent, resource_entry)

            elif resource_entry.resource_type_id == consts.RESOURCE_ENTRY_TYPE_TEXTFILE:
                self.__draw_textfile_window(parent, resource_entry)

            elif resource_entry.resource_type_id == consts.RESOURCE_ENTRY_TYPE_TEXTURE:
                self.__draw_texture_window(parent, resource_entry)

            else:
                self.__draw_resource_entry_window(parent, bndl, resource_entry)

    def add_bndl_window(self, bndl : BNDL):
        with self.__create_tab(bndl.file_name):
            dpg.add_text(f"Version: {bndl.version}")
            dpg.add_text(f"Platform: {bndl.platform}")
            dpg.add_text(f"Resource Entry Count: {bndl.resource_entries_count}")
            dpg.add_text(f"Actual Resource Entry Count: {len(bndl.get_all_resource_entries())}")
            dpg.add_text("Flags: ")

            dpg.add_separator()

            # copied from consts and should prob be in there but this will never change so 🤷‍♀️
            masks = {
                "ZLIB_COMPRESSION": 1,
                "MAIN_MEM_OPTIMISATION": 2,
                "GRAPHICS_MEM_OPTIMISATION": 4,
                "CONTAINS_DEBUG_DATA": 8,
                "NON_ASYNCH_FIXUP_REQUIRED": 16,
                "MULTISTREAM_BUNDLE": 32,
                "DELTA_BUNDLE": 64
            }

            for mask in masks:
                flag = masks[mask] & bndl.flags

                dpg.add_text(f"{mask}: {bool(flag)}")

    def add_resource_entry_window(self, _sender, _app_data, user_data):
        bndl : BNDL = user_data[0]
        resource_entry : ResourceEntry = user_data[1]

        with self.__create_tab() as parent:
            self.__draw_resource_entry_window(parent, bndl, resource_entry)


    def __create_tab(self, title = ""):
        tab = dpg.add_tab(parent=self.dpg_tab_bar, order_mode=dpg.mvTabOrder_Reorderable, label=title, closable=True)

        dpg.set_value(self.dpg_tab_bar, tab)

        return dpg.child_window(width=-1, height=-1, parent=tab, no_scrollbar=False, user_data=tab)


    def __draw_resource_entry_window(self, parent, bndl : BNDL, res : ResourceEntry):
        # set tab title
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label=f"Resource Entry: {res.resource_id & 0xFFFFFFFF : 08X}")

        _window = ResourceEntryWindow(parent, bndl, res)

    def __draw_genesys_instance_window(self, parent, parent_bndl, res : ResourceEntry):
        # set tab title
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label=f"Instance: {res.unpacked_object.obj_def.obj_name} {res.resource_id & 0xFFFFFFFF : 08X}")

        _window = GenesysInstanceWindow(parent, res, parent_bndl, self)


    def __draw_langfile_window(self, parent, res : ResourceEntry):
        # set tab title
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label="Language File")

        _window = LangFileWindow(parent, res)

    def __draw_genesys_definition_window(self, parent, res : ResourceEntry):
        # set tab title
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label=f"Definition: {res.unpacked_object.obj_name}")

        _window = GenesysDefinitionWindow(parent, res)

    def __draw_textfile_window(self, parent, res : ResourceEntry):
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label=f"Text File ({res.resource_id & 0xFFFFFFFF : 08X})")

        _window = TextfileWindow(parent, res)

    def __draw_texture_window(self, parent, res : ResourceEntry):
        tab = dpg.get_item_user_data(parent)
        dpg.configure_item(tab, label=f"Texture: {res.resource_id & 0xFFFFFFFF : 08X}")

        _window = TextureWindow(parent, res)
