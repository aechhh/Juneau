import dearpygui.dearpygui as dpg

from Juneau.formats.bndl.bndl import ResourceEntry
from Juneau.formats.texture.texture_file import TextureData

class GenesysDefinitionWindow():
    def __init__(self, parent_tag, res: ResourceEntry) -> None:
        self.parent_tag = parent_tag  # the tag of the parent dpg object
        # should be the root of the window
        self.resource_entry: ResourceEntry = res


        if self.resource_entry.unpacked_object is not None:
            self.texture : TextureData = self.resource_entry.unpacked_object

            dpg.add_image(self.texture.dpg_tag)
        else:
            dpg.add_text("Sorry, HPR textures are not supported at the moment")