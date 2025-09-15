#!/usr/bin/env python3
"""
数字人批量生成系统 - 每10句话术合并生成连贯视频
支持智能动作变化和批量处理
"""

import os
import sys
import time
import queue
import threading
import subprocess
import logging
import re
import random
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple, List
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class DigitalHumanConfig:
    """数字人系统配置"""
    # DeepSeek API配置
    deepseek_url: str = "https://api.deepseek.com/v1/chat/completions"
    
    # TTS配置
    tts_url: str = "http://127.0.0.1:9880/tts"
    reference_audio: str = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    reference_text: str = "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后"
    
    # 数字人模型配置
    dataset_dir: str = "input/mxbc_0913/"
    checkpoint_path: str = "checkpoint/195.pth"
    
    # 文件路径
    temp_dir: str = "temp"
    output_dir: str = "output"
    
    # 话术生成配置
    script_length: int = 10
    script_interval: float = 30.0
    product_info: str = "蜜雪冰城优惠券"
    auto_start: bool = True
    
    # 批量处理配置
    batch_size: int = 10           # 每批处理的句子数量
    sentence_pause: float = 0.5    # 句子间停顿时间（秒）
    
    # 优化配置
    parallel_workers: int = 2
    
    @classmethod
    def from_config_file(cls, config_path: str = "config.json"):
        """从配置文件加载配置"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                config = cls()
                for key, value in config_data.items():
                    if key == "deepseek_api_key":
                        continue
                    if hasattr(config, key):
                        setattr(config, key, value)
                
                logger.info(f"已加载配置文件: {config_path}")
                return config
            else:
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return cls()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls()

class ActionManager:
    """动作管理器 - 智能选择和管理数字人动作"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ActionManager")
        
        # 动作分类
        self.action_categories = {
            "greeting": {
                "keywords": ["你好", "大家好", "宝宝们", "欢迎", "开始", "直播"],
                "ranges": [(0, 150), (500, 650)],
                "description": "问候动作"
            },
            "pointing": {
                "keywords": ["点击", "小黄车", "链接", "这里", "看这里", "右下角"],
                "ranges": [(150, 300), (800, 950)],
                "description": "指向动作"
            },
            "excited": {
                "keywords": ["优惠", "抢购", "限时", "快", "赶紧", "立刻", "超值"],
                "ranges": [(300, 450), (950, 1100)],
                "description": "兴奋动作"
            },
            "explaining": {
                "keywords": ["这个", "产品", "价格", "质量", "特点", "划算"],
                "ranges": [(450, 600), (1100, 1177)],
                "description": "解释动作"
            },
            "urging": {
                "keywords": ["错过", "最后", "数量有限", "库存", "机会", "先到先得"],
                "ranges": [(600, 750), (200, 350)],
                "description": "催促动作"
            }
        }
        
        # 获取可用图片数量
        img_dir = os.path.join(self.config.dataset_dir, "full_body_img")
        if os.path.exists(img_dir):
            self.total_images = len([f for f in os.listdir(img_dir) if f.endswith('.jpg')])
            self.logger.info(f"发现 {self.total_images} 张参考图片")
        else:
            self.total_images = 1177
            self.logger.warning(f"参考图片目录不存在，使用默认数量: {self.total_images}")
    
    def analyze_batch_actions(self, sentences: List[str]) -> List[Tuple[int, int]]:
        """分析批量句子，生成动作序列"""
        action_sequence = []
        
        for sentence in sentences:
            action_type = self._analyze_single_sentence(sentence)
            action_info = self.action_categories[action_type]
            
            # 随机选择一个范围
            selected_range = random.choice(action_info["ranges"])
            start_img = min(selected_range[0], self.total_images - 1)
            end_img = min(selected_range[1], self.total_images - 1)
            
            action_sequence.append((start_img, end_img))
            self.logger.info(f"句子'{sentence[:15]}...' → {action_type} → 范围({start_img}-{end_img})")
        
        return action_sequence
    
    def _analyze_single_sentence(self, text: str) -> str:
        """分析单句内容，确定合适的动作类型"""
        text_lower = text.lower()
        
        # 计算每个动作类型的匹配分数
        scores = {}
        for action_type, info in self.action_categories.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword in text_lower:
                    score += 1
            scores[action_type] = score
        
        # 选择得分最高的动作类型
        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            # 如果没有匹配，随机选择一个动作类型
            return random.choice(list(self.action_categories.keys()))

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DeepSeekClient")
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not self.api_key:
            self.logger.error("环境变量 DEEPSEEK_API_KEY 未设置，DeepSeek 将使用备用话术")
        
    def generate_live_script(self, product_info: str = "蜜雪冰城优惠券") -> List[str]:
        """生成直播话术"""
        try:
            prompt = f"""
你是一个专业的直播带货主播，正在为"{product_info}"进行直播销售。
请生成{self.config.script_length}句自然流畅的直播话术，每句话要：
1. 语言生动有趣，充满感染力
2. 突出产品优势和优惠信息
3. 引导观众下单购买
4. 每句话控制在15-25个字
5. 语气要亲切自然，像和朋友聊天
6. 句子之间要有逻辑连贯性，适合连续播放

请直接输出{self.config.script_length}句话术，每句一行，不要编号。
"""
            
            if not self.api_key:
                return self._get_fallback_script()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.config.deepseek_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                sentences = self._parse_sentences(content)
                self.logger.info(f"DeepSeek生成话术成功，共{len(sentences)}句")
                return sentences
            else:
                self.logger.error(f"DeepSeek API请求失败: {response.status_code} - {response.text}")
                return self._get_fallback_script()
                
        except Exception as e:
            self.logger.error(f"DeepSeek API异常: {e}")
            return self._get_fallback_script()
    
    def _parse_sentences(self, content: str) -> List[str]:
        """解析生成的句子"""
        lines = content.strip().split('\n')
        sentences = []
        
        for line in lines:
            line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
            line = re.sub(r'^[•\-\*]\s*', '', line.strip())
            
            if line and len(line) > 5:
                sentences.append(line)
        
        return sentences[:self.config.script_length]
    
    def _get_fallback_script(self) -> List[str]:
        """获取备用话术"""
        return [
            "宝宝们，蜜雪冰城优惠券来啦！",
            "现在下单立享超值优惠！",
            "数量有限，先到先得！",
            "这个价格真的太划算了！",
            "快点击小黄车抢购吧！",
            "错过今天就没有这个价格了！",
            "已经有很多宝宝下单了！",
            "库存不多，抓紧时间！",
            "这么好的机会不要错过！",
            "赶紧加入购物车吧！"
        ]

