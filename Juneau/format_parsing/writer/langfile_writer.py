from Juneau.formats.lang_string import LangString

from Juneau.format_parsing.writer.file_writer import FileWriter

def write_lang_file(lang_strs : list[LangString], big_endian, is_hpr) -> bytes:
    if is_hpr:
        LANG_FILE_HEADER_SIZE = 0x18
        STR_ID_SIZE = 0x4
        PTR_STR_LEN = 0x10
    else:
        LANG_FILE_HEADER_SIZE = 0x10
        STR_ID_SIZE = 0x4
        PTR_STR_LEN = 0x8

    num_strs = len(lang_strs)
    
    lang_file_writer = FileWriter(big_endian)

    lang_file_writer.alloc_file_space(LANG_FILE_HEADER_SIZE)

    if is_hpr:
        lang_file_writer.write_dword_at_offset(0x0, 0x01)
        lang_file_writer.write_dword_at_offset(0x4, num_strs)

        # allocate space for string id list
        str_id_list_start = lang_file_writer.alloc_file_space(num_strs * STR_ID_SIZE)
        lang_file_writer.write_qword_at_offset(0x8, str_id_list_start)

        # allocate space for the ptr:str_len list
        ptr_list_start = lang_file_writer.alloc_file_space(num_strs * PTR_STR_LEN)
        lang_file_writer.write_qword_at_offset(0x10, ptr_list_start)

    else:
        lang_file_writer.write_dword_at_offset(0x0, 0x01)
        lang_file_writer.write_dword_at_offset(0x4, num_strs)
        lang_file_writer.write_dword_at_offset(0x8, 0x10)

        # allocate space for string id list
        str_id_list_start = lang_file_writer.alloc_file_space(num_strs * STR_ID_SIZE)

        # allocate space for the ptr:str_len list
        ptr_list_start = lang_file_writer.alloc_file_space(num_strs * PTR_STR_LEN)

        lang_file_writer.write_dword_at_offset(0xC, ptr_list_start)

    str_id_list_offset = str_id_list_start
    ptr_str_len_list_offset = ptr_list_start
 
    for lang_str in lang_strs:
        full_str = lang_str.full_string
        str_id = int(lang_str.id)
        str_len = len(full_str) + 1 # '+ 1' accounts for null byte
        
        # each char gets stored as 2 bytes
        str_byte_arr = []

        # create byte array for the string, could be optimized to be one pass but i think this is cleaner
        for char in full_str:
            str_bytes = [0, 0]

            str_short = ord(char)

            if(big_endian):
                raise Exception("Not implemented yet")                
            else:
                str_bytes[1] = (str_short & 0xFF00) >> 8
                str_bytes[0] = str_short & 0xFF

            str_byte_arr.extend(str_bytes)

        # add null byte to string
        str_byte_arr.extend([0, 0])

        # write str id
        lang_file_writer.write_dword_at_offset(str_id_list_offset, str_id)
        
        # allocate space for string
        str_offset = lang_file_writer.alloc_file_space(len(str_byte_arr), alignment=2)

        # write entry in ptr:str_len list
        if is_hpr:
            lang_file_writer.write_qword_at_offset(ptr_str_len_list_offset, str_offset)
            lang_file_writer.write_dword_at_offset(ptr_str_len_list_offset + 0x8, str_len)
        else:
            lang_file_writer.write_dword_at_offset(ptr_str_len_list_offset, str_offset)
            lang_file_writer.write_dword_at_offset(ptr_str_len_list_offset + 0x4, str_len)

        # write string
        str_byte_offset = str_offset
        for byte in str_byte_arr:
            lang_file_writer.write_byte_at_offset(str_byte_offset, byte)

            str_byte_offset += 1

        str_id_list_offset += STR_ID_SIZE
        ptr_str_len_list_offset += PTR_STR_LEN

    return lang_file_writer.get_file_bytes()