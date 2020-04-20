import os
from threading import Timer
from subprocess import Popen, PIPE, getstatusoutput

from src import Config

timeout_sec = Config.timeout_sec


def run_single_prog(prog_path):
    global timeout_sec
    proc = Popen(prog_path, stdout=PIPE, stderr=PIPE)
    timer = Timer(timeout_sec, proc.kill)
    try:
        timer.start()
        stdout, stderr = proc.communicate()
    finally:
        timer.cancel()
    return stdout, stderr


def compare_two_prog(prog1, prog2, result_dir):
    print('Checking ' + prog1 + ' & ' + prog2)

    stdout1, stderr1 = run_single_prog(prog1)
    stdout2, stderr2 = run_single_prog(prog2)

    if len(stdout1) > 100:
        result_log = os.path.join(result_dir, 'result_log.txt')
        f = open(result_log, 'a')
        f.write('WRONG: stdout1 is very long.\n')
        print('WRONG: stdout1 is very long.')
        f.write(prog1 + '\n')
        f.write(prog2 + '\n')
        f.close()
        # copy their source code to result directory
        status, output = \
            getstatusoutput('cp ' + prog1 + '.c ' + result_dir)
        status, output = \
            getstatusoutput('cp ' + prog2 + '.c ' + result_dir)
        return -1, ''
    elif len(stdout2) > 100:
        result_log = os.path.join(result_dir, 'result_log.txt')
        f = open(result_log, 'a')
        f.write('WRONG: stdout2 is very long.\n')
        print('WRONG: stdout2 is very long.')
        f.write(prog1 + '\n')
        f.write(prog2 + '\n')
        f.close()
        # copy their source code to result directory
        status, output = \
            getstatusoutput('cp ' + prog1 + '.c ' + result_dir)
        status, output = \
            getstatusoutput('cp ' + prog2 + '.c ' + result_dir)
        return -1, ''

    if stdout1 != stdout2:
        result_log = os.path.join(result_dir, 'result_log.txt')
        f = open(result_log, 'a')
        f.write('Found discrepancy:\n')
        print('Found discrepancy:')
        f.write(prog1 + '     outputs [' + str(stdout1) + ']\n')
        print(prog1 + '     outputs [' + str(stdout1) + ']')
        f.write(prog2 + ' outputs [' + str(stdout2) + ']\n')
        print(prog2 + ' outputs [' + str(stdout2) + ']')
        # add error information
        f.write(prog1 + '     errors [' + str(stderr1) + ']\n')
        #print(prog1 + '     errors [' + str(stderr1) + ']')
        f.write(prog2 + ' errors [' + str(stderr2) + ']\n')
        #print(prog2 + ' errors [' + str(stderr2) + ']')
        f.close()
        # copy their source code to result directory
        status, output = \
            getstatusoutput('cp ' + prog1 + '.c ' + result_dir)
        status, output = \
            getstatusoutput('cp ' + prog2 + '.c ' + result_dir)
        return -1,stdout1
    elif stderr1 != stderr2:
        result_log = os.path.join(result_dir, 'error_log.txt')
        f = open(result_log, 'a')
        f.write('Found discrepancy:\n')
        print('Found discrepancy:')
        # add output
        f.write(prog1 + '     outputs [' + str(stdout1) + ']\n')
        #print(prog1 + '     outputs [' + str(stdout1) + ']')
        f.write(prog2 + ' outputs [' + str(stdout2) + ']\n')
        #print(prog2 + ' outputs [' + str(stdout2) + ']')

        f.write(prog1 + '     errors [' + str(stderr1) + ']\n')
        print(prog1 + '     errors [' + str(stderr1) + ']')
        f.write(prog2 + ' errors [' + str(stderr2) + ']\n')
        print(prog2 + ' errors [' + str(stderr2) + ']')
        f.close()
        return -1,stdout1
    else:
        print(prog1 + '     outputs [' + str(stdout1) + ']')
        print(prog2 + ' outputs [' + str(stdout2) + ']')
        return 0,stdout1


