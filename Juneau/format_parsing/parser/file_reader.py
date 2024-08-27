from struct import unpack

class FileReader():
    def __init__(self, data, BIG_ENDIAN):
        if type(data) == str: # todo remove after rework
            raise Exception("Improper usage of FileReader")

        self.byte_list = list(data)
        # self.byte_list = []
        self.BIG_ENDIAN = BIG_ENDIAN

        # self.byte_format_string = "B"
        # if self.BIG_ENDIAN:
        #     self.byte_format_string = '>' + self.byte_format_string

        # with open(file_path, "rb") as f:
        #     file_byte = f.read(1)

        #     while(len(file_byte)):
        #         unpacked_byte = unpack(self.byte_format_string, file_byte)[0]

        #         self.byte_list.append(unpacked_byte)
        #         file_byte = f.read(1)

    def get_bytearray(self, offset, size):
        return bytes(self.byte_list[offset : offset + size])

    def get_nsized_data_at_offset(self, offset, size_in_bytes):
        ret = 0

        for i in range(size_in_bytes):
            if self.BIG_ENDIAN:
                ret <<= 8
                ret |= self.byte_list[offset + i]
            else:
                ret |= self.byte_list[offset + i] << (i * 8)

        return ret

    def get_qword_at_offset(self, offset):
        return self.get_nsized_data_at_offset(offset, 8)

    def get_dword_at_offset(self, offset):
        return self.get_nsized_data_at_offset(offset, 4)


    def get_byte_at_offset(self, offset):
        return self.byte_list[offset]
