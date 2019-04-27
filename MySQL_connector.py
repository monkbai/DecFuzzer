#!/usr/bin/python3
import random

import pymysql


class MysqlConncetor:
    host = 'localhost'
    user = "root"
    passwd = "123456"

    db_name = 'CODE_CORPUS'

    TABLES = dict()
    TABLES['code_snippets'] = (
        "CREATE TABLE `code_snippets` ("
        "  `code_num` int unsigned NOT NULL AUTO_INCREMENT,"
        "  `int8_t_num` int unsigned NOT NULL,"
        "  `i8_var_list` text ,"
        "  `int16_t_num` int unsigned NOT NULL,"
        "  `i16_var_list` text ,"
        "  `int32_t_num` int unsigned NOT NULL,"
        "  `i32_var_list` text ,"
        "  `uint8_t_num` int unsigned NOT NULL,"
        "  `u8_var_list` text ,"
        "  `uint16_t_num` int unsigned NOT NULL,"
        "  `u16_var_list` text ,"
        "  `uint32_t_num` int unsigned NOT NULL,"
        "  `u32_var_list` text ,"
        "  `label_num` int unsigned NOT NULL,"
        "  `label_list` text ,"
        "  `nested_loop` int unsigned NOT NULL,"
        "  `code_text` text ,"
        "  PRIMARY KEY (`code_num`)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8")

    add_stmt = ("INSERT INTO code_snippets "
                "(int8_t_num,  i8_var_list, "
                "int16_t_num,  i16_var_list, "
                "int32_t_num,  i32_var_list, "
                "uint8_t_num,  u8_var_list, "
                "uint16_t_num, u16_var_list, "
                "uint32_t_num, u32_var_list, "
                "label_num,    label_list, "
                "nested_loop,  code_text) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    query_stmt = ("SELECT i8_var_list, i16_var_list, i32_var_list, "
                  "u8_var_list, u16_var_list, u32_var_list, "
                  "label_list, code_text "
                  "FROM code_snippets "
                  "WHERE "
                  "int8_t_num <= %s AND "
                  "int16_t_num <= %s AND "
                  "int32_t_num <= %s AND "
                  "uint8_t_num <= %s AND "
                  "uint16_t_num <= %s AND "
                  "uint32_t_num <= %s AND "
                  "label_num <= %s AND "
                  "nested_loop <= %s "
                  "ORDER BY code_num DESC "
                  "LIMIT 500")

    delete_stmt = ["SET SQL_SAFE_UPDATES = 0; ",
                   "DELETE FROM a USING CODE_CORPUS.code_snippets AS a, CODE_CORPUS.code_snippets AS b where (a.code_num < b.code_num) and (a.code_text = b.code_text); ",
                   "SET SQL_SAFE_UPDATES = 1; "]

    def __init__(self):
        self.mydb = pymysql.connect(
            host=self.host,
            user=self.user,
            passwd=self.passwd
        )
        self.my_cursor = self.mydb.cursor()
        self.use_database(self.my_cursor)
        self.create_table(self.my_cursor)
        self.my_cursor.close()

    def __del__(self):
        self.delete_repeated_stmt()
        self.my_cursor.close()
        self.mydb.close()

    def connect(self):
        self.mydb = pymysql.connect(
            host=self.host,
            user=self.user,
            passwd=self.passwd
        )
        self.my_cursor = self.mydb.cursor()
        self.use_database(self.my_cursor)
        self.create_table(self.my_cursor)

    def create_database(self, cursor):
        try:
            cursor.execute(
                "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(self.db_name))
        except pymysql.Error as err:
            print("Failed creating database: {}".format(err))
            exit(-1)

    def use_database(self, cursor):
        try:
            cursor.execute("USE {}".format(self.db_name))
        except pymysql.Error as err:
            print("Database {} does not exists.".format(self.db_name))
            self.create_database(cursor)
            print("Database {} created successfully.".format(self.db_name))
            self.mydb.database = self.db_name

    def create_table(self, cursor):
        for table_name in self.TABLES:
            table_description = self.TABLES[table_name]
            # print("Creating table {}: ".format(table_name), end='')
            try:
                # print("Creating table {}: ".format(table_name), end='')
                self.my_cursor.execute(table_description)
            except pymysql.Error as err:
                code, message = err.args
                if code == 1050:
                    pass  # print("already exists.")
                else:
                    print(message)
            else:
                pass  # print("OK")

    def add_code_snippet(self, code_data=()):
        if len(code_data) != 16:
            return -1
        try:
            self.my_cursor = self.mydb.cursor()
        except pymysql.Error as err:
            self.connect()
        try:
            # Insert new record
            self.my_cursor.execute(self.add_stmt, code_data)
        except pymysql.Error as err:
            print('code_data', code_data)
            code, message = err.args
            print(">>>>>>>>>>>>>", code, message)
            exit(-1)
        code_num = self.my_cursor.lastrowid
        # Make sure data is committed to the database
        self.mydb.commit()
        self.my_cursor.close()
        return code_num

    def query_code_snippet(self, code_data=()):
        if len(code_data) != 8:
            return -1
        try:
            self.my_cursor = self.mydb.cursor()
        except pymysql.Error as err:
            self.connect()
        try:
            # select record
            self.my_cursor.execute(self.query_stmt, code_data)
        except pymysql.Error as err:
            print('query_data', code_data)
            code, message = err.args
            print(">>>>>>>>>>>>>", code, message)
            exit(-1)
        all_data = self.my_cursor.fetchall()
        self.my_cursor.close()
        return all_data

    def delete_repeated_stmt(self):
        try:
            self.my_cursor = self.mydb.cursor()
        except pymysql.Error as err:
            self.connect()
        try:
            self.my_cursor.execute(self.delete_stmt[0])
            effected_row = self.my_cursor.execute(self.delete_stmt[1])
            # print('try to delete repeated data:')
            # print(str(effected_row), 'rows are effected')
            self.my_cursor.execute(self.delete_stmt[2])
            # Make sure data is committed to the database
            self.mydb.commit()
        except pymysql.Error as err:
            code, message = err.args
            print(">>>>>>>>>>>>>", code, message)


def test():
    db = MysqlConncetor()

    test_data = ('0', 'a', '0', 'b', '0', 'c', '0', 'd', '0', 'e', '0', 'f', '0', 'g', '0', 'h')
    num = db.add_code_snippet(test_data)
    print('code_num', num, 'inserted')

    all_data = db.query_code_snippet(('10', '10', '10', '10', '10', '10', '10', '10'))
    print(type(all_data))
    print(type(all_data[0]))
    all_data = list(all_data)
    one = random.choice(all_data)
    print(one)

    all_data = db.query_code_snippet(('10', '10', '10', '10', '10', '10', '10', '10'))
    print(type(all_data))
    print(type(all_data[0]))
    all_data = list(all_data)
    one = random.choice(all_data)
    print(one)

    test_data = ('0', 'a', '0', 'b', '0', 'c', '0', 'd', '0', 'e', '0', 'f', '0', 'g', '0', 'h')
    num = db.add_code_snippet(test_data)
    print('code_num', num, 'inserted')


def tmp_test():
    li = ['1','2','3','4','5']
    lis = ''
    for l in li:
        lis += l
        if l != li[-1]:
            lis += ', '
    print(lis)

if __name__ == '__main__':
    query_stmt = ("SELECT i8_var_list, i16_var_list, i32_var_list, "
                  "u8_var_list, u16_var_list, u32_var_list, "
                  "label_list, code_text "
                  "FROM code_snippets "
                  "WHERE "
                  "int8_t_num <= %s AND "
                  "int16_t_num <= %s AND "
                  "int32_t_num <= %s AND "
                  "uint8_t_num <= %s AND "
                  "uint16_t_num <= %s AND "
                  "uint32_t_num <= %s AND "
                  "label_num <= %s AND "
                  "nested_loop <= %s")
    print(query_stmt, 5,5,5,5,5,5,5,5)
    # test()
