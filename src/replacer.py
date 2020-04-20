import re
from src import Config, modifier

type_reg_exp = r"(void|int|char|short|long|int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t|struct|union)"
id_reg_exp = r"([A-Za-z_]+[A-Za-z_0-9]*)"
# the regular expression used to match parameters
par_dec_reg = (r"("
               r"(unsigned\s+){0,1}" +   # unsigned
               type_reg_exp +   # type
               r"(\s*\**\s*)" +   # pointer
               id_reg_exp +   # var name
               r"(\s*(\[[0-9]*\]){0,1})"  # array
               r",{0,1}\s*"  # comma
               r")")
void_par_reg = r"((void){0,1})"
# the regular expression used to match function type
fun_type_reg = (r"("
                r"(static\s+){0,1}" +   # static
                r"((signed|unsigned)\s+){0,1}" +   # signed | unsigned
                type_reg_exp +   # type
                r"(\s+[A-Za-z0-9_]*\s+){0,1}" +
                r"(\s+\**\s*)"  # pointer
                r")")


def read_file(file_name):
    f = open(file_name)
    if f:
        txt = f.read()
        f.close()
        return txt
    return ''


def find_function_def(txt):
    # par_dec_reg=r"(int|char|short|long)(\s+\**\s*)([A-Za-z_]+[A-Za-z_0-9]*)(\s*(\[[0-9]*\]){0,1}),*"
    reg_exp = (fun_type_reg +
               id_reg_exp +
               r"\((" + par_dec_reg + '|' + void_par_reg + r")*\)"
               r"\s*{"
               )

    pattern = re.compile(reg_exp)
    match = pattern.search(txt)
    if match and __name__ == '__main__':
        print('reg exp: %s' % reg_exp)
        print(match.group(0))
        print('from %d to %d' % (match.start(), match.end()))
        print('function name: %s' % match.group(3))
    return match


def find_fun_with_name(txt, fun_name):
    reg_exp = (fun_type_reg +
               fun_name +
               r"\((" + par_dec_reg + '|' + void_par_reg + ")*\)\s*{"
               )
    pattern = re.compile(reg_exp)
    match = pattern.search(txt)
    if match and __name__ == '__main__':
        print('reg exp: %s' % reg_exp)
        print(match.group(0))
        print('from %d to %d' % (match.start(), match.end()))
        print('function name: %s' % fun_name)
    return match


def find_function_body(txt, body_start_pos):
    brace_num = 0
    length = len(txt)
    last_right_brace = -1
    if txt[body_start_pos-1]=='{':
        brace_num += 1
        # body_start_pos += 1
    while brace_num != 0:
        # in case { in a string: '{'
        # this may happen in Radare2
        if body_start_pos >= length:
            return last_right_brace + 1

        if txt[body_start_pos]=='{':
            if txt[body_start_pos - 1] != r"'" or txt[body_start_pos + 1] != r"'":
                brace_num += 1
        elif txt[body_start_pos]=='}':
            if txt[body_start_pos - 1] != r"'" or txt[body_start_pos + 1] != r"'":
                brace_num -= 1
            last_right_brace = body_start_pos
        body_start_pos += 1
    body_end_pos = body_start_pos
    return body_end_pos


def find_fun_pos_with_name(txt='', func_name=''):
    match = find_fun_with_name(txt, func_name)
    start_pos = match.start()
    end_pos = find_function_body(txt, match.end())
    return start_pos, end_pos


def replace_function(source_code, decompiled_code, func_name, keep_func_decl_unchange = 0):
    # Step A: pre-process
    if Config.JEB3_test:
        decompiled_code = modifier.JEB3_modifier_before(decompiled_code)
    elif Config.RetDec_test:
        decompiled_code = modifier.RetDec_modifier_before(decompiled_code)
    elif Config.IDA_test:
        decompiled_code = modifier.IDA_modifier_before(decompiled_code)
    elif Config.R2_test:
        decompiled_code = modifier.R2_modifier_before(decompiled_code)

    # Step B: get decompiled func_1 code
    m1 = find_fun_with_name(source_code, func_name)
    # print(source_code[m1.end() - 1])
    if source_code[m1.end() - 1] == '{':
        end_pos1 = find_function_body(source_code, m1.end())
    m2 = find_fun_with_name(decompiled_code, func_name)
    if decompiled_code[m2.end() - 1] == '{':
        end_pos2 = find_function_body(decompiled_code, m2.end())

    if keep_func_decl_unchange == 0:
        main_fun = decompiled_code[m2.start():end_pos2]
    else:
        main_fun = decompiled_code[m2.end()-1:end_pos2]

    # Step C: make decompiled func_1 code compilable
    # main_fun = JEB3_modifier(main_fun)
    if Config.JEB3_test:
        main_fun = modifier.JEB3_modifier_after(main_fun)
    elif Config.RetDec_test:
        main_fun = modifier.RetDec_modifier_after(main_fun)
    elif Config.IDA_test:
        main_fun = modifier.IDA_modifier_after(main_fun)
    elif Config.R2_test:
        main_fun = modifier.R2_modifier_after(main_fun)

    # Step D: replace
    if keep_func_decl_unchange == 0:
        new_code = source_code[0:m1.start()] + main_fun + source_code[end_pos1:]
    else:
        new_code = source_code[0:m1.end()-1] + main_fun + source_code[end_pos1:]
    return new_code


if __name__ == '__main__':
    test_str = 'abcdintchar * function(int a[]){'
    find_function_def(test_str)
    find_fun_with_name(test_str, 'function')
