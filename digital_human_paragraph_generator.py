#!/usr/bin/env python3
"""
数字人段落生成系统 - 按段落连续生成
直接使用DeepSeek返回的完整段落，让TTS自己处理分割
"""

import os
import sys
import time
import json
import threading
import queue
import subprocess
import requests
import logging
import random
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S%f'
)
logger = logging.getLogger(__name__)

@dataclass
class DigitalHumanConfig:
    """数字人系统配置"""
    # TTS配置
    tts_url: str = "http://127.0.0.1:9880/tts"
    reference_audio: str = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    reference_text: str = "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后"
    
    # 推理配置
    checkpoint_path: str = "checkpoint/195.pth"
    dataset_path: str = "input/mxbc_0913/"
    
    # DeepSeek配置
    product_info: str = "蜜雪冰城优惠券"
    auto_start: bool = True
    
    # 段落生成配置
    paragraph_length: int = 200  # 每段话术长度（字符数）
    paragraph_interval: float = 60.0  # 段落生成间隔（秒）
    
    # 并行配置
    parallel_workers: int = 2
    text_queue_size: int = 50
    video_queue_size: int = 10
    
    @classmethod
    def from_config_file(cls, config_path: str = "config.json"):
        """从配置文件加载"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = f.read()
                if not config_data.strip():
                    logger.warning(f"配置文件 {config_path} 为空，使用默认配置")
                    return cls()
                
                config_dict = json.loads(config_data)
                # 忽略 deepseek_api_key，从环境变量读取
                config_dict.pop('deepseek_api_key', None)
                return cls(**config_dict)
        except FileNotFoundError:
            logger.warning(f"配置文件 {config_path} 不存在，使用默认配置")
            return cls()
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 {config_path} 格式错误: {e}，使用默认配置")
            return cls()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls()

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.error("未设置环境变量 DEEPSEEK_API_KEY，将使用备用话术")
        
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
    
    def generate_paragraph_script(self, product_info: str, paragraph_length: int = 200) -> str:
        """生成段落话术"""
        if not self.api_key:
            return self._get_fallback_paragraph(product_info)
        
        try:
            prompt = f"""
请为"{product_info}"生成一段直播带货话术，要求：
1. 长度约{paragraph_length}字符
2. 内容连贯，语言生动
3. 包含产品介绍、优惠信息、购买引导
4. 语气亲切自然，适合直播场景
5. 不要使用标点符号分段，让语音更连贯
6. 直接返回话术内容，不要其他说明

