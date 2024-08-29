import dearpygui.dearpygui as dpg

class TextureData():
    def __init__(self, id, width, height, raw_pixel_data) -> None:
        self.id = id
        
        self.width = width
        self.height = height
        self.raw_pixel_data = raw_pixel_data

        with dpg.texture_registry(show=False):
            flattened_texture = []

            for row in self.raw_pixel_data:
                for pixel in row:
                    flattened_texture.extend(color / 255 for color in pixel)

            self.dpg_tag = dpg.add_static_texture(width=self.width, height=self.height, default_value=flattened_texture)
