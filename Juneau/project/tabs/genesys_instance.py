import dearpygui.dearpygui as dpg

from struct import pack, unpack
from copy import copy

from Juneau.formats.geneSys.instance_field import ImportEntry, InstanceField
from Juneau.formats.geneSys.object_instance import ObjectInstance
from Juneau.formats.geneSys.object_defintion import ObjectDefintion
from Juneau.formats.geneSys.object_utils import create_genesys_obj_inst

from Juneau.formats.bndl.bndl import  BNDL, ResourceEntry

from Juneau.utils.GeneSysTypeData import *

class GenesysInstanceWindow():
    def __init__(self, parent_tag, res : ResourceEntry, parent_bndl : BNDL, window_manager) -> None:
        self.parent_tag = parent_tag # the tag of the parent dpg object
                                     # should be the root of the window
        self.resource_entry : ResourceEntry = res
        self.parent_bndl : BNDL = parent_bndl

        self.window_manager = window_manager

        self.obj_defs : list[ObjectDefintion] = self.parent_bndl.get_all_genesys_defs()

        self.create_obj_tree_node(self.resource_entry.unpacked_object, self.parent_tag, first=True)

    # will recurse through an object and its subobjects and write their data to screen
    def create_obj_tree_node(self, obj, parent_tag, first=False):
        label_str = f"{obj.obj_def.obj_name}, ID: {obj.id:08X}, Offset: {obj.offset:08X}"

        if first:
            self.populate_obj_tree_node(obj, parent_tag)
        else:
            obj_tree_node = dpg.add_tree_node(label=label_str, parent=parent_tag)

            # only load object data when user clicks on drop down menu
            # massive boost in the time it takes to load an object window
            with dpg.item_handler_registry() as registry:
                dpg.add_item_clicked_handler(
                    button = dpg.mvMouseButton_Left,
                    user_data = [obj, obj_tree_node],
                    callback = lambda _, __, u : self.populate_obj_tree_node(u[0], u[1]),
                )

                dpg.bind_item_handler_registry(obj_tree_node, registry)

    def populate_obj_tree_node(self, obj, obj_tree_node_tag):
        if len(dpg.get_item_children(obj_tree_node_tag, 1)) != 0:
            return

        with dpg.group(parent=obj_tree_node_tag):
            for _, field in enumerate(obj.field_data):
                field: InstanceField = field
                field_data_type = field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK

                tool_tip_str = f"ID: {field.definition.id:08X}, "
                tool_tip_str += f"Type: {get_field_type_name(field.definition.type)} ({field.definition.type}), "
                tool_tip_str += f"Length: {field.definition.length}, "
                tool_tip_str += f"Offset: {field.offset:08X}, "
                tool_tip_str += f"Size: {field.definition.size}, "
                tool_tip_str += f"Offset in file: {field.offset:08X}, "

                if field.is_list:
                    tool_tip_str += f"List Data: {str(field)}"

                with dpg.group(horizontal=True):
                    field_name_text = dpg.add_text(field.definition.get_name() + ": ")

                    with dpg.tooltip(field_name_text):
                        dpg.add_text(tool_tip_str, color=(210,210,210))

                    if field_data_type == E_VALUETYPE_INSTANCE:
                        if field.is_list:
                            with dpg.group() as g:
                                # create all sub obj tree nodes
                                for i, sub_obj in enumerate(field.external_list_objects):
                                    with dpg.group(horizontal=True, parent=g) as sg:
                                        self.create_obj_tree_node(sub_obj, sg)

                                        dpg.add_button(
                                            label="Delete Object",
                                            user_data=[obj, obj_tree_node_tag, field, i],
                                            callback=lambda _s, _a, u, : self._remove_obj_pointer_list(*u)
                                        )

                                # button for creating appending an object onto a pointer list
                                dpg.add_button(label="Add Object")

                                with dpg.popup(dpg.last_item(), modal=True, mousebutton=dpg.mvMouseButton_Left):
                                    # dpg.configure_item(window, title="Create object")

                                    dpg.add_text("Select object definition")
                                    dpg.add_separator()

                                    add_obj_combo_menu = dpg.add_combo(self.obj_defs, default_value=self.obj_defs[0])

                                    dpg.add_button(
                                        label="Create object",
                                        user_data=[obj, obj_tree_node_tag, field, add_obj_combo_menu],
                                        callback=lambda _s, _a, u : self._add_pointer_list_obj(*u),
                                    )

                        else:
                            num_subobjs = len([subobj for subobj in field.subobjects if subobj is not None])

                            with dpg.group() as g:
                                dpg.set_value(field_name_text, dpg.get_value(field_name_text)[:-2] + f" ({num_subobjs}/{field.definition.size}):")

                                # create all sub obj tree nodes
                                for i in range(field.definition.size):
                                    if i < len(field.subobjects) and field.subobjects[i] is not None:
                                        with dpg.group(horizontal=True, parent=g) as sg:
                                            self.create_obj_tree_node(field.subobjects[i], sg)

                                            dpg.add_button(
                                                label = "Delete Object",
                                                user_data = [obj, obj_tree_node_tag, field, i],
                                                callback = lambda _s, _a, u : self._remove_obj_field_list(*u),
                                            )
                                    else:
                                        # button for creating an object in an empty field list slot
                                        dpg.add_button(label="Create Object")

                                        with dpg.popup(dpg.last_item(), modal=True, mousebutton=dpg.mvMouseButton_Left):
                                            # dpg.configure_item(window, title="Create object")

                                            dpg.add_text("Select object definition")
                                            dpg.add_separator()

                                            create_obj_combo_menu = dpg.add_combo(self.obj_defs, default_value=self.obj_defs[0])

                                            dpg.add_button(
                                                label="Create object",
                                                user_data=[obj, obj_tree_node_tag, field, i, create_obj_combo_menu],
                                                callback=lambda _s, _a, u : self._create_obj_in_field_index(*u),
                                            )

                                        break

                        continue

                    self.draw_field_data(field)

    def _refresh_obj_window(self, obj, obj_tree_node_tag):
        dpg.delete_item(obj_tree_node_tag, children_only=True)

        self.populate_obj_tree_node(obj, obj_tree_node_tag)

    # --- Object creation and deletion callbacks ---
    def _add_pointer_list_obj(self, obj : ObjectInstance, obj_tree_node_tag, field : InstanceField, obj_def_combomenu):
        obj_def_name = dpg.get_value(obj_def_combomenu)

        def_for_new_obj = None
        for obj_def in self.obj_defs:
            if str(obj_def) == obj_def_name:
                def_for_new_obj = obj_def

        if def_for_new_obj is None:
            raise Exception("Could not find challenge definition, something really bad has happened")

        new_obj : ObjectInstance = create_genesys_obj_inst(def_for_new_obj, self.resource_entry)

        field.external_list_data.append(new_obj.offset)
        field.external_list_objects.append(new_obj)

        field.data[1] += 1

        self._refresh_obj_window(obj, obj_tree_node_tag)

    def _remove_obj_pointer_list(self, obj : ObjectInstance, obj_tree_node_tag, field : InstanceField, index):
        field.external_list_data.pop(index)
        field.external_list_objects.pop(index)

        field.data[1] -= 1

        self._refresh_obj_window(obj, obj_tree_node_tag)

    def _create_obj_in_field_index(self, obj : ObjectInstance, obj_tree_node_tag, field : InstanceField, index, obj_def_combomenu):
        obj_def_name = dpg.get_value(obj_def_combomenu)

        def_for_new_obj = None
        for obj_def in self.obj_defs:
            if str(obj_def) == obj_def_name:
                def_for_new_obj = obj_def

        if def_for_new_obj is None:
            raise Exception("Could not find challenge definition, something really bad has happened")

        num_subobjs = len([subobj for subobj in field.subobjects if subobj is not None])

        if index == len(field.subobjects):
            field.subobjects.append(create_genesys_obj_inst(def_for_new_obj, self.resource_entry))
        elif index == num_subobjs:
            field.subobjects[index] = create_genesys_obj_inst(def_for_new_obj, self.resource_entry)
        else:
            print("Please define previous objects first")

        self._refresh_obj_window(obj, obj_tree_node_tag)

    def _remove_obj_field_list(self, obj : ObjectInstance, obj_tree_node_tag, field : InstanceField, index):
        field.subobjects[index] = None

        self._refresh_obj_window(obj, obj_tree_node_tag)


    def write_field_data_callback(self, _sender, app_data, user_data):
        # user_data = {
        # "field" = field
        # "data_index" = the index of the data being changed in whatever list is being modified (may not exist)
        # }

        field = user_data["field"]

        if field.is_list:
            if field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK == E_VALUETYPE_STRING:
                field_data_list = field.string_data
            else:
                field_data_list = field.external_list_data

            field_data_type = field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK
            field_data_size = field.data[2]
        else:
            if field.definition.type == E_VALUETYPE_STRING:
                field_data_list = field.string_data
            else:
                field_data_list = field.data

            field_data_type = field.definition.type
            field_data_size = field.definition.size

        if field_data_type == E_VALUETYPE_STRING:
            index = user_data["data_index"]

            new_str_data = app_data + '\x00'
            print("Attempting to change string data")
            print(f"Prev Value: {field_data_list[index]}")

            field_data_list[index] = new_str_data

            print(f"New Value: {field_data_list[index]}")

        elif field_data_type == E_VALUETYPE_BOOL:
            assert app_data in [True, False]

            index = user_data["data_index"]

            print(f"Attempting to change byte data at {index} to {app_data}")

            field_data_list[index] = 1 if app_data else 0

        elif field_data_type == E_VALUETYPE_BYTE:
            assert app_data < 0x10

            index = user_data["data_index"]

            print(f"Attempting to change byte data at {index} to {app_data}")

            field_data_list[index] = app_data

        elif field_data_type == E_VALUETYPE_FLOAT32:
            index = user_data["data_index"]
            float_data = unpack('I', pack('f', app_data))[0]

            print(f"Attempting to change float data at {index} to {float_data}")

            field_data_list[index] = float_data

        elif field_data_type == E_VALUETYPE_INT32:
            index = user_data["data_index"]
            int_data = unpack('I', pack('i', app_data))[0]

            print(f"Attempting to change int data at {index} to {int_data}")

            field_data_list[index] = int_data

        elif field_data_type == E_VALUETYPE_RESOURCE_HANDLE:
            for i, data in enumerate(field_data_list):
                import_entry : ImportEntry = field.res_imports[i]

                if import_entry is not None:
                    import_entry_res = self.parent_bndl.get_res_from_id(import_entry.resourse_id)
                    if import_entry_res is not None:
                        dpg.add_button(
                            label=f"Import: {import_entry.resourse_id:016X}",
                            user_data=[self.parent_bndl, import_entry_res],
                            callback = lambda _s, _a, u : self.window_manager.add_window(*u) # this is a circular import soo uhh oops
                        )
                    else:
                        dpg.add_text(f"Unknown import ID: {import_entry.resourse_id:016X}")

                else:
                    dpg.add_text("<None>")

        else:
            index = user_data["data_index"]

            if app_data == '':
                app_data = '0'

            data = int(app_data, 16)

            print(f"Attempting to change data at index {index} to {data} ({data:064X})")

            field_data_list[index] = data

    def draw_field_data(self, field):
        if field.is_list:
            field_data_list = field.external_list_data
            field_data_type = field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK
            field_data_size = field.data[2]

            if field.definition.type & E_VALUETYPE_VARIABLE_ARRAY_MASK == E_VALUETYPE_STRING:
                field_data_list = field.string_data
        else:
            if field.definition.type == E_VALUETYPE_STRING:
                field_data_list = field.string_data
            else:
                field_data_list = field.data

            field_data_type = field.definition.type
            field_data_size = field.definition.size

        # TODO make this better
        num_input_width = 150

        user_data = {
            "field": field
        }

        with dpg.group():
            if field_data_type == E_VALUETYPE_STRING:
                for i, field_str in enumerate(field.string_data):
                    user_data["data_index"] = i

                    if field_str == "" or field_str is None:
                        str_data = ""
                    else:
                        assert field_str[-1] == '\x00'
                        str_data = field_str[:-1]

                    dpg.add_input_text(default_value=str_data, hint="<Empty String>", callback=self.write_field_data_callback, user_data=copy(user_data))

            elif field_data_type == E_VALUETYPE_BOOL:
                for i, data in enumerate(field_data_list):
                    assert data in [0, 1]

                    user_data["data_index"] = i

                    dpg.add_checkbox(default_value=bool(data), callback=self.write_field_data_callback, user_data=copy(user_data))

            elif field_data_type == E_VALUETYPE_BYTE:
                for i, data in enumerate(field_data_list):
                    user_data["data_index"] = i

                    dpg.add_input_int(default_value=data, max_value=0xF, max_clamped=True, min_value=0, min_clamped=True, step=0, step_fast=0, width=num_input_width, callback=self.write_field_data_callback, user_data=copy(user_data))

            elif field_data_type == E_VALUETYPE_FLOAT32:
                data_list = [unpack('f', pack('I', data))[0] for data in field_data_list]

                for i, data in enumerate(data_list):
                    user_data["data_index"] = i

                    dpg.add_input_float(default_value=data, step=0, step_fast=0, width=num_input_width, callback=self.write_field_data_callback, user_data=copy(user_data))

            elif field_data_type == E_VALUETYPE_INT32:
                data_list = [unpack('i', pack('I', data))[0] for data in field_data_list]

                for i, data in enumerate(data_list):
                    user_data["data_index"] = i

                    dpg.add_input_int(default_value=data, step=0, step_fast=0, width=num_input_width, callback=self.write_field_data_callback, user_data=copy(user_data))

            elif field_data_type == E_VALUETYPE_RESOURCE_HANDLE:
                for i, data in enumerate(field_data_list):
                    import_entry : ImportEntry = field.res_imports[i]

                    if import_entry is not None:
                        import_entry_res = self.parent_bndl.get_res_from_id(import_entry.resourse_id)
                        if import_entry_res is not None:
                            dpg.add_button(label=f"Import: {import_entry.resourse_id:016X}", callback = lambda _, __, u : self.window_manager.add_window(u[0], u[1]), user_data=[self.parent_bndl, import_entry_res])
                        else:
                            dpg.add_text(f"Unknown import ID: {import_entry.resourse_id:016X}")

                    else:
                        dpg.add_text("<None>")

            else:
                size_of_char = 9 # TODO adjust to size of font ( or just put in the const file i hate gui programming )
                for i, data in enumerate(field_data_list):
                    user_data["data_index"] = i

                    with dpg.group(horizontal=True):
                        dpg.add_input_text(hexadecimal=True, default_value=f"{data:0{field_data_size*2}X}", no_spaces=True, width=field_data_size* 2 * size_of_char, callback=self.write_field_data_callback, user_data=copy(user_data))

                        if field_data_type == E_VALUETYPE_RESOURCE_ID:
                            if data == 0: # TODO get ids
                                dpg.add_text("<None>")
                            else:
                                dpg.add_text("<Unknown ID>")
