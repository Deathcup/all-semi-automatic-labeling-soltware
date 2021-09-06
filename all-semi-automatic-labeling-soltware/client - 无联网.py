from datetime import datetime, timedelta

from PySide2 import QtGui, QtCore
from PySide2.QtCore import QStringListModel, QRect, Qt
from PySide2.QtGui import QPainter, QPen, QImage, QPixmap
from PySide2.QtWidgets import QApplication, QInputDialog, QListView, QLabel, QWidget
from PySide2.QtUiTools import QUiLoader
import socket
import time
import sys
from threading import Thread
import cv2

#因为两个类都要用到就放在全局变量里了（暂时找不到更好的方法）
currentLabel = 'default'        #当前选择的标签
finishList = []     #已标注列表
finishIndex = 0     #选择的标记
exitFlag = False    #退出信号
delFlag = False     #删除信号
updateFlag = False  #更新信号
X = 0
Y = 0

class MyLabel(QLabel):

    x0 = 0
    y0 = 0
    x1 = 0
    y1 = 0
    flag = False

    #鼠标点击事件
    def mousePressEvent(self,event):
        self.flag = True
        self.x0 = event.x()
        self.y0 = event.y()
    #鼠标释放事件
    def mouseReleaseEvent(self,event):
        global currentLabel,finishList
        self.flag = False
        finishList.append([self.x0,self.y0,self.x1,self.y1,currentLabel])

    #鼠标移动事件
    def mouseMoveEvent(self,event):
        if self.flag:
            self.x1 = event.x()
            self.y1 = event.y()
            self.update()

    #绘制事件
    def paintEvent(self, event):
        global finishList,finishIndex,X,Y
        super().paintEvent(event)
        X = self.x1
        Y = self.y1
        painter = QPainter(self)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        for i in finishList:
            if i == finishList[finishIndex]:
                painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
                rect = QRect(i[0], i[1], i[2] - i[0], i[3] - i[1])      #绘制选择中的框
                painter.drawRect(rect)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            else:
                rect = QRect(i[0], i[1], i[2] - i[0], i[3] - i[1])      #绘制之前的框
                painter.drawRect(rect)

        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
        rect = QRect(self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0)  # 绘制当前的框
        painter.drawRect(rect)

    # 随时接受消息，并且更新xy
    def recvOrder(self):
        global exitFlag,delFlag,finishList,updateFlag
        while True:
            #接受删除信号
            if delFlag == True and len(finishList) != 0:
                delFlag = False
                painter = QPainter(self)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                for i in finishList:
                    rect = QRect(i[0], i[1], i[2] - i[0], i[3] - i[1])  # 绘制之前的框
                    painter.drawRect(rect)
                self.update()
            if delFlag == True and len(finishList) == 0:
                delFlag = False
                if self.flag == False:      #加个锁，以防画框的时候更新
                    self.x0 = 0
                    self.y0 = 0
                    self.x1 = 0
                    self.y1 = 0
                painter = QPainter(self)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                rect = QRect(2, 2, 2, 2)
                painter.drawRect(rect)
                self.update()
            # 接受更新信号
            if updateFlag == True:
                updateFlag = False
                self.x0 = 0
                self.y0 = 0
                self.x1 = 0
                self.y1 = 0
                updateFlag = False
                painter = QPainter(self)
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                for i in finishList:
                    if i == finishList[finishIndex]:
                        painter.setPen(QPen(Qt.blue, 2, Qt.SolidLine))
                        rect = QRect(i[0], i[1], i[2] - i[0], i[3] - i[1])  # 绘制选择中的框
                        painter.drawRect(rect)
                        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                    else:
                        rect = QRect(i[0], i[1], i[2] - i[0], i[3] - i[1])  # 绘制之前的框
                        painter.drawRect(rect)
                self.update()


            time.sleep(0.1)
            if exitFlag == True:
                exit(0)



