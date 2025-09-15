#!/usr/bin/env python3
"""
数字人UDP推流模块 - 真正异步版本
完全非阻塞的推流实现
"""

import os
import time
import logging
import subprocess
import queue
import threading
from typing import Tuple, Optional, Any, Dict
from dataclasses import dataclass
from enum import Enum
import signal

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

class StreamTaskStatus(Enum):
    """推流任务状态"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class StreamTask:
    """推流任务"""
    task_id: str
    video_path: str
    audio_path: Optional[str]
    created_time: float
    status: StreamTaskStatus = StreamTaskStatus.PENDING
    process: Optional[subprocess.Popen] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None

class AsyncUDPStreamer:
    """真正异步的UDP推流器"""
    
    def __init__(self, config: DigitalHumanConfig, max_concurrent_streams=3, stream_timeout=300):
        self.config = config
        self.max_concurrent_streams = max_concurrent_streams
        self.stream_timeout = stream_timeout
        
        # 推流队列和任务管理
        self.stream_queue = queue.Queue()
        self.active_tasks: Dict[str, StreamTask] = {}
        self.completed_tasks: Dict[str, StreamTask] = {}
        
        # 线程控制
        self.is_running = False
        self.manager_thread = None
        self.monitor_thread = None
        
        # 系统初始化
        self.host_ip = get_wsl_host_ip()
        logger.info(f"异步UDP推流器初始化完成，IP: {self.host_ip}, 最大并发: {max_concurrent_streams}")
    
    def start(self):
        """启动异步推流器"""
        if self.is_running:
            logger.warning("异步推流器已在运行")
            return
        
        self.is_running = True
        
        # 启动任务管理线程
        self.manager_thread = threading.Thread(target=self._task_manager, daemon=True)
        self.manager_thread.start()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._process_monitor, daemon=True)
        self.monitor_thread.start()
        
        logger.info("异步推流器已启动")
    
    def stop(self):
        """停止异步推流器"""
        logger.info("正在停止异步推流器...")
        self.is_running = False
        
        # 终止所有活跃的推流进程
        for task in self.active_tasks.values():
            if task.process and task.process.poll() is None:
                try:
                    task.process.terminate()
                    task.process.wait(timeout=2)
                except:
                    try:
                        task.process.kill()
                    except:
                        pass
        
        # 等待线程结束
        if self.manager_thread and self.manager_thread.is_alive():
            self.manager_thread.join(timeout=5)
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("异步推流器已停止")
    
    def add_stream_task(self, video_path: str, audio_path: Optional[str] = None) -> str:
        """添加推流任务，立即返回任务ID"""
        task_id = f"stream_{int(time.time() * 1000)}_{hash(video_path) % 10000:04d}"
        
        task = StreamTask(
            task_id=task_id,
            video_path=video_path,
            audio_path=audio_path,
            created_time=time.time()
        )
        
        try:
            self.stream_queue.put(task, timeout=1.0)
            logger.info(f"推流任务已加入队列: {task_id} -> {video_path}")
            return task_id
        except queue.Full:
            logger.error(f"推流队列已满，无法添加任务: {task_id}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[StreamTask]:
        """获取任务状态"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        return None
    
    def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        return {
            'queue_size': self.stream_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'max_concurrent': self.max_concurrent_streams
        }
    
    def _task_manager(self):
        """任务管理线程 - 负责启动新的推流任务"""
        logger.info("推流任务管理器已启动")
        
        while self.is_running:
            try:
                # 检查是否可以启动新任务
                if len(self.active_tasks) < self.max_concurrent_streams:
                    try:
                        task = self.stream_queue.get(timeout=1.0)
                        self._start_stream_task(task)
                    except queue.Empty:
                        continue
                else:
                    # 已达到最大并发数，等待
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"任务管理器异常: {e}")
                time.sleep(1.0)
        
        logger.info("推流任务管理器已退出")
    
    def _start_stream_task(self, task: StreamTask):
        """启动单个推流任务"""
        try:
            # 检查文件是否存在
            if not os.path.exists(task.video_path):
                task.status = StreamTaskStatus.FAILED
                task.error_message = f"视频文件不存在: {task.video_path}"
                self.completed_tasks[task.task_id] = task
                logger.error(f"推流任务失败: {task.error_message}")
                return
            
            # 构建ffmpeg命令
            cmd = self._build_ffmpeg_command(task.video_path, task.audio_path)
            
            # 启动推流进程（非阻塞）
            task.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新的进程组
            )
            
            task.status = StreamTaskStatus.STREAMING
            task.start_time = time.time()
            self.active_tasks[task.task_id] = task
            
            logger.info(f"推流任务已启动: {task.task_id} -> {task.video_path} (PID: {task.process.pid})")
            
        except Exception as e:
            task.status = StreamTaskStatus.FAILED
            task.error_message = f"启动推流进程失败: {str(e)}"
            self.completed_tasks[task.task_id] = task
            logger.error(f"启动推流任务失败: {task.task_id}, 错误: {e}")
    
    def _process_monitor(self):
        """进程监控线程 - 监控活跃的推流进程"""
        logger.info("推流进程监控器已启动")
        
        while self.is_running:
            try:
                current_time = time.time()
                completed_tasks = []
                
                # 检查所有活跃任务
                for task_id, task in self.active_tasks.items():
                    if task.process is None:
                        continue
                    
                    # 检查进程是否结束
                    return_code = task.process.poll()
                    if return_code is not None:
                        # 进程已结束
                        task.end_time = current_time
                        if return_code == 0:
                            task.status = StreamTaskStatus.COMPLETED
                            logger.info(f"推流任务完成: {task_id} (耗时: {task.end_time - task.start_time:.2f}秒)")
                        else:
                            task.status = StreamTaskStatus.FAILED
                            # 读取错误信息（非阻塞）
                            try:
                                _, stderr = task.process.communicate(timeout=0.1)
                                task.error_message = stderr.decode()[:200]  # 限制错误信息长度
                            except:
                                task.error_message = f"进程退出码: {return_code}"
                            logger.error(f"推流任务失败: {task_id}, 错误: {task.error_message}")
                        
                        completed_tasks.append(task_id)
                    
                    # 检查超时
                    elif current_time - task.start_time > self.stream_timeout:
                        # 任务超时，终止进程
                        try:
                            os.killpg(os.getpgid(task.process.pid), signal.SIGTERM)
                            task.process.wait(timeout=2)
                        except:
                            try:
                                os.killpg(os.getpgid(task.process.pid), signal.SIGKILL)
                            except:
                                pass
                        
                        task.status = StreamTaskStatus.TIMEOUT
                        task.end_time = current_time
                        task.error_message = f"推流超时: {self.stream_timeout}秒"
                        completed_tasks.append(task_id)
                        
                        logger.warning(f"推流任务超时终止: {task_id} -> {task.video_path}")
                
                # 移动完成的任务
                for task_id in completed_tasks:
                    task = self.active_tasks.pop(task_id)
                    self.completed_tasks[task_id] = task
                
                time.sleep(0.5)  # 监控间隔
                
            except Exception as e:
                logger.error(f"进程监控器异常: {e}")
                time.sleep(1.0)
        
        logger.info("推流进程监控器已退出")
    
    def _build_ffmpeg_command(self, video_path: str, audio_path: Optional[str] = None) -> list:
        """构建ffmpeg推流命令"""
        if audio_path and os.path.exists(audio_path):
            cmd = [
                "ffmpeg", "-y",
                "-re",
                "-stream_loop", "-1" if self.config.stream_loop else "0",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "libopenh264",
                "-b:v", "800k",
                "-c:a", "libmp3lame",
                "-b:a", "48k",
                "-ar", "32000",
                "-ac", "1",
                "-f", "mpegts",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-flush_packets", "1",
                "-fflags", "+genpts",
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
        
        return cmd

# 兼容性包装器，保持与原有接口一致
class UDPStreamer:
    """兼容性包装器"""
    
    def __init__(self, config: DigitalHumanConfig):
        self.async_streamer = AsyncUDPStreamer(config)
        self.async_streamer.start()
        logger.info("UDPStreamer兼容性包装器已初始化")
    
    def start_stream(self, video_queue: "queue.Queue[Tuple[str, Optional[str]]]"):
        """兼容原有接口的推流方法"""
        # 启动一个线程来处理队列中的视频
        def queue_processor():
            while True:
                try:
                    video_data = video_queue.get(timeout=1.0)
                    if isinstance(video_data, tuple) and len(video_data) == 2:
                        video_path, audio_path = video_data
                        if video_path and os.path.exists(video_path):
                            task_id = self.async_streamer.add_stream_task(video_path, audio_path)
                            logger.info(f"视频已添加到异步推流队列: {task_id}")
                    video_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"处理推流队列异常: {e}")
        
        processor_thread = threading.Thread(target=queue_processor, daemon=True)
        processor_thread.start()
    
    def stop_stream(self):
        """停止推流"""
        # 兼容性方法，实际不需要立即停止
        pass
    
    def stop(self):
        """完全停止推流器"""
        self.async_streamer.stop()