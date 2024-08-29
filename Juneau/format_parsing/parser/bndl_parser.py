import struct
import zlib

from pathlib import Path
from multiprocessing import Pool

import Juneau.config as consts

from Juneau.formats.bndl.bndl import BNDL, ResourceEntry, ImportEntry
from Juneau.formats.geneSys.object_defintion import ObjectDefintion

from Juneau.format_parsing.parser.genesys_parser import parse_object_defintion, parse_first_obj
from Juneau.format_parsing.parser.langfile_parser import read_lang_file
from Juneau.format_parsing.parser.textfile_parser import parse_textfile_data
from Juneau.format_parsing.parser.texture_parser import parse_texture

def lazy_parse_bndl(bndl_path, is_hpr, BIG_ENDIAN = False) -> BNDL:
    # We assume that the file being passed in is a valid bndl file
    bundleV2_struct_parse = "4sIIIII4II"
    bundleV2_struct_size = struct.calcsize(bundleV2_struct_parse)
    resource_entry_struct_parse = "QQ4I4I4IIIHBB4x"
    resource_entry_struct_size = struct.calcsize(resource_entry_struct_parse)

    if BIG_ENDIAN:
        bundleV2_struct_parse = ">" + bundleV2_struct_parse
        resource_entry_struct_parse = ">" + resource_entry_struct_parse

    with open(bndl_path, "rb") as f:
        bndl_header_data = struct.unpack(bundleV2_struct_parse, f.read(bundleV2_struct_size))
        bndl = BNDL(bndl_path, Path(bndl_path).parts[-1], bndl_header_data, True, is_hpr)

        for i in range(bndl.resource_entries_count):
            f.seek(bndl.resource_entries_offset + (i*resource_entry_struct_size), 0)

            resource_entry_data = struct.unpack(resource_entry_struct_parse, f.read(resource_entry_struct_size))
            bndl.add_object(ResourceEntry(resource_entry_data, bndl.has_compressed_data(), bndl.is_hpr))

    return bndl

def parse_obj_def_wrapper(res : ResourceEntry) -> ObjectDefintion:
    return parse_object_defintion(res.unpacked_data[0], False, res.is_hpr)

# silly ah solution from https://stackoverflow.com/questions/4827432/how-to-let-pool-map-take-a-lambda-function
# needed because Pool.map has a hard time with lambda functions
class __ParseGenesysInst(object):
    def __init__(self, obj_defs, BIG_ENDIAN):
        self.obj_defs = obj_defs
        self.BIG_ENDIAN = BIG_ENDIAN

    def __call__(self, res):
        return parse_first_obj(res, self.obj_defs, self.BIG_ENDIAN)

def fill_lazy_loaded_bndl(bndl : BNDL):
    if not bndl.lazy_loaded:
        return

    print(f"Loading lazy loaded bndl: {bndl.full_file_path}")

    with open(bndl.full_file_path, "rb") as f:
        for res_type in bndl.objects:
            for res in bndl.objects[res_type]:
                res : ResourceEntry = res

                # creating these lists here because otherwise lazy loading all bndls is really slow
                res.unpacked_data = [bytes(), bytes(), bytes(), bytes()]

                res.imports = []

                for bank_index in range(res.num_banks):
                    if res.uncompressed_size_and_alignment[bank_index] == 0:
                        continue

                    f.seek(bndl.resource_data_offset[bank_index] + res.disk_offset[bank_index], 0)

                    if res.is_compressed:
                        res.unpacked_data[bank_index] = f.read(res.size_and_alignment_on_disk[bank_index] & consts.RESOURCE_ENTRIES_SIZE_AND_ALIGNMENT_MASK)
                    else:
                        res.unpacked_data[bank_index] = f.read(res.uncompressed_size_and_alignment[bank_index] & consts.RESOURCE_ENTRIES_SIZE_AND_ALIGNMENT_MASK)

    # TODO check for endianness here
    import_entry_struct_parse_str = "QL4x"
    import_entry_size = struct.calcsize(import_entry_struct_parse_str)
    for res in bndl.get_all_resource_entries():
        if res.is_compressed:
            for i in range(len(res.unpacked_data)):
                if len(res.unpacked_data[i]) != 0:
                    res.unpacked_data[i]  = zlib.decompress(res.unpacked_data[i])

        if res.import_count != 0:
            # Huge assumption made here, is import data only in data bank 1? i sure hope so 🙏
            import_data = res.unpacked_data[0][res.import_offset:]

            # removing import data from the end of the data bank
            res.unpacked_data[0] = res.unpacked_data[0][:res.import_offset]

            for offset in range(0, res.import_count * import_entry_size, import_entry_size):
                import_entry_data = import_data[offset : offset + import_entry_size]
                resource_id, import_type_and_offset = struct.unpack(import_entry_struct_parse_str, import_entry_data)

                res.imports.append(ImportEntry(resource_id, import_type_and_offset))

    load_all_resource_entry_objects(bndl)

