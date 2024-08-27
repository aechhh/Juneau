from Juneau.format_parsing.parser.file_reader import FileReader

def parse_textfile_data(textfile_data, BIG_ENDIAN) -> bytes:
    textfile_reader = FileReader(textfile_data, BIG_ENDIAN)

    text_length = textfile_reader.get_dword_at_offset(0x0)

    text_data = textfile_reader.get_bytearray(0x4, text_length)

    return text_data # not converted to string because data can be compiled Lua files
