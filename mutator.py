#!/usr/bin/python3
import random
import os
import re

types = ['char', 'int', 'short', 'long', 'float', 'double']
file = 'test.c'
fileNameStr = ''  # file striped .c
outputDir = ''  # fileNameStr stripped .mutMethod
mutationCount = 0


def writeFile(code = '', mutMethod = '' ):
    global mutationCount
    global fileNameStr
    name = fileNameStr
    f = open(outputDir+name+'_mut'+str(mutationCount)+'_'+mutMethod+'.c', 'w')
    f.write(code)
    f.close()
    mutationCount += 1


def paserFileName(name):
    i = name.rfind('.')
    if i != -1:
        mutMethod = name[i+1:]
        others = name[:i]
    else:
        return [name, '']
    return [others, mutMethod]


'''Check if main is in the same line'''
def checkMain(code='', pos=0):
    indexend = code[pos:].find('\n') + pos
    indexbeg = code[:pos].rfind('\n')
    indexmain = code[indexbeg+1:indexend+1].find('main')
    if indexmain == -1:
        return False
    else:
        return True


def mutateType(srcCode=''):
    mutCode = srcCode
    for orgType in types:
        index = mutCode.find(orgType)
        while(index != -1):
            for mutType in types:
                if checkMain(mutCode, index) or mutCode[index+len(orgType)]!=' ':  # or mutCode[index-1]!=' ' ?
                    break
                if mutType == orgType:
                    continue
                mutCode = mutCode[:index] + mutType + mutCode[index + len(orgType):]
                writeFile(mutCode, 'type')
                mutCode = srcCode
            index = mutCode.find(orgType, index + len(orgType))


def findRightParen(str=''):
    '''find right parenthesis
    '''
    i = 0
    paren = 0
    while 1:
        if str[i] == '(':
            paren += 1
            i += 1
            break
        i += 1
    while paren != 0:
        if str[i] == '(': paren += 1
        elif str[i] == ')': paren -= 1
        i += 1
    return i


def changeValueInStmt(matched):
    value = int(matched.group('value'))
    return str(value + 1)


def mutateStmt(srcCode='', stmtType='', times = 10):

    if stmtType!='if' and stmtType!='for' and stmtType!='while':
        print('undefined type: '+stmtType)
        return -1

    mutCode = srcCode
    index = mutCode.find(stmtType)
    while index != -1 and times != 0 :
        RParen = findRightParen(mutCode[index:]) + index
        tmpString = re.sub('(?P<value>\d+)', changeValueInStmt, mutCode[index:RParen])
        mutString = ''
        for repTime in range(1, times+1):
            mutString = tmpString + mutString
            tmpString = re.sub('(?P<value>\d+)', changeValueInStmt, tmpString)

            tmpCode = mutCode[:index] + mutString + mutCode[index:RParen] + mutCode[RParen:]
            writeFile(tmpCode, stmtType+'Stmt')

        mutCode = srcCode
        index = mutCode.find(stmtType, RParen)  # find next statement


chars = '''abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\
    ~!@#$%^&*()_+-=`{}|:<>?,./;\'[]\\'''

def mutateStr(srcCode='', times =10):
    mutCode = srcCode
    index = mutCode.find('"')
    while index != -1 and times != 0:
        nextQuotes = mutCode[index+1:].find('"') + index+1

        for repTime in range(1, times+1):
            randChar = ''
            for i in range(repTime):
                randChar += random.choice(chars)
            tmpCode = mutCode[:index] + mutCode[index:nextQuotes] + randChar + mutCode[nextQuotes:]
            writeFile(tmpCode, 'str')

        mutCode = srcCode
        index = mutCode.find('"', nextQuotes+1)


def mutate_single_file(file_path, file_name, output_dir):
    global mutationCount
    global file
    global fileNameStr
    global outputDir
    file = file_path
    fileNameStr = file_name
    outputDir = output_dir
    mutationCount = 0

    isExists = os.path.exists(outputDir)
    if not isExists:
        os.makedirs(outputDir)
        print('create output dir: ' + outputDir)
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print('output dir ' + outputDir + ' exists.')

    print('begin to mutate file: ' + file + ' ...')

    f = open(file, 'r')
    src_code = f.read()
    f.close()

    mutateType(src_code)
    mutateStmt(src_code, 'if')
    mutateStmt(src_code, 'for')
    mutateStmt(src_code, 'while')
    mutateStr(src_code)

def main():
    global mutationCount
    global file
    mutationCount = 0
    f = open(file, 'r')
    srcCode = f.read()
    f.close()

    mutateType(srcCode)
    mutateStmt(srcCode, 'if')
    mutateStmt(srcCode, 'for')
    mutateStmt(srcCode, 'while')
    mutateStr(srcCode)


if __name__ == '__main__':

    i = file.find('.')
    if i != -1:
        fileNameStr = file[:i]
    else:
        fileNameStr = file

    i = file.rfind('.')
    if i != -1:
        outputDir = file[:i]
    else:
        outputDir = file
    outputDir = './' + outputDir + '/'


    isExists = os.path.exists(outputDir)
    if not isExists:
        os.makedirs(outputDir)
        print('create output dir: ' + outputDir)
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print('output dir '+outputDir+' exists.')

    print('begin to mutate file: '+file+' ...')
    main()
