import struct

import dearpygui.dearpygui as dpg

# used for filedialogs
import tkinter as tk
from tkinter import filedialog

import Juneau.config as consts

from Juneau.formats.bndl.bndl import  BNDL, ResourceEntry, ImportEntry
from Juneau.format_parsing.parser.bndl_parser import load_all_resource_entry_objects

class ResourceEntryWindow():
    def __init__(self, parent_tag, parent_bndl : BNDL, res : ResourceEntry) -> None:
        self.parent_tag = parent_tag # the tag of the parent dpg object
                                     # should be the root of the window
        self.resource_entry : ResourceEntry = res
        self.parent_bndl = parent_bndl

        self.export_w_import_entries = False
        self.bank_selection = 1

        self.__import_entries_combo_name = "Import Entries"

        # Header data
        dpg.add_text(f"ID: {res.resource_id:016X}")
        dpg.add_text(f"Import Hash: {res.import_hash:016X}")
        dpg.add_text(f"Resource Type ID: {res.get_resourse_type_name()}")
        dpg.add_text(f"Pool Offset: {res.pool_offset}")
        dpg.add_text(f"Flags: {res.flags}")

        dpg.add_separator()

        # Bank sizes
        for i in range(res.num_banks):
            dpg.add_text(f"Bank {i + 1} Size: {res.uncompressed_size_and_alignment[i] & consts.RESOURCE_ENTRIES_SIZE_AND_ALIGNMENT_MASK}")

        dpg.add_separator()

        # Data exporting section
        dpg.add_text("Data exporter/importer:")

        self.bank_selection_combo = dpg.add_combo((1, 2, 3, 4, self.__import_entries_combo_name), default_value=1, width=-1, callback = self.__bank_combo_callback )

        dpg.add_button(label="Export", callback=self.__export_data_callback)
        dpg.add_button(label="Import", callback=self.__import_data_callback)

        dpg.add_separator()

        # Import entries
        dpg.add_text(f"Import Entries: {len(res.imports)}")

        if len(res.imports) != 0:
            with dpg.table(header_row=True, row_background=True,
                                borders_innerH=True, borders_outerH=True, borders_innerV=True,
                                borders_outerV=True, delay_search=True, resizable=True):

                dpg.add_table_column(label="ID")
                dpg.add_table_column(label="Type and Offset")

                for import_entry in res.imports:
                    with dpg.table_row():
                        dpg.add_text(f"{import_entry.resourse_id:016X}")
                        dpg.add_text(f"{import_entry.import_type_and_offset:08X}")

    def __bank_combo_callback(self, _sender, app_data, _user_data):
        self.bank_selection = int(app_data)

    def __export_data_callback(self, _sender, _app_data, _user_data):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        if self.bank_selection == self.__import_entries_combo_name:
            file_suffix = "import_entries"
        else:
            file_suffix = self.bank_selection

        export_file = filedialog.asksaveasfile(
            mode="wb",
            title="Export data",
            initialfile=f"{self.resource_entry.resource_id:016X}_{file_suffix}",
            defaultextension=".bin",
            filetypes=(("Binary Data", "*.bin"), ("All files", "*"))
            )

        root.destroy()

        if export_file is None:
            return

        if self.bank_selection in (1, 2, 3, 4):
            data = bytes(self.resource_entry.unpacked_data[self.bank_selection - 1])

            print(f"Exporting {len(data)} bytes of data")

            export_file.write(data)
        else:
            print(f"Exporting {len(self.resource_entry.imports)} import entries")

            # TODO make this a constant, fix endianess
            import_entry_struct_parse_str = "QL4x"
            for import_entry in self.resource_entry.imports:
                export_file.write(struct.pack(import_entry_struct_parse_str, import_entry.resourse_id, import_entry.import_type_and_offset))

        export_file.close()

    def __import_data_callback(self, _sender, _app_data, _user_data):
        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(consts.ICON_FILENAME)

        if self.bank_selection == self.__import_entries_combo_name:
            file_suffix = "import_entries"
        else:
            file_suffix = self.bank_selection

        file_to_import = filedialog.askopenfile(
            mode="rb",
            title="Import data",
            initialfile=f"{self.resource_entry.resource_id:016X}_{file_suffix}",
            defaultextension=".bin",
            filetypes=(("Binary Data", "*.bin"), ("All files", "*"))
        )

        data = bytes(file_to_import.read())
        print(f"Importing {len(data)} bytes of data")

        if self.bank_selection in (1, 2, 3, 4):
            self.resource_entry.unpacked_data[self.bank_selection - 1] = data
        else:
            # TODO make this a constant, fix endianess
            import_entry_struct_parse_str = "QL4x"
            import_entry_struct_size = struct.calcsize(import_entry_struct_parse_str)

            self.resource_entry.imports = []
            counter = 0
            num_import_entries = int(len(data) / import_entry_struct_size)
            print(f"Importing {num_import_entries} import entries")
            for import_entry_offset in range(0, len(data), import_entry_struct_size):
                resource_id, import_type_and_offset = struct.unpack(import_entry_struct_parse_str, data[import_entry_offset : import_entry_offset + import_entry_struct_size])

                self.resource_entry.imports.append(ImportEntry(resource_id, import_type_and_offset))

                counter += 1

        load_all_resource_entry_objects(self.parent_bndl) # reloads the full bndl since import entries are recreated and will be desynced
                                                          # there also could be byte changes that have different cascading effects

        root.destroy()