产品信息：{product_info}
"""
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                # 清理可能的引号和多余空格
                content = content.replace('"', '').replace("'", '').strip()
                logger.info(f"DeepSeek生成段落话术成功，长度: {len(content)}字符")
                return content
            else:
                logger.error(f"DeepSeek API请求失败: {response.status_code}")
                return self._get_fallback_paragraph(product_info)
                
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return self._get_fallback_paragraph(product_info)
    
    def _get_fallback_paragraph(self, product_info: str) -> str:
        """备用段落话术"""
        fallback_paragraphs = [
            f"宝宝们{product_info}超值优惠来啦现在下单立享折扣优惠这个价格真的太划算了数量有限先到先得喜欢的宝子赶紧点击小黄车下单吧错过就没有了这么好的机会不要犹豫了立刻抢购",
            f"各位宝宝注意了{product_info}限时特价活动开始了原价要几十块现在只要这个价格真的是白菜价了质量绝对保证大家放心购买点击右下角小黄车立刻下单享受优惠价格",
            f"宝宝们看过来{product_info}今天特别优惠活动这个产品平时很难买到今天给大家争取到了最低价格机会难得数量真的不多了喜欢的宝子抓紧时间下单不要错过这个好机会",
            f"亲爱的宝宝们{product_info}超级划算的价格来了这个质量这个价格真的找不到第二家了现在下单还有额外优惠赠品相送点击小黄车马上抢购库存不多售完即止",
            f"宝子们{product_info}爆款推荐这个产品销量超高好评如潮现在活动价格真的太优惠了平时买不到这个价格今天给大家最大的优惠力度赶紧下单抢购吧"
        ]
        selected = random.choice(fallback_paragraphs)
        logger.info(f"使用备用段落话术，长度: {len(selected)}字符")
        return selected

class ActionManager:
    """智能动作管理器"""
    
    def __init__(self, total_images: int = 1178):
        self.total_images = total_images
        self.action_types = {
            'greeting': [(0, 150), (500, 650)],      # 问候动作
            'pointing': [(150, 300), (800, 950)],    # 指向动作  
            'excited': [(300, 450), (950, 1100)],    # 兴奋动作
            'explaining': [(450, 600), (1100, 1177)], # 解释动作
            'urging': [(600, 750), (200, 350)]       # 催促动作
        }
        
        self.keywords = {
            'greeting': ['宝宝', '大家', '各位', '亲爱', '朋友们', '宝子'],
            'pointing': ['点击', '小黄车', '链接', '右下角', '这里', '看这'],
            'excited': ['优惠', '特价', '限时', '抢购', '超值', '划算', '便宜'],
            'explaining': ['产品', '质量', '材质', '功能', '效果', '介绍'],
            'urging': ['赶紧', '快点', '马上', '立刻', '错过', '数量有限', '售完']
        }
    
    def analyze_text_action(self, text: str) -> str:
        """分析文本内容，返回最适合的动作类型"""
        action_scores = {action_type: 0 for action_type in self.action_types}
        
        # 计算每种动作类型的匹配分数
        for action_type, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in text:
                    action_scores[action_type] += 1
        
        # 选择得分最高的动作类型
        best_action = max(action_scores, key=action_scores.get)
        
        # 如果没有匹配的关键词，随机选择
        if action_scores[best_action] == 0:
            best_action = random.choice(list(self.action_types.keys()))
        
        logger.info(f"文本'{text[:20]}...' 匹配动作类型: {best_action}")
        return best_action
    
    def get_action_range(self, action_type: str) -> tuple:
        """获取动作类型对应的图片范围"""
        ranges = self.action_types.get(action_type, [(0, 100)])
        selected_range = random.choice(ranges)
        logger.info(f"选择动作范围: {selected_range[0]}-{selected_range[1]} ({action_type})")
        return selected_range

class DigitalHumanGenerator:
    """数字人生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.action_manager = ActionManager()
        
        # 确保输出目录存在
        os.makedirs("output", exist_ok=True)
        os.makedirs("temp", exist_ok=True)
        
        # 线程安全的计数器
        self.counter_lock = threading.Lock()
        self.video_counter = 0
        self.completed_videos = []
    
    def generate_paragraph_audio(self, text: str, base_name: str) -> str:
        """生成段落音频"""
        audio_path = f"temp/{base_name}.wav"
        
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
            hubert_output_path = f"temp/{base_name}_hu.npy"
            
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
            video_path = f"temp/{base_name}_video.mp4"
            
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
            final_video_path = f"output/paragraph_{base_name}.mp4"
            
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
    
    def _create_smart_inference_script(self, hubert_path: str, video_path: str, action_range: tuple, base_name: str) -> str:
        """创建智能推理脚本"""
        script_path = f"temp/smart_inference_{base_name}.py"
        
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
if project_root.endswith('/temp'):
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
        auds = torch.cat([auds, torch.zeros_like(auds[:pad_right])], dim=0)
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

# 创建视频写入器
video_writer = cv2.VideoWriter("{video_path}", cv2.VideoWriter_fourcc('M','J','P', 'G'), 25, (w, h))

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
    img_masked = cv2.rectangle(img_real_ex_ori,(5,5,150,145),(0,0,0),-1)
    
    img_masked = img_masked.transpose(2,0,1).astype(np.float32)
    img_real_ex = img_real_ex.transpose(2,0,1).astype(np.float32)
    
    img_real_ex_T = torch.from_numpy(img_real_ex / 255.0).to(device)
    img_masked_T = torch.from_numpy(img_masked / 255.0).to(device)  
    img_concat_T = torch.cat([img_real_ex_T, img_masked_T], axis=0)[None]
    
    # 获取音频特征
    audio_feat = get_audio_features(audio_feats, i)
    audio_feat = audio_feat.reshape(16,32,32)
    audio_feat = audio_feat[None]
    audio_feat = audio_feat.to(device)
    img_concat_T = img_concat_T.to(device)
    
    # 推理生成
    with torch.no_grad():
        pred = net(img_concat_T, audio_feat)[0]
        
    pred = pred.cpu().numpy().transpose(1,2,0)*255
    pred = np.array(pred, dtype=np.uint8)
    crop_img_ori[4:164, 4:164] = pred
    crop_img_ori = cv2.resize(crop_img_ori, (w_crop, h_crop))
    img[ymin:ymax, xmin:xmax] = crop_img_ori
    
    # 写入视频
    video_writer.write(img)
    
    if i % 50 == 0:
        print(f"已处理帧: {{i+1}}/{{len(audio_feats)}}, 当前动作图片: {{img_idx}}")

