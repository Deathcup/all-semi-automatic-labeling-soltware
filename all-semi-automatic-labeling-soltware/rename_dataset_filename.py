import os

user_dataset_path = "E:\\CQU-Project\\all-semi-automatic-labeling-soltware\\user-admin\\data"

old_file_list = []
new_file_list = []

#获取文件夹下指定格式的文件之后形成old_files_list
def get_img_in_folder(path):
    global old_file_list
    file_list = os.listdir(path)
    for item in file_list:
        #过滤jpg格式的图片
        if(item.endswith('.jpg')):
            old_file_list.append(item)

#定义序号命名的函数使得数据集看起来整齐有序
def rename_dataset_number():
    #这里根据标注系统而言 无0开头的图片序号
    num = 1
    global old_file_list,new_file_list
    for item in old_file_list:

        #获取要命名的每一个图片的全路径
        oldname = user_dataset_path + '\\' + item

        #不含路径的新子文件名
        sub_new_name = str(num)+'.jpg'

        #将更名后的所有图片文件的信息存储至new_file_list
        new_file_list.append(sub_new_name)

        # 设置新文件名：改成相应图片序号的编号文件名
        newname = user_dataset_path + '\\' + sub_new_name


        # 用os模块中的rename方法对文件改名
        os.rename(oldname, newname)

        #更新num的序号
        num = num + 1

def main():
    get_img_in_folder(user_dataset_path)
    print(old_file_list)
    rename_dataset_number()
    print(new_file_list)
    print("---格式化重命名带标注数据成功！！---")


if __name__ == '__main__':

    mian()

