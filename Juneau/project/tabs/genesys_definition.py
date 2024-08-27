import dearpygui.dearpygui as dpg

from Juneau.formats.geneSys.object_defintion import ObjectDefintion

from Juneau.formats.bndl.bndl import  BNDL, ResourceEntry

from Juneau.utils.GeneSysTypeData import *

class GenesysDefinitionWindow():
    def __init__(self, parent_tag, res : ResourceEntry) -> None:
        self.parent_tag = parent_tag # the tag of the parent dpg object
                                     # should be the root of the window
        self.resource_entry : ResourceEntry = res

        self.definition : ObjectDefintion = res.unpacked_object

        dpg.add_text(f"Name: {self.definition.obj_name}")
        dpg.add_text(f"ID: {self.definition.obj_id:08X}")
        dpg.add_text(f"Definition ID: {self.definition.obj_def_id:08X}")
        dpg.add_text(f"Index: {self.definition.obj_ref_index}")
        dpg.add_text(f"Number of Definitions: {self.definition.num_defs}")

        dpg.add_separator()

        dpg.add_text("Definitions:")

        with dpg.table(header_row=True, row_background=True,
                            borders_innerH=True, borders_outerH=True, borders_innerV=True,
                            borders_outerV=True, delay_search=True, resizable=True):

            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Type")
            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="Length")
            dpg.add_table_column(label="Size")

            for field in self.definition.fields:
                with dpg.table_row():
                    is_list = field.pointer_list_elem_size is not None

                    dpg.add_text(f"{field.get_name()}")
                    dpg.add_text(f"{get_field_type_name(field.type)}")
                    dpg.add_text(f"{field.id:08X}")
                    dpg.add_text(f"{field.length}")
                    dpg.add_text(f"{field.size if not is_list else field.pointer_list_elem_size}")
                                     