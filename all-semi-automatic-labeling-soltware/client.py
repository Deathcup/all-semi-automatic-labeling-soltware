from datetime import datetime, timedelta
from PySide2 import QtGui, QtCore
from PySide2.QtCore import QStringListModel, QRect, Qt
from PySide2.QtGui import QPainter, QPen, QImage, QPixmap
from PySide2.QtWidgets import QApplication, QInputDialog, QListView, QLabel, QWidget, QMessageBox
from PySide2.QtUiTools import QUiLoader
import socket
import time
import sys
from threading import Thread
import cv2
import json

#因为两个类都要用到就放在全局变量里了（暂时找不到更好的方法）
currentLabel = 'default'        #当前选择的标签
finishList = []     #已标注列表
finishIndex = 0     #选择的标记
exitFlag = False    #退出信号
delFlag = False     #删除信号
updateFlag = False  #更新信号
X = 0
Y = 0

#自定义Label类，可以画
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



#客户端
class Client:

    def __init__(self):
        self.ui = QUiLoader().load('my.ui')     #加载ui文件
        self.server = socket.socket()       #socket服务器
        self.labelList = []     #标签列表
        self.labelListModel = QStringListModel()    #标签列表model
        self.finishListModel = QStringListModel()       #已标注列表model
        self.labelIndex = 0     #当前选择的label序号
        self.finishIndex = 0    # 当前选择的finish序号
        self.autoFinishList = []    #自动标注的结果

        self.picLabel = MyLabel(self.ui.imgWidget)

        self.startTime = time.time()


        self.GUI_init()     #gui初始化
        self.net_init()     #网络初始化

        self.run()      #运行线程


    def GUI_init(self):
        self.ui.setWindowTitle('半自动标记软件')
        self.ui.setFixedSize(self.ui.width(), self.ui.height())      #禁止窗口放大缩小

        self.ui.plusLabelButton.clicked.connect(self.plus_label)
        self.ui.subLabelButton.clicked.connect(self.sub_label)
        self.ui.delButton.clicked.connect(self.del_finish)

        self.ui.labelListView.clicked.connect(self.check_label_item)
        self.ui.finishListView.clicked.connect(self.check_finish_item)

        self.ui.clearLabelButton.clicked.connect(self.clear_label)
        self.ui.redoButton.clicked.connect(self.redo_finish)

        self.picLabel.setGeometry(QRect(0, 0, 741, 601))
        self.picLabel.setCursor(Qt.CrossCursor)     #改变

        self.picLabel.setAlignment(Qt.AlignLeft)        #左上对齐
        self.picLabel.setAlignment(Qt.AlignTop)         #左上对齐

        self.ui.submitButton.clicked.connect(self.submit)       #提交按钮
        self.ui.suggestButton.clicked.connect(self.suggest)     #推荐标签按钮
        self.ui.autoButton.clicked.connect(self.autoLabing)     #自动标记按钮
        self.ui.skipButton.clicked.connect(self.skip)           #跳过按钮
        self.ui.exitButton.clicked.connect(self.quit)           #退出按钮


    def run(self):
        Thread(target=self.update_finish, args=()).start()
        Thread(target=self.picLabel.recvOrder, args=()).start()
        Thread(target=self.recv_massage,args=()).start()




    def net_init(self):
        self.server.connect(('127.0.0.1', 12306))    #链接服务器

    #接受消息的线程
    def recv_massage(self):
        while True:
            data = self.server.recv(1024).decode('utf-8').strip()
            #print(data)
            if data.startswith('IMG'):      #如果收到的是图片
                tmp = data.split(' ')
                fileSize = int(tmp[2])
                imgName = tmp[3]
                #print(fileSize)
                self.server.sendall('GOT SIZE'.encode('utf-8'))
                recvSize = 0
                imgPath = 'clientImg/'+imgName
                fp = open(imgPath, 'wb')
                #print("start receiving...")
                while not recvSize == fileSize:
                    #print(recvSize/fileSize)
                    self.ui.recvLabel.setText('已接收:{}%'.format(int(recvSize/fileSize*100)))
                    if fileSize - recvSize > 1024:
                        data = self.server.recv(1024)
                        recvSize += len(data)
                    else:
                        data = self.server.recv(fileSize - recvSize)
                        recvSize = fileSize
                    fp.write(data)
                fp.close()
                self.ui.recvLabel.setText('已接收:{}%'.format(100))
                self.ui.nameLabel.setText("当前标注的图片名称为：" + imgName)
                self.show_img(imgPath)
                #接收自动标注的信息
                jsonData = self.server.recv(1024).decode('utf-8')
                self.autoFinishList = json.loads(jsonData)
                #print(self.autoFinishList)
                #print("end receive...")
            if data == 'EXIT':
                exit(0)

    #将图片展示在label中
    def show_img(self,imgPath):
        # img = QtGui.QPixmap(imgPath)
        # print(imgPath)
        # self.picLabel.setPixmap(img)
        img = cv2.imread(imgPath)
        height, width, bytesPerComponent = img.shape
        bytesPerLine = 3*width
        cv2.cvtColor(img, cv2.COLOR_BGR2RGB, img)
        QImg = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(QImg)
        self.picLabel.setPixmap(pixmap)
        #self.picLabel.setScaledContents(True)




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

    #把结果提交给server
    def submit(self):
        #global finishList
        global  delFlag, finishList, updateFlag
        self.server.send('SUBMIT'.encode('utf-8'))
        data = json.dumps(finishList)       #把list变成json传
        self.server.send(bytes(data.encode('utf-8')))

        #每一次sunmit后设置相应清除画框的Flag
        finishList = []
        delFlag = True
        updateFlag = True

    #推荐标签
    def suggest(self):
        global currentLabel
        if len(self.autoFinishList) == 0:
            QMessageBox.about(self.ui, "提示", "目前没有推荐标签")
        else:
            suggestSet = set()
            for i in self.autoFinishList:
                suggestSet.add(i[4])
            suggestList = list(suggestSet)
            for i in suggestList:
                self.labelList.append(i)
            self.labelListModel.setStringList(self.labelList)        #加入到listmodel
            self.ui.labelListView.setModel(self.labelListModel)      #显示到list中
            self.labelIndex = 0  # 初始化
            currentLabel = 'default'  # 初始化

    #自动标记
    def autoLabing(self):
        global finishList,updateFlag
        if len(self.autoFinishList) == 0:
            QMessageBox.about(self.ui, "提示", "目前无法自动标注")
        else:
            finishList = []
            for i in self.autoFinishList:
                finishList.append(i)
            updateFlag = True
            pass

    #跳过
    def skip(self):
        pass

    #退出
    def quit(self):
        global exitFlag
        exitFlag = True     #修改退出信号，为了退出正在运行的线程
        self.server.send('EXIT'.encode('utf-8'))    #退出前告诉服务器
        sys.exit()

if __name__ == '__main__':
    app = QApplication([])
    client = Client()
    client.ui.show()
    #time.sleep(10)
    #client.run()        #运行线程
    app.aboutToQuit.connect(client.quit)    #把退出链接到红叉
    sys.exit(app.exec_())