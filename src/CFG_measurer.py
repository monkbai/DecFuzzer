#!/usr/bin/python3
import subprocess
import os
import re
import math
import time
import gc

from src import Config


class BlockInfo:
    block_name = ''
    num_of_line = 0
    block_txt = ''
    goto_num = 0  # flag >0, if there is any goto stmt at the end of this block
    goto_targets_list = []

    def delete_name(self, matched):
        txt = matched.group(0)
        name = matched.group(1)
        txt = txt.replace(name, '')
        return txt

    def replace_tmp_name(self, txt):
        return re.sub('[^a-z0-9_](_[0-9]+)[^a-z0-9_]', self.delete_name, txt)

    def __init__(self, txt=''):
        if txt == '':
            return
        self.block_txt = txt
        pos = self.block_txt.find('[0.00%]:')
        self.block_name = self.block_txt[:pos].strip(' ')
        self.num_of_line = self.block_txt.count('\n')

        self.goto_targets_list = []

        # get all goto tarets
        tmp_txt = self.block_txt
        goto_pos = tmp_txt.find('goto')
        while goto_pos != -1:
            self.goto_num += 1
            target_name = tmp_txt[goto_pos+4:]
            end_pos = target_name.find('[0.00%]')
            target_name = target_name[:end_pos]
            target_name = target_name.strip(' ;')
            self.goto_targets_list.append(target_name)
            tmp_txt = tmp_txt[tmp_txt.find('goto')+4:]
            goto_pos = tmp_txt.find('goto')

        # remove block name
        self.block_txt = self.block_txt[pos+8:]
        # remove goto target
        tmp_txt = re.sub(r'goto .* \[0.00%\]', 'goto', self.block_txt)
        # remove all tmp variables
        tmp_txt = self.replace_tmp_name(tmp_txt)
        self.block_txt = tmp_txt


class EdgeInfo:
    from_node_name = ''
    to_node_name = ''

    def __init__(self):
        self.from_node_name = ''
        self.to_node_name = ''


class CFGInfo:
    """store CFG information about func_1 in a single program"""
    cfg_txt = ''
    func_1_txt = ''

    nodes_list = [BlockInfo()]
    edges_list = [EdgeInfo()]

    func_1_size = 0  # the number of lines

    compile_cmd = Config.compile_cmd
    # running_directory = Config.running_directory  # not used?
    # runtime_dir = ' -I /home/fuzz/Documents/Fuzzer_3_17/tmp/src_code/runtime/ '
    runtime_dir = ' -I ' + Config.runtime_dir + ' '
    gcc_cfg_option = Config.gcc_cfg_option
    cfg_suffix = Config.cfg_suffix

    file_path = ''

    compilation_success_flag = True
    file_count = 0

    def __get_config(self, config_file):
        isExists = os.path.exists(config_file)
        if not isExists:
            return
        f = open(config_file)
        if f:
            conf_txt = f.read()
        else:
            return
        f.close()

        pos = conf_txt.find('error_tmp_file_count: ')
        if pos == -1:
            return
        count_txt = conf_txt[pos:]
        count_txt = count_txt[:count_txt.find('\n')]
        count_txt = count_txt.replace('error_tmp_file_count: ', '').strip(' \n')
        self.file_count = int(count_txt)

    def __set_config(self, config_file):
        f = open(config_file, 'w')
        f.write('error_tmp_file_count: ' + str(self.file_count) + '\n')
        f.close()

    def __execute_in_dir(self, directory, cmd):
        cmd = 'cd ' + directory + '; ' + cmd
        status, output = subprocess.getstatusoutput(cmd)
        return status, output

    def generate_cfg_file(self):
        if self.file_path != '':
            file_path = self.file_path
        else:
            return -1

        gc.collect()

        if os.path.isdir(file_path):
            pass
        elif os.path.splitext(file_path)[1] == '.c':
            file = os.path.basename(file_path)
            directory = os.path.dirname(file_path)
            file_name, ext_name = os.path.splitext(file)

            cmd = (self.compile_cmd +
                   self.gcc_cfg_option +
                   self.runtime_dir +
                   ' -o ./' + file_name +
                   ' ./' + file)
            # print(cmd)
            status, output = self.__execute_in_dir(directory, cmd)
            # print(output)
            if status != 0:
                print('failed to compile in generate_cfg_file()')
                print(output)
                # get file_count
                self.__get_config('./CFG_config.txt')
                self.file_count += 1
                cmd = 'cp '+file_path+' ' + \
                      os.path.join(directory+'/error/', file[:-2]+str(self.file_count)+'.c')
                print(cmd)
                self.__set_config('./CFG_config.txt')
                status, output = subprocess.getstatusoutput(cmd)
                return -1
            else:
                # print(file_path + self.cfg_suffix + ' generated')
                return 0
        else:
            return -1

    def get_cfg_information(self):
        file_path = self.file_path + self.cfg_suffix
        is_exists = os.path.exists(file_path)
        if not is_exists:
            return
        f = open(file_path)
        self.cfg_txt = f.read()
        f.close()
        func_name = Config.replaced_func_name
        pos = self.cfg_txt.find(func_name+' ()')
        if pos == -1:
            return
        self.func_1_txt = self.cfg_txt[pos:]
        self.func_1_txt = self.func_1_txt[:self.func_1_txt.find('}')+1]

        blocks = self.func_1_txt.split('\n\n')
        blocks = blocks[1:-1]

        # now handle blocks(nodes) one by one
        flag = 1  # last one has no goto stmt
        last_name = ''
        for txt in blocks:
            node = BlockInfo(txt)
            if flag == 0 and txt != blocks[0]:
                # last one has no goto, this node is the successor of last one
                edge = EdgeInfo()
                edge.from_node_name = last_name
                edge.to_node_name = node.block_name
                self.edges_list.append(edge)
            self.func_1_size += node.num_of_line
            self.nodes_list.append(node)
            flag = node.goto_num
            last_name = node.block_name
        # then handle edges
        for node in self.nodes_list:
            for target in node.goto_targets_list:
                edge = EdgeInfo()
                edge.from_node_name = node.block_name
                edge.to_node_name = target
                self.edges_list.append(edge)

    def __init__(self, file_path=''):
        self.nodes_list = []
        self.edges_list = []
        if file_path == '':
            return
        self.file_path = file_path
        status = self.generate_cfg_file()
        if status != 0:
            self.compilation_success_flag = False
            return
        self.get_cfg_information()

    def __del__(self):
        if self.file_path == '':
            return

        file = os.path.basename(self.file_path)
        directory = os.path.dirname(self.file_path)
        file_name, ext_name = os.path.splitext(file)
        file_path = os.path.join(directory, file_name)
        cmd = 'rm ' + file_path
        # print(cmd)
        status, output = subprocess.getstatusoutput(cmd)
        cmd = 'rm ' + self.file_path + self.cfg_suffix
        # print(cmd)
        status, output = subprocess.getstatusoutput(cmd)


