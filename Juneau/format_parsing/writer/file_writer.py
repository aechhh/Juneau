# this class writes to a given file by first allocating the space needed in the file and returning a pointer (offset) to that location
# this allows a method that uses this class to write to a file by:
#   1. allocating space for an object,
#   2. saving the pointer for that object to be written wherever its needed  
#   3. writing the data in the allocated space whenever the parent needs to

# This is also convenient because it allows byte alignment management be abstracted to this class alone
# This also allows makes it easy for us to create space for a list, then write list objects to the file then put their offsets into the offset list

from struct import pack

class FileWriter():
    def __init__(self, BIG_ENDIAN) -> None:
        self.byte_buffer = []

        self.__alloc_offset = 0

        self.BIG_ENDIAN = BIG_ENDIAN

    # this class writes to the file by first allocating the space needed in the file and returning a pointer (offset) to that location
    # this allows a method that uses this class to write to a file by:
    #   1. allocating space for an object,
    #   2. saving the pointer for that object to be written wherever its needed  
    #   3. writing the data in the allocated space whenever the parent needs to
    def alloc_file_space(self, bytes_needed, alignment=16) -> int:
        # testing if offsets line up better when no alignment is done when no bytes are actually needed
        # this happens when a pointer list has a length of 0 for example 
        if bytes_needed == 0:
            return self.__alloc_offset

        self.align(alignment)

        # --- Allocating the space requested ---
        offset_to_allocated_space = self.__alloc_offset

        # add bytes to end of dword buffer
        for _ in range(bytes_needed):
            self.byte_buffer.append(0)

        # update the current offset to the end of the file
        self.__alloc_offset += bytes_needed

        # return the offset to the newly allocated space
        return offset_to_allocated_space
    
    def align(self, alignment):
        bytes_needed_to_align = self.__align_offset(alignment)

        for _ in range(bytes_needed_to_align):
            self.byte_buffer.append(0)
        self.__alloc_offset += bytes_needed_to_align

        return self.__alloc_offset
    
    # returns the additional amount of bytes needed to alloc to align data to 4 bytes
    def __align_offset(self, byte_alignment) -> int:
        return byte_alignment - self.__alloc_offset % byte_alignment if self.__alloc_offset % byte_alignment != 0 else 0

    def close_file(self, file_path, align=False):
        out_file = open(file_path, "wb")
        
        self.write_to_and_close_file_obj(out_file, align)

    def write_to_and_close_file_obj(self, out_file, align=False):
        if align:
            bytes_needed_to_align = self.__align_offset(16)

            for _ in range(bytes_needed_to_align):
                self.byte_buffer.append(0)

            self.__alloc_offset += bytes_needed_to_align
        
        out_file.write(bytes(self.byte_buffer))
        
        out_file.close()

    def __write_failure(self, err_string, offset, dword):
            print(err_string)
            print(f"Offset: {offset:08X}")
            print(f"Data: {dword:08X}")
            print(f"Current dword buffer size: {self.__alloc_offset:08X}")
            raise Exception("")
    
    def write_nsized_byte_data_at_offset(self, offset, data, size):
        if offset > len(self.byte_buffer) - size:
            self.__write_failure("Tried to write to file at non-allocated area", offset, data)

        if data >= 2 ** (8*size) or data < 0:
            self.__write_failure(f"Tried to write invalid {size}-byte data to file", offset, data)

        for i in range(size):
            if self.BIG_ENDIAN:
                byte_val = (data >> (8 * (size - 1 - i))) & 0xFF
            else:
                byte_val = (data >> (8 * i)) & 0xFF

            self.byte_buffer[offset + i] = byte_val

    def write_byte_at_offset(self, offset, byte):
        if offset > len(self.byte_buffer) - 1:
            self.__write_failure("Tried to write byte to file at non allocated area", offset, byte)
        
        if byte > 0xFF or byte < 0:
            self.__write_failure("Tried to write invalid byte to file", offset, byte)

        self.byte_buffer[offset] = byte

    def write_dword_at_offset(self, offset, dword):
        self.write_nsized_byte_data_at_offset(offset, dword, 4)

    def write_qword_at_offset(self, offset, qword):
        self.write_nsized_byte_data_at_offset(offset, qword, 8)

    # assumes allocation has been done
    def write_struct_data(self, offset, format_str, data_list):
        self.write_byte_array(offset, pack(format_str, *data_list))

    def write_byte_array(self, offset, byte_arr):
        for i, byte in enumerate(byte_arr):
            self.write_byte_at_offset(offset + i, byte)

    def get_file_bytes(self):
        return bytes(self.byte_buffer)

    def print_hexdump(self, line_count):        
        for i in range(line_count):
            print(f"{i*0x10:06X}: ", end="")
            for j in range(0x10):
                if (i*0x10 + j) >= len(self.byte_buffer):
                    return

                print(f"{self.byte_buffer[i*0x10 + j]:02X}", end=" ")
            print("")