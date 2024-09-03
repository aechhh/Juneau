import Juneau.config as consts

from functools import cmp_to_key

from Juneau.formats.geneSys.object_defintion import ObjectDefintion

class ImportEntry():
    def __init__(self, resource_id, import_type_and_offset):
        self.resourse_id = resource_id
        self.import_type_and_offset = import_type_and_offset

        self.usages = 0

class ResourceEntry():
    def __init__(self, header_data, is_compressed, is_hpr) -> None:
        self.num_banks = 4 # this number should never be changed, see here: https://burnout.wiki/wiki/Bundle_2/Need_for_Speed_Hot_Pursuit

        self.uncompressed_size_and_alignment = list()
        for _ in range(self.num_banks):
            self.uncompressed_size_and_alignment.append(0)

        self.size_and_alignment_on_disk = list()
        for _ in range(self.num_banks):
            self.size_and_alignment_on_disk.append(0)

        self.disk_offset = list()
        for _ in range(self.num_banks):
            self.disk_offset.append(0)

        (
        self.resource_id,
        self.import_hash,
        self.uncompressed_size_and_alignment[0],
        self.uncompressed_size_and_alignment[1],
        self.uncompressed_size_and_alignment[2],
        self.uncompressed_size_and_alignment[3],
        self.size_and_alignment_on_disk[0],
        self.size_and_alignment_on_disk[1],
        self.size_and_alignment_on_disk[2],
        self.size_and_alignment_on_disk[3],
        self.disk_offset[0],
        self.disk_offset[1],
        self.disk_offset[2],
        self.disk_offset[3],
        self.import_offset,
        self.resource_type_id,
        self.import_count,
        self.flags,
        self.pool_offset
        ) = header_data

        self.is_compressed = is_compressed

        self.is_hpr = is_hpr

        # ⬇⬇⬇ Lazy loaded data ⬇⬇⬇
        self.unpacked_data = None # gets loaded in fill_lazy_loaded_bndl because creating lists is so slow
        self.unpacked_object = None # Will be filled in by the python object representing the object

        self.imports : list[ImportEntry] = []

    def get_header_data(self):
        return (
            self.resource_id,
            self.import_hash,
            self.uncompressed_size_and_alignment[0],
            self.uncompressed_size_and_alignment[1],
            self.uncompressed_size_and_alignment[2],
            self.uncompressed_size_and_alignment[3],
            self.size_and_alignment_on_disk[0],
            self.size_and_alignment_on_disk[1],
            self.size_and_alignment_on_disk[2],
            self.size_and_alignment_on_disk[3],
            self.disk_offset[0],
            self.disk_offset[1],
            self.disk_offset[2],
            self.disk_offset[3],
            self.import_offset,
            self.resource_type_id,
            self.import_count,
            self.flags,
            self.pool_offset
        )

    def get_resourse_type_name(self) -> str:
        return consts.RESOURCE_TYPE_ID_TO_STR_DICT[self.resource_type_id]

    def get_import_entry_from_offset(self, offset) -> ImportEntry:
        offset_from_import_type_and_offset_mask = 0x7fffffff

        for import_entry in self.imports:
            import_entry_offset = import_entry.import_type_and_offset & offset_from_import_type_and_offset_mask

            if import_entry_offset == offset:
                import_entry.usages += 1 # mostly used as a debug tool to track how many times an import is referenced
                                         # it should be one for every import but im not sure yet

                return import_entry

        return None

    def get_all_imports_used_n_times(self, n):
        for import_entry in self.imports:
            if import_entry.usages != n:
                return False

        return True

    def get_contains_debug_data(self) -> bool:
        return bool(self.flags & consts.RESOURCE_ENTRIES_FLAGS_CONTAINS_DEBUG_DATA)

    def has_gamechanger_id(self):
        # res id: 0xff000000ffffffff
        # id type in highest byte
        # id in lowest 4 bytes

        return ( self.resource_id >> (7*8) ) & 0xFF == 0x1 # 0x1 is the constant for the game changer id type
        # see here: https://burnout.wiki/wiki/Bundle_2/Need_for_Speed_Hot_Pursuit#CgsResource::ID::EIdType for more info

    # for below functions: see https://burnout.wiki/wiki/Bundle_2/Need_for_Speed_Hot_Pursuit#Game_Changer_ID
    def get_gamechanger_id_index(self):
        return ( ( self.resource_id >> (6*8) ) & 0xFF )

    def get_gamechanger_id_res_type(self):
        return ( ( self.resource_id >> (4*8) ) & 0xFFFF )

    def get_actual_id(self):
        return ( self.resource_id & 0xFFFFFFFF )

