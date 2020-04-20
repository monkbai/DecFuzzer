# running_directory = './tmp_retdec_test/csmith_files'  # where are test cases

probability_live_code_mutate = 0.3

timeout_sec = 2

replaced_func_name = 'func_1'

RetDec_test = False
JEB3_test = False
IDA_test = False
R2_test = True

time_cmd = "time -p "

JEB3_suffix = '_JEB3.c'
RetDec_suffix = '_retdec.c'
IDA_suffix = '_ida.c'
Radare2_suffix = '_r2.c'

JEB3_decompile_cmd = ("'/home/fuzz/Documents/jeb-pro-3.0-beta.8/jeb_linux.sh' "
                      " -c --srv2 --script='/home/fuzz/Documents/jeb-pro-3.0-beta.8/DecompileFile.py' "
                      " -- "
                      )
RetDec_decompile_cmd = (r"'/home/fuzz/Documents/retdec-install/bin/retdec-decompiler.py' --cleanup "
                        )
Radare2_decompile_cmd = r"python3 R2_decompile.py "

# this csmith command is not used in the Artifact Evaluation Package
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

compile_cmd = 'gcc -fno-stack-protector -no-pie -O0 -w -m32 '
# Absolute path to csmith runtime directory
runtime_dir = '/home/fuzz/Documents/DecFuzzer/runtime/ '

# CFG_measurer
gcc_cfg_option = ' -fdump-tree-cfg '
cfg_suffix = '.011t.cfg'


def get_live_code_mutate():
    global probability_live_code_mutate
    return probability_live_code_mutate


def set_live_code_mutate(value):
    global probability_live_code_mutate
    probability_live_code_mutate = value


def set_decompiler(tool=''):
    global RetDec_test, JEB3_test, IDA_test, R2_test
    RetDec_test = False
    JEB3_test = False
    IDA_test = False
    R2_test = False
    if tool.startswith('retdec'):
        RetDec_test = True
    elif tool.startswith('jeb'):
        JEB3_test = True
    elif tool.startswith('ida'):
        IDA_test = True
    elif tool.startswith('r2'):
        R2_test = True
