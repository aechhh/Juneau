from random import randint
from typing import Self

from Juneau.utils.geneSysBetaIdDirectory import get_genesys_beta_name_from_id


# represents a single field within an object defintion
class DefinitionField():
    def __init__(self, field_id, field_type, length, field_offset, field_size):
        self.id = field_id
        self.type = field_type
        # length of array, usually 1 but can be larger
        self.length = length
        self.offset_into_fieldstruct = field_offset

        # size of data in bytes
        self.size = field_size

        # this gets set after object parsing and only if the definition is a pointer list
        self.pointer_list_elem_size = None

        # # set when data type is an instance, used for object creation
        # self.instance_obj_def = None

    def get_name(self):
        name = get_genesys_beta_name_from_id(self.id)

        if name == "unk":
            name = f"unk_{self.id:08X}"

        return name

    def is_eq_to_other(self, other, print_diff):
        if other is None:
            if print_diff:
                print("DefinitionField: other is none")

            return False

        if self.id != other.id:
            if print_diff:
                print(f"DefinitionField.id difference: {self.id} != {other.id}")

            return False
        
        if self.type != other.type:
            if print_diff:
                print(f"DefinitionField.type difference: {self.type} != {other.type}")

            return False
        
        if self.length != other.length:
            if print_diff:
                print(f"DefinitionField.length difference: {self.length} != {other.length}")

            return False
        
        if self.offset_into_fieldstruct != other.offset_into_fieldstruct:
            if print_diff:
                print(f"DefinitionField.offset_into_fieldstruct difference: {self.offset_into_fieldstruct} != {other.offset_into_fieldstruct}")

            return False
        
        if self.size != other.size:
            if print_diff:
                print(f"DefinitionField.size difference: {self.size} != {other.size}")

            return False
        
        return True

    def __eq__(self, other: Self) -> bool:
        return self.is_eq_to_other(other, print_diff=False)

# represents an entire object defintion, class members and field data is automatically created by file_parser
class ObjectDefintion():
    fields : list[DefinitionField]

    def __init__(self, obj_id, obj_def_id, offset_to_defs, num_defs, obj_ref_index, name):        
        # ID used to represent the type of the object in the reference list
        self.obj_id = obj_id
        
        # ID used in the instance file to identify an object in its header
        self.obj_def_id = obj_def_id

        self.offset_to_defs = offset_to_defs
        self.num_defs = num_defs
        self.obj_ref_index = obj_ref_index
        self.obj_name = name

        self.fields = []

    def is_eq_to_other(self, other, print_diff):
        if other is None:
            if print_diff:
                print("ObjectDefintion: other is none")

            return False

        if not isinstance(other, ObjectDefintion):
            if print_diff:
                print("Compared definition is not of type ObjectDefintion")

            return False

        if self.obj_id != other.obj_id:
            if print_diff:
                print(f"ObjectDefintion.obj_id difference: {self.obj_id} != {other.obj_id}")

            return False
        
        if self.obj_def_id != other.obj_def_id:
            if print_diff:
                print(f"ObjectDefintion.obj_def_id difference: {self.obj_def_id} != {other.obj_def_id}")

            return False
        
        if self.num_defs != other.num_defs:
            if print_diff:
                print(f"ObjectDefintion.num_defs difference: {self.num_defs} != {other.num_defs}")
            
            return False
        
        if self.obj_ref_index != other.obj_ref_index:
            if print_diff:
                print(f"ObjectDefintion.obj_ref_index difference: {self.obj_ref_index} != {other.obj_ref_index}")

            return False
        
        if self.obj_name != other.obj_name:
            if print_diff:
                print(f"ObjectDefintion.obj_name difference: {self.obj_name} != {other.obj_name}")

            return False
        
        for field_defs in zip(self.fields, other.fields):
            if not field_defs[0].is_eq_to_other(field_defs[1], print_diff):
                if print_diff:
                    print("ObjectDefintion.field_defs difference: <above>")

                return False
            
        return True

    def __eq__(self, other: Self) -> bool:
        return self.is_eq_to_other(other, print_diff=False)

    def __str__(self) -> str:
        return f"{self.obj_name}_{self.obj_def_id:08X}"

    def get_imhex_struct_defintion(self):
        if len(self.fields) == 0:
            print(f"[objectDefintion - {self.obj_name}]: Warning: creating imhex struct with none field data")

        return_string = ""

        return_string += f"struct {self.obj_name}_{self.obj_def_id}"
        return_string += " {\n"

        index = -1
        last_offset = 0
        last_size = 0
        for field in self.fields:
            index += 1

            field_size = field.size * 8

            # if (field_size / 8) not in [1,4,8,12]:
            #     raise Exception("New field size just dropped")

            # if last_offset + last_size != field.field_offset:
            #     return_string += f"padding[{ field.field_offset - (last_offset + last_size) }];\n"

            #     if (field.field_offset - (last_offset + last_size)) < 0:
            #         pass

            last_offset = field.offset_into_fieldstruct
            last_size = field_size / 8

            field_name = field.get_name()
            imhex_color = f"[[color(\"{randint(0,225):02X}00{randint(50,255):02X}\")]]"

            # if field size == 96, we treat it like an int array with length 3; these are almost always lists formatted like: (list_type, list_length, elem_size)
            if field_size == 96:
                return_string += f"u{int(field_size/3)} name_{field_name}_id_{field.id:08X}_index_{index}_type_{field.type}[3] {imhex_color};\n"
                continue

            if field_size == 512:
                return_string += f"u{32} name_{field_name}_id_{field.id:08X}_index_{index}_type_{field.type}[16] {imhex_color};\n"
                continue

            return_string += f"u{field_size} name_{field_name}_id_{field.id:08X}_index_{index}_type_{field.type}[{field.length}] {imhex_color};\n"

        return_string += "};\n"

        return return_string