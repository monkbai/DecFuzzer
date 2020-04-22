#!/usr/bin/python3
import subprocess
import os

from src import EMI_generator, generator, replacer, checker, Config

file_count = 0
EMI_count = 0
total_real_time = 0
total_user_time = 0
total_sys_time = 0


def get_config(config_file):
    global file_count, EMI_count, total_real_time, total_user_time, total_sys_time
    isExists = os.path.exists(config_file)
    if not isExists:
        return
    f = open(config_file)
    if f:
        conf_txt = f.read()
    else:
        return
    f.close()
    pos = conf_txt.find('file_count: ')
    if pos != -1:
        count_txt = conf_txt[pos:]
        count_txt = count_txt[:count_txt.find('\n')]
        count_txt = count_txt.replace('file_count: ', '').strip(' \n')
        file_count = int(count_txt)

    if conf_txt.find('EMI_count: ') != -1:
        emi_count_txt = conf_txt[conf_txt.find('EMI_count: ')+11:].split('\n')[0].strip(' \n')
        EMI_count = int(emi_count_txt)
    if conf_txt.find('total_real_time: ') != -1:
        real_txt = conf_txt[conf_txt.find('total_real_time: ')+17:].split('\n')[0].strip(' \n')
        total_real_time = float(real_txt)
    if conf_txt.find('total_user_time: ') != -1:
        user_txt = conf_txt[conf_txt.find('total_user_time: ')+17:].split('\n')[0].strip(' \n')
        total_user_time = float(user_txt)
    if conf_txt.find('total_sys_time: ') != -1:
        sys_txt = conf_txt[conf_txt.find('total_sys_time: ')+16:].split('\n')[0].strip(' \n')
        total_sys_time = float(sys_txt)


def set_config(config_file):
    global file_count, EMI_count, total_real_time, total_user_time, total_sys_time
    f = open(config_file, 'w')
    f.write('file_count: ' + str(file_count) + '\n')
    f.write('EMI_count: ' + str(EMI_count) + '\n')
    f.write('total_real_time: ' + str(total_real_time) + '\n')
    f.write('total_user_time: ' + str(total_user_time) + '\n')
    f.write('total_sys_time: ' + str(total_sys_time) + '\n')
    f.close()


def copy_file(src, dst):
    sta, out = subprocess.getstatusoutput('cp ' + src + ' ' + dst)
    return sta, out


# This function is a little dangerous
# WASTED
def remove_all_file(directory):
    """remove all files except .txt files in this directory"""
    rm_cmd = "rm `ls | grep -v .txt`"
    cmd = "cd " + directory + "; " + rm_cmd
    sta, out = subprocess.getstatusoutput(cmd)
    return sta, out


def remove_file(file):
    sta, out = subprocess.getstatusoutput('rm ' + file)
    return sta, out


def remove_files(file_path, modified_file):
    # remove source files in this turn
    remove_file(file_path)
    # remove_file(modified_file)  # keep modified source code for debug
    remove_file(modified_file[:-2] + '_JEB3.c')
    remove_file(modified_file[:-2] + '_new.c')
    remove_file(modified_file[:-2] + '_new_nou.c')  # maybe
    # remove compiled files in this turn
    remove_file(file_path[:-2])
    remove_file(modified_file[:-2])
    remove_file(modified_file[:-2] + '_new')
    remove_file(modified_file[:-2] + '_new_nou')  # maybe


# -----------------------------------------------------------------------------------
# core functions: <test_single_file>, <recompile_single_file>, <generate_emi_variants>
# -----------------------------------------------------------------------------------


