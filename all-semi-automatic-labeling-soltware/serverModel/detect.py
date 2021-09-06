import argparse
import os
import shutil
import time
from pathlib import Path

import json

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
# from utils.datasets import path
from utils.general import (
    check_img_size, non_max_suppression, apply_classifier, scale_coords,
    xyxy2xywh, strip_optimizer, set_logging)
from utils.plots import colors, plot_one_box

from utils.torch_utils import select_device, load_classifier, time_sync


def detect(save_img=False):
    # 获取设置的参数数据
    out, source, weights, view_img, save_txt, imgsz = \
        opt.save_dir, opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size
    webcam = source.isnumeric() or source.startswith(('rtsp://', 'rtmp://', 'http://')) or source.endswith('.txt')

    #--------------------模型和图片检测入口-设置图片源文件夹和模型名称文件-------------------------------------------------
    source = "E:\\CQU-Project\\all-semi-automatic-labeling-soltware\\serverImg\\"
    weights = "E:\\CQU-Project\\all-semi-automatic-labeling-soltware\\serverModel\\yolov5s.pt"

    #out ="E:\\CQU-Project\\all-semi-automatic-labeling-soltware\\serverImg\\"
    out = "label_detect_img"

    # Initialize
    set_logging()
    device = select_device(opt.device)
    if os.path.exists(out):  # output dir
        shutil.rmtree(out)  # delete dir
    os.makedirs(out)  # make new dir
    # 如果设备为GPU时， 使用Float16
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model 确保用户设定的输入图片分辨率能整除32(如不能则调整为能整除并返回)
    model = attempt_load(weights, map_location=device)  # load FP32 model
    imgsz = check_img_size(imgsz, s=model.stride.max())  # check img_size
    if half:
        model.half()  # to FP16

    # Second-stage classifier 设置第二次分类，默认不使用
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model'])  # load weights
        modelc.to(device).eval()

    # Set Dataloader 通过不同的输入源来设置不同的数据加载方式
    vid_path, vid_writer = None, None
    if webcam:
        view_img = True
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz)
    else:
        save_img = True
        dataset = LoadImages(source, img_size=imgsz)

    # Get names and colors
    # 获取类别名字
    names = model.module.names if hasattr(model, 'module') else model.names
    # 设置画框的颜色
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    t0 = time.time()
    # 进行一次前向推理,测试程序是否正常
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)  # init img
    _ = model(img.half() if half else img) if device.type != 'cpu' else None  # run once

    # 输出json文件
    save_json = True
    content_json = []
    # 设置生成json文件的序号循环文件，按照通常命名逻辑，图片的序号与detect中图片吞吐的个数相同
    # 后期这里改成对文件名的获取

    json_number = 1
    # path 图片/视频路径
    # img 进行resize+pad之后的图片
    # img0 原size图片
    # cap 当读取图片时为None，读取视频时为视频源

    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        # 图片也设置为Float16
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        # 没有batch_size的话则在最前面添加一个轴
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        #利用path分割出当前处理的文件名
        # print(path)  先用\\分割出所有的目录路径
        all_split_path_file_name = path.split('\\')
        # print(all_split_path_file_name)
        # 取出倒数第一个就是文件名 例如 [1.jpg]
        split_path_file_name = all_split_path_file_name[-1:]
        #取出来字符串的文件名

        current_file_name = split_path_file_name[0]


        # Inference
        t1 = time_sync()
        """
        前向传播 返回pred的shape是(1, num_boxes, 5+num_class)
        h,w为传入网络图片的长和宽，注意dataset在检测时使用了矩形推理，所以这里h不一定等于w
        num_boxes = h/32 * w/32 + h/16 * w/16 + h/8 * w/8
        pred[..., 0:4]为预测框坐标
        预测框坐标为xywh(中心点+宽长)格式
        pred[..., 4]为objectness置信度
        pred[..., 5:-1]为分类结果
        """
        pred = model(img, augment=opt.augment)[0]

        # Apply NMS
        """
        pred:前向传播的输出
        conf_thres:置信度阈值
        iou_thres:iou阈值
        classes:是否只保留特定的类别
        agnostic:进行nms是否也去除不同类别之间的框
        经过nms之后，预测框格式：xywh-->xyxy(左上角右下角)
        pred是一个列表list[torch.tensor]，长度为batch_size
        每一个torch.tensor的shape为(num_boxes, 6),内容为box+conf+cls
        """
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t2 = time_sync()

        # Apply Classifier
        # 添加二次分类，默认不使用
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        # 对每一张图片作处理
        for i, det in enumerate(pred):  # detections per image
            # 如果输入源是webcam，则batch_size不为1，取出dataset中的一张图片
            if webcam:  # batch_size >= 1
                p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
            else:
                p, s, im0 = path, '', im0s

            # 设置保存图片/视频的路径
            save_path = str(Path(out) / Path(p).name)
            # 设置保存框坐标txt文件的路径
            txt_path = str(Path(out) / Path(p).stem) + ('_%g' % dataset.frame if dataset.mode == 'video' else '')
            # 设置打印信息（图片长宽）
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh

            if det is not None and len(det):
                # Rescale boxes from img_size to im0 size
                # 调整预测框的坐标：基于resize+pad的图片的坐标-->基于原size图片的坐标
                # 此时坐标格式为xyxy
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                # 打印检测到的类别数量
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += '%g %ss, ' % (n, names[int(c)])  # add to string

                # Write results


                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        # 将xyxy(左上角+右下角)格式转为xywh(中心点+宽长)格式，并除上w，h做归一化，转化为列表再保存
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, conf, *xywh) if opt.save_conf else (cls, *xywh)  # label format
                        with open(txt_path + '.txt', 'a') as f:
                            # 在原图上画框
                            f.write(('%g ' * len(line) + '\n') % line)

                    if save_img or view_img:  # Add bbox to image
                        label = '%s %.2f' % (names[int(cls)], conf)
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=3)

                    # 输出 json 文件
                    if save_json:
                        # windows下使用
                        file_name = save_path.split('\\')
                        # Linux下使用
                        # file_name = save_path.split('/')

                        #信息字符串的处理部分
                        #1 四个点的坐标获取 此处为一个list
                        bbox = torch.tensor(xyxy).view(1, 4).view(-1).tolist()
                        # 2使用append方法并使得每一个bbox-list满足消息格式json-list
                        bbox.append(names[int(cls)])
                        #赋予新的变量，此时bbox的list已经满足的所需格式

                        list_json = bbox
                        #调试输出已经处理好的list-json消息
                        print(list_json)

                        #合成为每一个图片的json-list文件
                        content_json.append(list_json)

                        #原始的json生成文件
                        # content_dic = {
                        #     "name": file_name[len(file_name)-1],
                        #     "category": (names[int(cls)]),
                        #     "bbox": torch.tensor(xyxy).view(1, 4).view(-1).tolist(),
                        #     "score": conf.tolist()
                        # }
                        # content_json.append(content_dic)
