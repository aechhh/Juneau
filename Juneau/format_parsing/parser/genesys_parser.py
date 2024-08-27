import os

import struct

from Juneau.utils.GeneSysTypeData import *

from Juneau.formats.geneSys.object_defintion import ObjectDefintion, DefinitionField
from Juneau.formats.geneSys.object_instance import ObjectInstance
from Juneau.formats.geneSys.instance_field import InstanceField

from Juneau.format_parsing.parser.file_reader import FileReader

from Juneau.formats.bndl.bndl import ResourceEntry


def parse_object_defintion(data, BIG_ENDIAN, is_hpr) -> ObjectDefintion:
    if is_hpr:
        definition_header_struct_format_string = "IIQIB51s"
    else:
        definition_header_struct_format_string = "IIIIB51s"

    definition_field_struct_format_string = "IIIII"

    if BIG_ENDIAN:
        definition_header_struct_format_string = ">" + definition_header_struct_format_string
        definition_field_struct_format_string = ">" + definition_field_struct_format_string

    def_header_size = struct.calcsize(definition_header_struct_format_string)

    def_header_arr = struct.unpack(definition_header_struct_format_string, data[0:def_header_size])

    obj_def_id = def_header_arr[0]
    obj_id = def_header_arr[1]
    offset_to_defs = def_header_arr[2]
    num_defs = def_header_arr[3]
    obj_ref_index = def_header_arr[4]

    obj_name = None
    for s in def_header_arr[5].decode().split("\x00"):
        if len(s) != 0:
            obj_name = s

    assert obj_name is not None

    obj_def = ObjectDefintion(obj_id, obj_def_id, offset_to_defs, num_defs, obj_ref_index, obj_name)

    field_def_size = struct.calcsize(definition_field_struct_format_string)

    # parse all defintion fields and add them to the list of fields for this given object defintion
    for offset in range(offset_to_defs, offset_to_defs + (num_defs*field_def_size), field_def_size):
        def_field_arr = struct.unpack(definition_field_struct_format_string, data[offset:offset+field_def_size])

        field_id = def_field_arr[0]
        field_type = def_field_arr[1]
        length = def_field_arr[2]
        field_offset = def_field_arr[3]
        field_size = def_field_arr[4]

        obj_def_field = DefinitionField(field_id, field_type, length, field_offset, field_size)

        obj_def.fields.append(obj_def_field)

    return obj_def


def parse_first_obj(res, obj_defs, BIG_ENDIAN) -> ObjectInstance:
    instance_data_reader = FileReader(res.unpacked_data[0], BIG_ENDIAN)

    obj = __parse_object_instance(0x0, res, obj_defs, instance_data_reader, BIG_ENDIAN)

    return obj

def __parse_object_instance(offset, res : ResourceEntry, obj_defs : list[ObjectDefintion], instance_data_reader : FileReader, BIG_ENDIAN) -> ObjectInstance:
    if res.is_hpr:
        obj_def_id = instance_data_reader.get_dword_at_offset(offset + 0x18)
    else:
        obj_def_id = instance_data_reader.get_dword_at_offset(offset + 0xC)

    obj_def = None
    for bndl_obj_def in obj_defs:
        if obj_def_id == bndl_obj_def.obj_def_id:
            obj_def = bndl_obj_def
            break

    if obj_def is None:
        print("[Object Instance] - Attempted to parse object with no object definition, aborting parsing")
        return None

    import_entry = res.get_import_entry_from_offset(offset)

    if import_entry is None:
        for import_entry in res.imports:
            print(f"Res offset: {hex(import_entry.import_type_and_offset)}")

        print(f"Obj offset: {hex(offset)}")
        raise Exception("Could not find definition import entry for genesys instance")

    if res.is_hpr:
        obj_instance_id = instance_data_reader.get_dword_at_offset(offset + 0x1C)
    else:
        obj_instance_id = instance_data_reader.get_dword_at_offset(offset + 0x10)

    if res.is_hpr:
        obj_data_offset = instance_data_reader.get_qword_at_offset(offset + 0x10)
    else:
        obj_data_offset = instance_data_reader.get_dword_at_offset(offset + 0x8)

    field_data = []
    for i, field_def in enumerate(obj_def.fields):
        offset_counter = obj_data_offset + field_def.offset_into_fieldstruct

        unhandled_types = [ # These are unused throughout the entirety of hp10
            E_VALUETYPE_WIDESTRING,
            E_VALUETYPE_COUNT
        ]

        if field_def.type in unhandled_types:
            raise Exception("Unhandled genesys field type encountered")

        new_field = __create_instance_field(offset_counter, i, field_def, instance_data_reader, res, obj_defs, BIG_ENDIAN)

        # fixing up pointer list elem size
        # used for creation of new objects
        if new_field.is_list:
            if field_def.pointer_list_elem_size is None:
                field_def.pointer_list_elem_size = new_field.data[2]
            else:
                if field_def.pointer_list_elem_size != new_field.data[2]:
                    raise Exception("Unexpected pointer list size")

        field_data.append(new_field)

    return ObjectInstance(offset, obj_instance_id, obj_def, field_data, import_entry)