class BNDL():
    def __init__(self, full_file_path, file_name, header_data, lazy_loaded, is_hpr) -> None:
        self.full_file_path : str = full_file_path
        self.file_name = file_name

        if full_file_path.split(".")[-1].lower() == "hpr":
            self.is_hpr = True
        elif full_file_path.split(".")[-1].lower() == "hp10":
            self.is_hpr = False
        else:
            self.is_hpr = is_hpr

        self.resource_data_offset = [0,0,0,0]

        (
        self.magic_num,
        self.version,
        self.platform,
        self.debug_data_offset,
        self.resource_entries_count,
        self.resource_entries_offset,
        self.resource_data_offset[0],
        self.resource_data_offset[1],
        self.resource_data_offset[2],
        self.resource_data_offset[3],
        self.flags
        ) = header_data

        # self.debug_data : bytes = debug_data

        self.objects : dict[int, list[ResourceEntry]] = {}

        self.parsed_objects = {}

        self.lazy_loaded = lazy_loaded

    # returns a tuple of all the fields in the header of a bndl
    # used when writing to file with struct.pack
    def get_header_attributes(self):
        return (
            self.magic_num,
            self.version,
            self.platform,
            self.debug_data_offset,
            self.resource_entries_count,
            self.resource_entries_offset,
            self.resource_data_offset[0],
            self.resource_data_offset[1],
            self.resource_data_offset[2],
            self.resource_data_offset[3],
            self.flags
        )

    def add_object(self, resource : ResourceEntry):
        if resource.resource_type_id not in self.objects:
            self.objects[resource.resource_type_id] = [resource]
        else:
            self.objects[resource.resource_type_id].append(resource)

    def has_compressed_data(self) -> bool:
        return bool(self.flags & consts.RESOURCE_ENTRIES_FLAGS_ZLIB_COMPRESSION)

    def get_all_genesys_defs(self) -> list[ObjectDefintion]:
        defs = []

        for res_id in self.objects:
            for res in self.objects[res_id]:
                if res.resource_type_id == consts.RESOURCE_ENTRY_TYPE_GENESYSDEFINITION:
                    defs.append(res.unpacked_object)

        return defs

    @staticmethod
    def resource_entry_game_sort(res_1 : ResourceEntry, res_2 : ResourceEntry) -> int:
        # see here for sorting reasoning:
        # https://burnout.wiki/wiki/Bundle_2/Need_for_Speed_Hot_Pursuit#CgsResource::BundleV2::ResourceEntry
        if res_1.pool_offset < res_2.pool_offset:
            return 1
        elif res_1.pool_offset > res_2.pool_offset:
            return -1

        if res_1.has_gamechanger_id() and res_2.has_gamechanger_id():
            if res_1.get_gamechanger_id_index() < res_2.get_gamechanger_id_index():
                return 1
            elif res_1.get_gamechanger_id_index() > res_2.get_gamechanger_id_index():
                return -1

            if res_1.get_gamechanger_id_res_type() < res_2.get_gamechanger_id_res_type():
                return 1
            elif res_1.get_gamechanger_id_res_type() > res_2.get_gamechanger_id_res_type():
                return -1

        if res_1.resource_type_id < res_2.resource_type_id:
            return 1
        elif res_1.resource_type_id > res_2.resource_type_id:
            return -1

        if res_1.get_actual_id() < res_2.get_actual_id():
            return 1
        elif res_1.get_actual_id() > res_2.get_actual_id():
            return -1

        return 0

    def get_all_resource_entries(self, game_order_sorted=False) -> list[ResourceEntry]:
        ret = []

        for resource_type_id in self.objects:
            for resource_entry in self.objects[resource_type_id]:
                ret.append(resource_entry)

        if game_order_sorted:
            ret = sorted(ret, key=cmp_to_key(self.resource_entry_game_sort))

        return ret

    def get_res_from_id(self, id_to_find) -> ResourceEntry:
        matches : list[ResourceEntry] = []

        for res in self.get_all_resource_entries():
            if res.resource_id == id_to_find:
                matches.append(res)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            return None
        else:
            print("FOUND MULTIPLE ENTRIES WITH THE SAME ID IN THE SAME BNDL")
            return None