def test_single_file(file_path, current_dir, EMI_dir='', mutation_flag=1, compile_flag=1, decompile_flag=1):
    global file_count, EMI_count, total_real_time, total_user_time, total_sys_time
    err_dir = os.path.join(current_dir, 'error/')
    result_dir = os.path.join(current_dir, 'result/')

    # Step 1: compile
    if compile_flag != 0:
        status, output = generator.compile_single_file(file_path)
        if status != 0:
            # copy their source code to error directory
            copy_file(file_path, err_dir)
            return

    # Step 2: decompile
    if decompile_flag != 0:
        status, real_time, user_time, sys_time = generator.decompile_single_file(file_path[:-2])
        total_real_time += real_time
        total_user_time += user_time
        total_sys_time += sys_time
        file_count += 1

        if status != 0:
            copy_file(file_path, err_dir)
            return

    # Step 3: recompile
    if Config.JEB3_test:
        decompiled_file_name = file_path[:-2] + Config.JEB3_suffix  # '_JEB3.c'
    elif Config.RetDec_test:
        decompiled_file_name = file_path[:-2] + Config.RetDec_suffix  # '_retdec.c'
    elif Config.IDA_test:
        decompiled_file_name = file_path[:-2] + Config.IDA_suffix  # '_ida.c'
    elif Config.R2_test:
        decompiled_file_name = file_path[:-2] + Config.Radare2_suffix  # '_r2.c'

    status, output = generator.recompile_single_file(file_path,
                                                     decompiled_file_name,
                                                     func_name=Config.replaced_func_name,  # func_1
                                                     keep_func_decl_unchanged=1,
                                                     try_second_time=1)
    if status != 0:
        copy_file(file_path, err_dir)
        copy_file(decompiled_file_name, err_dir)
        # remove_file(file_path[:-2])
        # remove_file(decompiled_file_name)

        error_log = os.path.join(err_dir, 'error_log.txt')
        f = open(error_log, 'a')
        f.write(output + '\n\n')
        f.close()
        return

    # Step 4: compare
    status, output = checker.compare_two_prog(file_path[:-2],
                                              file_path[:-2] + '_new',
                                              result_dir)

    # Step 5(may be skipped): EMI mutation
    if status == 0 and output != b'' and mutation_flag != 0:
        # information about code length
        f = open(file_path)
        original_code = f.read()
        f.close()
        f = open(file_path[:-2] + '_new.c')
        synthesized_code = f.read()
        f.close()
        start1, end1 = replacer.find_fun_pos_with_name(original_code, Config.replaced_func_name)
        start2, end2 = replacer.find_fun_pos_with_name(synthesized_code, Config.replaced_func_name)
        print('original    function length:', str(end1 - start1))
        print('synthesized function length:', str(end2 - start2))

        if ((end1 - start1) - (end2 - start2)) > 1000:
            number_of_var = ((end1 - start1) - (end2 - start2)) / 500
        else:
            number_of_var = 0
        # For efficiency, reduce some big programs which may need a HUGE time to decompile
        number_of_var = min(10, number_of_var)
        if ((end1 - start1) - (end2 - start2)) > 12000:
            number_of_var -= (((end1 - start1) - (end2 - start2)) - 12000) / 400

        variant_log_file_path = os.path.join(EMI_dir, 'variant_log.txt')
        append_to_file(variant_log_file_path, '\nfile '+file_path+'\n')
        generate_emi_variants(number_of_var, file_path, EMI_dir)

    # Step 6: remove redundant files
    pass


def append_to_file(file_path, append_str):
    f = open(file_path, 'a')
    f.write(append_str)
    f.close()


def generate_emi_variants(number_of_var, file_path, emi_dir):
    global EMI_count
    if number_of_var > 0:
        emi = EMI_generator.EMIWrapper(file_path)

        print('about %d variants will be generated, they are:' % int(number_of_var))
        variant_log_file_path = os.path.join(emi_dir, 'variant_log.txt')
        append_to_file(variant_log_file_path, 'about %d variants will be generated, they are:' % int(number_of_var)+'\n')
        for i in range(int(number_of_var)):
            status, variant_txt = emi.gen_a_new_variant()
            if status == -1:
                break
            if status != 0:
                continue

            variant_name = str(EMI_count) + '.c'
            EMI_count += 1
            variant_path = os.path.join(emi_dir, variant_name)
            f = open(variant_path, 'w')
            if f:
                f.write(variant_txt)
                f.close()
            print(variant_path, ' is generated')
            variant_log_file_path = os.path.join(emi_dir, 'variant_log.txt')
            append_to_file(variant_log_file_path, variant_path + ' is generated\n')

            # try to avoid redundant variants, too
            if emi.AP.dis_new == emi.AP.dis_old:
                print('variant has the same distance as old one, break')
                print('dis_new', str(emi.AP.dis_new), 'dis_old', str(emi.AP.dis_old))
                break
            if emi.AP.dis_new <= emi.AP.dis_old - 3:
                print(str(emi.AP.dis_new), '<=', str(emi.AP.dis_old), '- 3, break')
                break


