import dearpygui.dearpygui as dpg

import json

import tkinter as tk
from tkinter import filedialog

import Juneau.config as consts

from Juneau.formats.bndl.bndl import ResourceEntry

from Juneau.formats.lang_string import LangString

class LangFileWindow():
    def __init__(self, parent_tag, res : ResourceEntry) -> None:
        self.parent_tag = parent_tag
        self.resource_entry = res

        self.refresh()

    def refresh(self):
        dpg.delete_item(self.parent_tag, children_only=True)

        dpg.add_text("JSON Exporter/Importer", parent=self.parent_tag)

        dpg.add_button(
            label = "Export",
            callback = lambda _s, _a, _u : self.__export_langfile_to_json(),
            parent=self.parent_tag
        )

        dpg.add_button(
            label = "Import",
            callback = lambda _s, _a, _u : self.__import_langfile_from_json(),
            parent=self.parent_tag
        )

        dpg.add_separator(parent=self.parent_tag)

        with dpg.table(
                header_row=True,
                row_background=True,
                borders_innerH=True,
                borders_outerH=True,
                borders_innerV=True,
                borders_outerV=True,
                delay_search=True,
                resizable=True,
                parent=self.parent_tag
            ):

            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="String Data")

            for lang_str in self.resource_entry.unpacked_object:
                lang_str : LangString = lang_str

                with dpg.table_row():
                    dpg.add_text(f"{lang_str.id}")
                    dpg.add_text(f"{lang_str.full_string}")

    def __export_langfile_to_json(self):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        out_file = filedialog.asksaveasfile(
            mode="w",
            title="Export json",
            initialfile="langfile",
            defaultextension=".json",
            filetypes=(("JSON File", "*.json"), ("All files", "*"))
        )

        root.destroy()

        if out_file is None:
            return

        json_out = {}

        for lang_str in self.resource_entry.unpacked_object:
            lang_str : LangString = lang_str

            json_out[int(lang_str.id)] = lang_str.full_string

        out_file.write(json.dumps(json_out, indent=2, ensure_ascii=True))

        out_file.close()

    def __import_langfile_from_json(self):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        file_to_import = filedialog.askopenfile(
            mode="r",
            title="Import json",
            initialfile="langfile",
            defaultextension=".txt",
            filetypes=(("JSON File", "*.json"), ("All files", "*"))
        )

        root.destroy()

        json_strs = json.load(file_to_import)

        num_strs = len(json_strs)
        str_ids = list(json_strs.keys())
        lang_strs : list[LangString] = []

        for i in range(num_strs):
            full_str = json_strs[str_ids[i]]
            str_id = int(str_ids[i])
            str_len = len(full_str)

            lang_strs.append(LangString(-1, str_len, str_id, full_str))

        self.resource_entry.unpacked_object = lang_strs

        self.refresh()
