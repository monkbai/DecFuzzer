#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import sys, getopt, os

from src import fuzzer
from src import Config


def main(argv):
    files_dir = ''
    emi_dir = ''
    decompiler = ''
    EMI = False
    try:
        opts, args = getopt.getopt(argv, "", ["help", "EMI", "decompiler=", "files_dir=", "emi_dir="])
    except getopt.GetoptError:
        print('reproduce.py \n'
              '--decompiler <decompiler name> \n'
              '--files_dir <directory of C programs> \n'
              '--emi_dir <where to store EMI variants> \n'
              '--EMI generate EMI variants')
        sys.exit(2)
    for opt, arg in opts:
        # print(opt, arg)
        if opt == '--help':
            print('reproduce.py \n'
                  '--decompiler <decompiler name> \n'
                  '--files_dir <directory of C programs> \n'
                  '--emi_dir <where to store EMI variants> \n'
                  '--EMI generate EMI variants')
            sys.exit()
        elif opt == "--EMI":
            EMI = True
        elif opt == "--files_dir":
            files_dir = arg
        elif opt == "--emi_dir":
            emi_dir = arg
        elif opt == "--decompiler":
            decompiler = arg
    Config.set_decompiler(decompiler)
    if EMI:
        pass
        fuzzer.seed_test_AE(files_dir, emi_dir, os.path.join(files_dir, 'config.txt'))
    else:
        pass
        fuzzer.emi_test_AE(files_dir, os.path.join(files_dir, 'config.txt'))


if __name__ == "__main__":
    # print(sys.argv[1:])
    main(sys.argv[1:])
