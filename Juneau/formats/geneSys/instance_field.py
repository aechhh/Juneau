from typing import Self

from Juneau.formats import DefinitionField, ImportEntry

from Juneau.utils.GeneSysTypeData import *


class InstanceField():
    data : list
    # subobjects : list[ObjectInstance]
    # external_list_objects : list[ObjectInstance]

    def __init__(self, offset, index, field_def : DefinitionField) -> None:
        # --Meta Data--
        self.offset = offset
        self.index = index
        self.definition = field_def

        # --Field Data--
        # Data from the field struct, list of list of 4 byte values
        # Will almost always be one in length but thats entirely dependent on the definitions length
        # if self.is_list == true: data[0] = offset, data[1] = length, data[2] = elem_size
        # TODO figure out a better way to do this.
        self.data = []

        # if field is an instance type, this will contain its subobjects
        self.subobjects = []

        # Will be true if field_def.type & 0x1000 == 0x1000, that means its a pointer list
        # Masking the type with 0xFFF will give the varible type that the list contains
        self.is_list = False

        # list of data that is pointed to by a pointer list, type dictated by the field_def.type & 0xFFF
        # will be empty if field is a regular instance
        self.external_list_data = []

        # list of objects that were pointed to by the above list
        # will be empty unless field is an instance pointer list
        self.external_list_objects = []

        self.string_data : list[str] = []

        # contains all import entries referenced by the object, objects can be None
        self.res_imports : list[ImportEntry] = []



    def __pointer_lists_eq(self, other: Self, print_diff : bool) -> bool:
        # check list length
        if self.data[1] != other.data[1]:
            if print_diff:
                print(f"InstanceField_pointerlist.length different: {self.data[1]} != {other.data[1]}")

            return False

        # check elem size
        if self.data[2] != other.data[2]:
            if print_diff:
                print(f"InstanceField_pointerlist.elem_size different: {self.data[2]} != {other.data[2]}")

            return False

        # data type check may be unnecessary since we already check field def in __eq__ before calling this func
        self_data_type = self.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK
        other_data_type = other.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK

        if self_data_type != other_data_type:
            if print_diff:
                print(f"InstanceField_pointerlist.data_type different: {self_data_type} != {other_data_type}")

            return False

        if self_data_type == E_VALUETYPE_RESOURCE_HANDLE:
            if len(self.res_imports) != len(other.res_imports):
                if print_diff:
                    print("InstanceField_pointerlist.res_imports different: list length mismatch")
                return False

            for imports in zip(self.res_imports, other.res_imports):
                if (imports[0] is None) !=  (imports[1] is None):
                    if print_diff:
                        print(f"InstanceField.res_imports different: one is None {imports[0]} != {imports[1]}")

                    return False

                if imports[0] is None and imports[1] is None:
                    continue

                if imports[0].resourse_id != imports[1].resourse_id:
                    if print_diff:
                        print(f"InstanceField_pointerlist.res_imports different: id mismatch {imports[0].resourse_id} != {imports[1].resourse_id}")

                    return False

        elif self_data_type == E_VALUETYPE_STRING:
            if len(self.string_data) != len(other.string_data):
                if print_diff:
                    print("InstanceField_pointerlist.string_data different: list length mismatch")
                return False

            for string_data in zip(self.string_data, other.string_data):
                if string_data[0] != string_data[1]:
                    if print_diff:
                        print(f"InstanceField_pointerlist.string_data difference: {string_data[0]} != {string_data[1]}")

                    return False

        elif self_data_type == E_VALUETYPE_INSTANCE:
            if len(self.external_list_objects) != len(other.external_list_objects):
                if print_diff:
                    print("InstanceField_pointerlist.external_list_objects different: list length mismatch")

                return False

            for objs in zip(self.external_list_objects, other.external_list_objects):
                if (objs[0] is None) !=  (objs[1] is None):
                    if print_diff:
                        print(f"InstanceField.external_list_objects different: one is None {objs[0]} != {objs[1]}")

                    return False

                if objs[0] is None and objs[1] is None:
                    continue

                if not objs[0].is_eq_to_other(objs[1], print_diff):
                    if print_diff:
                        print("InstanceField_pointerlist.external_list_objects different: <above>")

                    return False
        else:
            if len(self.external_list_data) != len(other.external_list_data):
                if print_diff:
                    print("InstanceField_pointerlist.external_list_data different: list length mismatch")

                return False

            for data in zip(self.external_list_data, other.external_list_data):
                if data[0] != data[1]:
                    if print_diff:
                        print(f"InstanceField_pointerlist.external_list_data different: {data[0]} != {data[1]}")

                    return False

        return True

    def is_eq_to_other(self, other, print_diff):
        if other is None:
            if print_diff:
                print("InstanceField: other is none")

            return False

        if not self.definition.is_eq_to_other(other.definition, print_diff):
            if print_diff:
                print("InstanceField.definition different: <above>")

            return False

        if self.is_list != other.is_list:
            if print_diff:
                print("InstanceField.is_list difference: is_list mismatch")

            return False

        if self.is_list:
            return self.__pointer_lists_eq(other, print_diff)

        if self.definition.type == E_VALUETYPE_INSTANCE:
            if len(self.subobjects) != len(other.subobjects):
                if print_diff:
                    print("InstanceField.subobjects different: list length mismatch")

                return False

            for objs in zip(self.subobjects, other.subobjects):
                if (objs[0] is None) !=  (objs[1] is None):
                    if print_diff:
                        print(f"InstanceField.subobjects different: one is None {objs[0]} != {objs[1]}")

                    return False

                if objs[0] is None and objs[1] is None:
                    continue


                if not objs[0].is_eq_to_other(objs[1], print_diff):
                    if print_diff:
                        print("InstanceField.subobjects different: <above>")

                    return False

            return True

        if self.definition.type == E_VALUETYPE_STRING:
            if len(self.string_data) != len(other.string_data):
                if print_diff:
                    print("InstanceField.string_data different: list length mismatch")
                return False

            for string_data in zip(self.string_data, other.string_data):
                if string_data[0] != string_data[1]:
                    if print_diff:
                        print(f"InstanceField.data (string_data) difference: {string_data[0]} != {string_data[1]}")

                    return False

            return True

        if self.definition.type == E_VALUETYPE_RESOURCE_HANDLE:
            if len(self.res_imports) != len(other.res_imports):
                if print_diff:
                    print("InstanceField.res_imports different: list length mismatch")
                return False

            for imports in zip(self.res_imports, other.res_imports):
                if (imports[0] is None) !=  (imports[1] is None):
                    if print_diff:
                        print(f"InstanceField.res_imports different: one is None {imports[0]} != {imports[1]}")

                    return False

                if imports[0] is None and imports[1] is None:
                    continue

                if imports[0].resourse_id != imports[1].resourse_id:
                    if print_diff:
                        print(f"InstanceField.res_imports different: id mismatch {imports[0].resourse_id} != {imports[1].resourse_id}")

                    return False

            return True

        if len(self.data) != len(self.data):
            if print_diff:
                print("InstanceField.data different: list length mismatch")

            return False

        for data in zip(self.data, other.data):
            if data[0] != data[1]:
                if print_diff:
                    print(f"InstanceField.data difference: {data[0]} != {data[1]}")

                return False

        return True

    def __eq__(self, other: Self) -> bool:
        return self.is_eq_to_other(other, print_diff=False)


    def get_list_size(self):
        if not self.is_list:
            print("[instanceField] - WARNING: Non list field attempted to get list size data")
            return 0

        return len(self.external_list_data) * self.data[2]

    def __str__(self) -> str:
        if self.is_list:
            return f"Length: {self.data[1]}, Elem Size: {self.data[2]}"

        return str([f"{d:0{self.definition.size*2}X}" for d in self.data])