class Distance:
    cfg_1 = CFGInfo()
    cfg_2 = CFGInfo()

    equal_nodes_list = [['', '']]  # [block name in CFG 1, block name in CFG 2]
    equal_edges_list = [[0, 0]]  # [id of edge in CFG 1, id of edge in CFG 2]

    alpha = 5
    beta = 5
    gamma = 0.005
    # sigma = 0.5

    def __init__(self, cfg_1=CFGInfo(), cfg_2=CFGInfo()):
        self.cfg_1 = cfg_1
        self.cfg_2 = cfg_2
        self.equal_nodes_list = []
        self.equal_edges_list = []
        self.d_v = 0
        self.d_e = 0
        self.d_s = 0

    def get_equal_nodes(self):
        for node1 in self.cfg_1.nodes_list:
            for node2 in self.cfg_2.nodes_list:
                if node1.block_txt == node2.block_txt:
                    self.equal_nodes_list.append(
                        [node1.block_name, node2.block_name])
                    break

    def get_equal_edges(self):
        for edge1 in self.cfg_1.edges_list:
            for edge2 in self.cfg_2.edges_list:
                from_name1 = edge1.from_node_name
                from_name2 = edge2.from_node_name
                to_name1 = edge1.to_node_name
                to_name2 = edge2.to_node_name

                if self.equal_nodes_list.count([from_name1, from_name2]) != 0 and \
                        self.equal_nodes_list.count([to_name1, to_name2]) != 0:
                    index1 = self.cfg_1.edges_list.index(edge1)
                    index2 = self.cfg_2.edges_list.index(edge2)
                    self.equal_edges_list.append([index1, index2])
                    break

    def get_distance(self):
        self.get_equal_nodes()
        self.get_equal_edges()

        d_v = len(self.equal_nodes_list) / (len(self.cfg_1.nodes_list) +
                                            len(self.cfg_2.nodes_list) -
                                            len(self.equal_nodes_list))
        d_v = 1 - d_v
        self.d_v = d_v

        # d_v = len(self.cfg_1.nodes_list)+len(self.cfg_2.nodes_list)-len(self.equal_nodes_list)
        # d_v = d_v / (len(self.cfg_1.nodes_list)+len(self.cfg_2.nodes_list))

        d_e = len(self.equal_edges_list) / (len(self.cfg_1.edges_list) +
                                            len(self.cfg_2.edges_list) -
                                            len(self.equal_edges_list))
        d_e = 1 - d_e
        self.d_e = d_e
        # d_e = len(self.cfg_1.edges_list) + len(self.cfg_2.edges_list) - len(self.equal_edges_list)
        # d_e = d_e / (len(self.cfg_1.edges_list) + len(self.cfg_2.edges_list))

        d_s = self.cfg_1.func_1_size - self.cfg_2.func_1_size
        # d_s = abs(d_s)
        self.d_s = d_s
        # print('abs d_size ', abs(d_s))
        distance = self.alpha*d_v + self.beta*d_e - self.gamma*abs(d_s)

        # print('distance:', distance, '=',
        #       self.alpha, '*', d_v, '+', self.beta, '*', d_e, '-', self.gamma,'*', d_s)
        # prob = math.exp(distance)
        # print('exp:', prob)
        return distance


class AcceptProb:

    sigma = 3
    distance_old = Distance()
    distance_new = Distance()

    dis_new = 0.1
    dis_old = 0.2

    def __init__(self):
        dis_new = 0.1
        dis_old = 0.2

    def get_accept_prob(self, q_new, q_old, p):
        cfg_q_new = CFGInfo(q_new)
        if cfg_q_new.compilation_success_flag is False:
            return -1, 0, 0
        cfg_q_old = CFGInfo(q_old)
        cfg_p = CFGInfo(p)

        distance_old = Distance(cfg_q_old, cfg_p)
        distance_new = Distance(cfg_q_new, cfg_p)

        self.dis_new = distance_new.get_distance()
        # print('distance new', self.dis_new)
        self.dis_old = distance_old.get_distance()
        # print('distance old', self.dis_old)

        if math.exp(self.sigma * (self.dis_new - self.dis_old)) >= 1:
            # print('probability ', str(1))
            return 1, distance_new.d_s, distance_old.d_s
        # print('probability ', math.exp(self.sigma * (self.dis_new - self.dis_old)))
        # return accept_probability, diff_size_of_new_file, diff_size_of_old_file
        return math.exp(self.sigma * (self.dis_new - self.dis_old)), distance_new.d_s, distance_old.d_s