def test_batch_csmith_files(current_files_dir, EMI_variant_dir=''):
    """ First : test all csmith files in <csmith_files_dir> one by one
        during the test, if the recompiled program has the same output with original program
        then mutate this csmith file, put generated EMI variants into <EMI_variant_dir>

        Second : test all EMI variatns in <EMI_variant_dir>
    """
    global file_count
    config_file = os.path.join(current_files_dir, 'config_txt')
    get_config(config_file)
    while True:
        print('\n', str(file_count)+'.c')
        file_path = os.path.join(current_files_dir, str(file_count)+'.c')
        is_exist = os.path.exists(file_path)
        if not is_exist:
            break
        if EMI_variant_dir == '':
            mutation = 0
        else:
            mutation = 1

        test_single_file(file_path, current_files_dir, EMI_variant_dir, mutation)
        set_config(config_file)


def batch_recompile_and_test(current_files_dir, EMI_variant_dir=''):
    """ used for recompiling IDA outputs and generating new EMI variants
        without compilation and decompilation steps
    """
    global file_count
    config_file = os.path.join(current_files_dir, 'config_txt')
    get_config(config_file)
    while True:
        print('\n', str(file_count) + '.c')
        file_path = os.path.join(current_files_dir, str(file_count) + '.c')
        is_exist = os.path.exists(file_path)
        if not is_exist:
            break
        if EMI_variant_dir == '':
            mutation = 0
        else:
            mutation = 1

        test_single_file(file_path, current_files_dir, EMI_variant_dir, mutation, compile_flag=0, decompile_flag=0)
        file_count += 1
        set_config(config_file)
    pass


def create_directory(directory):
    if os.path.exists(directory):
        return
    os.mkdir(directory)


def prepare_dirs(files_dir, emi=False):
    create_directory(files_dir)
    error_dir = os.path.join(files_dir, 'error/')
    create_directory(error_dir)
    result_dir = os.path.join(files_dir, 'result/')
    create_directory(result_dir)
    if emi:
        emi_dir = os.path.join(files_dir, 'emi/')
        create_directory(emi_dir)


# fuzzing test on CSmith generated files,
# generating EMI variants
# for ISSTA'20 Artifact Evaluation
def seed_test_AE(files_dir, emi_dir, config_file):
    """files_dir: the seed files directory
       emi_dir: the directory to store generated EMI variants
       config_file: path to configure file (used in EMI mutation)
    """
    prepare_dirs(files_dir, emi=False)
    prepare_dirs(emi_dir, emi=False)
    for root, dirs, files in os.walk(files_dir):
        files.sort()
        for f in files:
            if f.endswith('.c') and not f.endswith('_new.c')\
                    and not f.endswith('_r2.c') and not f.endswith('_retdec.c')\
                    and not f.endswith('_ida.c') and not f.endswith('_JEB3.c'):
                if root.endswith(files_dir):

                    # test all files in this folder
                    file_path = os.path.join(root, f)
                    current_dir = root

                    get_config(config_file)
                    test_single_file(file_path, current_dir, EMI_dir=emi_dir,
                                     mutation_flag=1, compile_flag=1, decompile_flag=1)
                    set_config(config_file)


# fuzzing test on EMI variants,
# for ISSTA'20 Artifact Evaluation
def emi_test_AE(files_dir, config_file):
    """files_dir: the emi files directory
       config_file: path to configure file (used in EMI mutation)
    """
    prepare_dirs(files_dir, emi=False)
    for root, dirs, files in os.walk(files_dir):
        files.sort()
        for f in files:
            if f.endswith('.c') and not f.endswith('_new.c') \
                    and not f.endswith('_r2.c') and not f.endswith('_retdec.c') \
                    and not f.endswith('_ida.c') and not f.endswith('_JEB3.c'):
                if root.endswith(files_dir):
                    # test all files in this folder
                    file_path = os.path.join(root, f)
                    current_dir = root

                    get_config(config_file)
                    test_single_file(file_path, current_dir, EMI_dir="",
                                     mutation_flag=0, compile_flag=1, decompile_flag=1)
                    set_config(config_file)

