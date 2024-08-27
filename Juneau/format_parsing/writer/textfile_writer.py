from Juneau.format_parsing.writer.file_writer import FileWriter

def write_textfile(text_data : bytes, BIG_ENDIAN):
    textfile_writer = FileWriter(BIG_ENDIAN)

    text_data_size = len(text_data)

    textfile_writer.alloc_file_space(0x4)
    textfile_writer.write_dword_at_offset(0x0, text_data_size)

    textfile_writer.alloc_file_space(text_data_size)
    textfile_writer.write_byte_array(0x4, text_data)

    textfile_writer.align(0x10)

    return textfile_writer.get_file_bytes()
