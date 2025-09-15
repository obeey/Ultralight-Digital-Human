#!/usr/bin/env python3
"""
数字人生成器模块
"""

import os
import sys
import time
import logging
import subprocess
import threading
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List

# 导入配置和客户端
try:
    from .dh_config import DigitalHumanConfig
    from .dh_clients import ActionManager
except ImportError:
    # 如果模块未找到，定义简单的类以避免错误
    from dataclasses import dataclass
    @dataclass
    class DigitalHumanConfig:
        tts_url: str = "http://127.0.0.1:9880/tts"
        reference_audio: str = ""
        reference_text: str = ""
        checkpoint_path: str = "checkpoint/195.pth"
        dataset_path: str = "input/mxbc_0913/"
        output_dir: str = "output"
        temp_dir: str = "temp"
    
    class ActionManager:
        def analyze_text_action(self, text: str) -> str:
            return "greeting"
        def get_action_range(self, action_type: str) -> Tuple[int, int]:
            return (0, 100)

import requests

logger = logging.getLogger(__name__)

class DigitalHumanGenerator:
    """数字人生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.action_manager = ActionManager()
        
        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.temp_dir, exist_ok=True)
        
        # 线程安全的计数器
        self.counter_lock = threading.Lock()
        self.video_counter = 0
        self.completed_videos = []
    
    def generate_paragraph_audio(self, text: str, base_name: str) -> Optional[str]:
        """生成段落音频"""
        audio_path = f"{self.config.temp_dir}/{base_name}.wav"
        
        try:
            # 使用TTS API生成音频，让TTS自己处理文本分割
            data = {
                "text": text,
                "text_lang": "zh",
                "ref_audio_path": self.config.reference_audio,
                "prompt_text": self.config.reference_text,
                "prompt_lang": "zh",
                "text_split_method": "cut5",  # 让TTS自己分割
                "batch_size": 1,
                "speed_factor": 1.0,
                "streaming_mode": False,
                "parallel_infer": True,
                "repetition_penalty": 1.35
            }
            
            response = requests.post(
                self.config.tts_url,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"段落TTS音频生成成功: {audio_path}")
                return audio_path
            else:
                logger.error(f"TTS请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"TTS生成失败: {e}")
            return None
    
    def generate_video(self, audio_path: str, text: str, base_name: str) -> Optional[str]:
        """生成数字人视频"""
        try:
            # 步骤1: 提取HuBERT特征
            logger.info("步骤1: 提取HuBERT特征...")
            hubert_output_path = f"{self.config.temp_dir}/{base_name}_hu.npy"
            
            cmd = ["python3", "data_utils/hubert.py", "--wav", audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.error(f"HuBERT特征提取失败: {result.stderr}")
                return None
            
            if not os.path.exists(hubert_output_path):
                logger.error(f"HuBERT特征文件未生成: {hubert_output_path}")
                return None
            
            logger.info(f"HuBERT特征提取成功: {hubert_output_path}")
            
            # 步骤2: 智能数字人推理
            logger.info("步骤2: 生成数字人视频...")
            video_path = f"{self.config.temp_dir}/{base_name}_video.mp4"
            
            # 分析文本选择动作
            action_type = self.action_manager.analyze_text_action(text)
            action_range = self.action_manager.get_action_range(action_type)
            
            # 创建智能推理脚本
            smart_script_path = self._create_smart_inference_script(
                hubert_output_path, video_path, action_range, base_name
            )
            
            # 运行智能推理
            cmd = ["python3", smart_script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode != 0:
                logger.error(f"智能数字人推理失败: {result.stderr}")
                return None
            
            if not os.path.exists(video_path):
                logger.error(f"数字人视频未生成: {video_path}")
                return None
            
            logger.info(f"数字人视频生成成功: {video_path}")
            
            # 步骤3: 合并视频和音频
            logger.info("步骤3: 合并视频和音频...")
            final_video_path = f"{self.config.output_dir}/paragraph_{base_name}.mp4"
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(final_video_path), exist_ok=True)
            
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "32000",
                "-ac", "1",
                "-shortest",
                final_video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"视频音频合并失败: {result.stderr}")
                return None
            
            # 验证最终文件
            if os.path.exists(final_video_path):
                file_size = os.path.getsize(final_video_path)
                logger.info(f"✅ 数字人段落视频生成完成: {final_video_path} (大小: {file_size} 字节)")
                
                # 清理中间文件
                self.cleanup_intermediate_files(audio_path, hubert_output_path, video_path, smart_script_path)
                logger.info(f"已清理中间文件，保留最终视频: {final_video_path}")
                
                return final_video_path
            else:
                logger.error("最终视频文件未生成")
                return None
                
        except Exception as e:
            logger.error(f"数字人视频生成失败: {e}")
            return None
    
    def _create_smart_inference_script(self, hubert_path: str, video_path: str, 
                                      action_range: Tuple[int, int], base_name: str) -> str:
        """创建智能推理脚本"""
        script_path = f"{self.config.temp_dir}/smart_inference_{base_name}.py"
        
        start_idx, end_idx = action_range
        action_range_size = end_idx - start_idx + 1
        
        script_content = f'''#!/usr/bin/env python3
"""
智能数字人推理脚本 - 动作范围: {start_idx}-{end_idx}
"""

import sys
import os
import numpy as np
import torch
import cv2

# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root.endswith('/{self.config.temp_dir}'):
    project_root = os.path.dirname(project_root)
sys.path.insert(0, project_root)
os.chdir(project_root)

from unet import Model

# 设备配置
device = 'cuda' if torch.cuda.is_available() else 'cpu'

def get_audio_features(features, index):
    """获取音频特征 - 与原始inference.py相同的逻辑"""
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
        auds = torch.cat([auds, torch.zeros_like(auds[:pad_right])], dim=0) # [8, 2, 1024]
    
    # 将HuBERT特征 [8, 2, 1024] 转换为模型期望的 [16, H, W] 格式
    if auds.shape == (8, 2, 1024):
        # 重复通道维度：[8, 2, 1024] -> [8, 16, 1024]
        auds = auds.repeat(1, 8, 1)  # 将2个通道重复8次得到16个通道
        # 重新排列维度：[8, 16, 1024] -> [16, 8, 1024]
        auds = auds.permute(1, 0, 2)
        # 计算正确的空间维度：总元素数 = 16 * 8 * 1024 = 131072
        # 目标形状 [16, H, W]，其中 H * W = 131072 / 16 = 8192
        # 选择合适的 H, W 使得 H * W = 8192，例如 H=64, W=128
        total_spatial = auds.numel() // 16  # 8192
        H = 64
        W = total_spatial // H  # 128
        auds = auds.reshape(16, H, W)
    
    return auds

# 加载模型 - 使用正确的加载方式
net = Model(6, "hubert").to(device)
net.load_state_dict(torch.load("{self.config.checkpoint_path}", map_location=device))
net.eval()

# 加载HuBERT特征
audio_feats = np.load("{hubert_path}")
print(f"加载HuBERT特征: {{audio_feats.shape}}")

# 数据集路径
dataset_dir = "{self.config.dataset_path}"
img_dir = os.path.join(dataset_dir, "full_body_img/")
lms_dir = os.path.join(dataset_dir, "landmarks/")

# 智能动作选择参数
action_start = {start_idx}
action_end = {end_idx}
action_range_size = {action_range_size}

print(f"使用动作范围: {{action_start}}-{{action_end}}")

# 获取示例图片尺寸
exm_img = cv2.imread(img_dir + "0.jpg")
h, w = exm_img.shape[:2]

# 创建视频写入器 - 使用mp4v编码器以避免MJPG兼容性问题
video_writer = cv2.VideoWriter("{video_path}", cv2.VideoWriter_fourcc('m','p','4', 'v'), 25, (w, h))

# 生成视频帧
for i in range(audio_feats.shape[0]):
    # 智能动作选择：在指定范围内循环
    if action_range_size > 1:
        cycle_pos = i % (action_range_size * 2 - 2) if action_range_size > 1 else 0
        if cycle_pos < action_range_size:
            img_idx = action_start + cycle_pos
        else:
            img_idx = action_start + (action_range_size * 2 - 2 - cycle_pos)
    else:
        img_idx = action_start
    
    # 确保索引在有效范围内
    img_idx = max(0, min(img_idx, 1177))  # 0-1177范围
    
    # 构建文件路径
    img_path = img_dir + str(img_idx) + '.jpg'
    lms_path = lms_dir + str(img_idx) + '.lms'
    
    # 加载图片和landmarks
    img = cv2.imread(img_path)
    img_h, img_w = img.shape[:2]
    
    # 读取landmarks
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
        print(f"Warning: Insufficient landmarks in {{lms_path}}: got {{len(lms_list)}}, skipping frame")
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
        print(f"Warning: Invalid crop dimensions for frame {{i}}: width={{width}}, height={{height}}, skipping")
        continue
    
    crop_img = img[ymin:ymax, xmin:xmax]
    
    # Check if crop_img is valid
    if crop_img.size == 0 or crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
        print(f"Warning: Empty crop image for frame {{i}}, skipping")
        continue
        
    h_crop, w_crop = crop_img.shape[:2]
    crop_img = cv2.resize(crop_img, (168, 168), cv2.INTER_AREA)
    crop_img_ori = crop_img.copy()
    img_real_ex = crop_img[4:164, 4:164].copy()
    img_real_ex_ori = img_real_ex.copy()
    img_masked = cv2.rectangle(img_real_ex_ori,(5,5),(150,145),(0,0,0),-1)
    
    img_masked = img_masked.transpose(2,0,1).astype(np.float32)
    img_real_ex = img_real_ex.transpose(2,0,1).astype(np.float32)
    
    img_real_ex_T = torch.from_numpy(img_real_ex / 255.0).to(device)
    img_masked_T = torch.from_numpy(img_masked / 255.0).to(device)
    
    # 合并真实图像和掩码图像以创建6通道输入
    combined_input = torch.cat([img_real_ex_T, img_masked_T], dim=0)
    
    # 获取音频特征
    auds = get_audio_features(audio_feats, i)
    auds = auds.to(device)
    
    # 推理 - 使用合并的6通道输入
    with torch.no_grad():
        pred = net(combined_input.unsqueeze(0), auds.unsqueeze(0))
        pred = pred.squeeze(0).cpu().numpy()
    
    # 后处理
    pred = (pred * 255).astype(np.uint8)
    pred = pred.transpose(1, 2, 0)
    
    # 将预测结果放回原始图像
    crop_img_ori[4:164, 4:164] = pred
    
    # 将裁剪的图像放回原始图像
    img_resized = cv2.resize(crop_img_ori, (width, height), cv2.INTER_CUBIC)
    img[ymin:ymax, xmin:xmax] = img_resized
    
    # 写入视频帧
    video_writer.write(img)
    
    if i % 50 == 0:
        print(f"处理进度: {{i}}/{{audio_feats.shape[0]}} 帧")

# 释放资源
video_writer.release()
print(f"视频生成完成: {video_path}")
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        
        return script_path
    
    def cleanup_intermediate_files(self, audio_path: str, hubert_path: str, 
                                  video_path: str, script_path: str):
        """清理中间文件"""
        try:
            for path in [audio_path, hubert_path, video_path, script_path]:
                if path and os.path.exists(path):
                    os.remove(path)
                    logger.debug(f"已删除中间文件: {path}")
        except Exception as e:
            logger.warning(f"清理中间文件失败: {e}")
    
    def generate_unique_id(self, text: str) -> str:
        """生成唯一ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        with self.counter_lock:
            self.video_counter += 1
            counter = self.video_counter
        return f"{timestamp}_{text_hash}_{counter:03d}"