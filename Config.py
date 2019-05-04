# running_directory = './tmp_retdec_test/csmith_files'  # where are test cases

probability_live_code_mutate = 0.3

timeout_sec = 2

replaced_func_name = 'func_1'

RetDec_test = True
JEB3_test = False
IDA_test = False

time_cmd = "time -p "
# decompile_cmd may be not used anymore
decompile_cmd = ("'/home/fuzz/Documents/jeb-pro-3.0-beta.8/jeb_linux.sh' "
                 " -c --srv2 --script='/home/fuzz/Documents/jeb-pro-3.0-beta.8/DecompileFile.py' "
                 " -- "
                 )


JEB3_suffix = '_JEB3.c'
RetDec_suffix = '_retdec.c'

JEB3_decompile_cmd = ("'/home/fuzz/Documents/jeb-pro-3.0-beta.8/jeb_linux.sh' "
                      " -c --srv2 --script='/home/fuzz/Documents/jeb-pro-3.0-beta.8/DecompileFile.py' "
                      " -- "
                      )
RetDec_decompile_cmd = (r"'/home/fuzz/Documents/retdec-install/bin/retdec-decompiler.py' --cleanup "
                        )

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
runtime_dir = '/home/fuzz/Documents/Fuzzer_3_17/tmp/src_code/runtime/ '

# CFG_measurer
gcc_cfg_option = ' -fdump-tree-cfg '
cfg_suffix = '.011t.cfg'




def get_live_code_mutate():
    global probability_live_code_mutate
    return probability_live_code_mutate


def set_live_code_mutate(value):
    global probability_live_code_mutate
    probability_live_code_mutate = value