def load_all_resource_entry_objects(bndl : BNDL):
    genesys_def_res_list : list[ResourceEntry] = []
    genesys_inst_res_list : list[ResourceEntry] = []

    langfile_res_list : list[ResourceEntry] = []

    textfile_res_list : list[ResourceEntry] = []

    texture_res_list : list[ResourceEntry] = []

    for res in bndl.get_all_resource_entries():
        if res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSDEFINITION:
            genesys_def_res_list.append(res)

        elif res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSINSTANCE:
            genesys_inst_res_list.append(res)

        elif res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_LANGUAGE:
            langfile_res_list.append(res)

        elif res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_TEXTFILE:
            textfile_res_list.append(res)

        elif res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_TEXTURE:
            texture_res_list.append(res)

    # parse langfile
    for res in langfile_res_list:
        res.unpacked_object = read_lang_file(res.unpacked_data[0], False, res.is_hpr)

    # parse textfile
    for res in textfile_res_list:
        res.unpacked_object = parse_textfile_data(res.unpacked_data[0], False)

    # parse textures
    for res in texture_res_list:
        try:
            res.unpacked_object = parse_texture(res.unpacked_data[0], res.unpacked_data[1], False, res.is_hpr)
        except Exception as e:
            res.unpacked_object = None

            print("Texture file parsing failed")
            print(e)

    # parse the genesys definitions
    genesys_obj_defs : list[ObjectDefintion] = []
    if consts.GENESYS_PARSE_W_MULTIPROCESSING:
        print("Parsing genesys defs with multiprocessing")

        with Pool() as pool:
            results = pool.map(parse_obj_def_wrapper, genesys_def_res_list)

            for result in results:
                genesys_obj_defs.append(result)
    else:
        print("Parsing genesys defs")
        for res in genesys_def_res_list:
            genesys_obj_defs.append(parse_obj_def_wrapper(res))

    # add parsed object from multiprocessing results to the actual resource entries
    for obj_pair in zip(genesys_def_res_list, genesys_obj_defs):
        obj_pair[0].unpacked_object = obj_pair[1]

    genesys_obj_insts = []
    if consts.GENESYS_PARSE_W_MULTIPROCESSING:
        print("Parsing genesys instances with multiprocessing")
        with Pool() as pool:
            results = pool.map(__ParseGenesysInst(genesys_obj_defs, False), genesys_inst_res_list)

            for result in results:
                genesys_obj_insts.append(result)
    else:
        print("Parsing genesys instances")
        for res in genesys_inst_res_list:
            obj_inst = __ParseGenesysInst(genesys_obj_defs, False)(res)
            genesys_obj_insts.append(obj_inst)

        # TODO move to dedicated testing code
        #     if not res.get_all_imports_used_n_times(1):
        #         print(f"Imports used once ({obj_inst.obj_def.obj_name}): {res.get_all_imports_used_n_times(1)}")

        #     obj_name = obj_inst.obj_def.obj_name
        #     # print(f"Writing {obj_name}")
        #     test_obj = deepcopy(obj_inst)

        #     res.unpacked_data[0] = write_object(obj_inst, res.is_hpr)

        #     dogfood_obj = parse_first_obj(res, genesys_obj_defs, False)

        #     if not res.get_all_imports_used_n_times(2):
        #         print(f"Imports used twice ({obj_inst.obj_def.obj_name}): {res.get_all_imports_used_n_times(2)}")

        #     if not test_obj.is_eq_to_other(dogfood_obj, True):
        #         print(f"Objs are not equal: {obj_name}")

        # print("Done rewriting all objects :)")

    # add parsed object from multiprocessing results to the actual resource entries
    for obj_pair in zip(genesys_inst_res_list, genesys_obj_insts):
        obj_pair[0].unpacked_object = obj_pair[1]

    bndl.lazy_loaded = False

    print("Finished loading resource entries")
