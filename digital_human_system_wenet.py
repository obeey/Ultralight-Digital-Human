#!/usr/bin/env python3
"""
数字人直播系统 - WeNet版本
集成TTS、WeNet特征提取和数字人视频生成
"""

import os
import sys
import time
import queue
import threading
import subprocess
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple
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
    # TTS配置
    tts_url: str = "http://127.0.0.1:9880/tts"
    reference_audio: str = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    reference_text: str = "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后"
    
    # 数字人模型配置
    dataset_dir: str = "input/mxbc_0913/"
    checkpoint_path: str = "checkpoint/195.pth"
    
    # 推流配置
    udp_port: int = 1234
    
    # 文件路径
    temp_dir: str = "temp"

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
        """生成数字人视频"""
        try:
            # 生成输出路径
            base_name = os.path.basename(audio_path).replace('.wav', '')
            video_path = os.path.join(self.config.temp_dir, f"{base_name}.mp4")
            
            # 步骤1: 使用WeNet提取音频特征
            wenet_output_path = audio_path.replace('.wav', '_wenet.npy')
            
            self.logger.info("步骤1: 提取WeNet特征...")
            
            if not self._extract_wenet_features(audio_path, wenet_output_path):
                return self._create_fallback_video(audio_path)
            
            # 步骤2: 运行数字人推理
            self.logger.info("步骤2: 生成数字人视频...")
            
            if not self._run_inference(wenet_output_path, video_path):
                return self._create_fallback_video(audio_path)
            
            # 保存音频文件用于推流，清理WeNet特征文件
            self._cleanup_intermediate_files(None, wenet_output_path)  # 不删除音频文件
            
            self.logger.info(f"数字人视频生成成功: {video_path}")
            return video_path
            
        except Exception as e:
            self.logger.error(f"数字人视频生成异常: {e}")
            return None
    
    def _extract_wenet_features(self, audio_path: str, output_path: str) -> bool:
        """提取WeNet特征"""
        try:
            cmd = [
                "python", "data_utils/wenet_infer.py", audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                self.logger.error(f"WeNet特征提取失败: {result.stderr}")
                return False
                
            if not os.path.exists(output_path):
                self.logger.error(f"WeNet特征文件未生成: {output_path}")
                return False
            
            self.logger.info(f"WeNet特征提取成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"WeNet特征提取异常: {e}")
            return False
    
    def _run_inference(self, wenet_path: str, video_path: str) -> bool:
        """运行数字人推理"""
        try:
            cmd = [
                "python", "inference.py",
                "--asr", "wenet",  # 使用wenet模式
                "--dataset", self.config.dataset_dir,
                "--audio_feat", wenet_path,
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
    
    def _create_fallback_video(self, audio_path: str) -> Optional[str]:
        """创建备用视频"""
        self.logger.warning("使用备用视频生成方案")
        # 这里可以实现一个简单的备用方案
        return None
    
    def _cleanup_intermediate_files(self, audio_path: str, wenet_path: str):
        """清理中间文件，保留音频和mp4"""
        try:
            # 删除WeNet特征文件
            if wenet_path and os.path.exists(wenet_path):
                os.remove(wenet_path)
                logger.info(f"已清理WeNet特征文件: {wenet_path}")
                
        except Exception as e:
            logger.warning(f"清理文件失败: {e}")

class UDPStreamer:
    """UDP推流器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UDPStreamer")
        self.streaming = False
        
    def start_stream(self, video_queue: queue.Queue):
        """开始UDP推流"""
        self.streaming = True
        self.logger.info(f"开始UDP推流到端口 {self.config.udp_port}")
        
        while self.streaming:
            try:
                # 从队列获取视频数据
                video_data = video_queue.get(timeout=1.0)
                
                if isinstance(video_data, tuple) and len(video_data) == 2:
                    # 新格式: (video_path, audio_path)
                    video_path, audio_path = video_data
                    if video_path and os.path.exists(video_path):
                        self._stream_video(video_path, audio_path)
                        
                        # 保留推理生成的mp4文件，不删除
                        logger.info(f"保留数字人视频文件: {video_path}")
                        
                        # 保留音频文件用于推流（数字人mp4文件本身没有音频）
                        if audio_path and os.path.exists(audio_path):
                            logger.info(f"保留音频文件用于推流: {audio_path}")
                else:
                    # 兼容旧格式
                    video_path = video_data
                    if video_path and os.path.exists(video_path):
                        self._stream_video(video_path)
                        logger.info(f"保留数字人视频文件: {video_path}")
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"推流异常: {e}")
                
        logger.info("UDP推流已停止")
    
    def _stream_video(self, video_path: str, audio_path: str = None):
        """推流单个视频文件，如果有音频则合并"""
        try:
            logger.info(f"推流视频: {video_path}")
            
            if audio_path and os.path.exists(audio_path):
                # 有音频文件，合并音视频推流
                logger.info(f"合并音频推流: {audio_path}")
                cmd = [
                    "ffmpeg", "-y",
                    "-re",  # 实时播放
                    "-i", video_path,  # 视频输入
                    "-i", audio_path,  # 音频输入
                    "-c:v", "libopenh264",  # 重新编码MJPEG为H.264
                    "-b:v", "1000k",        # 降低视频比特率
                    "-c:a", "libmp3lame",   # 音频编码
                    "-b:a", "64k",          # 降低音频比特率
                    "-ar", "32000",         # 音频采样率匹配源文件
                    "-ac", "1",             # 单声道
                    "-f", "mpegts",
                    "-pix_fmt", "yuv420p",
                    "-shortest",  # 以最短的流为准
                    f"udp://172.18.0.1:{self.config.udp_port}?pkt_size=512"  # 更小的UDP包
                ]
            else:
                # 只有视频，重新编码推流
                cmd = [
                    "ffmpeg", "-y",
                    "-re",  # 实时播放
                    "-i", video_path,
                    "-c:v", "libopenh264",  # 重新编码MJPEG为H.264
                    "-b:v", "1000k",        # 视频比特率
                    "-f", "mpegts",
                    "-pix_fmt", "yuv420p",
                    f"udp://172.18.0.1:{self.config.udp_port}?pkt_size=512"
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"视频推流完成: {video_path}")
            else:
                logger.error(f"视频推流失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"推流视频异常: {e}")
    
    def stop_stream(self):
        """停止推流"""
        self.streaming = False

class DigitalHumanLiveSystem:
    """数字人直播系统主类"""
    
    def __init__(self):
        self.config = DigitalHumanConfig()
        self.tts_client = TTSClient(self.config)
        self.video_generator = DigitalHumanGenerator(self.config)
        self.udp_streamer = UDPStreamer(self.config)
        
        # 队列
        self.text_queue = queue.Queue(maxsize=10)
        self.video_queue = queue.Queue(maxsize=5)
        
        # 线程
        self.video_thread = None
        self.stream_thread = None
        
        # 计数器
        self.audio_counter = 0
        
        # 系统状态
        self.running = False
        
    def start(self):
        """启动系统"""
        try:
            logger.info("启动数字人直播系统...")
            
            # 检查必要文件
            if not self._check_requirements():
                return False
            
            # 创建临时目录
            os.makedirs(self.config.temp_dir, exist_ok=True)
            
            # 启动视频生成线程
            self.video_thread = threading.Thread(target=self._video_generation_worker, daemon=True)
            self.video_thread.start()
            
            # 启动推流线程
            self.stream_thread = threading.Thread(target=self.udp_streamer.start_stream, args=(self.video_queue,), daemon=True)
            self.stream_thread.start()
            
            self.running = True
            logger.info("数字人直播系统已启动")
            logger.info("请在VLC中打开: udp://@:1234")
            
            return True
            
        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            return False
    
    def stop(self):
        """停止系统"""
        logger.info("停止数字人直播系统...")
        self.running = False
        self.udp_streamer.stop_stream()
    
    def add_text(self, text: str):
        """添加文本到生成队列"""
        try:
            if not self.running:
                logger.warning("系统未启动")
                return False
                
            self.text_queue.put(text, timeout=1.0)
            logger.info(f"添加文本到队列: {text}...")
            return True
            
        except queue.Full:
            logger.warning("文本队列已满")
            return False
        except Exception as e:
            logger.error(f"添加文本失败: {e}")
            return False
    
    def _video_generation_worker(self):
        """视频生成工作线程"""
        while self.running:
            try:
                # 从文本队列获取任务
                text = self.text_queue.get(timeout=1.0)
                
                # 生成音频文件名
                audio_filename = f"audio_{self.audio_counter:06d}.wav"
                audio_path = os.path.join(self.config.temp_dir, audio_filename)
                self.audio_counter += 1
                
                # 步骤1: 生成TTS音频
                logger.info(f"生成TTS音频: {text}...")
                if not self.tts_client.generate_audio(text, audio_path):
                    continue
                
                logger.info(f"TTS音频生成成功: {audio_path}")
                
                # 步骤2: 生成数字人视频
                logger.info(f"开始生成数字人视频，音频文件: {audio_path}")
                video_path = self.video_generator.generate_video(audio_path)
                
                if video_path:
                    # 将视频和音频路径添加到推流队列
                    self.video_queue.put((video_path, audio_path), timeout=5.0)
                else:
                    logger.error("数字人视频生成失败")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"视频生成工作线程异常: {e}")
    
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
        
        # 检查WeNet脚本
        if not os.path.exists("data_utils/wenet_infer.py"):
            print("❌ WeNet脚本不存在: data_utils/wenet_infer.py")
            return False
        
        # 检查推理脚本
        if not os.path.exists("inference.py"):
            print("❌ 推理脚本不存在: inference.py")
            return False
        
        print("✅ 所有必要文件检查通过")
        return True

def main():
    """主函数"""
    print("🤖 数字人直播系统 - WeNet版本")
    print("=" * 40)
    
    # 创建系统实例
    system = DigitalHumanLiveSystem()
    
    # 启动系统
    if not system.start():
        print("❌ 系统启动失败")
        return
    
    print("\n🚀 系统已启动！")
    print("📺 请在VLC中打开: udp://@172.18.0.1:1234")
    print("💬 输入文本开始生成数字人视频，输入 'quit' 退出")
    print("-" * 40)
    
    try:
        while True:
            text = input("输入文本: ").strip()
            
            if text.lower() == 'quit':
                break
            
            if text:
                system.add_text(text)
            
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        system.stop()
        print("系统已停止")

if __name__ == "__main__":
    main()