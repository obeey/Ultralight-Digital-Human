import os
import cv2
import torch
import random
import numpy as np
import random

from torch.utils.data import Dataset
from torch.utils.data import DataLoader

class MyDataset(Dataset):
    
    def __init__(self, img_dir, mode):
    
        self.img_path_list = []
        self.lms_path_list = []
        self.mode = mode  # wenet or hubert
        
        for i in range(len(os.listdir(img_dir+"/full_body_img/"))):

            img_path = os.path.join(img_dir+"/full_body_img/", str(i)+".jpg")
            lms_path = os.path.join(img_dir+"/landmarks/", str(i)+".lms")
            self.img_path_list.append(img_path)
            self.lms_path_list.append(lms_path)
        
        if self.mode == "wenet":
            self.audio_feats = np.load(img_dir+"/aud_wenet.npy")
        if self.mode == "hubert":
            self.audio_feats = np.load(img_dir+"/aud_hu.npy")
            
        self.audio_feats = self.audio_feats.astype(np.float32)
        
    def __len__(self):
        return self.audio_feats.shape[0] if self.audio_feats.shape[0]<len(self.img_path_list) else len(self.img_path_list)
    
    def get_audio_features(self, features, index):  # 在当前音频帧前后各取4帧音频特征
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
    
    
    def process_img(self, img, lms_path, img_ex, lms_path_ex):
        if img is None:
            raise ValueError(f"Image is None for landmarks file: {lms_path}")
            
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
            raise ValueError(f"Insufficient landmarks in {lms_path}: got {len(lms_list)}, expected at least 10")
            
        lms = np.array(lms_list, dtype=np.int32)  # 关键点坐标
        
        # Use available landmarks to define face region
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
            raise ValueError(f"Invalid crop dimensions: width={width}, height={height}")
        
        crop_img = img[ymin:ymax, xmin:xmax] # 将人脸下半部分区域裁切出来
        
        # Check if crop_img is valid
        if crop_img.size == 0 or crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
            raise ValueError(f"Empty crop image from coordinates: xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}")
            
        crop_img = cv2.resize(crop_img, (168, 168), cv2.INTER_AREA) 
        # resize后保留边缘的4个像素，如果视频分辨率比较大的话 建议把resize值和这个值都改大 但宽高必须能被16整除，同时模型结构也要改
        img_real = crop_img[4:164, 4:164].copy() # 保留边缘的4个像素防止贴回去的时候比较违和
        img_real_ori = img_real.copy()
        img_masked = cv2.rectangle(img_real,(5,5,150,145),(0,0,0),-1) # 将图片中间区域涂黑
        
        # 取一张随机图像作为参考和要做推理的图像一起输入 ⬇️⬇️⬇️
        if img_ex is None:
            raise ValueError(f"Reference image is None for landmarks file: {lms_path_ex}")
            
        img_ex_h, img_ex_w = img_ex.shape[:2]
        
        lms_list = []
        with open(lms_path_ex, "r") as f:
            lines = f.read().splitlines()
            for line in lines:
                arr = line.split(" ")
                if len(arr) != 2:
                    continue
                arr = np.array(arr, dtype=np.float32)
                lms_list.append(arr)
        
        if len(lms_list) < 10:
            raise ValueError(f"Insufficient landmarks in {lms_path_ex}: got {len(lms_list)}, expected at least 10")
            
        lms = np.array(lms_list, dtype=np.int32)
        
        # Use available landmarks to define face region for reference image
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
        xmax = min(img_ex_w, xmax)
        ymax = min(img_ex_h, ymax)
        
        # Validate crop coordinates
        width = xmax - xmin
        height = ymax - ymin
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid crop dimensions for reference image: width={width}, height={height}")
        
        crop_img = img_ex[ymin:ymax, xmin:xmax]
        
        # Check if crop_img is valid
        if crop_img.size == 0 or crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
            raise ValueError(f"Empty crop image for reference from coordinates: xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}")
            
        crop_img = cv2.resize(crop_img, (168, 168), cv2.INTER_AREA) 
        img_real_ex = crop_img[4:164, 4:164].copy()
        
        img_real_ori = img_real_ori.transpose(2,0,1).astype(np.float32)
        img_masked = img_masked.transpose(2,0,1).astype(np.float32)
        img_real_ex = img_real_ex.transpose(2,0,1).astype(np.float32)
        
        img_real_ex_T = torch.from_numpy(img_real_ex / 255.0)
        img_real_T = torch.from_numpy(img_real_ori / 255.0)
        img_masked_T = torch.from_numpy(img_masked / 255.0)
        img_concat_T = torch.cat([img_real_ex_T, img_masked_T], axis=0)

        return img_concat_T, img_real_T

    def __getitem__(self, idx):
        max_retries = 10
        for retry in range(max_retries):
            try:
                current_idx = (idx + retry) % self.__len__()
                img = cv2.imread(self.img_path_list[current_idx])
                lms_path = self.lms_path_list[current_idx]
                
                ex_int = random.randint(0, self.__len__()-1)
                img_ex = cv2.imread(self.img_path_list[ex_int])
                lms_path_ex = self.lms_path_list[ex_int]
                
                img_concat_T, img_real_T = self.process_img(img, lms_path, img_ex, lms_path_ex) ## 图像处理
                audio_feat = self.get_audio_features(self.audio_feats, current_idx)  ## 音频特征处理
                
                if self.mode == "wenet":
                    audio_feat = audio_feat.reshape(128,16,32)
                if self.mode == "hubert":
                    audio_feat = audio_feat.reshape(16,32,32)  ## 修复为正确的维度，匹配UNet期望的16通道输入
                
                return img_concat_T, img_real_T, audio_feat
            except Exception as e:
                print(f"Warning: Failed to process sample {current_idx}: {str(e)}")
                if retry == max_retries - 1:
                    # If all retries failed, return a dummy sample
                    print(f"All retries failed for idx {idx}, returning dummy sample")
                    dummy_img_concat = torch.zeros(6, 160, 160).float()  # 6 channels (3+3)
                    dummy_img_real = torch.zeros(3, 160, 160).float()
                    if self.mode == "wenet":
                        dummy_audio = torch.zeros(128, 16, 32).float()
                    else:
                        dummy_audio = torch.zeros(32, 32, 32).float()
                    return dummy_img_concat, dummy_img_real, dummy_audio
                continue
    
        