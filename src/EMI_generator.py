#!/usr/bin/python3
import subprocess
import os
import threading
import random
import copy
import re

from src import replacer, Config, modifier
from src.MySQL_connector import MysqlConncetor
from src.CFG_measurer import AcceptProb, CFGInfo, Distance
from src.ENV_Profiler import Profiler, ENV, Synthesizer
from src.ContextTable import ContextTable


class StmtWithContext:
    context_table = ContextTable()
    stmt_txt = ''

    db = MysqlConncetor()

    def __init__(self):
        self.db = MysqlConncetor()

    def set_context_table(self, context):
        # this is the context BEFORE this statement
        self.context_table = copy.deepcopy(context)

    @staticmethod
    def list_to_line(var_list=[]):
        line = ''
        for item in var_list:
            line += str(item)
            if item != var_list[-1]:
                line += ','
        return line

    @staticmethod
    def set_var_in_list(stmt_txt, list_old, list_new):
        """The variables in <list_old> are used in <stmt>
           will be put into <list_new>
        """
        for var_name in list_old:
            if var_name == '{' or var_name == '}':
                continue
            reg_exp = var_name + r"[^0-9]+"
            pattern = re.compile(reg_exp)
            matches = pattern.finditer(stmt_txt)
            for m in matches:
                list_new.append(var_name)
                break
        # list_new = list(set(list_new)) # does not work

    def get_stmt(self, stmt_txt='', context=ContextTable()):
        """<stmt_txt>: extracted statement
           <context>: context table BEFORE this statement
           This statement should NOT include a label
           (conflict temporarily is not checked)
        """

        # <tmp_context> will store all context information used by this <stmt>
        tmp_context = ContextTable()

        # check if there is any break or continue
        if stmt_txt.find('break') != -1 or stmt_txt.find('continue') != -1:
            tmp_context.nested_loop = 1  # this stmt need to be in a loop

        # then check all outside variables
        self.set_var_in_list(stmt_txt, context.var_name_list_int8_t, tmp_context.var_name_list_int8_t)
        tmp_context.var_name_list_int8_t = list(set(tmp_context.var_name_list_int8_t))
        self.set_var_in_list(stmt_txt, context.var_name_list_int16_t, tmp_context.var_name_list_int16_t)
        tmp_context.var_name_list_int16_t = list(set(tmp_context.var_name_list_int16_t))
        self.set_var_in_list(stmt_txt, context.var_name_list_int32_t, tmp_context.var_name_list_int32_t)
        tmp_context.var_name_list_int32_t = list(set(tmp_context.var_name_list_int32_t))
        self.set_var_in_list(stmt_txt, context.var_name_list_uint8_t, tmp_context.var_name_list_uint8_t)
        tmp_context.var_name_list_uint8_t = list(set(tmp_context.var_name_list_uint8_t))
        self.set_var_in_list(stmt_txt, context.var_name_list_uint16_t, tmp_context.var_name_list_uint16_t)
        tmp_context.var_name_list_uint16_t = list(set(tmp_context.var_name_list_uint16_t))
        self.set_var_in_list(stmt_txt, context.var_name_list_uint32_t, tmp_context.var_name_list_uint32_t)
        tmp_context.var_name_list_uint32_t = list(set(tmp_context.var_name_list_uint32_t))

        # then check if there are goto statements
        reg_exp = r"goto .*;"
        pattern = re.compile(reg_exp)
        matches = pattern.finditer(stmt_txt)
        for m in matches:
            label_name = m.group().strip(' ;')
            label_name = label_name.replace('goto ', '')
            tmp_context.label_name_list.append(label_name)
        # remove duplicated elements
        tmp_context.label_name_list = list(set(tmp_context.label_name_list))

        # finally, we get a statement and a context that should be satisfied
        self.stmt_txt = stmt_txt
        self.context_table = tmp_context

    def generate_insert_tuple(self):
        return (str(len(self.context_table.var_name_list_int8_t)),  # int8_t_num
                self.list_to_line(self.context_table.var_name_list_int8_t),  # i8_var_list
                str(len(self.context_table.var_name_list_int16_t)),  # int16_t_num
                self.list_to_line(self.context_table.var_name_list_int16_t),  # i16_var_list,
                str(len(self.context_table.var_name_list_int32_t)),  # int32_t_num,
                self.list_to_line(self.context_table.var_name_list_int32_t),  # i32_var_list,
                str(len(self.context_table.var_name_list_uint8_t)),  # uint8_t_num,
                self.list_to_line(self.context_table.var_name_list_uint8_t),  # u8_var_list,
                str(len(self.context_table.var_name_list_uint16_t)),  # uint16_t_num,
                self.list_to_line(self.context_table.var_name_list_uint16_t),  # u16_var_list,
                str(len(self.context_table.var_name_list_uint32_t)),  # uint32_t_num,
                self.list_to_line(self.context_table.var_name_list_uint32_t),  # u32_var_list,
                str(len(self.context_table.label_name_list)),  # label_num,
                self.list_to_line(self.context_table.label_name_list),  # label_list,
                str(self.context_table.nested_loop),  # nested_loop,
                self.stmt_txt  # code_text
                )

    def store_stmt(self):
        code_data = self.generate_insert_tuple()
        # print(code_data)
        return self.db.add_code_snippet(code_data)

    def generate_query_tuple(self):
        return (str(max(0, len(self.context_table.var_name_list_int8_t) -
                        self.context_table.var_name_list_int8_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # int8_t_num
                str(max(0, len(self.context_table.var_name_list_int16_t) -
                        self.context_table.var_name_list_int16_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # int16_t_num
                str(max(0, len(self.context_table.var_name_list_int32_t) -
                        self.context_table.var_name_list_int32_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # int32_t_num,
                str(max(0, len(self.context_table.var_name_list_uint8_t) -
                        self.context_table.var_name_list_uint8_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # uint8_t_num,
                str(max(0, len(self.context_table.var_name_list_uint16_t) -
                        self.context_table.var_name_list_uint16_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # uint16_t_num,
                str(max(0, len(self.context_table.var_name_list_uint32_t) -
                        self.context_table.var_name_list_uint32_t.count('{') -
                        len(self.context_table.const_var_name_list))),  # uint32_t_num,
                str(max(0, len(self.context_table.label_name_list))),  # label_num,
                str(max(0, self.context_table.nested_loop)),  # nested_loop,
                )

    def replace_name_in_list(self, list_old_str='', list_current=[]):
        """For each name A in <list_old>, randomly choose a name B in <list_current>
           Then replace every A with B in <self.stmt_txt>
        """
        if list_old_str == '':
            return
        used_list = []
        list_old = list_old_str.split(',')

        random.shuffle(list_current)
        for name in list_old:
            # choose a new name from <list_current>
            for new_name in list_current:
                if new_name in used_list or new_name == '{' or new_name in self.context_table.const_var_name_list:
                    continue
                else:
                    used_list.append(new_name)
                    break
            if new_name == list_current[-1] and (new_name == '{' or new_name in self.context_table.const_var_name_list):
                new_name = used_list[0]
            # for debug info
            # print('replace', name, 'with', new_name)
            # then replace old name with new name
            reg_exp = r"[^a-zA-Z0-9_]" + name + r"[^a-zA-Z0-9_]"  # match exact name
            pattern = re.compile(reg_exp)
            matches = pattern.finditer(self.stmt_txt)
            pos1 = 0
            pos2 = 0
            new_stmt_txt = ''
            for m in matches:
                pos1 = pos2
                pos2 = m.end() - 1  # attention the <reg_exp>
                # check if it's a declaration in a compound statement
                if self.stmt_txt[m.start()-2:m.start()+1].startswith('_t '):
                    # if we meet a declaration with the same old name, break
                    new_stmt_txt += self.stmt_txt[pos1:pos2]
                    break
                new_stmt_txt += self.stmt_txt[pos1:m.start()+1] + new_name
            new_stmt_txt += self.stmt_txt[pos2:]
            # a new stmt_txt now
            self.stmt_txt = new_stmt_txt

    def parse_query_result(self, the_tuple):
        """The goal of this function is updating <stmt_txt>
           All variables and labels should be replaced with
           correspond vars and labels in current context table
        """
        (i8_var_list, i16_var_list, i32_var_list,
         u8_var_list, u16_var_list, u32_var_list,
         label_list, code_text) = the_tuple
        self.stmt_txt = code_text
        # replace variables
        self.replace_name_in_list(i8_var_list, self.context_table.var_name_list_int8_t)
        self.replace_name_in_list(i16_var_list, self.context_table.var_name_list_int16_t)
        self.replace_name_in_list(i32_var_list, self.context_table.var_name_list_int32_t)
        self.replace_name_in_list(u8_var_list, self.context_table.var_name_list_uint8_t)
        self.replace_name_in_list(u16_var_list, self.context_table.var_name_list_uint16_t)
        self.replace_name_in_list(u32_var_list, self.context_table.var_name_list_uint32_t)
        # replace labels in goto statements
        self.replace_name_in_list(label_list, self.context_table.label_name_list)
        # now the <self.stmt_txt> should be a transplantable statement

    def query_stmt(self):
        """query database, and randomly pick out a statement as result
           before call this function, <set_context_table> should be called
        """
        query_data = self.generate_query_tuple()
        # print(query_data)
        all_stmt = self.db.query_code_snippet(query_data)
        # print(all_stmt)
        if len(all_stmt) == 0:
            self.stmt_txt = ''
            return

        the_one = random.choice(all_stmt)
        self.parse_query_result(the_one)


class EMIGenerator:

    gcc_cmd = "gcc -fno-stack-protector -no-pie -O0 -m32 --coverage "
    include_csmith_runtime = " -I " + Config.runtime_dir + ' '
    gcov_cmd = "gcov -m "

    timeout_sec = 3

    probability_remove = 0.5
    probability_insert = 0.5

    file_path = ''
    source_code_txt = ''

    cov_txt = ''
    cov_code_list = []

    context_table = ContextTable()
    SWC = StmtWithContext()

    delete_files_list = []  # remove generated files when the object is destroying

    def __init__(self, file_path=''):
        if file_path != '':
            self.file_path = file_path
            f = open(file_path)
            if f:
                self.source_code_txt = f.read()
                f.close()
            self.cov_txt = ''
            self.cov_code_list = []
            self.SWC = StmtWithContext()
            self.profiler = Profiler()
            self.delete_files_list = []

    # @staticmethod
    def flip_coin(self, which_type=1):
        # self.probability_WholeLoop = random.random()
        if which_type == 1:
            return random.random() > 0.8
        elif which_type == 2:  # remove
            self.probability_remove = random.random()
            return (random.random() + 0.1) > self.probability_remove
        elif which_type == 3:  # insert
            self.probability_insert = random.random()
            return random.random() > self.probability_insert
        else:
            return random.random() > 0.5

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

    def __execute_in_dir(self, directory, cmd):
        cmd = 'cd ' + directory + '; ' + cmd
        status, output = subprocess.getstatusoutput(cmd)
        return status, output

    def gen_coverage_file(self):
        if self.file_path == '':
            print('wrong file path in gen_coverage_file()')
            return
        file_path = self.file_path
        file = os.path.basename(file_path)
        directory = os.path.dirname(file_path)
        file_name, ext_name = os.path.splitext(file)

        # First: compile with --coverage option, generate .gcno file
        cmd = (self.gcc_cmd +
               self.include_csmith_runtime +
               './'+file + ' -o ' + './'+file_name)
        sta, out = self.__execute_in_dir(directory, cmd)
        if sta != 0:
            print('Failed to compile in gen_coverage_file()')
            print(out)
            return sta, out

        # Second: then run the program, generate .gcda file
        fname, ename = os.path.splitext(file_path)
        stdout, stderr = self.__run_single_prog(fname)

        # Third: get coverage information, the .gcov file
        cmd = (self.gcov_cmd +
               './'+file +
               ' -o ./ ')
        sta, out = self.__execute_in_dir(directory, cmd)
        if sta != 0:
            print('Failed to execute gcov in gen_coverage_file()')
            print(out)
            return sta, out
        # Open and set cov_txt
        cov_file_path = file_path + '.gcov'
        f = open(cov_file_path)
        if f:
            self.cov_txt = f.read()
            f.close()
        # Finally: record files need to remove at the end
        self.delete_files_list.append(fname + '.gcno')
        self.delete_files_list.append(fname + '.gcda')
        self.delete_files_list.append(fname)
        # self.delete_files_list.append(file_path + '.gcov')
        while out.find("File '") != -1:
            out = out[out.find("File '")+6:]
            tmp_name = out[:out.find("'")]
            tmp_name = os.path.basename(tmp_name)
            tmp_name = os.path.join(directory, tmp_name)
            self.delete_files_list.append(tmp_name + '.gcov')

        return sta, out

    def __del__(self):
        for name in self.delete_files_list:
            status, output = subprocess.getstatusoutput("rm " + name)

    @staticmethod
    def strip_cov_line(line=''):
        return line[16:].strip(' ')

    def check_stmt(self, index, stmt=''):
        """check if it's a parent statement or declaration statement
           If it is a parent stmt, then check if its children have been executed
           return 0 if this statement can be removed, return 1 if not
        """
        if stmt == '':
            stmt = self.cov_code_list[index]
        # if this statement is a single statement, end_pos equals to index
        end_pos = index
        is_parent = 0
        # Check if it's a parent statement
        stmt = self.strip_cov_line(stmt)
        if stmt.startswith('for') or \
                stmt.startswith('while') or \
                stmt.startswith('switch') or \
                stmt.startswith('if') or \
                stmt.startswith('else'):
            flag, end_pos = self.check_children_stmt(index, stmt)
            is_parent = 1
            if flag > 0:
                return 1, end_pos, is_parent
            else:
                return 0, end_pos, is_parent

        # Check if it's a declaration
        elif stmt.startswith('int') or \
                stmt.startswith('uint') or \
                stmt.startswith('const') or \
                stmt.startswith('volatile') or \
                stmt.startswith('static') or \
                stmt.startswith('{') or \
                stmt.startswith('}'):
            return 1, end_pos, is_parent  # declaration cannot be removed
        elif stmt.startswith('set_var') or stmt.startswith('printf'):
            return 1, end_pos, is_parent
        # Check if it's a label
        elif stmt.endswith(':') or stmt.endswith(':;'):
            return 1, end_pos, is_parent
        # It's a single statement, which can be removed
        else:
            return 0, end_pos, is_parent

    def check_children_stmt(self, index, parent_stmt):
        """return the number of executed children statements
           so if return value <flag> is 0, this parent statement could be removed,
           not if <flag> larger than 0
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
        flag = 0  # the number of executed children statements
        while True:
            stmt = self.cov_code_list[index]
            # executed?
            if not stmt.startswith('    #####:') \
                    and not stmt.startswith('        -:'):
                flag += 1
            stmt = self.strip_cov_line(stmt)
            # brace?
            if stmt.startswith('{'):
                brace_count += 1
            elif stmt.startswith('}'):
                brace_count -= 1
            elif stmt.endswith(':'):  # TODO: temporarily ignore all stmt with inside labels
                flag += 1
            elif stmt.startswith('set_var') or stmt.startswith('printf') or stmt.startswith('packed_printf'):
                flag += 1
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

    @staticmethod
    def get_blank_prefix(string=''):
        if not string.startswith(' '):
            return ''
        c = string.strip(' ')[0]
        str_list = string.split(c)
        return str_list[0]

    @staticmethod
    def replace_blank_prefix(string='', new_prefix=''):
        if string == '':
            return string
        prefix_blank = EMIGenerator.get_blank_prefix(string)
        str_list = string.split('\n')
        result_str = ''
        for line in str_list:
            if prefix_blank == '':
                line = new_prefix + line
            else:
                line = line.replace(prefix_blank, new_prefix, 1)
            if line != str_list[-1]:
                line += '\n'
            result_str += line
        return result_str

    def get_pos_of_func1(self):
        start, end = replacer.find_fun_pos_with_name(self.source_code_txt, 'func_1')
        start_line_num = self.source_code_txt[:start].count('\n') + 1
        end_line_num = self.source_code_txt[:end].count('\n')
        return start_line_num, end_line_num

    def remove_stmt(self, line, index, end_pos, is_parent):
        txt_section = ''
        removed_stmt_txt = ''
        # in the case of parent statement
        if is_parent != 0:
            # Authors of EMI paper said the probability could be random
            # and that may leads to a huge statement being deleted at one time
            # We try to avoid remove a long compound statement
            huge_stmt_flag = (end_pos - index) / 100.0
            if random.random() >= huge_stmt_flag and self.flip_coin(2):
                # this statement should be removed
                txt_section += \
                    ''  # self.get_blank_prefix(line[16:]) + ';\n'
                # record the whole statement
                for i in range(index, end_pos+1):
                    removed_stmt_txt += self.cov_code_list[i][16:] + '\n'
                index = end_pos  # jump over it
            else:  # not remove
                txt_section += line[16:] + '\n'
        # in the case of single statement
        elif is_parent == 0:
            last_line = self.strip_cov_line(self.cov_code_list[index-1])
            if last_line.startswith('if') or last_line.startswith('else'):
                txt_section += line[16:] + '\n'
            elif self.flip_coin(2):  # remove this single statement
                # replace whole stmt with ;
                txt_section += \
                    ''  # self.get_blank_prefix(line[16:]) + ';\n'
                # record removed statement
                removed_stmt_txt += line[16:] + '\n'
            else:  # not remove
                txt_section += line[16:] + '\n'
        return index, txt_section, removed_stmt_txt

    def insert_stmt(self):
        """According to current context_table,
           return a transplantable statement
           (most parts of this function are implemented in SWC)
        """
        # self.SWC.set_context_table(self.context_table) # not always
        self.SWC.query_stmt()
        return self.SWC.stmt_txt

    def gen_fcb(self, env):
        '''False Condition Block of Live Code Mutation'''
        pred_depth = random.randint(1, 4)
        predicate = Synthesizer.syn_pred(env, False, pred_depth)
        block_txt = 'if' + predicate + '\n'
        block_txt+= '{/*False Condition Block*/\n'

        # randomly select some code from Database
        self.SWC.set_context_table(self.context_table)
        add_stmt_txt = self.insert_stmt()  # insert function
        add_stmt_txt = self.replace_blank_prefix(add_stmt_txt, '    ')

        block_txt+= add_stmt_txt
        block_txt+= '}\n'

        return block_txt

    def gen_tg(self, env, start_pos, end_pos):
        '''True Guard of Live Code Mutation'''
        pred_depth = random.randint(1, 4)
        predicate = Synthesizer.syn_pred(env, True, pred_depth)
        block_txt = 'if' + predicate + '\n'
        block_txt += '{/*True Guard */\n'

        # get the original code , from start_pos to end_pos
        org_stmt_txt = ''
        for i in range(start_pos, end_pos + 1):
            org_stmt_txt += self.cov_code_list[i][16:] + '\n'
        org_stmt_txt = self.replace_blank_prefix(org_stmt_txt, '    ')

        block_txt += org_stmt_txt
        block_txt += '}\n'

        return block_txt

    def gen_tcb(self, env=ENV()):
        '''True Condition Block of Live Code Mutation'''
        # select some variables at random
        tmp_var_list = list(env.env_var_dict.keys())
        if len(tmp_var_list)-len(self.context_table.const_var_name_list) <= 0:
            return ''
        var_num = random.randint(1, len(tmp_var_list)-len(self.context_table.const_var_name_list))
        # I am not sure if var_num should be limited to some small value
        var_num = min(var_num, 5)
        var_list = []
        while len(var_list) < var_num:
            var_name = random.choice(tmp_var_list)
            if var_name not in var_list and var_name not in self.context_table.const_var_name_list:
                var_list.append(var_name)

        syn = Synthesizer(self.context_table)
        current_env = copy.deepcopy(env)

        # a True Condition
        block_txt = ''
        pred_depth = random.randint(1, 4)
        predicate = Synthesizer.syn_pred(env, True, pred_depth)
        block_txt += 'if' + predicate + '\n'
        block_txt += '{/*True Condition Block*/\n'

        # declarations of backup variables
        decl_txt = ''
        for var_name in var_list:
            var_type = self.context_table.type_of_var(var_name)
            expr_txt = syn.syn_expr(env)
            # current_env.env_var_dict['backup_'+var_name] = syn.current_env[expr_txt]
            decl_txt += '    ' + var_type + ' backup_' + var_name + ' = ' + expr_txt + ';\n'
        block_txt += decl_txt

        # backup
        for var_name in var_list:
            # current_env.env_var_dict['backup_' + var_name] = env.env_var_dict[var_name]
            block_txt += '    backup_' + var_name + ' = ' + var_name + ';\n'

        # randomly set value to selected variables
        for var_name in var_list:
            expr_txt = syn.syn_expr(current_env)

            # here, we want to update new value of this var
            # Type of this var and type of the expr may be different
            value_set = set()
            for value in list(syn.current_env.env_var_dict[expr_txt]):
                c_type_var = self.context_table.get_c_type_of_var(var_name, value)
                value_set.add(c_type_var.value)
            current_env.env_var_dict[var_name] = value_set
            ''' Since I failed to get right value at here
                and wrong value often lead to wrong predicate below
                So I choose to delete used variables ...
            '''
            del current_env.env_var_dict[var_name]
            block_txt += '    ' + var_name + ' = ' + expr_txt + ';\n'

        # a False Condition Block
        pred_depth = random.randint(1, 4)
        predicate = Synthesizer.syn_pred(current_env, False, pred_depth)

        ##### for debug
        if predicate.find('False') != -1 or predicate.find('True') != -1:
            print('debug')

        if_or_while = random.randint(1, 2)
        if if_or_while == 1:  # is statement
            stmt_type = 'if'
        else:  # while statement
            stmt_type = 'while'
        block_txt += '    ' + stmt_type + predicate + '\n'
        block_txt += '    {\n'
        for var_name in var_list:
            block_txt += '        ' + 'packed_printf(' + var_name + ');\n'
        block_txt += '    }\n'

        # restore all variables
        for var_name in var_list:
            block_txt += '    ' + var_name + ' = ' + 'backup_' + var_name + ';\n'

        # end of True Condition Block
        block_txt += '}\n'

        return block_txt

    def gen_variant(self):
        if self.cov_txt == '':
            return
        self.context_table = ContextTable()
        start_line, end_line = self.get_pos_of_func1()

        # First: set cov_txt, cov_list and code_list
        cov_list = self.cov_txt.split('\n')
        # info_list = cov_list[:5]
        self.cov_code_list = cov_list[5:]
        # set profiler, too
        self.profiler = Profiler(cov_txt=self.cov_txt, src_txt=self.source_code_txt)
        self.profiler.profile()
        instrumented_line_num_list =[]
        for env in self.profiler.env_list:
            instrumented_line_num_list.append(env.line_num)

        # Second: visit each line in txt
        variant_txt = ''
        length = len(self.cov_code_list)
        index = 0
        while index < length:
            line = self.cov_code_list[index]
            # check if this line is in func_1
            if index < start_line or index > end_line:
                variant_txt += line[16:] + '\n'
                index += 1
                continue

            # If this line is executed, we can just update context_table
            # But if it's un-executed, updating ctx table or not depends on
            # if we would remove this statement
            tmp_line = self.strip_cov_line(line)
            if line.startswith('    #####:'):  # this line is un-executed
                # check if it's children stmts have been executed
                flag, end_pos, is_parent = self.check_stmt(index, line)
                if flag == 0:  # it can be removed
                    '''It is un-executed and can be removed(no executed children)
                       We can choose to remove it or
                        insert stmt before or after it
                    '''

                    '''Step A: try to insert before this statement (half chance)'''
                    if (not tmp_line.startswith('else') and   # do not insert before else stmt
                            (not self.strip_cov_line(self.cov_code_list[index-1]).startswith('if')) and
                            (not self.strip_cov_line(self.cov_code_list[index - 1]).startswith('else')) and
                            self.flip_coin(1) and self.flip_coin(3)):
                        self.SWC.set_context_table(self.context_table)
                        add_stmt_txt = self.insert_stmt()  # insert function
                        pre_blank = self.get_blank_prefix(line[16:])
                        add_stmt_txt = self.replace_blank_prefix(add_stmt_txt, pre_blank)
                        variant_txt += add_stmt_txt

                    '''Step B: try to remove this statement( with certain possibility )'''
                    new_index, txt_section, removed_stmt_txt = \
                        self.remove_stmt(line, index, end_pos, is_parent)
                    index = new_index
                    variant_txt += txt_section
                    if removed_stmt_txt != '':  # this stmt is removed
                        # store removed stmt
                        self.SWC.get_stmt(removed_stmt_txt, self.context_table)
                        self.SWC.store_stmt()  # store into database
                    else:
                        # if it's not removed, update context table
                        self.context_table.add_context_line(line[16:])

                    '''Step C: try to insert after this statement (half chance)'''
                    if (not (removed_stmt_txt=='' and tmp_line.startswith('while')) and
                            not (removed_stmt_txt=='' and tmp_line.startswith('for')) and  # do not insert after loop
                            not (removed_stmt_txt=='' and tmp_line.startswith('if')) and  # do not insert after if stmt
                            self.flip_coin(1) and self.flip_coin(3)):
                        self.SWC.set_context_table(self.context_table)  # update context
                        add_stmt_txt = self.insert_stmt()  # insert function
                        pre_blank = self.get_blank_prefix(line[16:])
                        add_stmt_txt = self.replace_blank_prefix(add_stmt_txt, pre_blank)
                        variant_txt += add_stmt_txt

                elif not tmp_line == '':  # it cannot be removed
                    self.context_table.add_context_line(line[16:])
                    variant_txt += line[16:]+'\n'
                else:
                    print(tmp_line)
                    pass
            elif index + 1 in instrumented_line_num_list:  # it's selected, try to add FCB, TG or TCB
                # get env of current line
                # current_env = self.profiler.env_list[instrumented_line_num_list.index(index+1)]
                for env in self.profiler.env_list:
                    if env.line_num == index + 1:
                        current_env = env
                        current_env.correct_value(self.context_table)
                        break

                # get the end position of this statement (used for True Guard)
                flag, end_pos, is_parent = self.check_stmt(index, line)

                type_choice = random.randint(1, 5)
                if type_choice <= 2:  # False Condition Block
                    fcb_txt = self.gen_fcb(current_env)
                    self.context_table.add_context_line(line[16:])
                    pre_blank = self.get_blank_prefix(line[16:])
                    fcb_txt = self.replace_blank_prefix(fcb_txt, pre_blank)
                    variant_txt += fcb_txt
                    variant_txt += line[16:] + '\n'
                    # print('FCB inserted') # pass
                elif type_choice <= 4:  # True Guard
                    tg_txt = self.gen_tg(current_env, index, end_pos)
                    pre_blank = self.get_blank_prefix(line[16:])
                    tg_txt = self.replace_blank_prefix(tg_txt, pre_blank)
                    variant_txt += tg_txt
                    for pos in range(index, end_pos+1):
                        inside_line = self.cov_code_list[pos]
                        self.context_table.add_context_line(inside_line[16:])
                    index = end_pos
                    # print('TG inserted') # pass
                elif type_choice == 5:  # True Condition Block
                    tcb_txt = self.gen_tcb(current_env)
                    self.context_table.add_context_line(line[16:])
                    pre_blank = self.get_blank_prefix(line[16:])
                    tcb_txt = self.replace_blank_prefix(tcb_txt, pre_blank)
                    variant_txt += tcb_txt
                    variant_txt += line[16:] + '\n'
                    # print('TCB inserted') # pass
            else:  # it is executed
                self.context_table.add_context_line(line[16:])
                variant_txt += line[16:]+'\n'
            # add a semicolon at the end of a label
            if variant_txt.endswith(':\n'):
                variant_txt = variant_txt[:-1]+';\n'
            # turn to next line
            index += 1
        # here we get a variant
        return variant_txt[:-2]  # remove redundant \n at the end


class EMIWrapper:
    """ MCMC sampling"""
    org_file = ''
    AP = AcceptProb()

    last_variant_txt = ''
    new_variant_txt = ''

    def __init__(self, original_file_path=''):
        if original_file_path != '':
            self.org_file = original_file_path
        self.emi = EMIGenerator()
        self.AP = AcceptProb()
        self.last_variant_txt = ''
        self.new_variant_txt = ''

    @staticmethod
    def write_to_file(path, txt):
        f = open(path, 'w')
        f.write(txt)
        f.close()

    def gen_a_new_variant(self):
        if self.last_variant_txt == '':
            self.emi = EMIGenerator(self.org_file)
            sta, out = self.emi.gen_coverage_file()
            if sta != 0:
                return sta, ''
            self.last_variant_txt = self.emi.gen_variant()
            self.last_variant_txt = modifier.check_for_printf(self.last_variant_txt)
            return 0, self.last_variant_txt

        flag = False
        times_count = 0
        while not flag:
            if times_count > 10:
                return -1, ''

            times_count += 1
            path1 = './last_variant_txt.tmp.c'
            self.write_to_file(path1, self.last_variant_txt)
            # print('trying %dth times to generate next variant...' % times_count)
            self.emi = EMIGenerator(path1)
            sta, out = self.emi.gen_coverage_file()
            if sta != 0:
                return sta, ''
            self.new_variant_txt = self.emi.gen_variant()
            self.new_variant_txt = modifier.check_for_printf(self.new_variant_txt)

            # temporarily store <variant_txt>, to get their CFG info
            path2 = './new_variant_txt.tmp.c'
            self.write_to_file(path2, self.new_variant_txt)

            pro, d_s_new, d_s_old = self.AP.get_accept_prob(q_new=path2, q_old=path1, p=self.org_file)
            # print('probability', pro)
            status, output = subprocess.getstatusoutput("rm " + path1)
            status, output = subprocess.getstatusoutput("rm " + path2)

            # extra probability is used to prevent generating to many times
            extra_pro = (times_count-3) * 0.05
            extra_pro = min(0.5, extra_pro)

            if random.random() < pro + extra_pro:
                flag = True
                # tune probability of live code mutation
                if d_s_new > 300:
                    Config.probability_live_code_mutate = (0.3 - (0.1 * (d_s_new / 100.0)))
                elif d_s_new < 0:
                    Config.probability_live_code_mutate = 0.3
                # print('new variant generated, distance: ', str(self.AP.dis_new))
        self.last_variant_txt = self.new_variant_txt
        return 0, self.new_variant_txt

