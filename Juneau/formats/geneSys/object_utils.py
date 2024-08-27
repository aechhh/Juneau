from Juneau.formats.geneSys.object_defintion import ObjectDefintion
from Juneau.formats.geneSys.object_instance import ObjectInstance
from Juneau.formats.geneSys.instance_field import InstanceField

from Juneau.formats.bndl.bndl import ImportEntry, ResourceEntry

from Juneau.utils.GeneSysTypeData import *

def create_genesys_obj_inst(obj_def: ObjectDefintion, parent_res : ResourceEntry) -> ObjectInstance:
    fields = []

    for i, field_def in enumerate(obj_def.fields):
        field = InstanceField(-1, i, field_def)
        field_type = field.definition.type & (~E_VALUETYPE_VARIABLE_ARRAY)

        if field.definition.type & E_VALUETYPE_VARIABLE_ARRAY == E_VALUETYPE_VARIABLE_ARRAY:
            field.is_list = True

            field.data.append(-1) # set offset to -1
            field.data.append(0) # set length to 0
            field.data.append(field.definition.pointer_list_elem_size) # set elem size

            fields.append(field)

            continue

        # create field data
        for i in range(field.definition.length):
            field.data.append(0)

            if field_type == E_VALUETYPE_STRING:
                field.string_data.append("\x00")

            if field_type == E_VALUETYPE_RESOURCE_HANDLE:
                field.res_imports.append(None)

        fields.append(field)

    # HACK we should just get the full 8 byte id from the res but we dont have it
    # so until this gets refactored we make the id from scratch
    res_id = ( ( 1 << (3*8) | obj_def.obj_ref_index << (2*8) ) << (4*8) ) | obj_def.obj_id

    genesys_def_import_entry = ImportEntry(res_id, 0x80000000)

    parent_res.imports.append(genesys_def_import_entry)
    parent_res.import_count += 1

    return ObjectInstance(-1, 0x0, obj_def, fields, genesys_def_import_entry)
