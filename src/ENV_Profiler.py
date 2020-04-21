#!/usr/bin/python3
import re
import random
import subprocess
import threading
import copy
from ctypes import *

from src import replacer, Config
# from EMI_generator import EMIGenerator
from src.ContextTable import ContextTable


class ENV:
    line_num = 0
    env_var_dict = {'': set()}

    def __init__(self, line_num=0):
        self.env_var_dict = {}
        self.line_num = line_num

    def add_value(self, var_name, value):
        if var_name in self.env_var_dict:
            value_set = self.env_var_dict[var_name]
        else:
            value_set = set()
        value_set.add(value)
        self.env_var_dict[var_name] = value_set

    def correct_value(self, ctx=ContextTable()):
        var_list = list(self.env_var_dict.keys())
        for var_name in var_list:
            for value in self.env_var_dict[var_name]:
                if var_name in ctx.var_name_list_int8_t:
                    c_type_var = c_int8(value)
                elif var_name in ctx.var_name_list_int16_t:
                    c_type_var = c_int16(value)
                elif var_name in ctx.var_name_list_int32_t:
                    c_type_var = c_int32(value)
                elif var_name in ctx.var_name_list_uint8_t:
                    c_type_var = c_uint8(value)
                elif var_name in ctx.var_name_list_uint16_t:
                    c_type_var = c_uint16(value)
                elif var_name in ctx.var_name_list_uint32_t:
                    c_type_var = c_uint32(value)
                else:
                    continue

                value_set = self.env_var_dict[var_name]
                value_set.remove(value)
                value_set.add(c_type_var.value)


