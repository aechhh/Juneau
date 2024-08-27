from Juneau.formats.lang_string import LangString

from Juneau.format_parsing.parser.file_reader import FileReader

def read_lang_file(byte_data, big_endian, is_hpr) -> list[LangString]:
    lang_file = FileReader(byte_data, big_endian)

    num_strs = lang_file.get_dword_at_offset(0x4)

    str_id_list_offset = None
    str_ptr_list_offset = None

    if is_hpr:
        str_id_list_offset = lang_file.get_qword_at_offset(0x8)
        str_ptr_list_offset = lang_file.get_qword_at_offset(0x10)
    else:
        str_id_list_offset = lang_file.get_dword_at_offset(0x8)
        str_ptr_list_offset = lang_file.get_dword_at_offset(0xC)

    str_ids = []

    for i in range(str_id_list_offset, str_id_list_offset + (num_strs * 4), 4):
        str_ids.append(lang_file.get_dword_at_offset(i))

    counter = 0
    strs = []

    str_ptr_len_size = None

    if is_hpr:
        str_ptr_len_size = 0x10
    else:
        str_ptr_len_size = 0x8

    for ptr in range(str_ptr_list_offset, str_ptr_list_offset + (num_strs * str_ptr_len_size), str_ptr_len_size):
        str_offset = None
        str_len = None

        if is_hpr:
            str_offset = lang_file.get_qword_at_offset(ptr)
            str_len = lang_file.get_dword_at_offset(ptr + 0x8)
        else:
            str_offset = lang_file.get_dword_at_offset(ptr)
            str_len = lang_file.get_dword_at_offset(ptr + 0x4)

        strs.append(LangString(str_offset, str_len, str_ids[counter]))

        counter += 1

    seen_specials = set()
    for str_obj in strs:
        curr_str = ""

        for i in range(str_obj.len):
            char_offset = str_obj.offset + i * 2
            special_char_offser = char_offset + 1

            char = lang_file.get_byte_at_offset(char_offset)
            special_char = lang_file.get_byte_at_offset(special_char_offser)

            if char == 0 and special_char == 0:
                if i != str_obj.len - 1:
                    raise Exception("string parsing has failed so bad")

                continue

            # # deal with regular chars
            # if special_char == 0:
            #     curr_str += chr(char)
            #     continue

            char_num = ((special_char << 8) | char)

            if char_num > 128 and not char_num in seen_specials:
                seen_specials.add(char_num)

            curr_str += chr(char_num)

            # # dealing with special charecters
            # special_char = (char << 8) | special_char

            # curr_str += ("|" + f"{special_char:04X}" + "|")

        # TODO figure out whats going on with
        # if str_obj.id == 172383:
        #     print('h')

        str_obj.full_string = curr_str

    return strs
