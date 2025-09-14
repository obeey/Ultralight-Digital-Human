#!/usr/bin/env python3
"""
Windows专用实时直播流系统
简化版本，支持UDP流和文件输出
"""

import asyncio
import threading
import queue
import subprocess
import json
import time
import os
import logging
import socket
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StreamConfig:
    """流配置"""
    deepseek_base_url: str = "https://api.deepseek.com"
    gpt_sovits_path: str = "../GPT-SoVITS"
    
    # 输出模式配置
    output_mode: str = "udp"  # udp, file, rtmp
    
    # UDP配置
    udp_host: str = "localhost"
    udp_port: int = 1234
    
    # RTMP配置
    rtmp_url: str = "rtmp://localhost:1935/live/stream"
    
    # 文件输出配置
    output_dir: str = "C:/temp/stream"
    
    # 通用配置
    buffer_size: int = 10
    max_workers: int = 4
    video_resolution: str = "1920x1080"
    video_fps: int = 30

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, base_url: str):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_long_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """生成长篇文案"""
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的直播文案创作者，请生成连贯、有趣的直播内容。"},
                    {"role": "user", "content": f"{prompt}。请生成一段1500-2000字的直播文案，内容要连贯有趣。"}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            return ""

class GPTSoVITSClient:
    """GPT-SoVITS语音合成客户端"""
    
    def __init__(self, sovits_path: str):
        self.sovits_path = sovits_path
        self.audio_cache = {}
    
    def synthesize_audio(self, text: str, output_path: str) -> bool:
        """合成语音"""
        try:
            # 检查缓存
            if text in self.audio_cache:
                logger.info(f"使用缓存音频: {text[:50]}...")
                return True
            
            # 调用GPT-SoVITS合成命令（根据实际情况调整）
            cmd = [
                "python", f"{self.sovits_path}/inference_webui.py",
                "--text", text,
                "--output", output_path,
                "--ref_audio", "reference.wav",
                "--ref_text", "参考文本"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.audio_cache[text] = output_path
                logger.info(f"语音合成成功: {output_path}")
                return True
            else:
                logger.error(f"语音合成失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"语音合成异常: {e}")
            return False

class VideoGenerator:
    """视频生成器"""
    
    def __init__(self, config: StreamConfig):
        self.config = config
    
    def create_video_from_audio(self, audio_path: str, text: str, output_path: str) -> bool:
        """从音频创建视频"""
        try:
            # 创建简单的文字视频
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:size={self.config.video_resolution}:duration=10",
                "-i", audio_path,
                "-vf", f"drawtext=text='{text[:100]}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logger.info(f"视频生成成功: {output_path}")
                return True
            else:
                logger.error(f"视频生成失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"视频生成异常: {e}")
            return False

class StreamBuffer:
    """流缓冲管理器"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.video_queue = queue.Queue(maxsize=max_size)
        self.text_queue = queue.Queue(maxsize=max_size * 2)
        self.lock = threading.Lock()
    
    def add_text(self, text: str):
        """添加文本到队列"""
        try:
            self.text_queue.put(text, timeout=1)
        except queue.Full:
            logger.warning("文本队列已满，丢弃旧内容")
            try:
                self.text_queue.get_nowait()
                self.text_queue.put(text)
            except queue.Empty:
                pass
    
    def add_video(self, video_path: str):
        """添加视频到队列"""
        try:
            self.video_queue.put(video_path, timeout=1)
        except queue.Full:
            logger.warning("视频队列已满，丢弃旧内容")
            try:
                old_video = self.video_queue.get_nowait()
                if os.path.exists(old_video):
                    os.remove(old_video)
                self.video_queue.put(video_path)
            except queue.Empty:
                pass
    
    def get_video(self) -> Optional[str]:
        """获取视频"""
        try:
            return self.video_queue.get(timeout=5)
        except queue.Empty:
            return None
    
    def get_text(self) -> Optional[str]:
        """获取文本"""
        try:
            return self.text_queue.get(timeout=1)
        except queue.Empty:
            return None

class WindowsLiveStreamSystem:
    """Windows专用实时直播流系统"""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self.deepseek_client = DeepSeekClient(config.deepseek_base_url)
        self.sovits_client = GPTSoVITSClient(config.gpt_sovits_path)
        self.video_generator = VideoGenerator(config)
        self.stream_buffer = StreamBuffer(config.buffer_size)
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        self.is_running = False
        self.ffmpeg_process = None
    
    def split_text_to_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        import re
        sentences = re.split(r'[。！？.!?]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def generate_content_batch(self, topic: str):
        """批量生成内容"""
        logger.info(f"开始生成内容批次: {topic}")
        
        # 生成长篇文案
        long_content = await self.deepseek_client.generate_long_content(topic)
        if not long_content:
            logger.error("文案生成失败")
            return
        
        # 分割为句子
        sentences = self.split_text_to_sentences(long_content)
        logger.info(f"生成了 {len(sentences)} 个句子")
        
        # 添加到文本队列
        for sentence in sentences:
            self.stream_buffer.add_text(sentence)
    
    def process_audio_video(self):
        """处理音频视频生成（在线程中运行）"""
        while self.is_running:
            text = self.stream_buffer.get_text()
            if not text:
                continue
            
            try:
                # 生成唯一文件名
                timestamp = int(time.time() * 1000)
                audio_path = f"temp/audio_{timestamp}.wav"
                video_path = f"temp/video_{timestamp}.mp4"
                
                # 确保临时目录存在
                os.makedirs("temp", exist_ok=True)
                
                # 合成语音
                if self.sovits_client.synthesize_audio(text, audio_path):
                    # 生成视频
                    if self.video_generator.create_video_from_audio(audio_path, text, video_path):
                        self.stream_buffer.add_video(video_path)
                    
                    # 清理音频文件
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                
            except Exception as e:
                logger.error(f"音视频处理异常: {e}")
    
    def start_stream_output(self):
        """启动流输出"""
        if self.config.output_mode == "udp":
            self._start_udp_stream()
        elif self.config.output_mode == "file":
            self._start_file_output()
        elif self.config.output_mode == "rtmp":
            self._start_rtmp_stream()
        else:
            logger.error(f"不支持的输出模式: {self.config.output_mode}")
    
    def _start_udp_stream(self):
        """启动UDP流"""
        try:
            logger.info(f"启动UDP流: {self.config.udp_host}:{self.config.udp_port}")
            
            # FFmpeg UDP推流命令
            cmd = [
                "ffmpeg",
                "-re",
                "-f", "concat",
                "-safe", "0",
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-c:a", "aac",
                "-f", "mpegts",
                f"udp://{self.config.udp_host}:{self.config.udp_port}"
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info("UDP流已启动")
            self._stream_video_loop()
            
        except Exception as e:
            logger.error(f"UDP流启动失败: {e}")
    
    def _start_rtmp_stream(self):
        """启动RTMP推流"""
        try:
            logger.info(f"启动RTMP推流到: {self.config.rtmp_url}")
            
            cmd = [
                "ffmpeg",
                "-re",
                "-f", "concat",
                "-safe", "0",
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-tune", "zerolatency",
                "-c:a", "aac",
                "-f", "flv",
                self.config.rtmp_url
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info("RTMP推流已启动")
            self._stream_video_loop()
            
        except Exception as e:
            logger.error(f"RTMP推流启动失败: {e}")
    
    def _start_file_output(self):
        """启动文件输出模式"""
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            logger.info(f"启动文件输出模式: {self.config.output_dir}")
            
            self._file_output_loop()
            
        except Exception as e:
            logger.error(f"文件输出启动失败: {e}")
    
    def _stream_video_loop(self):
        """视频流推送循环"""
        while self.is_running:
            video_path = self.stream_buffer.get_video()
            if video_path and os.path.exists(video_path):
                try:
                    # 写入文件路径到FFmpeg stdin
                    self.ffmpeg_process.stdin.write(f"file '{video_path}'\n")
                    self.ffmpeg_process.stdin.flush()
                    
                    # 等待视频播放完成后删除
                    time.sleep(5)
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        
                except Exception as e:
                    logger.error(f"推送视频失败: {e}")
                    break
            else:
                time.sleep(0.1)
    
    def _file_output_loop(self):
        """文件输出循环"""
        file_counter = 0
        while self.is_running:
            video_path = self.stream_buffer.get_video()
            if video_path and os.path.exists(video_path):
                try:
                    # 复制到输出目录
                    output_file = os.path.join(self.config.output_dir, f"stream_{file_counter:06d}.mp4")
                    import shutil
                    shutil.copy2(video_path, output_file)
                    
                    logger.info(f"输出文件: {output_file}")
                    file_counter += 1
                    
                    # 删除临时文件
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        
                except Exception as e:
                    logger.error(f"文件输出失败: {e}")
            else:
                time.sleep(0.1)
    
    async def start_streaming(self, initial_topic: str):
        """启动流媒体系统"""
        logger.info("启动Windows实时直播流系统")
        self.is_running = True
        
        # 启动音视频处理线程
        audio_video_thread = threading.Thread(target=self.process_audio_video)
        audio_video_thread.daemon = True
        audio_video_thread.start()
        
        # 启动流输出线程
        output_thread = threading.Thread(target=self.start_stream_output)
        output_thread.daemon = True
        output_thread.start()
        
        # 生成初始内容缓冲
        await self.generate_content_batch(initial_topic)
        
        # 持续生成新内容
        while self.is_running:
            try:
                # 检查缓冲区状态
                if self.stream_buffer.text_queue.qsize() < 5:
                    logger.info("缓冲区内容不足，生成新内容")
                    await self.generate_content_batch(initial_topic)
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("收到停止信号")
                break
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                await asyncio.sleep(5)
        
        self.stop_streaming()
    
    def stop_streaming(self):
        """停止流媒体系统"""
        logger.info("停止Windows实时直播流系统")
        self.is_running = False
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
        
        # 清理临时文件
        if os.path.exists("temp"):
            import shutil
            shutil.rmtree("temp")

# 使用示例
async def main():
    config = StreamConfig(
        output_mode="udp",
        udp_host="localhost",
        udp_port=1234
    )
    
    system = WindowsLiveStreamSystem(config)
    
    try:
        await system.start_streaming("今天聊聊人工智能的发展趋势")
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    finally:
        system.stop_streaming()

if __name__ == "__main__":
    asyncio.run(main())