class BatchTTSClient:
    """批量TTS客户端"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.BatchTTSClient")
        
    def generate_batch_audio(self, sentences: List[str], output_path: str) -> bool:
        """生成批量TTS音频（合并多句话）"""
        try:
            # 将多句话直接连接，不添加停顿
            combined_text = "".join(sentences)
            
            self.logger.info(f"合并文本长度: {len(combined_text)} 字符")
            self.logger.info(f"合并内容预览: {combined_text[:100]}...")
            
            # TTS请求参数
            params = {
                "text": combined_text,
                "text_lang": "zh",
                "ref_audio_path": self.config.reference_audio,
                "prompt_text": self.config.reference_text,
                "prompt_lang": "zh",
                "top_k": 5,
                "top_p": 1,
                "temperature": 1,
                "text_split_method": "cut5",
                "batch_size": 1,
                "batch_threshold": 0.75,
                "split_bucket": True,
                "speed_factor": 1.0,
                "fragment_interval": 0.3,
                "seed": -1,
                "media_type": "wav",
                "streaming_mode": False
            }
            
            response = requests.post(self.config.tts_url, json=params, timeout=60)  # 增加超时时间
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # 检查文件大小
                file_size = os.path.getsize(output_path)
                self.logger.info(f"批量TTS音频生成成功: {output_path} (大小: {file_size} 字节)")
                return True
            else:
                self.logger.error(f"批量TTS请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"批量TTS生成异常: {e}")
            return False

class BatchDigitalHumanGenerator:
    """批量数字人视频生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.BatchDigitalHumanGenerator")
        self.action_manager = ActionManager(config)
        
    def generate_batch_video(self, audio_path: str, sentences: List[str]) -> Optional[str]:
        """生成批量数字人视频"""
        try:
            # 生成输出路径
            base_name = os.path.basename(audio_path).replace('.wav', '')
            video_path = os.path.join(self.config.temp_dir, f"{base_name}_video.mp4")
            
            # 步骤1: 使用HuBERT提取音频特征
            hubert_output_path = audio_path.replace('.wav', '_hu.npy')
            
            self.logger.info("步骤1: 提取HuBERT特征...")
            
            if not self._extract_hubert_features(audio_path, hubert_output_path):
                return None
            
            # 步骤2: 运行批量智能推理
            self.logger.info("步骤2: 生成批量数字人视频（智能动作变化）...")
            
            if not self._run_batch_inference(hubert_output_path, video_path, sentences):
                return None
            
            # 清理HuBERT特征文件
            self._cleanup_intermediate_files(hubert_output_path)
            
            self.logger.info(f"批量数字人视频生成成功: {video_path}")
            return video_path
            
        except Exception as e:
            self.logger.error(f"批量数字人视频生成异常: {e}")
            return None
    
    def _extract_hubert_features(self, audio_path: str, output_path: str) -> bool:
        """提取HuBERT特征"""
        try:
            cmd = [
                "python", "data_utils/hubert.py", "--wav", audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                self.logger.error(f"HuBERT特征提取失败: {result.stderr}")
                return False
                
            if not os.path.exists(output_path):
                self.logger.error(f"HuBERT特征文件未生成: {output_path}")
                return False
            
            self.logger.info(f"HuBERT特征提取成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"HuBERT特征提取异常: {e}")
            return False
    
    def _run_batch_inference(self, hubert_path: str, video_path: str, sentences: List[str]) -> bool:
        """运行批量智能推理"""
        try:
            # 创建临时的批量推理脚本
            batch_script_path = os.path.join(self.config.temp_dir, f"batch_inference_{int(time.time())}.py")
            self._create_batch_inference_script(batch_script_path, sentences)
            
            cmd = [
                "python", batch_script_path,
                "--asr", "hubert",
                "--dataset", self.config.dataset_dir,
                "--audio_feat", hubert_path,
                "--checkpoint", self.config.checkpoint_path,
                "--save_path", video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            # 清理临时脚本
            if os.path.exists(batch_script_path):
                os.remove(batch_script_path)
            
            if result.returncode != 0:
                self.logger.error(f"批量智能推理失败: {result.stderr}")
                return False
                
            if not os.path.exists(video_path):
                self.logger.error(f"批量数字人视频未生成: {video_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"批量智能推理异常: {e}")
            return False
    
    def _create_batch_inference_script(self, script_path: str, sentences: List[str]):
        """创建批量智能推理脚本"""
        # 分析批量动作序列
        action_sequence = self.action_manager.analyze_batch_actions(sentences)
        
        # 读取原始推理脚本
        with open("inference.py", "r", encoding="utf-8") as f:
            original_script = f.read()
        
        # 生成动作切换逻辑
        action_logic = self._generate_batch_action_logic(action_sequence, sentences)
        
        # 修改图片选择逻辑
        old_logic = '''if img_idx>len_img - 1:
        step_stride = -1  # step_stride 决定取图片的间隔，目前这个逻辑是从头开始一张一张往后，到最后一张后再一张一张往前
    if img_idx<1:
        step_stride = 1
    img_idx += step_stride'''
        
        # 添加系统路径以解决模块导入问题
        path_fix = '''import sys
import os
# 添加项目根目录到Python路径，解决模块导入问题
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root.endswith('/temp'):
    project_root = os.path.dirname(project_root)
sys.path.insert(0, project_root)
os.chdir(project_root)

'''
        
        # 替换逻辑
        batch_script = original_script.replace(old_logic, action_logic)
        
        # 在导入语句前添加路径修复
        batch_script = batch_script.replace('import argparse', path_fix + 'import argparse')
        
        # 添加注释说明
        sentences_preview = " | ".join([s[:10] + "..." for s in sentences[:3]])
        batch_script = f'''# 批量智能动作数字人推理脚本
# 句子数量: {len(sentences)}
# 内容预览: {sentences_preview}
# 动作序列: {len(action_sequence)} 个动作范围
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{batch_script}'''
        
        # 写入临时脚本
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(batch_script)
        
        self.logger.info(f"创建批量推理脚本: {script_path} ({len(sentences)}句话, {len(action_sequence)}个动作)")
    
    def _generate_batch_action_logic(self, action_sequence: List[Tuple[int, int]], sentences: List[str]) -> str:
        """生成批量动作切换逻辑"""
        # 估算每句话的帧数（粗略估算：每个字符约1帧）
        sentence_frames = []
        total_chars = sum(len(s) for s in sentences)
        
        for sentence in sentences:
            # 根据句子长度分配帧数
            sentence_char_ratio = len(sentence) / total_chars if total_chars > 0 else 1.0 / len(sentences)
            estimated_frames = max(10, int(sentence_char_ratio * 100))  # 最少10帧
            sentence_frames.append(estimated_frames)
        
        # 生成动作切换逻辑代码
        logic_code = f'''# 批量智能动作选择
    # 动作序列: {action_sequence}
    # 句子帧数: {sentence_frames}
    
    action_ranges = {action_sequence}
    sentence_frames = {sentence_frames}
    
    # 计算当前帧属于哪个句子
    current_sentence = 0
    frame_in_sentence = i
    
    for idx, frames in enumerate(sentence_frames):
        if frame_in_sentence < frames:
            current_sentence = idx
            break
        frame_in_sentence -= frames
    
    # 确保索引在有效范围内
    current_sentence = min(current_sentence, len(action_ranges) - 1)
    
    # 获取当前句子的动作范围
    if current_sentence < len(action_ranges):
        start_img, end_img = action_ranges[current_sentence]
        range_size = end_img - start_img + 1
        
        if range_size <= 1:
            img_idx = start_img
        else:
            # 在当前动作范围内循环
            cycle_pos = frame_in_sentence % (range_size * 2 - 2) if range_size > 1 else 0
            if cycle_pos < range_size:
                img_idx = start_img + cycle_pos
            else:
                img_idx = start_img + (range_size * 2 - 2 - cycle_pos)
    else:
        img_idx = 0
    
    # 确保图片索引在有效范围内
    img_idx = max(0, min(img_idx, len_img))'''
        
        return logic_code
    
    def _cleanup_intermediate_files(self, hubert_path: str):
        """清理中间文件"""
        try:
            if hubert_path and os.path.exists(hubert_path):
                os.remove(hubert_path)
                logger.info(f"已清理HuBERT特征文件: {hubert_path}")
        except Exception as e:
            logger.warning(f"清理文件失败: {e}")

class VideoAudioMerger:
    """视频音频合并器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.VideoAudioMerger")
        
    def merge_video_audio(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """合并视频和音频为最终MP4"""
        try:
            self.logger.info(f"合并视频音频: {video_path} + {audio_path} -> {output_path}")
            
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
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"视频音频合并成功: {output_path}")
                return True
            else:
                self.logger.error(f"视频音频合并失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"视频音频合并异常: {e}")
            return False
    
    def cleanup_intermediate_files(self, video_path: str, audio_path: str):
        """清理中间文件"""
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                self.logger.info(f"已清理临时视频文件: {video_path}")
            
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                self.logger.info(f"已清理音频文件: {audio_path}")
                
        except Exception as e:
            self.logger.warning(f"清理中间文件失败: {e}")

class BatchDigitalHumanSystem:
    """批量数字人生成系统主类"""
    
    def __init__(self):
        self.config = DigitalHumanConfig.from_config_file()
        self.deepseek_client = DeepSeekClient(self.config)
        self.tts_client = BatchTTSClient(self.config)
        self.video_generator = BatchDigitalHumanGenerator(self.config)
        self.video_merger = VideoAudioMerger(self.config)
        
        # 队列
        self.batch_queue = queue.Queue(maxsize=50)  # 批量处理队列
        self.completed_videos = []
        
        # 线程
        self.script_thread = None
        self.video_threads = []
        
        # 计数器和锁
        self.batch_counter = 0
        self.counter_lock = threading.Lock()
        
        # 系统状态
        self.running = False
        
        # 产品信息
        self.product_info = "蜜雪冰城优惠券"
        
    def start(self, product_info: str = None):
        """启动系统"""
        try:
            logger.info("启动批量数字人生成系统...")
            
            if product_info:
                self.product_info = product_info
            
            # 检查必要文件
            if not self._check_requirements():
                return False
            
            # 创建目录
            os.makedirs(self.config.temp_dir, exist_ok=True)
            os.makedirs(self.config.output_dir, exist_ok=True)
            
            # 先设置运行状态，再启动线程
            self.running = True
            
            # 启动话术生成线程
            self.script_thread = threading.Thread(target=self._script_generation_worker, daemon=True)
            self.script_thread.start()
            
            # 启动批量视频生成线程
            for i in range(self.config.parallel_workers):
                video_thread = threading.Thread(target=self._batch_video_generation_worker, daemon=True, name=f"batch_worker_{i}")
                video_thread.start()
                self.video_threads.append(video_thread)
            
            logger.info("批量数字人生成系统已启动")
            logger.info(f"批量大小: {self.config.batch_size} 句/批")
            logger.info(f"线程状态: script_alive={self.script_thread.is_alive()} batch_workers={len([t for t in self.video_threads if t.is_alive()])}")
            
            return True
            
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            return False
    
    def stop(self):
        """停止系统"""
        logger.info("停止批量数字人生成系统...")
        self.running = False
        
        # 只显示统计信息
        total_videos = len(self.completed_videos)
        if total_videos > 0:
            logger.info(f"✅ 本次共生成 {total_videos} 个批量数字人MP4文件")
            logger.info(f"📁 输出目录: {self.config.output_dir}")
            logger.info(f"📊 平均每个文件包含 {self.config.batch_size} 句话术")
        else:
            logger.info("本次未生成任何视频文件")
    
    def _script_generation_worker(self):
        """话术生成工作线程"""
        while self.running:
            try:
                # 生成新的话术
                logger.info(f"正在为'{self.product_info}'生成新话术批次...")
                sentences = self.deepseek_client.generate_live_script(self.product_info)
                logger.info(f"生成话术条数: {len(sentences)}")
                
                # 将整批句子添加到批量队列
                if sentences:
                    try:
                        self.batch_queue.put(sentences, timeout=5.0)
                        logger.info(f"话术批次已入队: {len(sentences)} 句")
                    except queue.Full:
                        logger.warning("批量队列已满，跳过本批次话术")
                
                # 等待一段时间再生成新话术
                time.sleep(self.config.script_interval)
                
            except Exception as e:
                logger.error(f"话术生成工作线程异常: {e}")
                time.sleep(5)
    
    def _batch_video_generation_worker(self):
        """批量视频生成工作线程"""
        worker_name = threading.current_thread().name
        logger.info(f"批量视频生成工作线程 {worker_name} 已启动")
        
        while self.running:
            try:
                # 从批量队列获取任务
                sentences = self.batch_queue.get(timeout=1.0)
                logger.info(f"[{worker_name}] 取到话术批次: {len(sentences)} 句")
                
                # 线程安全地生成唯一文件名
                with self.counter_lock:
                    self.batch_counter += 1
                    current_counter = self.batch_counter
                
                timestamp = int(time.time() * 1000) % 100000
                thread_id = threading.get_ident() % 1000
                base_name = f"batch_digital_human_{current_counter:06d}_{timestamp}_{thread_id}"
                audio_filename = f"{base_name}.wav"
                audio_path = os.path.join(self.config.temp_dir, audio_filename)
                
                logger.info(f"[{worker_name}] 批次标识: {base_name}")
                
                # 步骤1: 生成批量TTS音频
                logger.info(f"[{worker_name}] 生成批量TTS音频: {len(sentences)} 句话...")
                if not self.tts_client.generate_batch_audio(sentences, audio_path):
                    logger.error(f"[{worker_name}] 批量TTS生成失败，跳过该批次")
                    continue
                
                logger.info(f"[{worker_name}] 批量TTS音频生成成功: {audio_path}")
                
                # 步骤2: 生成批量数字人视频
                logger.info(f"[{worker_name}] 开始生成批量数字人视频...")
                video_path = self.video_generator.generate_batch_video(audio_path, sentences)
                
                if not video_path:
                    logger.error(f"[{worker_name}] 批量数字人视频生成失败")
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    continue
                
                # 步骤3: 合并视频和音频
                final_output_path = os.path.join(self.config.output_dir, f"{base_name}.mp4")
                logger.info(f"[{worker_name}] 合并视频音频到最终文件: {final_output_path}")
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
                
                if self.video_merger.merge_video_audio(video_path, audio_path, final_output_path):
                    # 验证最终文件是否真的存在
                    if os.path.exists(final_output_path):
                        file_size = os.path.getsize(final_output_path)
                        logger.info(f"[{worker_name}] ✅ 批量数字人MP4生成完成: {final_output_path} (大小: {file_size} 字节)")
                        logger.info(f"[{worker_name}] 📝 包含话术: {len(sentences)} 句")
                        self.completed_videos.append(final_output_path)
                        
                        # 清理中间文件
                        self.video_merger.cleanup_intermediate_files(video_path, audio_path)
                        logger.info(f"[{worker_name}] 已清理中间文件，保留最终MP4: {final_output_path}")
                    else:
                        logger.error(f"[{worker_name}] 合并成功但最终文件不存在: {final_output_path}")
                else:
                    logger.error(f"[{worker_name}] 视频音频合并失败")
                    self.video_merger.cleanup_intermediate_files(video_path, audio_path)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[{worker_name}] 批量视频生成工作线程异常: {e}")
    
    def get_completed_videos(self) -> List[str]:
        """获取已完成的视频列表"""
        return self.completed_videos.copy()
    
    def _check_requirements(self):
        """检查必要文件和依赖"""
        # 检查数据集目录
        if not os.path.exists(self.config.dataset_dir):
            print(f"❌ 数据集目录不存在: {self.config.dataset_dir}")
            return False
        
        # 检查模型文件
        if not os.path.exists(self.config.checkpoint_path):
            print(f"❌ 模型文件不存在: {self.config.checkpoint_path}")
            return False
        
        # 检查参考音频
        if not os.path.exists(self.config.reference_audio):
            print(f"❌ 参考音频不存在: {self.config.reference_audio}")
            return False
        
        # 检查HuBERT脚本
        if not os.path.exists("data_utils/hubert.py"):
            print("❌ HuBERT脚本不存在: data_utils/hubert.py")
            return False
        
        # 检查推理脚本
        if not os.path.exists("inference.py"):
            print("❌ 推理脚本不存在: inference.py")
            return False
        
        print("✅ 所有必要文件检查通过")
        return True

def main():
    """主函数"""
    print("🎬 批量数字人MP4生成系统 - 连贯视频版本")
    print("=" * 60)
    
    # 显示功能特点
    print("🚀 批量处理特点:")
    print("  ✅ 每10句话术合并生成一个连贯视频")
    print("  ✅ 智能动作变化 - 根据内容切换动作")
    print("  ✅ 自然语音停顿 - 句子间自动添加停顿")
    print("  ✅ 流畅动作过渡 - 避免突兀的动作跳跃")
    print("  ✅ 批量并行处理 - 提升生成效率")
    print("-" * 60)
    
    # 创建系统实例
    system = BatchDigitalHumanSystem()
    
    # 自动从配置读取产品信息
    product_info = getattr(system.config, "product_info", None) or "蜜雪冰城优惠券"
    
    # 启动系统
    if not system.start(product_info):
        print("❌ 系统启动失败")
        return
    
    print(f"\n🚀 批量系统已启动！自动为 '{product_info}' 持续生成连贯数字人视频")
    print(f"📁 输出目录: {system.config.output_dir}")
    print(f"📊 批量大小: {system.config.batch_size} 句话/视频")
    print("🔄 持续运行中，按 Ctrl+C 停止")
    print("🎭 每个视频包含多句连贯话术，动作自然变化")
    print("-" * 60)
    
    try:
        # 持续运行，每分钟显示进度
        start_time = time.time()
        while True:
            time.sleep(60)  # 每分钟检查一次
            completed_count = len(system.get_completed_videos())
            elapsed_minutes = int((time.time() - start_time) / 60)
            total_sentences = completed_count * system.config.batch_size
            logger.info(f"系统运行: {elapsed_minutes} 分钟，已完成 {completed_count} 个批量MP4 (约 {total_sentences} 句话术)")
            
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        system.stop()
        print("系统已停止")

if __name__ == "__main__":
    main()