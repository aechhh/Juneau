class TextureData():
    def __init__(self, id, width, height, raw_pixel_data) -> None:
        self.id = id
        
        self.width = width
        self.height = height
        self.raw_pixel_data = raw_pixel_data

        self.dpg_tag = None
