from ctypes import *


class ContextTable:
    context_stack = ['']

    nested_loop = 0

    var_name_list_int8_t = ['']
    var_name_list_int16_t = ['']
    var_name_list_int32_t = ['']
    var_name_list_uint8_t = ['']
    var_name_list_uint16_t = ['']
    var_name_list_uint32_t = ['']

    const_var_name_list = ['']

    label_name_list = ['']

    def type_of_var(self, var_name):
        if var_name in self.var_name_list_int8_t:
            return 'int8_t'
        if var_name in self.var_name_list_int16_t:
            return 'int16_t'
        if var_name in self.var_name_list_int32_t:
            return 'int32_t'
        if var_name in self.var_name_list_uint8_t:
            return 'uint8_t'
        if var_name in self.var_name_list_uint16_t:
            return 'uint16_t'
        if var_name in self.var_name_list_uint32_t:
            return 'uint32_t'
        return 'int'

    def get_c_type_of_var(self, var_name, value):
        if var_name in self.var_name_list_int8_t:
            return c_int8(value)
        if var_name in self.var_name_list_int16_t:
            return c_int16(value)
        if var_name in self.var_name_list_int32_t:
            return c_int32(value)
        if var_name in self.var_name_list_uint8_t:
            return c_uint8(value)
        if var_name in self.var_name_list_uint16_t:
            return c_uint16(value)
        if var_name in self.var_name_list_uint32_t:
            return c_uint32(value)

    def pop_out_stack(self, list):
        while list[len(list)-1] != '{':
            tmp = list.pop()
            if tmp.strip(' ').startswith('for') or tmp.strip(' ').startswith('while'):
                self.nested_loop -= 1
        tmp = list.pop()

    def __init__(self):
        self.context_stack = []
        self.nested_loop = 0
        self.var_name_list_int8_t = []
        self.var_name_list_int16_t = []
        self.var_name_list_int32_t = []
        self.var_name_list_uint8_t = []
        self.var_name_list_uint16_t = []
        self.var_name_list_uint32_t = []
        self.const_var_name_list = []
        self.label_name_list = []

    def set_name_in_var_list(self, txt):
        tmp_txt_list = txt.split(' ')
        name = tmp_txt_list[1]
        if txt.startswith('int8_t'):
            self.var_name_list_int8_t.append(name)
        elif txt.startswith('int16_t'):
            self.var_name_list_int16_t.append(name)
        elif txt.startswith('int32_t'):
            self.var_name_list_int32_t.append(name)
        elif txt.startswith('uint8_t'):
            self.var_name_list_uint8_t.append(name)
        elif txt.startswith('uint16_t'):
            self.var_name_list_uint16_t.append(name)
        elif txt.startswith('uint32_t'):
            self.var_name_list_uint32_t.append(name)

    def add_context_line(self, txt=''):
        txt = txt.strip(' ')
        txt = txt.replace('volatile ', '')
        if (txt.startswith('for') or
                txt.startswith('while')):
            self.nested_loop += 1
            self.context_stack.append(txt)
        elif txt.startswith('if') or txt.startswith('else'):
            pass
        elif txt.startswith('/*') or txt.startswith('\n'):
            pass
        elif txt.startswith('const'):
            # const variables are readable only
            tmp_txt_list = txt.split(' ')
            name = tmp_txt_list[2]
            self.const_var_name_list.append(name)

            txt = txt.replace('const ', '')
            self.set_name_in_var_list(txt)
            pass
        elif txt.startswith('int') or txt.startswith('uint'):
            # variables declarations
            self.set_name_in_var_list(txt)

            self.context_stack.append(txt)
        elif txt.startswith('{'):
            self.context_stack.append('{')
            self.var_name_list_int8_t.append('{')
            self.var_name_list_int16_t.append('{')
            self.var_name_list_int32_t.append('{')
            self.var_name_list_uint8_t.append('{')
            self.var_name_list_uint16_t.append('{')
            self.var_name_list_uint32_t.append('{')
        elif txt.startswith('}'):
            self.pop_out_stack(self.context_stack)
            self.pop_out_stack(self.var_name_list_int8_t)
            self.pop_out_stack(self.var_name_list_int16_t)
            self.pop_out_stack(self.var_name_list_int32_t)
            self.pop_out_stack(self.var_name_list_uint8_t)
            self.pop_out_stack(self.var_name_list_uint16_t)
            self.pop_out_stack(self.var_name_list_uint32_t)
            if len(self.context_stack) != 0 and \
                    (self.context_stack[-1].startswith('for') or
                     self.context_stack[-1].startswith('while')):
                self.nested_loop -= 1
                self.context_stack.pop()
        elif txt == '':
            pass
        elif txt.endswith(':'):  # label
            self.label_name_list.append(txt.strip(' :\n'))
        else:
            # print('Class: ContextTable\n    undefined line prefix:', txt)
            pass

