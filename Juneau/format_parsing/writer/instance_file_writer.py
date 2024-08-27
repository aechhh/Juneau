from Juneau.formats.geneSys.object_instance import ObjectInstance
from Juneau.formats.bndl.bndl import ImportEntry

from Juneau.format_parsing.writer.file_writer import FileWriter
from Juneau.utils.GeneSysTypeData import *


def write_object(obj : ObjectInstance, is_hpr) -> bytes:
    file_writer = FileWriter(BIG_ENDIAN=False)

    __write_object(obj, file_writer, is_hpr)

    return file_writer.get_file_bytes()

def __write_object(obj : ObjectInstance, file_writer : FileWriter, is_hpr):
    # TODO move this (and other constants) to a dedicated file
    if is_hpr:
        OBJ_HEADER_SIZE = 0x30
    else:
        OBJ_HEADER_SIZE = 0x20

    # allocating space for the header of the object
    obj.offset = file_writer.alloc_file_space(OBJ_HEADER_SIZE)

    import_type_mask = 0x80000000
    import_type = obj.res_import.import_type_and_offset & import_type_mask

    obj.res_import.import_type_and_offset = obj.offset | import_type

    # allocating space in the file for the object's field data
    obj_fieldstruct_offset = file_writer.alloc_file_space(obj.get_fieldstruct_size(), alignment=0x10)

    # watermark lol
    # file_writer.write_byte_array(file_writer.alloc_file_space(0x30, 0x10), bytes("aech"*12, "ascii"))

    # writing object header info
    if is_hpr:
        file_writer.write_qword_at_offset(obj.offset + 0x10, obj_fieldstruct_offset)
        file_writer.write_dword_at_offset(obj.offset + 0x18, obj.obj_def.obj_def_id)
        file_writer.write_dword_at_offset(obj.offset + 0x1C, obj.id)
    else:
        file_writer.write_dword_at_offset(obj.offset + 0x8, obj_fieldstruct_offset)
        file_writer.write_dword_at_offset(obj.offset + 0xC, obj.obj_def.obj_def_id)
        file_writer.write_dword_at_offset(obj.offset + 0x10, obj.id)

    # --- Writing the fieldstruct ---
    for field in obj.field_data:
        # --- Writing the lists ---
        if field.is_list:
            # Allocate space for the list
            list_length = field.data[1]
            list_elem_size = field.data[2]

            list_offset = file_writer.alloc_file_space(list_length * list_elem_size, alignment=4)
            # Update the offset of the list
            field.data[0] = list_offset


            if list_length != len(field.external_list_data):
                raise Exception("Malformed pointer list data")

            list_data_type = field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK

            # write external list data to file
            if list_data_type == E_VALUETYPE_STRING:
                for i, string_data in enumerate(field.string_data):
                    # print("Writing string pointer list, potential issues ahead")

                    assert list_elem_size == 8

                    if string_data != "":
                        assert string_data[-1] == '\x00'

                    str_len = len(string_data)
                    str_offset_in_file = file_writer.alloc_file_space(str_len, alignment=1)
                    str_offset_from_field = str_offset_in_file - (list_offset + (i * list_elem_size))

                    data = ( str_len << (4*8) ) | str_offset_from_field

                    file_writer.write_nsized_byte_data_at_offset(list_offset + (i * list_elem_size), data, list_elem_size)

                    for j, char in enumerate(string_data):
                        file_writer.write_byte_at_offset(str_offset_in_file + j, ord(char))

            # write external objects if this is an instance pointer list
            elif list_data_type == E_VALUETYPE_INSTANCE:
                if len(field.external_list_data) != len(field.external_list_objects) or list_length != len(field.external_list_data):
                    raise Exception("Malformed instance list data")

                for i, sub_obj in enumerate(field.external_list_objects):
                    new_obj_offset = __write_object(sub_obj, file_writer, is_hpr)
                    file_writer.write_nsized_byte_data_at_offset(list_offset + (i * list_elem_size), new_obj_offset, list_elem_size)

            elif list_data_type == E_VALUETYPE_RESOURCE_HANDLE:
                for i in range(len(field.external_list_data)):
                    import_type_mask = 0x80000000

                    if field.res_imports[i] is not None:
                        import_type = field.res_imports[i].import_type_and_offset & import_type_mask

                        field.res_imports[i].import_type_and_offset = (list_offset + (i * list_elem_size)) | import_type

            else:
                for i, data in enumerate(field.external_list_data):
                    file_writer.write_nsized_byte_data_at_offset(list_offset + (i * list_elem_size), data, list_elem_size)

            # writing list data
            if is_hpr:
                base_offset = obj_fieldstruct_offset + field.definition.offset_into_fieldstruct

                file_writer.write_qword_at_offset(base_offset, field.data[0])
                file_writer.write_dword_at_offset(base_offset + 0x8, field.data[1])
                file_writer.write_dword_at_offset(base_offset + 0xC, field.data[2])
            else:
                for i, data in enumerate(field.data):
                    offset = obj_fieldstruct_offset + field.definition.offset_into_fieldstruct + (i*4)
                    file_writer.write_dword_at_offset(offset, data)

            continue

        # --- Writing field data ---
        field_offset = obj_fieldstruct_offset + field.definition.offset_into_fieldstruct

        if field.definition.type == E_VALUETYPE_STRING:
            # print("Writing string field list, potential issues ahead")

            assert field.definition.size == 8

            for i, string_data in enumerate(field.string_data):

                if string_data != "":
                    if string_data[-1] != '\x00':
                        print(string_data)

                    assert string_data[-1] == '\x00'

                str_len = len(string_data)
                str_offset_in_file = file_writer.alloc_file_space(str_len, alignment=1)
                str_offset_from_field = str_offset_in_file - (field_offset + (i * field.definition.size))

                data = ( str_len << (4*8) ) | str_offset_from_field

                file_writer.write_nsized_byte_data_at_offset(field_offset + (i * field.definition.size), data, field.definition.size)

                for j, char in enumerate(string_data):
                    file_writer.write_byte_at_offset(str_offset_in_file + j, ord(char))
            continue

        if field.definition.type == E_VALUETYPE_INSTANCE:
            for i in range(field.definition.length):
                if i < len(field.subobjects):
                    sub_obj = field.subobjects[i]
                else:
                    sub_obj = None

                if sub_obj is not None:
                    new_obj_offset = __write_object(sub_obj, file_writer, is_hpr)
                    file_writer.write_nsized_byte_data_at_offset(field_offset + (i * field.definition.size), new_obj_offset, field.definition.size)
                else:
                    file_writer.write_nsized_byte_data_at_offset(field_offset + (i * field.definition.size), 0, field.definition.size)

            continue

        for i in range(field.definition.length):
            file_writer.write_nsized_byte_data_at_offset(field_offset + (i * field.definition.size), field.data[i], field.definition.size)

            if field.definition.type == E_VALUETYPE_RESOURCE_HANDLE:
                import_type_mask = 0x80000000

                if field.res_imports[i] is not None:
                    import_type = field.res_imports[i].import_type_and_offset & import_type_mask

                    field.res_imports[i].import_type_and_offset = (field_offset + (i * field.definition.size)) | import_type

    return obj.offset
