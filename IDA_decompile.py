import os
import sys
from subprocess import Popen, PIPE, getstatusoutput
# use IDA (on Windows) to decompile files
time_cmd = r"C:\cygwin64\bin\time.exe -p "
ida_path = r"C:\Users\john\Desktop\tools\ollydbg_IDAPRO\IDA_Pro_v7.0_Portable\ida.exe "
ida_option = r" -A -OIDAPython:1;"
ida_script_path = r".\idapy_decompile.py "
python27_path = r"C:\Users\john\Desktop\tools\ollydbg_IDAPRO\IDA_Pro_v7.0_Portable\python27"
target_bin_path = r"C:\Users\john\Desktop\IDA_test\tmp_test\csmith_test_5_m"


def get_script_path():
    global ida_script_path
    # current_file_path = sys.path[0]
    current_file_path = os.path.realpath(__file__)
    fpath, fname = os.path.split(current_file_path)
    ida_script_path = os.path.join(fpath, "idapy_decompile.py")
    ida_script_path += ' '
    # print(ida_script_path)


def decompile(target_bin_path, generated_file_path):
    get_script_path()

    cmd = time_cmd + ida_path + ida_option + ida_script_path + target_bin_path
    # print(cmd)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, env={'PYTHONHOME': python27_path})
    stdout, stderr = proc.communicate()
    # status, stdout = getstatusoutput(cmd)
    # print(stdout)
    # print(stderr.decode())  # Why stderr is the output? ... Whatever, it works.
    time_out = stderr.decode()  # real, user, sys
    decompile_tmp_file_path = os.path.join(os.path.split(target_bin_path)[0], 'decompile_tmp.c')
    isExists = os.path.exists(decompile_tmp_file_path)
    if not isExists:
        return -1, time_out
    else:
        status, output = getstatusoutput(r'copy ' + decompile_tmp_file_path+ ' '+ generated_file_path)
        status, output = getstatusoutput(r'del ' + decompile_tmp_file_path)
        return 0, time_out

if __name__ == '__main__':
    # test
    decompile(target_bin_path,'.\\test_tmp.c')

    # cmd = r"C:\cygwin64\bin\time.exe -p C:\Users\john\Desktop\tools\ollydbg_IDAPRO\IDA_Pro_v7.0_Portable\ida.exe -A -OIDAPython:1;C:\Users\john\Desktop\IDA_test\tmp_test\idapy_test.py C:\Users\john\Desktop\IDA_test\tmp_test\csmith_test_5_m"
    cmd = time_cmd + ida_path + ida_option + ida_script_path + target_bin_path
    print(cmd)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, env={'PYTHONHOME':python27_path})
    stdout, stderr = proc.communicate()
    # status, stdout = getstatusoutput(cmd)
    print(stdout)
    print(stderr.decode())  # Why stderr is the output? ... Whatever, it works.
