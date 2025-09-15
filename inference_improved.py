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
import time
import signal
import logging
from contextlib import contextmanager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description='Train',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--asr', type=str, default="hubert")
parser.add_argument('--dataset', type=str, default="")  
parser.add_argument('--audio_feat', type=str, default="")
parser.add_argument('--save_path', type=str, default="")     # end with .mp4 please
parser.add_argument('--checkpoint', type=str, default="")
parser.add_argument('--timeout', type=int, default=300)      # 添加超时参数，默认5分钟
parser.add_argument('--max_frames', type=int, default=None)  # 添加最大帧数限制
args = parser.parse_args()

checkpoint = args.checkpoint
save_path = args.save_path
dataset_dir = args.dataset
audio_feat_path = args.audio_feat
mode = args.asr
timeout_seconds = args.timeout
max_frames = args.max_frames

device = 'cuda' if torch.cuda.is_available() else 'cpu'

class TimeoutError(Exception):
    pass

@contextmanager
def timeout_context(seconds):
    """超时上下文管理器"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"操作超时 ({seconds} 秒)")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def get_audio_features(features, index):
    """获取音频特征，与datasets里面的逻辑相同"""
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

def cleanup_gpu_memory():
    """清理GPU内存"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def main():
    video_writer = None
    try:
        logger.info(f"开始推理，超时设置: {timeout_seconds}秒")
        
        # 加载音频特征
        logger.info("加载音频特征...")
        audio_feats = np.load(audio_feat_path)
        logger.info(f"音频特征形状: {audio_feats.shape}")
        
        # 设置路径和参数
        img_dir = os.path.join(dataset_dir, "full_body_img/")
        lms_dir = os.path.join(dataset_dir, "landmarks/")
        len_img = len(os.listdir(img_dir)) - 1
        exm_img = cv2.imread(img_dir+"0.jpg")
        
        if exm_img is None:
            raise ValueError(f"无法读取示例图片: {img_dir}0.jpg")
            
        h, w = exm_img.shape[:2]
        logger.info(f"图片尺寸: {w}x{h}")

        # 创建视频写入器
        if mode=="hubert":
            video_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc('M','J','P','G'), 25, (w, h))
        elif mode=="wenet":
            video_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc('M','J','P','G'), 20, (w, h))
        else:
            raise ValueError(f"不支持的模式: {mode}")
            
        if not video_writer.isOpened():
            raise ValueError(f"无法创建视频写入器: {save_path}")

        # 加载模型
        logger.info("加载模型...")
        net = Model(6, mode).to(device)
        net.load_state_dict(torch.load(checkpoint, map_location=device))
        net.eval()
        logger.info("模型加载完成")

        step_stride = 0
        img_idx = 0
        processed_frames = 0
        skipped_frames = 0
        
        # 确定处理的帧数
        total_frames = audio_feats.shape[0]
        if max_frames is not None:
            total_frames = min(total_frames, max_frames)
        
        logger.info(f"开始处理 {total_frames} 帧")
        start_time = time.time()
        
        # 使用超时上下文
        with timeout_context(timeout_seconds):
            for i in tqdm(range(total_frames), desc="处理帧"):
                try:
                    # 更新图片索引
                    if img_idx > len_img - 1:
                        step_stride = -1
                    if img_idx < 1:
                        step_stride = 1
                    img_idx += step_stride
                    
                    img_path = img_dir + str(img_idx) + '.jpg'
                    lms_path = lms_dir + str(img_idx) + '.lms'
                    
                    # 检查文件是否存在
                    if not os.path.exists(img_path):
                        logger.warning(f"图片文件不存在: {img_path}")
                        skipped_frames += 1
                        continue
                        
                    if not os.path.exists(lms_path):
                        logger.warning(f"landmarks文件不存在: {lms_path}")
                        skipped_frames += 1
                        continue
                    
                    # 读取图片
                    img = cv2.imread(img_path)
                    if img is None:
                        logger.warning(f"无法读取图片: {img_path}")
                        skipped_frames += 1
                        continue
                        
                    img_h, img_w = img.shape[:2]
                    
                    # 读取landmarks
                    lms_list = []
                    with open(lms_path, "r") as f:
                        lines = f.read().splitlines()
                        for line in lines:
                            arr = line.split(" ")
                            if len(arr) != 2:
                                continue
                            try:
                                arr = np.array(arr, dtype=np.float32)
                                lms_list.append(arr)
                            except ValueError:
                                continue
                    
                    if len(lms_list) < 10:
                        logger.warning(f"landmarks数量不足: {lms_path}, 数量: {len(lms_list)}")
                        skipped_frames += 1
                        continue
                        
                    lms = np.array(lms_list, dtype=np.int32)
                    
                    # 裁剪逻辑
                    all_x = lms[:, 0]
                    all_y = lms[:, 1]
                    
                    xmin = np.min(all_x)
                    xmax = np.max(all_x)
                    ymin = np.min(all_y)
                    ymax = np.max(all_y)
                    
                    width = xmax - xmin
                    height = ymax - ymin
                    size = max(width, height)
                    
                    center_x = (xmin + xmax) // 2
                    center_y = (ymin + ymax) // 2
                    
                    size = int(size * 1.2)
                    
                    xmin = center_x - size // 2
                    ymin = center_y - size // 2
                    xmax = xmin + size
                    ymax = ymin + size
                    
                    xmin = max(0, xmin)
                    ymin = max(0, ymin)
                    xmax = min(img_w, xmax)
                    ymax = min(img_h, ymax)
                    
                    width = xmax - xmin
                    height = ymax - ymin
                    if width <= 0 or height <= 0:
                        logger.warning(f"无效的裁剪尺寸: width={width}, height={height}")
                        skipped_frames += 1
                        continue
                    
                    crop_img = img[ymin:ymax, xmin:xmax]
                    
                    if crop_img.size == 0 or crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
                        logger.warning(f"空的裁剪图片，帧 {i}")
                        skipped_frames += 1
                        continue
                        
                    h_crop, w_crop = crop_img.shape[:2]
                    crop_img = cv2.resize(crop_img, (168, 168), cv2.INTER_AREA)
                    crop_img_ori = crop_img.copy()
                    img_real_ex = crop_img[4:164, 4:164].copy()
                    img_real_ex_ori = img_real_ex.copy()
                    img_masked = cv2.rectangle(img_real_ex_ori, (5,5,150,145), (0,0,0), -1)
                    
                    img_masked = img_masked.transpose(2,0,1).astype(np.float32)
                    img_real_ex = img_real_ex.transpose(2,0,1).astype(np.float32)
                    
                    img_real_ex_T = torch.from_numpy(img_real_ex / 255.0).to(device)
                    img_masked_T = torch.from_numpy(img_masked / 255.0).to(device)  
                    img_concat_T = torch.cat([img_real_ex_T, img_masked_T], axis=0)[None]
                    
                    # 获取音频特征
                    audio_feat = get_audio_features(audio_feats, i)
                    if mode=="hubert":
                        audio_feat = audio_feat.reshape(16,32,32)
                    elif mode=="wenet":
                        audio_feat = audio_feat.reshape(128,16,32)
                    audio_feat = audio_feat[None].to(device)
                    
                    # 推理
                    with torch.no_grad():
                        pred = net(img_concat_T, audio_feat)[0]
                        
                    pred = pred.cpu().numpy().transpose(1,2,0)*255
                    pred = np.array(pred, dtype=np.uint8)
                    crop_img_ori[4:164, 4:164] = pred
                    crop_img_ori = cv2.resize(crop_img_ori, (w_crop, h_crop))
                    img[ymin:ymax, xmin:xmax] = crop_img_ori
                    
                    # 写入视频
                    video_writer.write(img)
                    processed_frames += 1
                    
                    # 定期清理GPU内存
                    if i % 100 == 0:
                        cleanup_gpu_memory()
                        
                except Exception as e:
                    logger.error(f"处理帧 {i} 时出错: {str(e)}")
                    skipped_frames += 1
                    continue
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"处理完成!")
        logger.info(f"总处理时间: {processing_time:.2f}秒")
        logger.info(f"成功处理帧数: {processed_frames}")
        logger.info(f"跳过帧数: {skipped_frames}")
        logger.info(f"平均每帧处理时间: {processing_time/max(processed_frames, 1):.3f}秒")
        
    except TimeoutError as e:
        logger.error(f"推流超时: {str(e)}")
        logger.info(f"已处理帧数: {processed_frames}")
        return 1
    except Exception as e:
        logger.error(f"推理过程中出现错误: {str(e)}")
        return 1
    finally:
        # 确保资源被正确释放
        if video_writer is not None:
            video_writer.release()
            logger.info("视频写入器已释放")
        cleanup_gpu_memory()
        logger.info("GPU内存已清理")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)