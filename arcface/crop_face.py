import sys
import time
import argparse
import os

import cv2

import ailia

# import original modules
sys.path.append('../util')
from utils import check_file_existance  # noqa: E402
from model_utils import check_and_download_models  # noqa: E402
from webcamera_utils import adjust_frame_size  # noqa: E402C
#from detector_utils import plot_results, load_image  # noqa: E402C
from image_utils import load_image  # noqa: E402

sys.path.append('../blazeface')
from blazeface_utils import *

# ======================
# Parameters
# ======================
WEIGHT_PATH = 'yolov3-face.opt.onnx'
MODEL_PATH = 'yolov3-face.opt.onnx.prototxt'
FACE_CATEGORY = ['face']

WEIGHT_PATH = 'ax_masked_face.opt.onnx'
MODEL_PATH = 'ax_masked_face.opt.onnx.prototxt'
FACE_CATEGORY = ['masked','half','no_mask']

REMOTE_PATH = 'https://storage.googleapis.com/ailia-models/yolov3-face/'

THRESHOLD = 0.1
IOU = 0.45

WEIGHT_PATH = 'blazeface.onnx'
MODEL_PATH = 'blazeface.onnx.prototxt'
REMOTE_PATH = "https://storage.googleapis.com/ailia-models/blazeface/"

# ======================
# Arguemnt Parser Config
# ======================
parser = argparse.ArgumentParser(
    description='Yolov3 face detection model'
)
args = parser.parse_args()


# ======================
# Main functions
# ======================

def recognize_from_image_blazeface(detector,dst_path,src_dir,file_):
    IMAGE_HEIGHT = 128
    IMAGE_WIDTH = 128

    # prepare input data
    img = cv2.imread(src_dir+"/"+file_)

    input_data = load_image(
        src_dir+"/"+file_,
        (IMAGE_HEIGHT, IMAGE_WIDTH),
        normalize_type='127.5',
        gen_input_ailia=True
    )

    # inference
    preds_ailia = detector.predict([input_data])

    # postprocessing
    detections = postprocess(preds_ailia)

    # generate detections
    h, w = img.shape[0], img.shape[1]
    count = len(detections)
    texts = []
    written = False
    for idx in range(count):
        # get detected face
        obj = detections[idx]
        d = obj[0]

        obj_w=d[3]-d[1]
        obj_h=d[2]-d[0]
        obj_x=d[1]
        obj_y=d[0]

        cx = (obj_x + obj_w/2) * w
        cy = (obj_y + obj_h/2) * h
        margin = 1.4
        cw = max(obj_w * w * margin,obj_h * h * margin)
        fx = max(cx - cw/2, 0)
        fy = max(cy - cw/2, 0)
        fw = min(cw, w-fx)
        fh = min(cw, h-fy)
        top_left = (int(fx), int(fy))
        bottom_right = (int((fx+fw)), int(fy+fh))

        print(top_left)
        print(bottom_right)

        # get detected face
        crop_img = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], 0:3]
        if crop_img.shape[0]<=0 or crop_img.shape[1]<=0:
            continue
        cv2.imwrite(dst_path, crop_img)
        written = True
    
    if not written:
        print("face not found")



def recognize_from_image(detector,dst_path,src_dir,file_):
    # prepare input data
    img = load_image(src_dir+"/"+file_)

    # inference
    detector.compute(img, THRESHOLD, IOU)
    
    h, w = img.shape[0], img.shape[1]
    count = detector.get_object_count()
    texts = []
    written = False
    for idx in range(count):
        # get detected face
        obj = detector.get_object(idx)
        cx = (obj.x + obj.w/2) * w
        cy = (obj.y + obj.h/2) * h
        margin = 1.0
        cw = max(obj.w * w * margin,obj.h * h * margin)
        fx = max(cx - cw/2, 0)
        fy = max(cy - cw/2, 0)
        fw = min(cw, w-fx)
        fh = min(cw, h-fy)
        top_left = (int(fx), int(fy))
        bottom_right = (int((fx+fw)), int(fy+fh))

        # get detected face
        crop_img = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0], 0:3]
        if crop_img.shape[0]<=0 or crop_img.shape[1]<=0:
            continue
        cv2.imwrite(dst_path, crop_img)
        written = True
    
    if not written:
        print("face not found")

def main():
    # model files check and download
    check_and_download_models(WEIGHT_PATH, MODEL_PATH, REMOTE_PATH)

    root_src_dir="./dataset/no_crop/"
    if not os.path.exists(root_src_dir):
        print("error : directory not found "+root_src_dir)
        sys.exit(1)
        
    no = 0

    # net initialize
    env_id = ailia.get_gpu_environment_id()
    print(f'env_id: {env_id}')
    if WEIGHT_PATH == 'blazeface.onnx':
        detector = ailia.Net(MODEL_PATH, WEIGHT_PATH, env_id=env_id)
    else:
        detector = ailia.Detector(
            MODEL_PATH,
            WEIGHT_PATH,
            len(FACE_CATEGORY),
            format=ailia.NETWORK_IMAGE_FORMAT_RGB,
            channel=ailia.NETWORK_IMAGE_CHANNEL_FIRST,
            range=ailia.NETWORK_IMAGE_RANGE_U_FP32,
            algorithm=ailia.DETECTOR_ALGORITHM_YOLOV3,
            env_id=env_id
        )

    for src_dir, dirs, files in os.walk(root_src_dir):
        files = sorted(files)
        for file_ in files:
            root, ext = os.path.splitext(file_)

            if file_==".DS_Store":
                continue
            if file_=="Thumbs.db":
                continue
            if not(ext == ".jpg" or ext == ".png" or ext == ".bmp"):
                continue

            print(src_dir+"/"+file_)
            folders=src_dir.split("/")
            folder=folders[len(folders)-1]
            dst_dir = "./dataset/crop/"+folder
            if not os.path.exists(dst_dir):
                os.mkdir(dst_dir)
            dst_path= dst_dir+ "/"+str(no)+".jpg"
            if WEIGHT_PATH == 'blazeface.onnx':
                recognize_from_image_blazeface(detector,dst_path,src_dir,file_)
            else:
                recognize_from_image(detector,dst_path,src_dir,file_)
            no=no+1

if __name__ == '__main__':
    main()