# Defines a class that represents an object instance parsed from an instance file
# Contains a list of fields generated based of the object defintion
# Fields can be offsets to other objects raw data
# Fields can also be pointers to lists which can be a list of data or a list of objects

from Juneau.formats.geneSys.instance_field import InstanceField
from Juneau.formats.geneSys.object_defintion import ObjectDefintion

from Juneau.formats.bndl.bndl import ImportEntry

from Juneau.utils.GeneSysTypeData import *

from Juneau.utils.hp_crc32 import calculate_crc32

from typing import Self

class ObjectInstance():
    field_data : list[InstanceField]
    obj_def : ObjectDefintion

    def __init__(self, offset, obj_id, obj_def : ObjectDefintion, field_data : list[InstanceField], res_import : ImportEntry):
        # -- Metadata --
        # offset from within the file we parsed this from
        self.offset = offset

        # kinda a hack for storing the file name for use in the gui, p much only used/modified by gui code
        self.file_name = ""
        self.full_file_path = ""
        self.path_to_parent_bndl_id = ""

        # the object def that defines this object
        self.obj_def = obj_def

        # the in game id of the instance
        self.id = obj_id
        
        # -- Data from file --
        # list of instanceField objects, used for storing and reading field data of object
        self.field_data = field_data

        self.res_import : ImportEntry = res_import # for an individual object instance the first field of its header is a resource handle
                                     # to its genesys definition, then associated with this import entry

    def get_obj_param(self, param_name):
        # Note: In terms of typing this can return just about anything (See GenesysTypeData) so use with caution
        crc_hash = calculate_crc32(param_name)

        for field in self.field_data:
            if field.definition.id == crc_hash:
                return field
            
        print(f"Failed to find object parameter: '{param_name}'")

        return None


    def is_eq_to_other(self, other, print_diff):
        if other is None:
            return False

        if not isinstance(other, ObjectInstance):
            return False

        if not self.obj_def.is_eq_to_other(other.obj_def, print_diff):
            if print_diff:
                print("ObjectInstance.obj_def different: <above>")

            return False
    
        if self.id != other.id:
            if print_diff:
                print(f"ObjectInstance.id different: {self.id} != {other.id}")

            return False

        if len(self.field_data) != len(other.field_data):
            if print_diff:
                print(f"ObjectInstance.field_data length different: {len(self.field_data)} != {len(other.field_data)}")

            return False
        
        for fields in zip(self.field_data, other.field_data):
            if not fields[0].is_eq_to_other(fields[1], print_diff):
                if print_diff:
                    print("ObjectInstance.fields different: <above>")
                
                return False
            
        return True

    def __eq__(self, other: Self) -> bool:
        return self.is_eq_to_other(other, print_diff=False)

    def get_subobject_list(self) -> list[Self]:
        return self.__get_subobject_list()
    
    def __get_subobject_list(self) -> list[Self]:
        sub_objs = [self]

        for field in self.field_data:
            if len(field.subobjects) != 0:
                for obj in field.subobjects:
                    sub_objs.extend(obj.get_subobject_list())

            if field.is_list and field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK == E_VALUETYPE_INSTANCE:
                for obj in field.external_list_objects:
                    sub_objs.extend(obj.get_subobject_list())

        return sub_objs
    
    def get_fieldstruct_size(self):
        last_field_def = self.field_data[-1].definition
        return last_field_def.offset_into_fieldstruct + (last_field_def.size * last_field_def.length)