#修改版本的save
                if save_txt or save_img or save_json:
                    print('Results saved to %s' % Path(out))
                    #从当前的文件名中获取对应的json文件名
                    temp_json_name = current_file_name.split(".")
                    current_json_name = temp_json_name[0] + ".json"
                    # print(current_json_name)

                    # 将 json 数据写入文件
                    json_file_name = current_json_name
                    json_number = json_number + 1

                    #测试json 文件名
                    # print(json_file_name)

                    with open(os.path.join(Path(out), json_file_name), 'w') as f:
                        json.dump(content_json, f)
                    #写完一个图片的json文件之后，把content_json 全局的json文件置空
                    content_json = []

                    #测试json文件名的序号
                    #print(json_number)

            # Print time (inference + NMS)
            # 打印前向传播时间
            print('%sDone. (%.3fs)' % (s, t2 - t1))




            # Stream results
            # 如果设置展示，则show图片/视频
            if view_img:
                cv2.imshow(p, im0)
                if cv2.waitKey(1) == ord('q'):  # q to quit
                    raise StopIteration
#原始版本的save
            # Save results (image with detections)
            # 设置保存图片/视频
            # if save_img:
            #     if dataset.mode == 'images':
            #         cv2.imwrite(save_path, im0)
            #     else:
            #         if vid_path != save_path:  # new video
            #             vid_path = save_path
            #             if isinstance(vid_writer, cv2.VideoWriter):
            #                 vid_writer.release()  # release previous video writer
            #
            #             fourcc = 'mp4v'  # output video codec
            #             fps = vid_cap.get(cv2.CAP_PROP_FPS)
            #             w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            #             h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            #             vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*fourcc), fps, (w, h))
            #         vid_writer.write(im0)

    # if save_txt or save_img or save_json:
    #     print('Results saved to %s' % Path(out))
    #     # 将 json 数据写入文件
    #     with open(os.path.join(Path(out), 'result.json'), 'w') as f:
    #         json.dump(content_json, f)

    # 打印总时间
    print('ALL-TIME-DONE. (%.3fs)' % (time.time() - t0))

def main():
    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect()
                # 去除pt文件中的优化器等信息
                strip_optimizer(opt.weights)
        else:
            detect()


if __name__ == '__main__':
    """
    weights:训练的权重
    source:测试数据，可以是图片/视频路径，也可以是'0'(电脑自带摄像头),也可以是rtsp等视频流
    output:网络预测之后的图片/视频的保存路径
    img-size:网络输入图片大小
    conf-thres:置信度阈值
    iou-thres:做nms的iou阈值
    device:设置设备
    view-img:是否展示预测之后的图片/视频，默认False
    save-txt:是否将预测的框坐标以txt文件形式保存，默认False
    classes:设置只保留某一部分类别，形如0或者0 2 3
    agnostic-nms:进行nms是否也去除不同类别之间的框，默认False
    augment:推理的时候进行多尺度，翻转等操作(TTA)推理
    update:如果为True，则对所有模型进行strip_optimizer操作，去除pt文件中的优化器等信息，默认为False
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='best.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='../tile/testA_imgs', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=1600, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.1, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-dir', type=str, default='detect_img/output', help='directory to save results')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')

    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    opt = parser.parse_args()
    print(opt)

    main()