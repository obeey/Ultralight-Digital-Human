import argparse
import os
import cv2
import torch
import numpy as np
import torch.nn as nn
from torch import optim
from tqdm import tqdm
from torch.utils.data import DataLoader
from unet import Model
# from unet2 import Model
# from unet_att import Model

import time
parser = argparse.ArgumentParser(description='Train',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--asr', type=str, default="hubert")
parser.add_argument('--dataset', type=str, default="")  
parser.add_argument('--audio_feat', type=str, default="")
parser.add_argument('--save_path', type=str, default="")     # end with .mp4 please
parser.add_argument('--checkpoint', type=str, default="")
args = parser.parse_args()

checkpoint = args.checkpoint
save_path = args.save_path
dataset_dir = args.dataset
audio_feat_path = args.audio_feat
mode = args.asr

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def get_audio_features(features, index): # 这个逻辑跟datasets里面的逻辑相同
    left = index - 4
    right = index + 4
    pad_left = 0
    pad_right = 0
    if left < 0:
        pad_left = -left
        left = 0
    if right > features.shape[0]:
        pad_right = right - features.shape[0]
        right = features.shape[0]
    auds = torch.from_numpy(features[left:right])
    if pad_left > 0:
        auds = torch.cat([torch.zeros_like(auds[:pad_left]), auds], dim=0)
    if pad_right > 0:
        auds = torch.cat([auds, torch.zeros_like(auds[:pad_right])], dim=0) # [8, 16]
    return auds

audio_feats = np.load(audio_feat_path)
img_dir = os.path.join(dataset_dir, "full_body_img/")
lms_dir = os.path.join(dataset_dir, "landmarks/")
len_img = len(os.listdir(img_dir)) - 1
exm_img = cv2.imread(img_dir+"0.jpg")
h, w = exm_img.shape[:2]

if mode=="hubert":
    video_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc('M','J','P', 'G'), 25, (w, h))
if mode=="wenet":
    video_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc('M','J','P', 'G'), 20, (w, h))
step_stride = 0
img_idx = 0

net = Model(6, mode).to(device)
net.load_state_dict(torch.load(checkpoint, map_location=device))
net.eval()
for i in range(audio_feats.shape[0]):
    if img_idx>len_img - 1:
        step_stride = -1  # step_stride 决定取图片的间隔，目前这个逻辑是从头开始一张一张往后，到最后一张后再一张一张往前
    if img_idx<1:
        step_stride = 1
    img_idx += step_stride
    img_path = img_dir + str(img_idx)+'.jpg'
    lms_path = lms_dir + str(img_idx)+'.lms'
    
    img = cv2.imread(img_path)
    img_h, img_w = img.shape[:2]
    
    lms_list = []
    with open(lms_path, "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            arr = line.split(" ")
            if len(arr) != 2:
                continue
            arr = np.array(arr, dtype=np.float32)
            lms_list.append(arr)
    
    if len(lms_list) < 10:
        print(f"Warning: Insufficient landmarks in {lms_path}: got {len(lms_list)}, skipping frame")
        continue
        
    lms = np.array(lms_list, dtype=np.int32)
    
    # 使用与训练时相同的裁剪逻辑
    all_x = lms[:, 0]
    all_y = lms[:, 1]
    
    xmin = np.min(all_x)
    xmax = np.max(all_x)
    ymin = np.min(all_y)
    ymax = np.max(all_y)
    
    # Add some padding and make it square
    width = xmax - xmin
    height = ymax - ymin
    size = max(width, height)
    
    # Center the crop
    center_x = (xmin + xmax) // 2
    center_y = (ymin + ymax) // 2
    
    # Add 20% padding
    size = int(size * 1.2)
    
    xmin = center_x - size // 2
    ymin = center_y - size // 2
    xmax = xmin + size
    ymax = ymin + size
    
    # Ensure crop coordinates are within image bounds
    xmin = max(0, xmin)
    ymin = max(0, ymin)
    xmax = min(img_w, xmax)
    ymax = min(img_h, ymax)
    
    # Validate crop coordinates
    width = xmax - xmin
    height = ymax - ymin
    if width <= 0 or height <= 0:
        print(f"Warning: Invalid crop dimensions for frame {i}: width={width}, height={height}, skipping")
        continue
    
    crop_img = img[ymin:ymax, xmin:xmax]
    
    # Check if crop_img is valid
    if crop_img.size == 0 or crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
        print(f"Warning: Empty crop image for frame {i}, skipping")
        continue
    h, w = crop_img.shape[:2]
    crop_img = cv2.resize(crop_img, (168, 168), cv2.INTER_AREA)
    crop_img_ori = crop_img.copy()
    img_real_ex = crop_img[4:164, 4:164].copy()
    img_real_ex_ori = img_real_ex.copy()
    img_masked = cv2.rectangle(img_real_ex_ori,(5,5,150,145),(0,0,0),-1)
    
    img_masked = img_masked.transpose(2,0,1).astype(np.float32)
    img_real_ex = img_real_ex.transpose(2,0,1).astype(np.float32)
    
    img_real_ex_T = torch.from_numpy(img_real_ex / 255.0).to(device)
    img_masked_T = torch.from_numpy(img_masked / 255.0).to(device)  
    img_concat_T = torch.cat([img_real_ex_T, img_masked_T], axis=0)[None]
    # 这个地方逻辑和dataset里面完全一样，只是不需要另外取一张参考图 而是用要推理的这张图片即可
    
    audio_feat = get_audio_features(audio_feats, i)
    if mode=="hubert":
        audio_feat = audio_feat.reshape(16,32,32)
    if mode=="wenet":
        audio_feat = audio_feat.reshape(128,16,32)
    audio_feat = audio_feat[None]
    audio_feat = audio_feat.to(device)
    img_concat_T = img_concat_T.to(device)
    
    with torch.no_grad():
        pred = net(img_concat_T, audio_feat)[0]
        
    pred = pred.cpu().numpy().transpose(1,2,0)*255
    pred = np.array(pred, dtype=np.uint8)
    crop_img_ori[4:164, 4:164] = pred
    crop_img_ori = cv2.resize(crop_img_ori, (w, h))
    img[ymin:ymax, xmin:xmax] = crop_img_ori
    video_writer.write(img)
video_writer.release()

# ffmpeg -i test_video.mp4 -i test_audio.pcm -c:v libx264 -c:a aac result_test.mp4