import struct
import zlib

# used for filedialogs
import tkinter as tk
from tkinter import filedialog

import Juneau.config as consts

from Juneau.format_parsing.writer.file_writer import FileWriter
from Juneau.format_parsing.writer.instance_file_writer import write_object

from Juneau.formats.bndl.bndl import BNDL

def export_bndl_to_file(bndl : BNDL):
    # needed for file dialog popups

    root = tk.Tk()
    root.withdraw()
    root.iconbitmap(consts.ICON_FILENAME)

    export_file = filedialog.asksaveasfile(
        mode="wb",
        title="Export BNDL",
        initialfile=bndl.file_name,
        defaultextension=".BNDL",
        filetypes=(("Bundle File", "*.BNDL"), ("Bundle File", "*.BUNDLE"), ("Bundle File", "*.BIN"), ("All files", "*"))
        )

    root.destroy()

    if export_file is None:
        return

    print("Writing bndl to file")

    print("Rewriting all genesys instances")

    for res in bndl.get_all_resource_entries():
        if res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSINSTANCE:
            res.unpacked_data[0] = write_object(res.unpacked_object, res.is_hpr)

    print("Successfully rewrote genesys instances")

    # TODO make this not hard coded
    file_writer = FileWriter(BIG_ENDIAN=False)

    # TODO move this to constants file
    bndl_header_format = "4sIIIII4II"
    bndl_header_size = struct.calcsize(bndl_header_format)
    resource_entry_format = "QQ4I4I4IIIHBB4x"
    resource_entry_size = struct.calcsize(resource_entry_format)

    # allocate space for the bndl header
    file_writer.alloc_file_space(bndl_header_size)

    with open("data/juneau_bndl_header.bin", "rb") as f:
        juneau_header_data  = f.read()

        file_writer.write_byte_array(file_writer.alloc_file_space(len(juneau_header_data)), juneau_header_data)

    # allocate space for all the resource entries
    resource_entry_offset = file_writer.alloc_file_space(resource_entry_size * bndl.resource_entries_count)

    # set the proper resource entry offset in the bndl header
    bndl.resource_entries_offset = resource_entry_offset

    bndl_is_compressed = bndl.flags & consts.RESOURCE_ENTRIES_FLAGS_ZLIB_COMPRESSION

    for mem_bank in range(4): # 4 is the number of mem banks
        bndl.resource_data_offset[mem_bank] = file_writer.align(16)

        for res in bndl.get_all_resource_entries():
            if len(res.unpacked_data[mem_bank]) == 0:
                continue

            # --- appending import entries to data ---
            data = bytearray(res.unpacked_data[mem_bank])

            if mem_bank == 0:
                # make sure end of data is 16 byte aligned
                padding_needed = 16 - (len(data) % 16) if len(data) % 16 != 0 else 0

                for _ in range(padding_needed):
                    data.append(0)

                res.import_offset = len(data)

                if res.import_count != len(res.imports):
                    raise Exception("Malformed import count")

                # TODO check endianness
                import_entry_struct_parse_str = "QL4x"
                for import_entry in res.imports:
                    data.extend(struct.pack(import_entry_struct_parse_str, import_entry.resourse_id, import_entry.import_type_and_offset))

            # --- writing the data ---
            uncompressed_size = len(data)

            data_alignment = res.uncompressed_size_and_alignment[mem_bank] & (~consts.RESOURCE_ENTRIES_SIZE_AND_ALIGNMENT_MASK)
            res.uncompressed_size_and_alignment[mem_bank] = uncompressed_size | data_alignment

            alignment_nibble = data_alignment >> 28

            res.size_and_alignment_on_disk[mem_bank] = uncompressed_size

            compressed_data = zlib.compress(bytes(data), 9)
            compressed_size = len(compressed_data)

            if bndl_is_compressed:
                res.size_and_alignment_on_disk[mem_bank] = compressed_size

            data_offset = file_writer.alloc_file_space(res.size_and_alignment_on_disk[mem_bank], alignment = (1 << alignment_nibble) )

            res.disk_offset[mem_bank] = data_offset - bndl.resource_data_offset[mem_bank]

            if bndl_is_compressed:
                file_writer.write_byte_array(res.disk_offset[mem_bank] + bndl.resource_data_offset[mem_bank], compressed_data)
            else:
                file_writer.write_byte_array(res.disk_offset[mem_bank] + bndl.resource_data_offset[mem_bank], data)

    end_of_file = file_writer.align(16)

    bndl.debug_data_offset = end_of_file

    # write the bndl header
    file_writer.write_struct_data(0, bndl_header_format, bndl.get_header_attributes())

    # write all the resource entry headers
    for mem_bank, resource_entry in enumerate(bndl.get_all_resource_entries()):
        offset = resource_entry_offset + mem_bank * resource_entry_size

        file_writer.write_struct_data(offset, resource_entry_format, resource_entry.get_header_data())

    file_writer.write_to_and_close_file_obj(export_file)

    print("Done :)")
