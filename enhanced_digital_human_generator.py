#!/usr/bin/env python3
"""
增强版数字人生成器 - 支持多样化动作变化
根据话术内容智能选择动作，实现丰富的动作变化
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
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
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
    
    # 动作变化配置
    enable_action_variety: bool = True      # 启用动作变化
    action_change_probability: float = 0.7  # 动作变化概率
    min_action_duration: int = 3            # 最小动作持续帧数
    max_action_duration: int = 8            # 最大动作持续帧数
    
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
                "keywords": ["你好", "大家好", "宝宝们", "欢迎", "开始"],
                "ranges": [(0, 100), (500, 600)],  # 图片范围
                "description": "问候动作"
            },
            "pointing": {
                "keywords": ["点击", "小黄车", "链接", "这里", "看这里"],
                "ranges": [(100, 200), (800, 900)],
                "description": "指向动作"
            },
            "excited": {
                "keywords": ["优惠", "抢购", "限时", "快", "赶紧", "立刻"],
                "ranges": [(200, 350), (900, 1000)],
                "description": "兴奋动作"
            },
            "explaining": {
                "keywords": ["这个", "产品", "价格", "质量", "特点"],
                "ranges": [(350, 500), (1000, 1100)],
                "description": "解释动作"
            },
            "urging": {
                "keywords": ["错过", "最后", "数量有限", "库存", "机会"],
                "ranges": [(600, 800), (1100, 1177)],
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
        
        # 动作状态
        self.current_action = None
        self.action_start_frame = 0
        self.action_duration = 0
        
    def analyze_text_action(self, text: str) -> str:
        """分析文本内容，确定合适的动作类型"""
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
            best_action = max(scores, key=scores.get)
            self.logger.info(f"文本'{text[:20]}...' 匹配动作类型: {best_action}")
            return best_action
        else:
            # 如果没有匹配，随机选择一个动作类型
            action_type = random.choice(list(self.action_categories.keys()))
            self.logger.info(f"文本'{text[:20]}...' 使用随机动作类型: {action_type}")
            return action_type
    
    def get_action_sequence(self, text: str, audio_length: int) -> List[int]:
        """根据文本和音频长度生成动作序列"""
        if not self.config.enable_action_variety:
            # 如果禁用动作变化，使用原始逻辑
            return self._get_simple_sequence(audio_length)
        
        # 分析文本确定主要动作类型
        main_action_type = self.analyze_text_action(text)
        action_info = self.action_categories[main_action_type]
        
        sequence = []
        frame_idx = 0
        
        while frame_idx < audio_length:
            # 选择动作范围
            action_range = random.choice(action_info["ranges"])
            start_img, end_img = action_range
            
            # 确保范围在有效图片数量内
            start_img = min(start_img, self.total_images - 1)
            end_img = min(end_img, self.total_images - 1)
            
            # 随机选择动作持续时间
            duration = random.randint(
                self.config.min_action_duration,
                self.config.max_action_duration
            )
            duration = min(duration, audio_length - frame_idx)
            
            # 生成这段动作的图片序列
            if start_img == end_img:
                # 如果范围只有一张图片，重复使用
                segment = [start_img] * duration
            else:
                # 在范围内生成变化序列
                segment = self._generate_smooth_sequence(start_img, end_img, duration)
            
            sequence.extend(segment)
            frame_idx += len(segment)
            
            # 随机决定是否切换到其他动作类型
            if frame_idx < audio_length and random.random() < self.config.action_change_probability:
                # 切换到其他动作类型
                other_actions = [k for k in self.action_categories.keys() if k != main_action_type]
                if other_actions:
                    main_action_type = random.choice(other_actions)
                    action_info = self.action_categories[main_action_type]
                    self.logger.info(f"动作切换到: {main_action_type}")
        
        # 确保序列长度匹配音频长度
        if len(sequence) > audio_length:
            sequence = sequence[:audio_length]
        elif len(sequence) < audio_length:
            # 重复最后一个动作
            last_img = sequence[-1] if sequence else 0
            sequence.extend([last_img] * (audio_length - len(sequence)))
        
        self.logger.info(f"生成动作序列: 长度={len(sequence)}, 范围={min(sequence)}-{max(sequence)}")
        return sequence
    
    def _generate_smooth_sequence(self, start_img: int, end_img: int, duration: int) -> List[int]:
        """生成平滑的动作序列"""
        if duration <= 1:
            return [start_img]
        
        sequence = []
        
        # 生成平滑过渡
        for i in range(duration):
            progress = i / (duration - 1)
            # 使用缓动函数使动作更自然
            eased_progress = self._ease_in_out(progress)
            img_idx = int(start_img + (end_img - start_img) * eased_progress)
            img_idx = max(0, min(img_idx, self.total_images - 1))
            sequence.append(img_idx)
        
        return sequence
    
    def _ease_in_out(self, t: float) -> float:
        """缓动函数，使动作过渡更自然"""
        return t * t * (3.0 - 2.0 * t)
    
    def _get_simple_sequence(self, audio_length: int) -> List[int]:
        """简单的顺序动作序列（原始逻辑）"""
        sequence = []
        img_idx = 0
        step_stride = 1
        
        for i in range(audio_length):
            if img_idx >= self.total_images - 1:
                step_stride = -1
            if img_idx <= 0:
                step_stride = 1
            
            sequence.append(img_idx)
            img_idx += step_stride
        
        return sequence

class EnhancedDigitalHumanGenerator:
    """增强版数字人视频生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.EnhancedDigitalHumanGenerator")
        self.action_manager = ActionManager(config)
        
    def generate_video(self, audio_path: str, text: str) -> Optional[str]:
        """生成数字人视频（支持动作变化）"""
        try:
            # 生成输出路径
            base_name = os.path.basename(audio_path).replace('.wav', '')
            video_path = os.path.join(self.config.temp_dir, f"{base_name}_video.mp4")
            
            # 步骤1: 使用HuBERT提取音频特征
            hubert_output_path = audio_path.replace('.wav', '_hu.npy')
            
            self.logger.info("步骤1: 提取HuBERT特征...")
            
            if not self._extract_hubert_features(audio_path, hubert_output_path):
                return None
            
            # 步骤2: 运行增强版数字人推理
            self.logger.info("步骤2: 生成数字人视频（支持动作变化）...")
            
            if not self._run_enhanced_inference(hubert_output_path, video_path, text):
                return None
            
            # 清理HuBERT特征文件
            self._cleanup_intermediate_files(hubert_output_path)
            
            self.logger.info(f"增强版数字人视频生成成功: {video_path}")
            return video_path
            
        except Exception as e:
            self.logger.error(f"数字人视频生成异常: {e}")
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
    
    def _run_enhanced_inference(self, hubert_path: str, video_path: str, text: str) -> bool:
        """运行增强版数字人推理"""
        try:
            # 创建临时的增强推理脚本
            enhanced_script_path = os.path.join(self.config.temp_dir, "enhanced_inference.py")
            self._create_enhanced_inference_script(enhanced_script_path, text)
            
            cmd = [
                "python", enhanced_script_path,
                "--asr", "hubert",
                "--dataset", self.config.dataset_dir,
                "--audio_feat", hubert_path,
                "--checkpoint", self.config.checkpoint_path,
                "--save_path", video_path,
                "--text", text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                self.logger.error(f"增强版数字人推理失败: {result.stderr}")
                return False
                
            if not os.path.exists(video_path):
                self.logger.error(f"数字人视频未生成: {video_path}")
                return False
            
            # 清理临时脚本
            if os.path.exists(enhanced_script_path):
                os.remove(enhanced_script_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"增强版数字人推理异常: {e}")
            return False
    
    def _create_enhanced_inference_script(self, script_path: str, text: str):
        """创建增强版推理脚本"""
        # 读取原始推理脚本
        with open("inference.py", "r", encoding="utf-8") as f:
            original_script = f.read()
        
        # 生成动作序列
        import numpy as np
        # 估算音频长度（这里简化处理，实际应该从音频文件获取）
        estimated_frames = len(text) * 2  # 粗略估算
        action_sequence = self.action_manager.get_action_sequence(text, estimated_frames)
        
        # 修改推理脚本以使用动作序列
        enhanced_script = self._modify_inference_script(original_script, action_sequence)
        
        # 写入临时脚本
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(enhanced_script)
    
    def _modify_inference_script(self, original_script: str, action_sequence: List[int]) -> str:
        """修改推理脚本以支持动作序列"""
        # 在脚本开头添加动作序列
        action_sequence_str = str(action_sequence)
        
        # 替换图片选择逻辑
        modified_script = original_script.replace(
            'parser.add_argument(\'--checkpoint\', type=str, default="")',
            '''parser.add_argument('--checkpoint', type=str, default="")
parser.add_argument('--text', type=str, default="")'''
        )
        
        # 添加动作序列变量
        modified_script = modified_script.replace(
            'args = parser.parse_args()',
            f'''args = parser.parse_args()
text_content = args.text
action_sequence = {action_sequence_str}'''
        )
        
        # 替换图片选择逻辑
        old_logic = '''if img_idx>len_img - 1:
        step_stride = -1  # step_stride 决定取图片的间隔，目前这个逻辑是从头开始一张一张往后，到最后一张后再一张一张往前
    if img_idx<1:
        step_stride = 1
    img_idx += step_stride'''
        
        new_logic = '''# 使用预生成的动作序列
    if i < len(action_sequence):
        img_idx = action_sequence[i]
    else:
        # 如果序列用完，使用最后一个动作
        img_idx = action_sequence[-1] if action_sequence else 0'''
        
        modified_script = modified_script.replace(old_logic, new_logic)
        
        return modified_script
    
    def _cleanup_intermediate_files(self, hubert_path: str):
        """清理中间文件"""
        try:
            if hubert_path and os.path.exists(hubert_path):
                os.remove(hubert_path)
                logger.info(f"已清理HuBERT特征文件: {hubert_path}")
        except Exception as e:
            logger.warning(f"清理文件失败: {e}")

# 其他类保持不变，只需要修改主系统类中的视频生成器
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

class TTSClient:
    """TTS客户端"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.TTSClient")
        
    def generate_audio(self, text: str, output_path: str) -> bool:
        """生成TTS音频"""
        try:
            params = {
                "text": text,
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
            
            response = requests.post(self.config.tts_url, json=params, timeout=30)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                self.logger.info(f"TTS音频生成成功: {output_path}")
                return True
            else:
                self.logger.error(f"TTS请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"TTS生成异常: {e}")
            return False

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

def main():
    """主函数"""
    print("🎭 增强版数字人MP4生成系统 - 支持多样化动作变化")
    print("=" * 60)
    
    # 显示功能特点
    print("🚀 新功能:")
    print("  ✅ 智能动作选择 - 根据话术内容匹配动作")
    print("  ✅ 动作分类系统 - 问候/指向/兴奋/解释/催促")
    print("  ✅ 平滑动作过渡 - 自然的动作变化")
    print("  ✅ 随机动作组合 - 避免重复单调")
    print("  ✅ 可配置动作参数 - 灵活调整动作变化")
    print("-" * 60)
    
    config = DigitalHumanConfig.from_config_file()
    
    if config.enable_action_variety:
        print("🎭 动作变化功能: 已启用")
        print(f"   动作变化概率: {config.action_change_probability}")
        print(f"   动作持续时间: {config.min_action_duration}-{config.max_action_duration} 帧")
    else:
        print("📹 动作变化功能: 已禁用（使用原始顺序动作）")
    
    print(f"📁 输出目录: {config.output_dir}")
    print("🔄 持续运行中，按 Ctrl+C 停止")
    print("=" * 60)

if __name__ == "__main__":
    main()