video_writer.release()
print(f"智能数字人视频生成完成: {video_path}")
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logger.info(f"创建智能推理脚本: {script_path} (动作范围: {start_idx}-{end_idx})")
        return script_path
    
    def cleanup_intermediate_files(self, audio_path: str, hubert_path: str, video_path: str, script_path: str):
        """清理中间文件"""
        files_to_clean = [audio_path, hubert_path, video_path, script_path]
        for file_path in files_to_clean:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"清理文件失败 {file_path}: {e}")

class DigitalHumanParagraphSystem:
    """数字人段落生成系统"""
    
    def __init__(self):
        self.config = DigitalHumanConfig.from_config_file()
        self.deepseek_client = DeepSeekClient()
        self.generator = DigitalHumanGenerator(self.config)
        
        # 队列和线程管理
        self.text_queue = queue.Queue(maxsize=self.config.text_queue_size)
        self.running = False
        
        # 线程
        self.script_thread = None
        self.video_threads = []
        
        # 统计
        self.start_time = None
        self.completed_count = 0
        self.completed_lock = threading.Lock()
    
    def start(self, product_info: str = None):
        """启动系统"""
        if product_info is None:
            product_info = self.config.product_info
        
        logger.info("启动数字人段落生成系统...")
        
        # 检查必要文件
        required_files = [
            self.config.reference_audio,
            self.config.checkpoint_path,
            "data_utils/hubert.py",
            "inference.py"
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                logger.error(f"必要文件不存在: {file_path}")
                return False
        
        logger.info("✅ 所有必要文件检查通过")
        
        # 设置运行标志
        self.running = True
        self.start_time = time.time()
        
        # 启动段落生成线程
        self.script_thread = threading.Thread(
            target=self._paragraph_generation_worker, 
            args=(product_info,), 
            daemon=True
        )
        self.script_thread.start()
        
        # 启动视频生成线程
        for i in range(self.config.parallel_workers):
            thread = threading.Thread(
                target=self._video_generation_worker,
                args=(f"video_worker_{i}",),
                daemon=True
            )
            thread.start()
            self.video_threads.append(thread)
        
        logger.info("数字人段落生成系统已启动")
        
        # 预热：立即生成一段话术
        try:
            bootstrap_text = self.deepseek_client.generate_paragraph_script(
                product_info, self.config.paragraph_length
            )
            self.text_queue.put_nowait(bootstrap_text)
            logger.info(f"预热段落已入队: {bootstrap_text[:50]}...")
        except Exception as e:
            logger.warning(f"预热段落入队失败: {e}")
        
        return True
    
    def _paragraph_generation_worker(self, product_info: str):
        """段落生成工作线程"""
        logger.info("段落生成线程已启动")
        
        try:
            while self.running:
                try:
                    # 生成段落话术
                    paragraph_text = self.deepseek_client.generate_paragraph_script(
                        product_info, self.config.paragraph_length
                    )
                    
                    # 添加到队列
                    self.text_queue.put(paragraph_text, timeout=5.0)
                    logger.info(f"段落话术已入队: {paragraph_text[:50]}... (长度: {len(paragraph_text)}字符)")
                    
                    # 等待下一次生成
                    time.sleep(self.config.paragraph_interval)
                    
                except queue.Full:
                    logger.warning("文本队列已满，跳过本次生成")
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"段落生成异常: {e}")
                    time.sleep(10)
                    
        except Exception as e:
            logger.error(f"段落生成线程异常退出: {e}")
    
    def _video_generation_worker(self, worker_name: str):
        """视频生成工作线程"""
        logger.info(f"视频生成线程 {worker_name} 已启动")
        
        try:
            while self.running:
                try:
                    # 从文本队列获取任务
                    text = self.text_queue.get(timeout=1.0)
                    logger.info(f"[{worker_name}] 取到段落话术: {text[:50]}... (长度: {len(text)}字符)")
                    
                    # 生成唯一文件名
                    timestamp = int(time.time() * 1000000)
                    thread_id = threading.get_ident() % 1000
                    
                    with self.generator.counter_lock:
                        self.generator.video_counter += 1
                        current_counter = self.generator.video_counter
                    
                    base_name = f"paragraph_{current_counter:06d}_{timestamp}_{thread_id}"
                    
                    # 步骤1: 生成段落音频
                    logger.info(f"[{worker_name}] 生成段落TTS音频: {text[:30]}...")
                    audio_path = self.generator.generate_paragraph_audio(text, base_name)
                    
                    if not audio_path:
                        logger.error(f"[{worker_name}] 段落TTS音频生成失败")
                        continue
                    
                    logger.info(f"[{worker_name}] 段落TTS音频生成成功: {audio_path}")
                    
                    # 步骤2: 生成数字人视频
                    logger.info(f"[{worker_name}] 开始生成数字人段落视频...")
                    final_video_path = self.generator.generate_video(audio_path, text, base_name)
                    
                    if final_video_path:
                        with self.completed_lock:
                            self.completed_count += 1
                            self.generator.completed_videos.append(final_video_path)
                        
                        logger.info(f"[{worker_name}] ✅ 段落视频生成完成: {final_video_path}")
                    else:
                        logger.error(f"[{worker_name}] 段落视频生成失败")
                    
                    # 标记任务完成
                    self.text_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"[{worker_name}] 视频生成异常: {e}")
                    time.sleep(5)
                    
        except Exception as e:
            logger.error(f"视频生成线程 {worker_name} 异常退出: {e}")
    
    def stop(self):
        """停止系统"""
        logger.info("停止数字人段落生成系统...")
        self.running = False
        
        # 等待线程结束
        if self.script_thread and self.script_thread.is_alive():
            self.script_thread.join(timeout=5)
        
        for thread in self.video_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        # 显示统计信息
        runtime = time.time() - self.start_time if self.start_time else 0
        logger.info(f"✅ 本次共生成 {self.completed_count} 个数字人段落视频")
        logger.info(f"📁 输出目录: output")
        logger.info(f"⏱️ 运行时间: {runtime:.1f} 秒")
        
        logger.info("数字人段落生成系统已停止")
    
    def run_forever(self):
        """持续运行"""
        try:
            logger.info("🔄 持续运行中，按 Ctrl+C 停止")
            logger.info("--" * 25)
            
            last_report_time = time.time()
            
            while self.running:
                time.sleep(1)
                
                # 每分钟报告一次进度
                current_time = time.time()
                if current_time - last_report_time >= 60:
                    runtime_minutes = int((current_time - self.start_time) / 60)
                    logger.info(f"系统运行: {runtime_minutes} 分钟，已完成 {self.completed_count} 个数字人段落视频")
                    last_report_time = current_time
                    
        except KeyboardInterrupt:
            logger.info("收到中断信号...")
        finally:
            self.stop()

def main():
    """主函数"""
    print("🎬 数字人段落生成系统")
    print("=" * 50)
    
    try:
        # 加载配置
        config = DigitalHumanConfig.from_config_file()
        logger.info(f"已加载配置文件: config.json")
        
        # 创建系统
        system = DigitalHumanParagraphSystem()
        
        # 启动系统
        if system.start(config.product_info):
            print(f"\n🚀 系统已启动！自动为 '{config.product_info}' 持续生成段落话术并制作视频")
            print(f"📁 输出目录: output/")
            print(f"📊 段落长度: {config.paragraph_length} 字符")
            print(f"⏱️ 生成间隔: {config.paragraph_interval} 秒")
            print(f"🔄 持续运行中，按 Ctrl+C 停止")
            print("--" * 25)
            
            # 持续运行
            system.run_forever()
        else:
            logger.error("系统启动失败")
            
    except Exception as e:
        logger.error(f"系统运行异常: {e}")

if __name__ == "__main__":
    main()