class Client:

    def __init__(self):
        self.ui = QUiLoader().load('my.ui')     #加载ui文件
        self.server = socket.socket()       #socket服务器
        self.labelList = []     #标签列表
        self.labelListModel = QStringListModel()    #标签列表model
        self.finishListModel = QStringListModel()       #已标注列表model
        self.labelIndex = 0     #当前选择的label序号
        self.finishIndex = 0  # 当前选择的finish序号

        self.piclabel = MyLabel(self.ui.imgWidget)

        self.startTime = time.time()


        self.GUI_init()     #gui初始化
        self.net_init()     #网络初始化


    def GUI_init(self):
        self.ui.setFixedSize(self.ui.width(), self.ui.height())      #禁止窗口放大缩小

        self.ui.plusLabelButton.clicked.connect(self.plus_label)
        self.ui.subLabelButton.clicked.connect(self.sub_label)
        self.ui.delButton.clicked.connect(self.del_finish)

        self.ui.labelListView.clicked.connect(self.check_label_item)
        self.ui.finishListView.clicked.connect(self.check_finish_item)

        self.ui.clearLabelButton.clicked.connect(self.clear_label)
        self.ui.redoButton.clicked.connect(self.redo_finish)

        self.piclabel.setGeometry(QRect(0, 0, 741, 601))
        self.piclabel.setCursor(Qt.CrossCursor)

    def run(self):
        Thread(target=self.update_finish, args=()).start()
        Thread(target=self.piclabel.recvOrder, args=()).start()


    def net_init(self):
        pass


    #更新finishListView
    def update_finish(self):
        old = -1
        while True:
            global finishList,finishIndex,updateFlag
            if len(finishList) != old:
                old = len(finishList)
                newFinishList = []
                for i in finishList:
                    newFinishList.append('({},{})->({},{})  {}'.format(i[0],i[1],i[2],i[3],i[4]))
                self.finishListModel.setStringList(newFinishList)        #加入到listmodel
                self.ui.finishListView.setModel(self.finishListModel)      #显示到list中
                finishIndex = len(finishList)-1     #初始化为最后一位
                updateFlag = True


            #顺便更新xy
            global X,Y
            self.ui.xyLabel.setText('X:{} Y:{}'.format(X,Y))

            #顺便更新时间
            sec = time.time()-self.startTime
            d = datetime(1,1,1) + timedelta(seconds=int(sec))
            self.ui.timeLabel.setText('{}:{}:{}'.format(d.hour,d.minute,d.second))

            time.sleep(0.1)
            if exitFlag == True:
                exit(0)

    #点击finishList里的item
    def check_finish_item(self,index):
        global finishIndex,updateFlag
        finishIndex = index.row()
        updateFlag = True
        # print(finishIndex)


    #删除finish的item
    def del_finish(self):
        global finishList,finishIndex,delFlag
        finishList.pop(finishIndex)
        finishIndex = len(finishList)-1     #初始化为最后一位
        newFinishList = []
        for i in finishList:
            newFinishList.append('({},{})->({},{})  {}'.format(i[0], i[1], i[2], i[3], i[4]))
        self.finishListModel.setStringList(newFinishList)  # 加入到listmodel
        self.ui.finishListView.setModel(self.finishListModel)  # 显示到list中
        delFlag = True

    #重做finish
    def redo_finish(self):
        global finishList,finishIndex,delFlag
        finishList = []
        finishIndex = 0
        newFinishList = []
        self.finishListModel.setStringList(newFinishList)  # 加入到listmodel
        self.ui.finishListView.setModel(self.finishListModel)  # 显示到list中
        delFlag = True


    #清空label
    def clear_label(self):
        global currentLabel
        self.labelList = []
        self.labelListModel.setStringList(self.labelList)  # 新列表加入到listmodel
        self.ui.labelListView.setModel(self.labelListModel)  # 显示到list中
        self.labelIndex = 0     #初始化
        currentLabel = 'default'  #初始化
        print('del')

    #添加label
    def plus_label(self):
        global currentLabel
        reply = QInputDialog.getText(None, "添加标签", "请输入要添加的标签信息:")      #弹出输入框
        if reply[1]:
            # 确定
            replyText = reply[0]    #收到的输入信息
            self.labelList.append(replyText)        #增加到label列表
            self.labelListModel.setStringList(self.labelList)        #加入到listmodel
            self.ui.labelListView.setModel(self.labelListModel)      #显示到list中
            self.labelIndex = 0  # 初始化
            currentLabel = 'default'  # 初始化

    #点击label的item
    def check_label_item(self,index):
        global currentLabel
        currentLabel = self.labelList[index.row()]
        self.labelIndex = index.row()
        print(self.labelList[index.row()])

    #删除label的item
    def sub_label(self):
        global currentLabel
        self.labelList.pop(self.labelIndex)
        self.labelListModel.setStringList(self.labelList)  # 新列表加入到listmodel
        self.ui.labelListView.setModel(self.labelListModel)  # 显示到list中
        self.labelIndex = 0     #初始化
        currentLabel = 'default'  #初始化

    def quit(self):
        global exitFlag
        exitFlag = True

if __name__ == '__main__':
    app = QApplication([])
    client = Client()
    client.ui.show()
    #time.sleep(10)
    client.run()
    app.aboutToQuit.connect(client.quit)
    sys.exit(app.exec_())