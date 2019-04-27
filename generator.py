#!/usr/bin/python3
import subprocess
import os
import re

import replacer
import checker

file_num = 0

csmith_cmd = ("/home/fuzz/Documents/csmith-2.3.0/src/csmith"
              " --no-arrays"
              " --no-structs"
              " --no-unions"
              " --no-safe-math"
              " --no-pointers"
              " --no-longlong"
              " --max-funcs 1"
              " --max-expr-complexity 5"  # " --max-expr-complexity 10" # too complicated to analyse?
              )


def gen_single_file(file_name):
    global csmith_cmd
    cmd_line = csmith_cmd + " --output " + file_name
    status, output = subprocess.getstatusoutput(cmd_line)
    if status != 0:
        print(output)
    else:
        print(file_name + ' generated')
    return status


def batch_generate(outdir, num):
    global file_num
    old_num = file_num
    for i in range(num):
        status = gen_single_file(outdir + 'test'+str(file_num)+'.c')
        if status == 0:
            file_num += 1
    return file_num - old_num


# compile_cmd = 'gcc -fno-stack-protector -no-pie -O0 -Wall -m32 '
compile_cmd = 'gcc -fno-stack-protector -no-pie -O0 -w -m32 '
runtime_dir = '/home/fuzz/Documents/Fuzzer_3_17/tmp/src_code/runtime/'


def compile_single_file(file_path):
    if os.path.isdir(file_path):
        pass
    elif os.path.splitext(file_path)[1] == '.c':
        status, output = \
            subprocess.getstatusoutput(compile_cmd +
                                       ' -I ' + runtime_dir +
                                       ' -o ' + os.path.splitext(file_path)[0] +
                                       ' ' + file_path)
        if status != 0:
            print(output)
            return -1, output
        else:
            print(file_path + ' compiled')
            return 0, ''


def batch_compile(src_dir):
    """compile all .c files in the directory"""
    files = os.listdir(src_dir)
    files.sort()
    for file in files:
        file_path = os.path.join(src_dir, file)
        if compile_single_file(file_path) == (0, ''):
            print(file + ' compiled')


time_cmd = "time -p "
decompile_cmd = ("'/home/fuzz/Documents/jeb-pro-3.0-beta.8/jeb_linux.sh' "
                 " -c --srv2 --script='/home/fuzz/Documents/jeb-pro-3.0-beta.8/DecompileFile.py' "
                 " -- "
                 )


def decompile_single_file(file_path, generated_file_path=''):
    if generated_file_path == '':
        generated_file_path = file_path + '_JEB3.c'
    fname, extname = os.path.splitext(file_path)
    if os.path.isdir(file_path):
        pass
    elif extname == '':
        print('Decompiling ' + file_path + ' ...')
        status, output = \
            subprocess.getstatusoutput(time_cmd + decompile_cmd +
                                       fname + ' ' +
                                       generated_file_path)
        # It seems JEB3 returns 0 even
        # when it failed to generate decompiled code file
        isExists = os.path.exists(generated_file_path)
        if status != 0 or not isExists:
            print('decompile ' + file_path + ' failed:')
            print(output)
            return -1, 0, 0, 0
        else:
            print(file_path + ' decompiled')
            # get CPU time
            real_time = 0
            user_time = 0
            sys_time = 0
            output_list = output.split('\n')
            output_list = output_list[-3:]
            if output_list[0].find('real') != -1:
                time_str = output_list[0].split(' ')[1].strip(' s\n')
                real_time = float(time_str)
            if output_list[1].find('user') != -1:
                time_str = output_list[1].split(' ')[1].strip(' s\n')
                user_time = float(time_str)
            if output_list[2].find('sys') != -1:
                time_str = output_list[2].split(' ')[1].strip(' s\n')
                sys_time = float(time_str)
            print('real time:', real_time)
            print('user time:', user_time)
            print('sys time:', sys_time)
            return 0, real_time, user_time, sys_time


def batch_decompile(dir):
    """decompile all files in the directory with JEB3"""
    files = os.listdir(dir)
    files.sort()
    for file in files:
        file_path = os.path.join(dir, file)
        if decompile_single_file(file_path) == 0:
            print(file + ' decompiled')


def add_extra_declarations(code_txt, error_msg):
    var_list = []
    reg_exp = r"error: ‘([a-z0-9]+)’ undeclared"  # match global var name
    pattern = re.compile(reg_exp)
    matches = pattern.finditer(error_msg)
    # get all undeclared vars
    for m in matches:
        var_name = m.group(1)

        if __name__ == '__main__':
            print('var name: ', var_name)
        var_list.append(var_name)
    # new declaration stmt
    decl_txt = '    unsigned int '
    for name in var_list:
        decl_txt += name
        if name != var_list[-1]:
            decl_txt += ', '
        else:
            decl_txt += ';\n'
    # insert into code_txt
    reg_exp = r"func_1\(void\)\s*{"  # match func_1
    pattern = re.compile(reg_exp)
    matches = pattern.finditer(code_txt)
    for m in matches:
        pos = m.end()
        new_txt = code_txt[:pos] + decl_txt + code_txt[pos:]
        return new_txt


def recompile_single_file(source_file='', decompiled_file='', func_name='', keep_func_decl_unchanged=0):
    source_code = replacer.read_file(source_file)
    decompiled_code = replacer.read_file(decompiled_file)
    new_code = replacer.replace_function(source_code,
                                         decompiled_code,
                                         func_name,
                                         keep_func_decl_unchanged)
    if source_file.endswith('.c'):
        new_file_name = source_file[:-2] + '_new.c'
        f = open(new_file_name, 'w')
        f.write(new_code)
        f.close()

        status, output = compile_single_file(new_file_name)
        if status == 0:
            # print(new_file_name + ' recompiled')
            return 0, ''
        else:
            # if error: ‘v45’ undeclared
            # try to add declaration then try again
            new_code = add_extra_declarations(new_code, output)
            f = open(new_file_name, 'w')
            f.write(new_code)
            f.close()
            status, output = compile_single_file(new_file_name)
            if status == 0:
                # print(new_file_name + ' recompiled')
                return 0, ''
            return status, output
    else:
        return -1, ''


def batch_recompile(dir):
    files = os.listdir(dir)
    files.sort()
    for file in files:
        file_path = os.path.join(dir, file)
        fname, extname = os.path.splitext(file_path)
        if os.path.isdir(file_path):
            pass
        elif extname == '.c' and fname.endswith('JEB3'):
            recompile_single_file(fname[:-5]+'.c', file_path, 'main')


if __name__ == '__main__':
    pass
    # status, output = subprocess.getstatusoutput('ls')
    # print(status)
    # print(output)

    # batch_generate('./tmp/src_code/', 10)
    # f = open('./tmp/src_code/test0.c')
    # print(f.read())
    # f.close()

    # batch_compile("./test")
    # batch_decompile("./test")
    # batch_recompile("./test")
    # checker.batch_compare("./test")

    f = open('./tmp/src_code/csmith_test_16_m_new.c')
    txt = f.read()
    f.close()
    error = """./tmp/src_code/csmith_test_16_m_new.c: In function ‘func_1’:
./tmp/src_code/csmith_test_16_m_new.c:140:32: error: ‘v30’ undeclared (first use in this function); did you mean ‘v20’?
                 (unsigned char)v30 = (unsigned char)v6;
                                ^~~
                                v20
./tmp/src_code/csmith_test_16_m_new.c:140:32: note: each undeclared identifier is reported only once for each function it appears in"""
    new_txt = add_extra_declarations(txt, error)
    print(new_txt)
