# 
# cmd: <path_to_ida.exe> -A -OIDAPython:1;<path_to_idapy_test.py> <path_to_program>
#                                       ^ 1 is important, this script will be executed after hexrays is loaded.
from __future__ import print_function
from idautils import *
from idaapi import *

outputfile = './decompile_tmp.c'

func_1_ea = 0x0

def get_func_1_ea():
	global func_1_ea
	#ea = BeginEA()
	#for funcea in Functions(SegStart(ea), SegEnd(ea)):
	for funcea in Functions():
		functionName = GetFunctionName(funcea)
		functionStart = "0x%08x"%funcea
		functionEnd = "0x%08x"%FindFuncEnd(funcea)
		print("func name:", functionName)
		print("func start:", functionStart)
		print("func end:", functionEnd)
		if functionName == 'func_1':  # only decompile one function
			func_1_ea = funcea
	
def main():
	# Wait for auto-analysis to finish before running script
	# This is important! Functions() can get all functions ONLY AFTER auto-analysis
	autoWait()
	
	print("Hex-rays version %s has been detected" % idaapi.get_hexrays_version())
	
	if not idaapi.init_hexrays_plugin():
		return False	

	get_func_1_ea()
	
	# f = idaapi.get_func(idaapi.get_screen_ea());
	f = idaapi.get_func(func_1_ea)
	if f is None:
		print("Please position the cursor within a function")
		return False

	cfunc = idaapi.decompile(f)
	if cfunc is None:
		print("Failed to decompile!")
		return False

	sv = cfunc.get_pseudocode()
	tmp_f = open(outputfile, 'w')
	for sline in sv:
		print(idaapi.tag_remove(sline.line));
		tmp_f.write(str(idaapi.tag_remove(sline.line)) + '\n')
	tmp_f.flush()
	tmp_f.close()
	return True
	
if main():
	qexit(0)
	pass
else:
	qexit(-1)
	pass
