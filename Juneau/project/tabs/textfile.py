import dearpygui.dearpygui as dpg

import tkinter as tk
from tkinter import filedialog

import Juneau.config as consts
from Juneau.formats.bndl.bndl import ResourceEntry

class TextfileWindow():
    def __init__(self, parent_tag, res : ResourceEntry) -> None:
        self.refresh(parent_tag, res)

    def refresh(self, parent_tag, res : ResourceEntry):
        self.parent_tag = parent_tag
        self.resource_entry = res

        self.text_data : bytes = self.resource_entry.unpacked_object
        self.is_luaq = False

        self.text_parse_error_msg = "Sorry but Juneau isnt able to show this text file. "
        self.text_parse_error_msg_lua = "It looks like this is a compiled Lua file."

        try:
            self.text_string_value = self.text_data.decode("utf-8")
        except UnicodeDecodeError:
            self.text_string_value = self.text_parse_error_msg

            try:
                if self.text_data[1:5].decode('utf-8') == "LuaQ":
                    self.is_luaq = True

                    self.text_string_value += self.text_parse_error_msg_lua
            except UnicodeDecodeError:
                pass


        self.__draw_window()


    def __draw_window(self):
        dpg.delete_item(self.parent_tag, children_only=True)

        dpg.add_text(f"Length: {len(self.text_data)} ({len(self.text_data):08X})", parent=self.parent_tag)

        dpg.add_separator(parent=self.parent_tag)

        dpg.add_text("Text exporter/importer", parent=self.parent_tag)

        dpg.add_button(
            label = "Export",
            callback = lambda _s, _a, _u : self.__export_text_to_file(),
            parent=self.parent_tag
        )

        dpg.add_button(
            label = "Import",
            callback = lambda _s, _a, _u : self.__import_text_from_file(),
            parent=self.parent_tag
        )

        dpg.add_separator(parent=self.parent_tag)

        dpg.add_text(self.text_string_value, wrap=0, parent=self.parent_tag)

    def __export_text_to_file(self):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        export_file = filedialog.asksaveasfile(
            mode="wb" if self.is_luaq else "w",
            title="Export text",
            initialfile=f"{self.resource_entry.resource_id:016X}_{'lua' if self.is_luaq else 'text'}",
            defaultextension="luac" if self.is_luaq else ".txt",
            filetypes=(("Text File", "*.txt"), ("Compiled Lua File", "*.luac"), ("All files", "*"))
        )

        root.destroy()

        if export_file is None:
            return

        export_file.write(self.text_data if self.is_luaq else self.text_string_value)

        export_file.close()

    def __import_text_from_file(self):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        file_to_import = filedialog.askopenfile(
            mode="rb",
            title="Import text",
            initialfile=f"{self.resource_entry.resource_id:016X}_{'lua' if self.is_luaq else 'text'}",
            defaultextension=".txt",
            filetypes=(("Text File", "*.txt"), ("Compiled Lua File", "*.luac"), ("All files", "*"))
        )

        root.destroy()

        self.resource_entry.unpacked_object = file_to_import.read()

        self.refresh(self.parent_tag, self.resource_entry)

        file_to_import.close()
