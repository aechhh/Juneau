from copy import deepcopy
from struct import unpack, pack

from texture2ddecoder import decode_bc3, decode_bc1

from Juneau.format_parsing.parser.file_reader import FileReader
from Juneau.formats.texture.texture_file import TextureData

def parse_texture(main_mem_data, graphics_data, BIG_ENDIAN) -> TextureData:
    dat_file_reader = FileReader(main_mem_data, BIG_ENDIAN)
    texture_file_reader = FileReader(graphics_data, BIG_ENDIAN)

    # ----- parsing .dat file -----
    magic = dat_file_reader.get_dword_at_offset(0x8)

    if magic != 0x1:
        raise Exception(f"Unexpected texture .dat magic number in file {file_path}")

    # parse width and height from file
    width = dat_file_reader.get_nsized_data_at_offset(0x10, 0x2)
    height = dat_file_reader.get_nsized_data_at_offset(0x12, 0x2)

    # parse texture type (either 0x15 for bgra data, 'DXT1' or 'DXT5')
    texture_type = dat_file_reader.get_dword_at_offset(0xC)

    # ----- parsing _texture.dat -----

    # create empty pixel data array
    temp_empty_row = [[0,0,0,0] for _ in range(width)]
    texture_pixel_data = [deepcopy(temp_empty_row) for _ in range(height)]

    # pixel data is 3d array//2d array of 4 wide pixel arrays
    # [y][x] = [r,g,b,a]

    if texture_type == 0x15:
        # parse raw pixel data
        for x in range(width):
            for y in range(height):
                pixel_offset = (y * width + x) * 4

                b, g, r, a = unpack("BBBB", pack("I", texture_file_reader.get_dword_at_offset(pixel_offset)))

                texture_pixel_data[y][x][0] = r
                texture_pixel_data[y][x][1] = g
                texture_pixel_data[y][x][2] = b
                texture_pixel_data[y][x][3] = a
    else:
        # parse dxt texture data
        texture_type = "".join( [chr(dat_file_reader.get_byte_at_offset(0xC + i)) for i in range(4)] )

        if texture_type == "DXT5":
            decoded_data = decode_bc3(graphics_data, width, height)
        elif texture_type == "DXT1":
            decoded_data = decode_bc1(graphics_data, width, height)
        else:
            raise Exception(f"Unknown texture type {texture_type} in {file_path}")

        offset = 0
        for y in range(height):
            for x in range(width):
                b, g, r, a = unpack("BBBB", decoded_data[offset:offset+4])

                texture_pixel_data[y][x][0] = r
                texture_pixel_data[y][x][1] = g
                texture_pixel_data[y][x][2] = b
                texture_pixel_data[y][x][3] = a

                offset += 4

    return TextureData(id, width, height, texture_pixel_data)
