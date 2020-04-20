import sys
import r2pipe


def decompile(file_path, generated_file_path, func_name="func_1"):
    """ try to decompile <func_name> in file <file_path>
        with r2ghidra_dec plugin of Radare2
        (which is the native ghidra decompiler)
    """
    r = r2pipe.open(file_path)
    r.cmd('aaa')  # analyze all
    r.cmd('afl')  # analyze function list
    r.cmd('s sym.{}'.format(func_name))  # go to func_1
    dec_code = r.cmd('pdg')  # decompile with ghidra

    status = -1
    if dec_code:
        status = 0
        open(generated_file_path, 'w').write(dec_code)
    return status, dec_code  # not necessary


if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) == 3:
        decompile(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        decompile(sys.argv[1], sys.argv[2], sys.argv[3])
