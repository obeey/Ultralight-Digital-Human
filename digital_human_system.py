#!/usr/bin/env python3
"""
数字人直播系统
集成TTS、HuBERT特征提取和数字人视频生成
"""

import os
import sys
import time
import queue
import threading
import subprocess
import logging
from typing import Optional, Dict, Any
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('digital_human.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DigitalHumanConfig:
    """数字人系统配置"""
    def __init__(self):
        self.tts_url = "http://127.0.0.1:9880/tts"
        self.dataset_dir = "input/mxbc_0913/"
        self.checkpoint_path = "checkpoint/195.pth"
        self.temp_dir = "temp"
        self.udp_port = 1234
        self.video_counter = 0
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)

class TTSClient:
    """TTS客户端"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        
    def generate_audio(self, text: str) -> Optional[str]:
        """生成TTS音频"""
        try:
            logger.info(f"生成TTS音频: {text[:50]}...")
            
            # TTS请求参数
            data = {
                "text": text,
                "text_lang": "zh",
                "ref_audio_path": "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC",
                "prompt_text": "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后",
                "prompt_lang": "zh",
                "top_k": 5,
                "top_p": 1.0,
                "temperature": 1.0,
                "text_split_method": "cut5",
                "batch_size": 1,
                "batch_threshold": 0.75,
                "split_bucket": True,
                "speed_factor": 1.0,
                "fragment_interval": 0.3,
                "seed": -1,
                "media_type": "wav",
                "streaming_mode": False,
                "parallel_infer": True,
                "repetition_penalty": 1.35
            }
            
            response = requests.post(self.config.tts_url, json=data, timeout=30)
            
            if response.status_code == 200:
                # 生成音频文件名
                audio_filename = os.path.join(
                    self.config.temp_dir, 
                    f"audio_{self.config.video_counter:06d}.wav"
                )
                
                # 保存音频文件
                with open(audio_filename, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"TTS音频生成成功: {audio_filename}")
                return audio_filename
            else:
                logger.error(f"TTS请求失败: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"TTS生成失败: {e}")
            return None

class DigitalHumanGenerator:
    """数字人视频生成器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        
    def generate_video(self, audio_path: str, text: str) -> Optional[tuple]:
        """从音频生成数字人视频，返回(video_path, audio_path)"""
        try:
            logger.info(f"开始生成数字人视频，音频文件: {audio_path}")
            
            # 步骤1: 使用HuBERT提取音频特征
            hubert_output_path = audio_path.replace('.wav', '_hu.npy')
            logger.info("步骤1: 提取HuBERT特征...")
            
            if not self._extract_hubert_features(audio_path, hubert_output_path):
                return self._create_fallback_video(audio_path)
            
            # 步骤2: 使用训练好的模型生成视频
            video_path = audio_path.replace('.wav', '.mp4')
            logger.info("步骤2: 生成数字人视频...")
            
            if not self._run_inference(hubert_output_path, video_path):
                return self._create_fallback_video(audio_path)
            
            # 保存音频文件用于推流，清理HuBERT特征文件
            self._cleanup_intermediate_files(None, hubert_output_path)  # 不删除音频文件
            
            logger.info(f"数字人视频生成成功: {video_path}")
            return (video_path, audio_path)
            
        except Exception as e:
            logger.error(f"数字人视频生成失败: {e}")
            return self._create_fallback_video(audio_path)
    
    def _extract_hubert_features(self, audio_path: str, output_path: str) -> bool:
        """提取HuBERT特征"""
        try:
            cmd = [
                "python", "hubert_torch28_fix.py", 
                "--wav", audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"HuBERT特征提取失败: {result.stderr}")
                return False
            
            if not os.path.exists(output_path):
                logger.error(f"HuBERT特征文件未生成: {output_path}")
                return False
            
            logger.info(f"HuBERT特征提取成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"HuBERT特征提取异常: {e}")
            return False
    
    def _run_inference(self, hubert_path: str, video_path: str) -> bool:
        """运行数字人推理"""
        try:
            # 检查必要的文件和目录
            if not os.path.exists(self.config.dataset_dir):
                logger.error(f"数据集目录不存在: {self.config.dataset_dir}")
                return False
            
            if not os.path.exists(self.config.checkpoint_path):
                logger.error(f"模型检查点不存在: {self.config.checkpoint_path}")
                return False
            
            cmd = [
                "python", "inference.py",
                "--asr", "hubert",
                "--dataset", self.config.dataset_dir,
                "--audio_feat", hubert_path,
                "--checkpoint", self.config.checkpoint_path,
                "--save_path", video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.error(f"视频推理失败: {result.stderr}")
                return False
            
            if not os.path.exists(video_path):
                logger.error(f"视频文件未生成: {video_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"视频推理异常: {e}")
            return False
    
    def _create_fallback_video(self, audio_path: str) -> Optional[tuple]:
        """创建简单的回退视频，返回(video_path, audio_path)"""
        try:
            logger.info("回退到简单视频生成...")
            
            video_path = audio_path.replace('.wav', '.mp4')
            
            # 获取音频时长
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            
            try:
                duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                duration = float(duration_result.stdout.strip())
            except:
                duration = 5.0
            
            # 生成无声视频
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={duration}",
                "-c:v", "libopenh264",
                "-pix_fmt", "yuv420p",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(video_path):
                logger.info(f"回退视频生成成功: {video_path}")
                return (video_path, audio_path)
            else:
                logger.error(f"回退视频生成失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"回退视频生成异常: {e}")
            return None
    
    def _cleanup_intermediate_files(self, audio_path: str, hubert_path: str):
        """清理中间文件，保留音频和mp4"""
        try:
            # 保留音频文件用于推流
            if audio_path and os.path.exists(audio_path):
                logger.info(f"保留音频文件用于推流: {audio_path}")
            
            # 删除HuBERT特征文件
            if hubert_path and os.path.exists(hubert_path):
                os.remove(hubert_path)
                logger.info(f"已清理HuBERT特征文件: {hubert_path}")
                
        except Exception as e:
            logger.warning(f"清理中间文件失败: {e}")

class UDPStreamer:
    """UDP推流器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.streaming = False
        
    def start_stream(self, video_queue: queue.Queue):
        """开始UDP推流"""
        self.streaming = True
        logger.info(f"开始UDP推流到端口 {self.config.udp_port}")
        
        while self.streaming:
            try:
                # 从队列获取视频和音频文件
                video_data = video_queue.get(timeout=1)
                
                if isinstance(video_data, tuple):
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
                    "-b:v", "2000k",        # 视频比特率
                    "-maxrate", "2500k",    # 最大比特率
                    "-bufsize", "5000k",    # 缓冲区大小
                    "-g", "50",             # GOP大小
                    "-r", "25",             # 帧率
                    "-f", "mpegts",
                    "-pix_fmt", "yuv420p",
                    f"udp://172.18.0.1:{self.config.udp_port}?pkt_size=1316"
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
        self.threads = []
        self.running = False
    
    def start(self):
        """启动直播系统"""
        logger.info("启动数字人直播系统...")
        self.running = True
        
        # 启动视频生成线程
        video_thread = threading.Thread(target=self._video_generation_loop)
        video_thread.daemon = True
        video_thread.start()
        self.threads.append(video_thread)
        
        # 启动UDP推流线程
        stream_thread = threading.Thread(target=self.udp_streamer.start_stream, args=(self.video_queue,))
        stream_thread.daemon = True
        stream_thread.start()
        self.threads.append(stream_thread)
        
        logger.info("数字人直播系统已启动")
        logger.info(f"请在VLC中打开: udp://@:{self.config.udp_port}")
    
    def add_text(self, text: str):
        """添加文本到生成队列"""
        try:
            self.text_queue.put(text, timeout=1)
            logger.info(f"添加文本到队列: {text[:50]}...")
        except queue.Full:
            logger.warning("文本队列已满，丢弃文本")
    
    def _video_generation_loop(self):
        """视频生成循环"""
        while self.running:
            try:
                # 从队列获取文本
                text = self.text_queue.get(timeout=1)
                
                # 生成TTS音频
                audio_path = self.tts_client.generate_audio(text)
                if not audio_path:
                    continue
                
                # 生成数字人视频
                video_result = self.video_generator.generate_video(audio_path, text)
                if not video_result:
                    continue
                
                # 添加到推流队列
                try:
                    self.video_queue.put(video_result, timeout=1)
                    self.config.video_counter += 1
                except queue.Full:
                    logger.warning("视频队列已满，丢弃视频")
                    if isinstance(video_result, tuple):
                        video_path, audio_path = video_result
                        try:
                            if os.path.exists(video_path):
                                os.remove(video_path)
                            if os.path.exists(audio_path):
                                os.remove(audio_path)
                        except:
                            pass
                    else:
                        try:
                            os.remove(video_result)
                        except:
                            pass
                        
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"视频生成循环异常: {e}")
    
    def stop(self):
        """停止直播系统"""
        logger.info("停止数字人直播系统...")
        self.running = False
        self.udp_streamer.stop_stream()
        
        # 等待线程结束
        for thread in self.threads:
            thread.join(timeout=5)
        
        logger.info("数字人直播系统已停止")

def main():
    """主函数"""
    print("🤖 数字人直播系统")
    print("=" * 40)
    
    # 检查必要的文件
    config = DigitalHumanConfig()
    
    if not os.path.exists(config.dataset_dir):
        print(f"❌ 数据集目录不存在: {config.dataset_dir}")
        return False
    
    if not os.path.exists(config.checkpoint_path):
        print(f"❌ 模型检查点不存在: {config.checkpoint_path}")
        return False
    
    if not os.path.exists("data_utils/hubert.py"):
        print("❌ HuBERT脚本不存在: data_utils/hubert.py")
        return False
    
    if not os.path.exists("inference.py"):
        print("❌ 推理脚本不存在: inference.py")
        return False
    
    print("✅ 所有必要文件检查通过")
    
    # 创建并启动系统
    system = DigitalHumanLiveSystem()
    
    try:
        system.start()
        
        print("\n🚀 系统已启动！")
        print(f"📺 请在VLC中打开: udp://@:{config.udp_port}")
        print("💬 输入文本开始生成数字人视频，输入 'quit' 退出")
        print("-" * 40)
        
        while True:
            text = input("输入文本: ").strip()
            
            if text.lower() in ['quit', 'exit', '退出']:
                break
            
            if text:
                system.add_text(text)
            
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        system.stop()
        print("系统已退出")

if __name__ == "__main__":
    main()