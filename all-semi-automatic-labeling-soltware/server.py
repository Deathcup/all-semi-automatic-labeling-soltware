import socket
from threading import Thread
import json
import os

g_socket = None
g_conn_pool = []

#设定图片文件夹
imgs_path = "E:\\CQU-Project\\all-semi-automatic-labeling-soltware\\serverImg"
#编写函数计算文件夹下图片的个数，并将所有的图片文件名存到 file_list 列表中
file_list = []
#图片的总个数
img_numbers = 0
#上线的总用户数量
num_user_online = 0


def get_img_in_folder(path):
    global file_list
    filelist = os.listdir(path)
    for item in filelist:
        #过滤jpg格式的图片
        if(item.endswith('.jpg')):
            file_list.append(item)



def handle_client():    #接收新client
    global num_user_online
    while True:
        client, addr = g_socket.accept()
        print()
        print(addr,end='')
        print('上线了')
        #统计当前在线的用户数
        num_user_online = num_user_online + 1
        g_conn_pool.append(client)
        t = Thread(target=message_handle, args=(client,addr,))
        t.setDaemon(True)
        t.start()

def message_handle(client,addr):        #处理线程

        #获取处理好的文件名file_list列表
        global file_list
        print(file_list)

        #
        for item in file_list:
            print(item)
            global num_user_online
            send_img(client,item)

            while True:
                data = client.recv(1024).decode('utf-8')
                print(data)
                if data == 'SUBMIT':
                    jsonData = client.recv(1024).decode('utf-8')
                    finishList = json.loads(jsonData)
                    client.send('Submitted successfully'.encode('utf-8'))  # 返回提交成功的信息

                    print(finishList)

                    #取客户端取到的json名称并保存
                    split_name_file = item.split(".")
                    temp_json_clinet_name = split_name_file[0]
                    client_filename = 'clientImg/' + temp_json_clinet_name + ".json"  # 暂时存起来
                    with open(client_filename, 'w') as file_obj:
                        json.dump(finishList, file_obj)
                    break

                if data == 'EXIT':
                    g_conn_pool.remove(client)
                    client.send(data.encode('utf-8'))
                    print(addr, end='')
                    print('下线了')
                    # 更新当前在线的用户数
                    num_user_online = num_user_online - 1
                    break


        # send_img(client,'1.jpg')
        # while True:
        #     data = client.recv(1024).decode('utf-8')
        #     print(data)
        #     if data == 'SUBMIT':
        #
        #         jsonData = client.recv(1024).decode('utf-8')
        #         finishList = json.loads(jsonData)
        #         client.send('Submitted successfully'.encode('utf-8'))       #返回提交成功的信息
        #
        #         print(finishList)
        #         filename = 'clientImg/1.json'      #暂时存起来
        #         with open(filename, 'w') as file_obj:
        #             json.dump(finishList, file_obj)
        #
        #         send_img(client, '2.jpg')
        #
        #     if data == 'EXIT':
        #         g_conn_pool.remove(client)
        #         client.send(data.encode('utf-8'))
        #         print(addr,end='')
        #         print('下线了')
        #         break

#传输图片
def send_img(client,imgName):
    imgPath = 'serverImg/'+imgName
    fp = open(imgPath,'rb')
    bytes = fp.read()
    size = len(bytes)
    client.sendall("IMG SIZE {} {}".format(size,imgName).encode('utf-8'))
    answer = client.recv(1024).decode('utf-8')
    # print(answer)

    while True:
        data = bytes[:1024]     #每次发1024bit
        bytes = bytes[1024:]
        if not data:
            print('{} file send over'.format(imgName))
            break
        client.send(data)
    #一起传送标记信息 json
    filepath = 'serverImg/' + imgName[:-4] + '.json'
    finishList = []
    if os.path.exists(filepath):
        print('json Labeling Files exits')
        with open(filepath) as file_obj:
            finishList = json.load(file_obj)
    print(finishList)
    jsonData = json.dumps(finishList)
    client.send(jsonData.encode('utf-8'))


def get_nums_user_online():
    global num_user_online
    print(num_user_online)
    return num_user_online




def main():
    global g_socket, g_conn_pool,file_list
    g_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    g_socket.bind(('127.0.0.1', 12306))
    g_socket.listen(5)
    print("服务端已启动，等待客户端连接...")

    t = Thread(target=handle_client)
    t.setDaemon(True)
    t.start()

    get_img_in_folder(imgs_path)
    print(file_list)
    print(len(file_list))

    while True:
        cmd = input("请输入操作：")
        if cmd == '':
            continue
        if int(cmd) == 1:
            print("--------------------------")
            print("当前在线人数：", len(g_conn_pool))
        if cmd == 'exit':
            exit()

if __name__ == '__main__':
    main()