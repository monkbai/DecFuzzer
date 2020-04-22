#!/usr/bin/python3
# -*- coding: UTF-8 -*-

# import sys, getopt

from src import fuzzer
from src import Config

Config.set_decompiler("retdec")
# fuzzer.seed_test_AE('./seed_for_retdec/', './seed_for_retdec/emi/', './seed_for_retdec/config.txt')
# fuzzer.emi_test_AE('./seed_for_retdec/emi/', './seed_for_retdec/emi/config.txt')

Config.set_decompiler("r2")
fuzzer.seed_test_AE('./seed_for_r2/', './seed_for_r2/emi/', './seed_for_r2/config.txt')
fuzzer.emi_test_AE('./seed_for_r2/emi/', './seed_for_r2/emi/config.txt')
