class LangString():
    def __init__(self, offset, str_len, str_id, full_string=None):
        self.offset = offset
        self.len = str_len
        self.id = str_id

        self.full_string = full_string