class Profiler:
    """ give a coverage infomation file,
        Profiler try to :
        1. choose some executed stmts at random
        2. instrument before each of selected stmts (print: line_num, values of variables)
        3. compile and run instrumented program
        4. collect all information and generate ENVs for every selected stmts
    """
    gcc_cmd = Config.compile_cmd
    include_csmith_runtime = " -I " + Config.runtime_dir + ' '

    cov_txt = ''
    source_code_txt = ''
    cov_code_list = []

    env_list = [ENV()]

    def __init__(self, cov_txt='', src_txt=''):
        if cov_txt == '':
            return
        if src_txt != '':
            self.source_code_txt = src_txt
        if cov_txt != '':
            self.cov_txt = cov_txt
        self.cov_code_list = []
        self.env_list = []
        self.timeout_sec = Config.timeout_sec

    def __run_single_prog(self, prog_path):
        proc = subprocess.Popen(prog_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        timer = threading.Timer(self.timeout_sec, proc.kill)
        try:
            timer.start()
            stdout, stderr = proc.communicate()
        finally:
            timer.cancel()
        return stdout, stderr

    def get_pos_of_func1(self):
        start, end = replacer.find_fun_pos_with_name(self.source_code_txt, Config.replaced_func_name)
        start_line_num = self.source_code_txt[:start].count('\n') + 1
        end_line_num = self.source_code_txt[:end].count('\n')
        return start_line_num, end_line_num

    @staticmethod
    def strip_cov_line(line=''):
        return line[16:].strip(' ')

    def check_stmt(self, index, stmt=''):
        """check if it's a parent statement or declaration statement
           If it is a parent stmt, then check if its children have been executed
           return 0 if this statement can be used as an candidate
           return 1 if not
        """
        if stmt == '':
            stmt = self.cov_code_list[index]
        # if this statement is a single statement, end_pos equals to index
        end_pos = index
        is_parent = 0

        # Begin
        # Check if it's a parent statement
        stmt = self.strip_cov_line(stmt)
        if stmt.startswith('for') or \
                stmt.startswith('while') or \
                stmt.startswith('switch') or \
                stmt.startswith('if') or \
                stmt.startswith('else'):
            flag, end_pos = self.check_children_stmt(index, stmt)
            is_parent = 1
            return flag, end_pos, is_parent

        # Check if it's a declaration
        elif stmt.startswith('int') or \
                stmt.startswith('uint') or \
                stmt.startswith('const') or \
                stmt.startswith('static') or \
                stmt.startswith('{') or \
                stmt.startswith('}'):
            # it may cause error to insert a True Guard on a declaration
            return 1, end_pos, is_parent
        # Check stmt of set_var + return
        elif stmt.startswith('set_var'):
            return 0, end_pos, is_parent
        # Check if it's a label
        elif stmt.endswith(':') or stmt.endswith(':;'):
            return 1, end_pos, is_parent
        # It's a single statement, which can be chose to mutate
        else:
            return 0, end_pos, is_parent

    def check_children_stmt(self, index, parent_stmt):
        """return the number of un-executed children statements(lines)
        """
        if parent_stmt == '':
            parent_stmt = self.cov_code_list[index]

        # Find left brace, which should be at the next line
        #TODO: not safe
        brace_count = 0
        stmt = self.cov_code_list[index + 1]
        stmt = self.strip_cov_line(stmt)
        if stmt.startswith('{'):
            brace_count += 1
            index = index + 2
        else:
            index = index + 1
        # Find corresponding right brace
        flag = 0  # the number of un-executed children statements
        while True:
            stmt = self.cov_code_list[index]
            # un-executed?
            if stmt.startswith('    #####:'):
                flag += 1
            stmt = self.strip_cov_line(stmt)
            # brace?
            if stmt.startswith('{'):
                brace_count += 1
            elif stmt.startswith('}'):
                brace_count -= 1
            # elif stmt.endswith(':'):
            #     flag += 1
            # elif stmt.startswith('set_var'):
            #     flag += 1

            # the end?
            if brace_count == 0:
                # break
                # special case in if .. else ... statements
                if self.strip_cov_line(self.cov_code_list[index + 1]).startswith('else'):
                    if self.strip_cov_line(self.cov_code_list[index + 2]).startswith('{'):
                        brace_count += 1
                        index = index + 2
                    else:
                        index = index + 1
                else:
                    break
            index += 1
        return flag, index

    def find_out_vars(self, former_code_txt='', stmt_txt=''):
        env = ENV()

        reg_exp = r"[^a-zA-Z0-9_]" + r"(g|l)_[0-9]*(_l){0,1}" + r"[^a-zA-Z0-9_]"  # match exact name
        pattern = re.compile(reg_exp)
        matches = pattern.finditer(stmt_txt)
        declared_var_list = []  # some variables may declared in stmt_txt
        for m in matches:
            var_name = m.group()[1:-1]
            if not (var_name.startswith('g') or var_name.startswith('l')):
                print('invalid var_name %s in calss: Profiler, func:find_out_vars ' % var_name)
                continue

            # check if it's a declaration
            start_pos = m.start()
            if stmt_txt[start_pos-2:start_pos+1] == '_t ':  # it's a declaration
                declared_var_list.append(var_name)
                continue

            if var_name in declared_var_list:
                continue

            pos = former_code_txt.find(var_name)
            if pos != -1 and not former_code_txt[pos+len(var_name)].isdecimal():
                if var_name not in env.env_var_dict:
                    env.env_var_dict[var_name] = set()
        return env

    def gen_instrumentation(self, env=ENV()):
        names = list(env.env_var_dict.keys())
        if len(names) == 0:
            return ''  # can not generate expr without variables
        elif len(names) > 0:
            print_txt = 'printf("line_num: %d,", ' + str(env.line_num) + ');'
        for var_name in names:
            if var_name == names[-1]:
                print_txt += 'printf("' + var_name + r': %d\n", ' + var_name + ');'
                break
            print_txt += 'printf("' + var_name + ': %d,", ' + var_name + ');'
        return print_txt

    def instrument(self):
        # First: set cov_txt, cov_list and code_list
        cov_list = self.cov_txt.split('\n')
        # info_list = cov_list[:5]
        self.cov_code_list = cov_list[5:]

        start_line, end_line = self.get_pos_of_func1()

        # Second: visit each line in txt
        instrumented_txt = ''
        length = len(self.cov_code_list)
        index = 0
        while index < length:
            line = self.cov_code_list[index]
            # check if this line is in func_1
            if index < start_line or index > end_line:
                instrumented_txt += line[16:] + '\n'
                index += 1
                continue

            tmp_line = self.strip_cov_line(line)
            if line.startswith('    #####:'):  # this line is un-executed
                instrumented_txt += line[16:] + '\n'
            elif line.startswith('        -:'):
                instrumented_txt += line[16:] + '\n'
            else:  # it's executed

                # If this line is executed,
                # we first want to know where is the end(in the compound statement case)
                # Then get its text, so we can find out which variables are used inside

                # check if it's children stmts have been executed
                flag, end_pos, is_parent = self.check_stmt(index, line)
                if flag == 0:  # it can be selected
                    stmt_txt = ''
                    for i in range(index, end_pos + 1):
                        stmt_txt += self.cov_code_list[i][16:] + '\n'

                    #### for debug
                    prob_live_code_mutate = Config.probability_live_code_mutate
                    # print('pro_live_code_mutation', str(prob_live_code_mutate))
                    skip_or_not = False
                    if is_parent == 0 and random.random() > prob_live_code_mutate:  # this stmt will not be selected
                        skip_or_not = True
                    # the longer this statement is, the less probability it will be instrumented
                    if is_parent == 1 and random.random() > min(prob_live_code_mutate, (end_pos-index)/200.0):
                        skip_or_not = True
                    if skip_or_not:  # skip, do not instrument this stmt
                        instrumented_txt += line[16:] + '\n'
                        index += 1
                        continue

                    ''' now we have a selected statement
                        try to find out all variables used in it
                    '''
                    env = self.find_out_vars(instrumented_txt, stmt_txt)
                    env.line_num = index + 1

                    # generate instrumentation statement (printf)
                    # and insert into this line
                    print_txt = self.gen_instrumentation(env)
                    if print_txt != '':
                        instrumented_txt += print_txt+'\n'
                        instrumented_txt += stmt_txt
                        index = end_pos

                        self.env_list.append(env)
                    else:  # this line is not instrumented
                        instrumented_txt += line[16:] + '\n'
                        pass

                elif not tmp_line == '':  # it cannot be selected to mutate  # it's not an empty line
                    instrumented_txt += line[16:] + '\n'
                else:
                    pass
            # turn to next line
            index += 1
        # here we get a variant
        return instrumented_txt[:-2]

    def profile(self):
        """ compile instrumented file
            run the program
            collect info
            get <self.env_list>
        """
        instrumented_txt = self.instrument()
        tmp_file_name = './profiler_tmp.c'
        # it's not good to use a hard-coded file name, but ... it's easy
        f = open(tmp_file_name, 'w')
        f.write(instrumented_txt)
        f.close()

        # Compile it
        cmd = self.gcc_cmd + self.include_csmith_runtime + ' -o '+tmp_file_name[:-2] + ' ' + tmp_file_name
        status, output = subprocess.getstatusoutput(cmd)
        if status != 0:
            print('failed to compile, in class:Profiler, func:profile')
            print(output)
            exit(-1)

        # Run it
        output = ''
        out, err = self.__run_single_prog(tmp_file_name[:-2])
        output += str(out, encoding='utf-8')
        if output.find('checksum') == -1:
            print('failed to run, in class:Profiler, func:profile')
            exit(-1)
        # print(output)  # for debug info
        # Collect info
        output_list = output.split('\n')
        for line in output_list:
            self.parse_line(line)

        # status, output = subprocess.getstatusoutput('rm ' + tmp_file_name)
        # status, output = subprocess.getstatusoutput('rm ' + tmp_file_name[:-2])

    def parse_line(self, line=''):
        if not line.startswith('line_num'):
            return
        line_list = line.split(',')
        line_num_item = line_list[0]
        line_num = int(line_num_item.split(' ')[1])
        for env in self.env_list:
            if env.line_num == line_num:
                target_env = env
                break
        for item in line_list:
            [var_name, var_value] = item.split(' ')
            if var_name.endswith(':'):
                var_name = var_name[:-1]
            if var_name.startswith('line_num'):
                continue
            value = int(var_value)
            target_env.add_value(var_name, value)  # we do not know the type of this variable
            # so the value may be wrong
            # we need to correct the value after getting type info


class Synthesizer:

    @staticmethod
    def syn_pred(env, bool_expected, depth):
        if depth <= 0:
            return Synthesizer.syn_atom(env, bool_expected)

        rnd_int = random.randint(1, 4)
        if rnd_int == 1:
            return Synthesizer.syn_neg(env, bool_expected, depth)
        elif rnd_int == 2:
            return Synthesizer.syn_con(env, bool_expected, depth)
        elif rnd_int == 3:
            return Synthesizer.syn_dis(env, bool_expected, depth)
        elif rnd_int == 4:
            pred = Synthesizer.syn_atom(env, bool_expected)
            if pred.find('False') != -1 or pred.find('True') != -1:
                print('debug')
            return pred

    @staticmethod
    def syn_neg(env, bool_expected, depth):
        return '(!' + Synthesizer.syn_pred(env, bool(1-bool_expected), depth-1) + ')'

    @staticmethod
    def syn_con(env, bool_expected, depth):
        if bool_expected:
            left = True
            right = True
        elif random.random() > 0.5:
            left = False
            right = True
        elif random.random() > 0.5:
            left = True
            right = False
        else:
            left = False
            right = False
        return '(' + Synthesizer.syn_pred(env, left, depth-1) + ' && ' + Synthesizer.syn_pred(env, right, depth-1) + ')'

    @staticmethod
    def syn_dis(env, bool_expected, depth):
        if not bool_expected:
            left = False
            right = False
        elif random.random() > 0.5:
            left = False
            right = True
        elif random.random() > 0.5:
            left = True
            right = False
        else:
            left = True
            right = True
        return '(' + Synthesizer.syn_pred(env, left, depth-1) + ' || ' + Synthesizer.syn_pred(env, right, depth-1) + ')'

    @staticmethod
    def syn_atom(env, bool_expected, two_var=True):
        var_list = list(env.env_var_dict.keys())
        if len(var_list) == 0:
            if bool_expected:
                return '(1)'
            else:
                return '(0)'

        if len(var_list) == 1 or (not two_var) or random.random() > 0.5:  # var and truth value
            var_name = random.choice(var_list)

            if len(list(env.env_var_dict[var_name])) == 0:
                print(var_name, 'var set is empty')
                print('line', env.line_num)

            max_val = max(list(env.env_var_dict[var_name]))
            min_val = min(list(env.env_var_dict[var_name]))

            if min_val == 0 and bool_expected:
                return '(' + var_name + ' <= ' + str(max_val) + ')'
            elif min_val == 0 and not bool_expected:
                return '(' + var_name + ' > ' + str(max_val) + ')'
            elif max_val == 0 and bool_expected:
                return '(' + var_name + ' >= ' + str(min_val) + ')'
            elif max_val == 0 and not bool_expected:
                return '(' + var_name + ' < ' + str(min_val) + ')'

            rnd_int = random.randint(1, 4)
            if rnd_int == 1:  # <
                if bool_expected:  # < max+1
                    t_val = max_val + min(random.randint(1, 5), abs(max_val))
                else:  # < min
                    t_val = min_val
                return '(' + var_name + ' < ' + str(t_val) + ')'
            elif rnd_int == 2:  # >
                if bool_expected:  # > min-1
                    t_val = min_val - min(random.randint(1, 5), abs(min_val))
                else:  # > max
                    t_val = max_val
                return '(' + var_name + ' > ' + str(t_val) + ')'
            elif rnd_int == 3:  # <=
                if bool_expected:  # <= max
                    t_val = max_val
                else:  # <= min-1
                    t_val = min_val - min(random.randint(1, 5), abs(min_val))
                return '(' + var_name + ' <= ' + str(t_val) + ')'
            elif rnd_int == 4:  # >=
                if bool_expected:  # >= min
                    t_val = min_val
                else:  # >= max+1
                    t_val = max_val + min(random.randint(1, 5), abs(max_val))
                return '(' + var_name + ' >= ' + str(t_val) + ')'
        else:  # var and var
            for i in range(5):  # try 5 times at most
                # get two different var
                var_name1 = random.choice(var_list)
                var_name2 = random.choice(var_list)
                while var_name1 == var_name2:
                    var_name2 = random.choice(var_list)
                # analyze their relation
                val_list1 = list(env.env_var_dict[var_name1])
                val_list2 = list(env.env_var_dict[var_name2])
                # for debug
                if len(val_list1) == 0:
                    print(var_name1, 'var set is empty')
                    print('line', env.line_num)
                elif len(val_list2) == 0:
                    print(var_name2, 'var set is empty')
                    print('line', env.line_num)

                max1 = max(val_list1)
                min1 = min(val_list1)
                max2 = max(val_list2)
                min2 = min(val_list2)
                if max1 < min2 and ((max1 > 0 and min2 > 0) or (max1 < 0 and min2 < 0)):  # both plus or both minus
                    if bool_expected:
                        return '(' + var_name1 + ' < ' + var_name2 + ')'
                    else:
                        return '(' + var_name1 + ' > ' + var_name2 + ')'
                elif max2 < min1 and ((max2 > 0 and min1 > 0) or (max2 < 0 and min1 < 0)):
                    if bool_expected:
                        return '(' + var_name2 + ' < ' + var_name1 + ')'
                    else:
                        return '(' + var_name2 + ' > ' + var_name1 + ')'
            return Synthesizer.syn_atom(env, bool_expected, False)

    unary_operator = ['!', '~', '-']
    binary_operator = ['+', '-', '*', '/', '%', '>>', '<<', '&', '|', '^', '>', '>=', '==', '!=', '<', '<=']

    current_env = ENV()

    def __init__(self, ctx_table):
        self.ctx_table = copy.deepcopy(ctx_table)

    def syn_expr(self, env):
        # choose some vars to generate expression
        all_var_list = list(env.env_var_dict.keys())
        if len(all_var_list) < 1:
            return '0'  # this should not be used
        var_num = random.randint(1, len(all_var_list))
        var_num = min(var_num, 5)
        expr_var_list = []
        while len(expr_var_list) < var_num:
            new_var = random.choice(all_var_list)
            if new_var not in expr_var_list:
                expr_var_list.append(new_var)

        # get value info of all vars
        '''
        self.current_env.line_num = env.line_num
        self.current_env.env_var_dict = {}
        for name in expr_var_list:
            for value in env.env_var_dict[name]:
                self.current_env.add_value(name, value)
        '''
        self.current_env = copy.deepcopy(env)

        # generate expression
        total_opt_flag = 0
        unary_flag = 0
        while len(expr_var_list) > 1 or total_opt_flag == 0:
            if (unary_flag <= 2 and random.random() > 0.5) or len(expr_var_list) == 1:  # unary expr
                name = random.choice(expr_var_list)
                u_opt_list = copy.deepcopy(self.unary_operator)
                random.shuffle(u_opt_list)
                for unary_opt in u_opt_list:
                    if self.add_unary_expr(unary_opt, name, expr_var_list):
                        unary_flag += 1
                        total_opt_flag += 1
                        break

            elif len(expr_var_list) > 1:  # binary expr
                name1 = random.choice(expr_var_list)
                name2 = random.choice(expr_var_list)
                while name1 == name2:
                    name2 = random.choice(expr_var_list)

                bin_opt_list = copy.deepcopy(self.binary_operator)
                random.shuffle(bin_opt_list)

                for bin_opt in bin_opt_list:
                    if self.is_undefined(bin_opt, name1, name2):
                        continue
                    if self.add_binary_expr(bin_opt, name1, name2, expr_var_list):
                        unary_flag = 0
                        total_opt_flag += 1
                        break
        return expr_var_list[0]

    def add_unary_expr(self, u_op, name, expr_var_list=[]):
        new_name = '(' + u_op + name + ')'
        # set new type
        self.set_new_type(new_name, name, operator=u_op)
        # find out what type this new var is, and get a ctype var
        # c_type_var, sign_flag = self.get_c_type_var(new_name)

        new_value = set()
        for old_value in self.current_env.env_var_dict[name]:
            c_type_var, sign_flag = self.get_c_type_var(new_name, old_value)
            if u_op == '!':
                if c_type_var.value != 0:
                    c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                else:
                    c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
            elif u_op == '~':
                c_type_var, sign_flag = self.get_c_type_var(new_name, ~c_type_var.value)
            elif u_op == '-':
                c_type_var, sign_flag = self.get_c_type_var(new_name, -c_type_var.value)
            new_value.add(c_type_var.value)
            if str(c_type_var.value) == 'False' or str(c_type_var.value) == 'True':
                print('debug')
        if len(new_value) == 0:
            print('empty value set, unary')

        # set new value
        del self.current_env.env_var_dict[name]
        self.current_env.env_var_dict[new_name] = new_value
        # set new name
        if expr_var_list.count(name) != 0:
            expr_var_list[expr_var_list.index(name)] = new_name

        return True

    def add_binary_expr(self, bin_op, name1, name2, expr_var_list=[]):
        # what type should the new_var is ?
        new_name = '(' + name1 + ' ' + bin_op + ' ' + name2 + ')'
        self.set_new_type(new_name, name1, name2)

        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)  # this value is not true

        new_value_set = set()
        for old_value1 in self.current_env.env_var_dict[name1]:
            for old_value2 in self.current_env.env_var_dict[name2]:

                if not sign_flag:
                    c_type_var1, flag = self.get_c_type_var(name1, old_value1, unsigned=True)
                    c_type_var2, flag = self.get_c_type_var(name2, old_value2, unsigned=True)
                else:
                    c_type_var1, flag = self.get_c_type_var(name1, old_value1)
                    c_type_var2, flag = self.get_c_type_var(name2, old_value2)

                if bin_op == '+':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value + c_type_var2.value)
                elif bin_op == '-':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value - c_type_var2.value)
                elif bin_op == '*':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value * c_type_var2.value)
                elif bin_op == '/':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, int(c_type_var1.value / c_type_var2.value))
                elif bin_op == '%':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value % c_type_var2.value)
                elif bin_op == '>>':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value >> c_type_var2.value)
                elif bin_op == '<<':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value << c_type_var2.value)
                elif bin_op == '&':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value & c_type_var2.value)
                elif bin_op == '|':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value | c_type_var2.value)
                elif bin_op == '^':
                    c_type_var, sign_flag = self.get_c_type_var(new_name, c_type_var1.value ^ c_type_var2.value)
                elif bin_op == '>':
                    if c_type_var1.value > c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                elif bin_op == '>=':
                    if c_type_var1.value >= c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                elif bin_op == '==':
                    if c_type_var1.value == c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                elif bin_op == '!=':
                    if c_type_var1.value != c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                elif bin_op == '<':
                    if c_type_var1.value < c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                elif bin_op == '<=':
                    if c_type_var1.value <= c_type_var2.value:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 1)
                    else:
                        c_type_var, sign_flag = self.get_c_type_var(new_name, 0)
                new_value_set.add(c_type_var.value)
        if len(new_value_set) == 0:
            print('empty value set, binary')
        del self.current_env.env_var_dict[name1]
        del self.current_env.env_var_dict[name2]
        self.current_env.env_var_dict[new_name] = new_value_set
        if expr_var_list.count(name1) != 0:
            del expr_var_list[expr_var_list.index(name1)]
        if expr_var_list.count(name2) != 0:
            del expr_var_list[expr_var_list.index(name2)]
        expr_var_list.append(new_name)

        return True

    def is_undefined(self, bin_op, name1, name2):
        if bin_op == '/' or bin_op == '%' or bin_op == '>>' or bin_op == '<<':
            for right_value in self.current_env.env_var_dict[name2]:
                if bin_op == '/' and right_value == 0:
                    return True
                if bin_op == '%' and right_value <= 0:
                    return True
                if bin_op == '>>' and right_value < 0:
                    return True
                if bin_op == '<<' and right_value < 0:
                    return True
                if bin_op == '<<' and right_value > 32:
                    return True
                if bin_op == '>>' and right_value > 32:
                    return True
                # there are too many bugs ...
                if bin_op == '/' and abs(right_value) <= 1:
                    return True
                if bin_op == '%' and abs(right_value) <= 1:
                    return True

        for value1 in self.current_env.env_var_dict[name1]:
            for value2 in self.current_env.env_var_dict[name2]:
                new_value = 0
                if bin_op == '+':
                    new_value = value1 + value2
                elif bin_op == '-':
                    new_value = value1 - value2
                elif bin_op == '*':
                    new_value = value1 * value2
                elif bin_op == '<<':
                    new_value = value1 - value2

                if new_value > 0x7fffffff or new_value < -0x7fffffff:
                    return True

            return False

    def set_new_type(self, new_name, name1, name2='', operator=''):
        # (it should not be write like this ...it's awful! )
        if name2 == '':  # unary operator
            ''' It's totally wrong 
                It seems I can not use Python to get the right value of C expression
                (Because of the complex implicit type conversion in C)
                ......
                I choose to modify TCB generation method to avoid wrong predicate
            '''

            if operator == '-':
                if name1 in self.ctx_table.var_name_list_uint8_t or name1 in self.ctx_table.var_name_list_int8_t:
                    self.ctx_table.var_name_list_int8_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_uint16_t or name1 in self.ctx_table.var_name_list_int16_t:
                    self.ctx_table.var_name_list_int16_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_uint32_t or name1 in self.ctx_table.var_name_list_int32_t:
                    self.ctx_table.var_name_list_int32_t.append(new_name)
            else:
                if name1 in self.ctx_table.var_name_list_uint8_t:
                    self.ctx_table.var_name_list_uint8_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_uint16_t:
                    self.ctx_table.var_name_list_uint16_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_uint32_t:
                    self.ctx_table.var_name_list_uint32_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_int8_t:
                    self.ctx_table.var_name_list_int8_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_int16_t:
                    self.ctx_table.var_name_list_int16_t.append(new_name)
                elif name1 in self.ctx_table.var_name_list_int32_t:
                    self.ctx_table.var_name_list_int32_t.append(new_name)

        else:  # binary operator
            if name1 in self.ctx_table.var_name_list_uint8_t:
                bit_len1 = 8
                signed1 = 0
            elif name1 in self.ctx_table.var_name_list_uint16_t:
                bit_len1 = 16
                signed1 = 0
            elif name1 in self.ctx_table.var_name_list_uint32_t:
                bit_len1 = 32
                signed1 = 0
            elif name1 in self.ctx_table.var_name_list_int8_t:
                bit_len1 = 8
                signed1 = 1
            elif name1 in self.ctx_table.var_name_list_int16_t:
                bit_len1 = 16
                signed1 = 1
            elif name1 in self.ctx_table.var_name_list_int32_t:
                bit_len1 = 32
                signed1 = 1

            if name2 in self.ctx_table.var_name_list_uint8_t:
                bit_len2 = 8
                signed2 = 0
            elif name2 in self.ctx_table.var_name_list_uint16_t:
                bit_len2 = 16
                signed2 = 0
            elif name2 in self.ctx_table.var_name_list_uint32_t:
                bit_len2 = 32
                signed2 = 0
            elif name2 in self.ctx_table.var_name_list_int8_t:
                bit_len2 = 8
                signed2 = 1
            elif name2 in self.ctx_table.var_name_list_int16_t:
                bit_len2 = 16
                signed2 = 1
            elif name2 in self.ctx_table.var_name_list_int32_t:
                bit_len2 = 32
                signed2 = 1

            # bit_len_new = max(bit_len1, bit_len2)
            bit_len_new = 32  # only 32 bit int right now
            signed = 1
            if (bit_len1==32 and signed1 == 0) or (bit_len2==32 and signed2 == 0):
                signed = 0

            if bit_len_new == 32 and signed == 0:
                self.ctx_table.var_name_list_uint32_t.append(new_name)
            elif bit_len_new == 32 and signed == 1:
                self.ctx_table.var_name_list_int32_t.append(new_name)
            elif bit_len_new == 8 and signed == 0:
                self.ctx_table.var_name_list_uint8_t.append(new_name)
            elif bit_len_new == 8 and signed == 1:
                self.ctx_table.var_name_list_int8_t.append(new_name)
            elif bit_len_new == 16 and signed == 0:
                self.ctx_table.var_name_list_uint16_t.append(new_name)
            elif bit_len_new == 16 and signed == 1:
                self.ctx_table.var_name_list_int16_t.append(new_name)

            pass

    def get_c_type_var(self, var_name, value, unsigned=False):
        if var_name in self.ctx_table.var_name_list_uint32_t:
            c_type_var = c_uint32(value)
            sign_flag = False
        elif unsigned:
            c_type_var = c_uint32(value)
            sign_flag = False
        else:
            c_type_var = c_int32(value)
            sign_flag = True

        return c_type_var, sign_flag