# Ah, this function is redundant, I feel terrible to write like these
# TODO: optimize the code structure
def compare_there_prog(prog1, prog2, prog3, result_dir):
    print('Checking ' + prog1 + ' & ' + prog2 + ' & ' + prog3)

    stdout1, stderr1 = run_single_prog(prog1)
    stdout2, stderr2 = run_single_prog(prog2)
    stdout3, stderr3 = run_single_prog(prog3)

    if stdout1 != stdout2 or stdout2 != stdout3:
        result_log = os.path.join(result_dir, 'result_log.txt')
        f = open(result_log, 'a')
        f.write('\nFound discrepancy:\n')
        print('Found discrepancy:')
        f.write(prog1 + '       outputs [' + str(stdout1) + ']\n')
        print(prog1 + '       outputs [' + str(stdout1) + ']')
        f.write(prog2 + '     outputs [' + str(stdout2) + ']\n')
        print(prog2 + '     outputs [' + str(stdout2) + ']')
        f.write(prog3 + ' outputs [' + str(stdout3) + ']\n')
        print(prog3 + ' outputs [' + str(stdout3) + ']')
        f.close()
        # copy their source code to result directory
        if stdout1 != '' or stdout2 != '' or \
                stderr1.find('Float') == -1 or stderr2.find('Float') == -1:
            status, output = \
                getstatusoutput('cp ' + prog1 + '.c ' + result_dir)
            status, output = \
                getstatusoutput('cp ' + prog2 + '.c ' + result_dir)
            status, output = \
                getstatusoutput('cp ' + prog3 + '.c ' + result_dir)
        return -1,stdout1
    elif stderr1 != stderr2 or stderr2 != stderr3:
        result_log = os.path.join(result_dir, 'error_log.txt')
        f = open(result_log, 'a')
        f.write('Found discrepancy:\n')
        print('Found discrepancy:')
        f.write(prog1 + '       errors [' + stderr1 + ']\n')
        print(prog1 + '       errors [' + stderr1 + ']')
        f.write(prog2 + '     errors [' + stderr2 + ']\n')
        print(prog2 + '     errors [' + stderr2 + ']')
        f.write(prog3 + ' errors [' + stderr3 + ']\n')
        print(prog3 + ' errors [' + stderr3 + ']')
        f.close()
        return -1,stdout1
    else:
        print(prog1 + '       outputs [' + str(stdout1) + ']')
        print(prog2 + '     outputs [' + str(stdout2) + ']')
        print(prog3 + ' outputs [' + str(stdout3) + ']')
        return 0,stdout1


def batch_compare(dir):
    global timeout_sec
    files = os.listdir(dir)
    files.sort()
    for file in files:
        file_path = os.path.join(dir, file)
        fname, extname = os.path.splitext(file_path)
        if os.path.isdir(file_path):
            pass
        elif extname == '' and fname.endswith('_new'):
            print('Checking ' + fname + ' ...')

            org_name = fname[:-4]
            # run original program
            proc = Popen(org_name, stdout=PIPE, stderr=PIPE)
            timer = Timer(timeout_sec, proc.kill)
            try:
                timer.start()
                stdout1, stderr1 = proc.communicate()
            finally:
                timer.cancel()
            # run new program
            proc = Popen(file_path, stdout=PIPE, stderr=PIPE)
            timer = Timer(timeout_sec, proc.kill)
            try:
                timer.start()
                stdout2, stderr2 = proc.communicate()
            finally:
                timer.cancel()

            if stdout1 != stdout2:
                print('Found discrepancy:')
                print(org_name + ' outputs [' + str(stdout1) + ']')
                print(file_path + ' outputs [' + str(stdout2) + ']')

                status, output = \
                    getstatusoutput('cp ' + org_name + '.c ' + ' ./results')
                status, output = \
                    getstatusoutput('cp ' + org_name + '_JEB3.c ' + ' ./results')

            elif stderr1 != stderr2:
                print('Found discrepancy:')
                print(org_name + ' errors [' + stderr1 + ']')
                print(file_path + ' errors [' + stderr2 + ']')

