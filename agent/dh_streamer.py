#!/usr/bin/env python3
"""
数字人UDP推流模块
"""

import os
import time
import logging
import subprocess
import queue
import threading
from typing import Tuple, Optional, Any
# 导入配置类
try:
    from .dh_config import DigitalHumanConfig
except ImportError:
    # 如果模块未找到，定义一个简单的配置类以避免错误
    from dataclasses import dataclass
    @dataclass
    class DigitalHumanConfig:
        udp_port: int = 1234
        stream_loop: bool = True
        output_dir: str = "output"
        temp_dir: str = "temp"

# 导入网络工具
try:
    from network_utils import get_wsl_host_ip
except ImportError:
    # 如果模块未找到，使用默认IP
    def get_wsl_host_ip():
        return "172.18.0.1"

logger = logging.getLogger(__name__)

class UDPStreamer:
    """UDP推流器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.config = config
        self.streaming = False
        self.current_process = None
        self.stream_thread = None
        
        # 系统启动时初始化获取WSL主机IP，避免每次推流都获取
        self.host_ip = get_wsl_host_ip()
        logger.info(f"UDP推流器初始化完成，使用IP地址: {self.host_ip}")
    
    def start_stream(self, video_queue: "queue.Queue[Tuple[str, Optional[str]]]"):
        """开始UDP推流"""
        if self.streaming:
            logger.warning("UDP推流已在运行中")
            return
            
        self.streaming = True
        self.stream_thread = threading.Thread(
            target=self._stream_worker,
            args=(video_queue,),
            daemon=True
        )
        self.stream_thread.start()
        logger.info(f"开始UDP推流到端口 {self.config.udp_port}")
    
    def _stream_worker(self, video_queue: "queue.Queue[Tuple[str, Optional[str]]]"):
        """推流工作线程"""
        # 视频缓冲池
        video_buffer = []
        
        while self.streaming:
            try:
                # 填充缓冲池
                while len(video_buffer) < 5:  # 保持5个视频的缓冲
                    try:
                        video_data = video_queue.get(timeout=0.1)
                        if isinstance(video_data, tuple) and len(video_data) == 2:
                            video_path, audio_path = video_data
                            if video_path and os.path.exists(video_path):
                                video_buffer.append((video_path, audio_path))
                                logger.info(f"缓冲池添加视频: {video_path} (当前缓冲: {len(video_buffer)})")
                    except queue.Empty:
                        break
                
                # 如果缓冲池有视频，开始推流
                if video_buffer:
                    video_path, audio_path = video_buffer.pop(0)
                    self._stream_video(video_path, audio_path)
                else:
                    # 缓冲池为空，等待
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"推流异常: {e}")
                time.sleep(1)
                
        logger.info("UDP推流已停止")
    
    def _stream_video(self, video_path: str, audio_path: Optional[str] = None):
        """视频推流"""
        try:
            logger.info(f"推流视频: {video_path}")
            logger.debug(f"使用推流IP地址: {self.host_ip}")
            
            if audio_path and os.path.exists(audio_path):
                logger.info(f"合并音频推流: {audio_path}")
                cmd = [
                    "ffmpeg", "-y",
                    "-re",
                    "-stream_loop", "-1" if self.config.stream_loop else "0",  # 循环推流
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "libopenh264",
                    "-b:v", "800k",  # 降低比特率提升速度
                    "-c:a", "libmp3lame",
                    "-b:a", "48k",   # 降低音频比特率
                    "-ar", "32000",
                    "-ac", "1",
                    "-f", "mpegts",
                    "-pix_fmt", "yuv420p",
                    "-shortest",
                    "-flush_packets", "1",  # 立即刷新包
                    "-fflags", "+genpts",   # 生成时间戳
                    f"udp://{self.host_ip}:{self.config.udp_port}?pkt_size=1316&buffer_size=65536"
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-re",
                    "-stream_loop", "-1" if self.config.stream_loop else "0",
                    "-i", video_path,
                    "-c:v", "libopenh264",
                    "-b:v", "800k",
                    "-f", "mpegts",
                    "-pix_fmt", "yuv420p",
                    "-flush_packets", "1",
                    "-fflags", "+genpts",
                    f"udp://{self.host_ip}:{self.config.udp_port}?pkt_size=1316&buffer_size=65536"
                ]
            
            # 终止之前的推流进程
            if self.current_process and self.current_process.poll() is None:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            
            # 启动新的推流进程
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 等待推流完成或超时
            try:
                stdout, stderr = self.current_process.communicate(timeout=30)
                if self.current_process.returncode == 0:
                    logger.info(f"视频推流完成: {video_path}")
                else:
                    logger.warning(f"视频推流警告: {stderr.decode()}")
            except subprocess.TimeoutExpired:
                self.current_process.terminate()
                logger.info(f"视频推流超时终止: {video_path}")
                
        except Exception as e:
            logger.error(f"推流视频异常: {e}")
    
    def stop_stream(self):
        """停止推流"""
        if not self.streaming:
            return
            
        self.streaming = False
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)
            
        logger.info("UDP推流已停止")