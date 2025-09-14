#!/usr/bin/env python3
"""
数字人MP4生成系统 - 生成完整音视频文件版本
每句话生成数字人视频，然后与音频合并为最终MP4
"""

import os
import sys
import time
import queue
import threading
import subprocess
import logging
import re
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
    output_dir: str = "output"  # 最终MP4输出目录
    
    # 话术生成配置
    script_length: int = 10
    script_interval: float = 30.0
    product_info: str = "蜜雪冰城优惠券"
    auto_start: bool = True
    
    # 优化配置
    parallel_workers: int = 2   # 并行生成数量
    
    @classmethod
    def from_config_file(cls, config_path: str = "config.json"):
        """从配置文件加载配置"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 创建配置实例
                config = cls()
                
                # 更新配置值（安全起见忽略配置文件中的 deepseek_api_key）
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

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DeepSeekClient")
        # 从环境变量获取API Key
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not self.api_key:
            self.logger.error("环境变量 DEEPSEEK_API_KEY 未设置，DeepSeek 将使用备用话术")
        
    def generate_live_script(self, product_info: str = "蜜雪冰城优惠券") -> List[str]:
        """生成直播话术"""
        try:
            # 构建提示词
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
            
            # API请求
            # 若无API Key，直接返回备用话术
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
                
                # 解析生成的话术
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
        # 按行分割并清理
        lines = content.strip().split('\n')
        sentences = []
        
        for line in lines:
            # 清理行首的编号、符号等
            line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
            line = re.sub(r'^[•\-\*]\s*', '', line.strip())
            
            if line and len(line) > 5:  # 过滤太短的句子
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
            # TTS请求参数
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
            
            # 发送请求
            response = requests.post(self.config.tts_url, json=params, timeout=30)
            
            if response.status_code == 200:
                # 保存音频文件
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

class DigitalHumanGenerator:
    """数字人视频生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DigitalHumanGenerator")
        
    def generate_video(self, audio_path: str) -> Optional[str]:
        """生成数字人视频（无音频）"""
        try:
            # 生成输出路径
            base_name = os.path.basename(audio_path).replace('.wav', '')
            video_path = os.path.join(self.config.temp_dir, f"{base_name}_video.mp4")
            
            # 步骤1: 使用HuBERT提取音频特征
            hubert_output_path = audio_path.replace('.wav', '_hu.npy')
            
            self.logger.info("步骤1: 提取HuBERT特征...")
            
            if not self._extract_hubert_features(audio_path, hubert_output_path):
                return None
            
            # 步骤2: 运行数字人推理
            self.logger.info("步骤2: 生成数字人视频...")
            
            if not self._run_inference(hubert_output_path, video_path):
                return None
            
            # 清理HuBERT特征文件
            self._cleanup_intermediate_files(hubert_output_path)
            
            self.logger.info(f"数字人视频生成成功: {video_path}")
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
    
    def _run_inference(self, hubert_path: str, video_path: str) -> bool:
        """运行数字人推理"""
        try:
            cmd = [
                "python", "inference.py",
                "--asr", "hubert",
                "--dataset", self.config.dataset_dir,
                "--audio_feat", hubert_path,
                "--checkpoint", self.config.checkpoint_path,
                "--save_path", video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                self.logger.error(f"数字人推理失败: {result.stderr}")
                return False
                
            if not os.path.exists(video_path):
                self.logger.error(f"数字人视频未生成: {video_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"数字人推理异常: {e}")
            return False
    
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
            
            # 使用FFmpeg合并视频和音频
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,  # 输入视频（无音频）
                "-i", audio_path,  # 输入音频
                "-c:v", "copy",    # 视频流直接复制，不重新编码
                "-c:a", "aac",     # 音频编码为AAC
                "-b:a", "128k",    # 音频比特率
                "-ar", "32000",    # 音频采样率匹配TTS输出
                "-ac", "1",        # 单声道
                "-shortest",       # 以较短的流为准
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
            # 删除临时视频文件
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                self.logger.info(f"已清理临时视频文件: {video_path}")
            
            # 删除音频文件
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                self.logger.info(f"已清理音频文件: {audio_path}")
                
        except Exception as e:
            self.logger.warning(f"清理中间文件失败: {e}")

class DigitalHumanMP4System:
    """数字人MP4生成系统主类"""
    
    def __init__(self):
        self.config = DigitalHumanConfig.from_config_file()
        self.deepseek_client = DeepSeekClient(self.config)
        self.tts_client = TTSClient(self.config)
        self.video_generator = DigitalHumanGenerator(self.config)
        self.video_merger = VideoAudioMerger(self.config)
        
        # 队列
        self.text_queue = queue.Queue(maxsize=100)
        self.completed_videos = []  # 存储完成的视频路径
        
        # 线程
        self.script_thread = None
        self.video_threads = []
        
        # 计数器和锁
        self.video_counter = 0
        self.counter_lock = threading.Lock()  # 保护计数器的线程锁
        
        # 系统状态
        self.running = False
        
        # 产品信息
        self.product_info = "蜜雪冰城优惠券"
        
    def start(self, product_info: str = None):
        """启动系统"""
        try:
            logger.info("启动数字人MP4生成系统...")
            
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
            
            # 启动多个视频生成线程（并行处理）
            for i in range(self.config.parallel_workers):
                video_thread = threading.Thread(target=self._video_generation_worker, daemon=True, name=f"video_worker_{i}")
                video_thread.start()
                self.video_threads.append(video_thread)
            
            logger.info("数字人MP4生成系统已启动")
            logger.info(f"线程状态: script_alive={self.script_thread.is_alive()} video_workers={len([t for t in self.video_threads if t.is_alive()])}")
            
            # 立即预热多条话术，填充队列
            bootstrap_scripts = [
                f"{self.product_info}直播马上开始，福利多多，点击小黄车立刻抢购！",
                f"{self.product_info}超值优惠限时开抢，喜欢的宝子抓紧下单！",
                f"{self.product_info}现在下单立享超值优惠，数量有限先到先得！",
                f"{self.product_info}这个价格真的太划算了，快点击小黄车抢购吧！",
                f"{self.product_info}错过今天就没有这个价格了，赶紧加入购物车！"
            ]
            
            for bootstrap in bootstrap_scripts:
                try:
                    self.text_queue.put_nowait(bootstrap)
                    logger.info(f"预热话术已入队: {bootstrap}")
                except Exception:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            return False
    
    def stop(self):
        """停止系统"""
        logger.info("停止数字人MP4生成系统...")
        self.running = False
        
        # 只显示统计信息
        total_videos = len(self.completed_videos)
        if total_videos > 0:
            logger.info(f"✅ 本次共生成 {total_videos} 个数字人MP4文件")
            logger.info(f"📁 输出目录: {self.config.output_dir}")
        else:
            logger.info("本次未生成任何视频文件")
    
    def _script_generation_worker(self):
        """话术生成工作线程"""
        while self.running:
            try:
                # 生成新的话术
                logger.info(f"正在为'{self.product_info}'生成新话术...")
                sentences = self.deepseek_client.generate_live_script(self.product_info)
                logger.info(f"生成话术条数: {len(sentences)}")
                
                # 将句子添加到文本队列
                added = 0
                for sentence in sentences:
                    if not self.running:
                        break
                    try:
                        self.text_queue.put(sentence, timeout=1.0)
                        added += 1
                    except queue.Full:
                        logger.warning("文本队列已满，跳过部分话术")
                        break
                logger.info(f"本轮已入队话术数: {added}")
                
                # 等待一段时间再生成新话术
                time.sleep(self.config.script_interval)
                
            except Exception as e:
                logger.error(f"话术生成工作线程异常: {e}")
                time.sleep(5)  # 出错后等待5秒再重试
    
    def _video_generation_worker(self):
        """视频生成工作线程（支持并行）"""
        worker_name = threading.current_thread().name
        logger.info(f"视频生成工作线程 {worker_name} 已启动")
        
        while self.running:
            try:
                # 从文本队列获取任务
                text = self.text_queue.get(timeout=1.0)
                logger.info(f"[{worker_name}] 取到话术: {text}")
                
                # 线程安全地生成唯一文件名
                with self.counter_lock:
                    self.video_counter += 1
                    current_counter = self.video_counter
                
                # 使用时间戳+计数器+线程ID确保唯一性
                timestamp = int(time.time() * 1000) % 100000  # 取后5位毫秒
                thread_id = threading.get_ident() % 1000      # 取后3位线程ID
                base_name = f"digital_human_{current_counter:06d}_{timestamp}_{thread_id}"
                audio_filename = f"{base_name}.wav"
                audio_path = os.path.join(self.config.temp_dir, audio_filename)
                
                logger.info(f"[{worker_name}] 生成唯一标识: {base_name}")
                
                # 步骤1: 生成TTS音频
                logger.info(f"[{worker_name}] 生成TTS音频: {text}...")
                if not self.tts_client.generate_audio(text, audio_path):
                    logger.error(f"[{worker_name}] TTS生成失败，跳过该条")
                    continue
                
                logger.info(f"[{worker_name}] TTS音频生成成功: {audio_path}")
                
                # 步骤2: 生成数字人视频（无音频）
                logger.info(f"[{worker_name}] 开始生成数字人视频，音频文件: {audio_path}")
                video_path = self.video_generator.generate_video(audio_path)
                
                if not video_path:
                    logger.error(f"[{worker_name}] 数字人视频生成失败")
                    # 清理音频文件
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
                        logger.info(f"[{worker_name}] ✅ 数字人MP4生成完成: {final_output_path} (大小: {file_size} 字节)")
                        self.completed_videos.append(final_output_path)
                        
                        # 步骤4: 清理中间文件 (只删除temp目录下的文件)
                        self.video_merger.cleanup_intermediate_files(video_path, audio_path)
                        logger.info(f"[{worker_name}] 已清理中间文件，保留最终MP4: {final_output_path}")
                    else:
                        logger.error(f"[{worker_name}] 合并成功但最终文件不存在: {final_output_path}")
                else:
                    logger.error(f"[{worker_name}] 视频音频合并失败")
                    # 清理失败的中间文件
                    self.video_merger.cleanup_intermediate_files(video_path, audio_path)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[{worker_name}] 视频生成工作线程异常: {e}")
    
    def add_manual_text(self, text: str):
        """手动添加文本"""
        try:
            self.text_queue.put(text, timeout=1.0)
            logger.info(f"手动添加文本到队列: {text}")
            return True
        except queue.Full:
            logger.warning("文本队列已满")
            return False
    
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
    print("🎬 数字人MP4生成系统 - DeepSeek AI版本")
    print("=" * 50)
    
    # 创建系统实例
    system = DigitalHumanMP4System()
    
    # 自动从配置读取产品信息；若未配置则使用默认
    product_info = getattr(system.config, "product_info", None) or "蜜雪冰城优惠券"
    
    # 启动系统（无交互，直接运行）
    if not system.start(product_info):
        print("❌ 系统启动失败")
        return
    
    print(f"\n🚀 系统已启动！自动为 '{product_info}' 持续生成话术并制作数字人MP4")
    print(f"📁 输出目录: {system.config.output_dir}")
    print("🔄 持续运行中，按 Ctrl+C 停止")
    print("🎥 每句话术将生成一个完整的数字人MP4文件")
    print("-" * 50)
    
    try:
        # 持续运行，每分钟显示进度
        start_time = time.time()
        while True:
            time.sleep(60)  # 每分钟检查一次
            completed_count = len(system.get_completed_videos())
            elapsed_minutes = int((time.time() - start_time) / 60)
            logger.info(f"系统运行: {elapsed_minutes} 分钟，已完成 {completed_count} 个数字人MP4")
            
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        system.stop()
        print("系统已停止")

if __name__ == "__main__":
    main()