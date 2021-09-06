from PySide2.QtWidgets import QApplication, QMessageBox
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QTextCursor
from PySide2.QtCore import QStringListModel
from PyQt5 import QtCore
#导入自定义的功能模块
from server import g_conn_pool as conn_list
from server import main as server_main
from rename_dataset_filename import main as rename_main


from threading import Thread
import os
import subprocess

server_message = []
server_model_message = []


class Winodow_stats:

    def __init__(self):
        # 从文件中加载UI定义

        # 从 UI 定义中动态 创建一个相应的窗口对象
        # 注意：里面的控件对象也成为窗口对象的属性了
        # 比如 self.ui.button , self.ui.textEdit
        self.ui = QUiLoader().load('server.ui')


        self.ui.startserverButton.clicked.connect(self.start_server_thread)
        self.ui.startModelButton.clicked.connect(self.server_model_thread)
        self.ui.renameButton.clicked.connect(self.rename_function)


        self.labelServerListModel = QStringListModel()  # 标签列表model
        self.labelModelListModel = QStringListModel()  # 标签列表model

    # 执行shell指令 下面分别是两个按钮对应的功能启动所用的命令
    def cmd_server_start(self):
        self.run_server("python server.py")
        # server_main()



    def cmd_model_start(self):
        self.run_model("python serverModel/detect.py")
        # os.system('python serverModel/detect.py')
        MessageBox.warning(self.ui, "提示", "服务器自动标注运行模型完成！！")

    #分线程处理的入口
    def server_model_thread(self):
        print("+++ Start Model server succeed! +++ 启动模型训练与自动标注服务器成功 +++")
        QMessageBox.warning(self.ui, "提示", "模型监测与自动标注服务已经启动，请耐心等待新的标签生成完毕！")
        # 启动自动标注模型
        t = Thread(target=self.cmd_model_start)
        t.setDaemon(True)
        t.start()

    def start_server_thread(self):
        # 创建线程执行函数
        t1 = Thread(target=self.cmd_server_start)
        print("+++ Start server succeed! +++ 启动数据分发与监控服务器成功 +++")
        t1.start()

    def update_online_user(self):
        t2 = Thread(target=self.update_nums_user)
        t2.setDaemon(True)
        t2.start()

    def update_nums_user(self):
        # while True:
        self.ui.statusLabel.setText("SET:当前服务器在线用户数：" + str(len(conn_list)))

    def rename_function(self):
        QMessageBox.warning(self.ui, "提示", "正在格式化命名数据集图片文件.....")
        rename_main()
        QMessageBox.warning(self.ui, "提示", "格式化命名数据集图片文件完成！")

    def run_model(self, command):
        global server_model_message
        process = subprocess.Popen(command,shell=False,stdout=subprocess.PIPE,universal_newlines=True,encoding='UTF-8')

        while process.poll() is None:
            line = process.stdout.readline()
            line = line.strip()
            info = str(line)
            if line:
                pinfo = 'Model Logs output :  {}'.format(info)
                server_model_message.append(pinfo)

                print(server_model_message)

                self.labelModelListModel.setStringList(server_model_message)
                self.ui.modelInfoList.setModel(self.labelModelListModel)

    # shell执行函数，支持长时间运行
    def run_server(self, command):
        global server_message
        process = subprocess.Popen(command,shell=False,stdout=subprocess.PIPE,universal_newlines=True,encoding='UTF-8')

        while process.poll() is None:
            line = process.stdout.readline()
            line = line.strip()
            info = str(line)
            if line:
                pinfo = 'Server Logs output :  {}'.format(info)
                server_message.append(pinfo)
                # print(type(server_model_message))

                self.labelServerListModel.setStringList(server_message)
                self.ui.serverInfoList.setModel(self.labelServerListModel)
                self.update_online_user()


if __name__ == '__main__':

    app = QApplication([])
    window_stats = Winodow_stats()
    window_stats.ui.show()
    app.exec_()