def __create_instance_field(offset, index, field_def : DefinitionField, instance_data_reader : FileReader, res, obj_defs, BIG_ENDIAN) -> InstanceField:
    field = InstanceField(offset, index, field_def)

    # if the field is a pointer list then we just parse it totally differently
    if field.definition.type & E_VALUETYPE_VARIABLE_ARRAY == E_VALUETYPE_VARIABLE_ARRAY:
        field.is_list = True

        __parse_instance_list(field, instance_data_reader, res, obj_defs, BIG_ENDIAN)

        return field

    # add data to data list, usually length = 1
    for i in range(field.definition.length):
        data_offset = field.offset + (i * field.definition.size)
        data = instance_data_reader.get_nsized_data_at_offset(data_offset, field.definition.size)

        field.data.append(data)

        # resource handle types showup in the reflist but not in the file itself (like their data is always zero)
        # a pointer to the resource gets put into the resource handle field dynamically
        if field.definition.type == E_VALUETYPE_RESOURCE_HANDLE:
            import_entry = res.get_import_entry_from_offset(data_offset)

            field.res_imports.append(import_entry)

    # if field is string then it needs special parsing
    if field.definition.type == E_VALUETYPE_STRING:
        for i, offset in enumerate(field.data):
            str_data = ""

            str_len = offset >> (4*8)
            str_offset_from_field = offset & 0xFFFFFFFF
            str_offset = ((i * 0x8) + field.offset) + str_offset_from_field

            for j in range(str_len):
                str_data += chr(instance_data_reader.get_byte_at_offset(str_offset + j))

            field.string_data.append(str_data)

    # parse subobjects in instance field
    if field.definition.type == E_VALUETYPE_INSTANCE:
        field.subobjects = [None] * len(field.data)

        for i, obj_off in enumerate(field.data):
            if obj_off != 0:
                field.subobjects[i] = __parse_object_instance(obj_off, res, obj_defs, instance_data_reader, BIG_ENDIAN)

    return field

def __parse_instance_list(field : InstanceField, instance_data_reader : FileReader, res : ResourceEntry, obj_defs, BIG_ENDIAN):
    if field.definition.length != 1:
        raise Exception("Found list type with length != 1, what the heck")

    if res.is_hpr:
        if field.definition.size != 16:
            raise Exception("Found list type with size != 12, what the heck")
    else:
        if field.definition.size != 12:
            raise Exception("Found list type with size != 12, what the heck")

    if res.is_hpr:
        field.data = [
            instance_data_reader.get_qword_at_offset(field.offset),
            instance_data_reader.get_dword_at_offset(field.offset + 0x8),
            instance_data_reader.get_dword_at_offset(field.offset + 0xC)
        ]
    else:
        field.data = [ instance_data_reader.get_dword_at_offset(field.offset + i) for i in range(0, 12, 4) ]

    list_offset = field.data[0]
    list_length = field.data[1]
    list_elem_size = field.data[2]

    list_data_type = field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK

    if list_length == 0:
        return

    for external_data_offset in range(list_offset, list_offset + (list_length * list_elem_size), list_elem_size):
        data = instance_data_reader.get_nsized_data_at_offset(external_data_offset, list_elem_size)
        field.external_list_data.append(data)

        if list_data_type == E_VALUETYPE_RESOURCE_HANDLE:
            import_entry = res.get_import_entry_from_offset(external_data_offset)
            # Note: These can be None

            field.res_imports.append(import_entry)
        elif list_data_type == E_VALUETYPE_STRING:
            # print("!!!! Found a string pointer list !!!!")

            str_data = ""

            str_len = data >> (4*8)
            str_offset_from_field = data & 0xFFFFFFFF
            str_offset = external_data_offset + str_offset_from_field

            for i in range(str_len):
                str_data += chr(instance_data_reader.get_byte_at_offset(str_offset + i))

            field.string_data.append(str_data)

    assert len(field.external_list_data) == list_length

    if list_data_type == E_VALUETYPE_INSTANCE:
        for offset in field.external_list_data:
            new_obj_inst = __parse_object_instance(offset, res, obj_defs, instance_data_reader, BIG_ENDIAN)
            field.external_list_objects.append(new_obj_inst)
