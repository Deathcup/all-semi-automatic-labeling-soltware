import numpy as np
def cal_Cmass(data):
    '''
    input:data(ndarray):数据样本
    output:mass(ndarray):数据样本质心
    '''
    Cmass = np.mean(data,axis=0)
    return Cmass

cmass = cal_Cmass([[-1,3],
                   [1,1],
                   [-2,2]])

print(cmass)



# import shlex
# import subprocess
#
# if __name__ == '__main__':
#     shell_cmd = 'ping baidu.com'
#     cmd = shlex.split(shell_cmd)
#     print(cmd)
#     p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, universal_newlines=True)
#
#     while p.poll() is None:
#         line = p.stdout.readline()
#         line = line.strip()
#         if line:
#             print('Subprogram output: {}'.format(line))

# from subprocess import *
# import subprocess
#
# # host = input('输入一个主机地址:')
# #
# # p = Popen(['ping', '-c5', host],
# #           stdin=PIPE,
# #           stdout=PIPE,
# #           )
# # p.wait()
# # out = p.stdout.read()
# #
# # print(out)
#
# ret = subprocess.check_output(['ping', 'baidu.com'], universal_newlines=True)
# print(ret)

# import sys
#
#
# class myStdout():
#     def __init__(self):
#         self.stdoutbak = sys.stdout
#         self.stderrbak = sys.stderr
#         sys.stdout = self
#         sys.stderr = self
#
#     def write(self, info):
#         # info信息即标准输出sys.stdout和sys.stderr接收到的输出信息
#         str = info.rstrip("\r\n")
#         if len(str): self.processInfo(str)  # 对输出信息进行处理的方法
#
#     def processInfo(self, info):
#         self.stdoutbak.write("标准输出接收到消息：" + info + "\n")  # 可以将信息再输出到原有标准输出，在定位问题时比较有用
#
#     def restoreStd(self):
#         print("准备恢复标准输出")
#         sys.stdout = self.stdoutbak
#         sys.stderr = self.stderrbak
#         print("恢复标准输出完成")
#
#     def __del__(self):
#         self.restoreStd()
#
#
# print("主程序开始运行,创建标准输出替代对象....")
# mystd = myStdout()
# print("test12314")
# print("标准输出替代对象创建完成,准备销毁该替代对象")
#
# mystd.restoreStd()
# #del mystd
# print("主程序结束")
