#!/usr/bin/env python3
"""
数字人段落系统模块
"""

import os
import sys
import time
import logging
import threading
import queue
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# 导入自定义模块
try:
    from .dh_config import DigitalHumanConfig
    from .dh_clients import DeepSeekClient
    from .dh_generator import DigitalHumanGenerator
    from .dh_streamer_async import AsyncUDPStreamer
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有模块文件在同一目录下")
    sys.exit(1)

logger = logging.getLogger(__name__)

class DigitalHumanParagraphSystem:
    """数字人段落系统"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化系统"""
        # 配置日志
        self._setup_logging()
        
        # 加载配置
        self.config = DigitalHumanConfig.from_config_file(config_path)
        logger.info(f"加载配置完成: {self.config}")
        
        # 创建目录
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.temp_dir, exist_ok=True)
        
        # 初始化组件
        self.deepseek_client = DeepSeekClient()
        self.generator = DigitalHumanGenerator(self.config)
        self.async_streamer = AsyncUDPStreamer(self.config, max_concurrent_streams=3, stream_timeout=300)
        
        # 创建队列
        self.text_queue = queue.Queue(maxsize=self.config.text_queue_size)
        # 注意：异步推流不需要video_queue，直接添加任务即可
        
        # 线程控制
        self.running = False
        self.threads = []
        
        logger.info("数字人段落系统初始化完成")
    
    def _setup_logging(self):
        """设置日志"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = f"{log_dir}/digital_human_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def start(self):
        """启动系统"""
        if self.running:
            logger.warning("系统已在运行中")
            return
        
        self.running = True
        logger.info("启动数字人段落系统")
        
        # 启动文本生成线程
        text_thread = threading.Thread(
            target=self._text_generation_worker,
            daemon=True
        )
        self.threads.append(text_thread)
        text_thread.start()
        
        # 启动视频生成线程
        for i in range(self.config.parallel_workers):
            video_thread = threading.Thread(
                target=self._video_generation_worker,
                args=(i,),
                daemon=True
            )
            self.threads.append(video_thread)
            video_thread.start()
        
        # 启动异步UDP推流
        if self.config.enable_streaming:
            self.async_streamer.start()
            logger.info("异步推流器已启动")
        
        logger.info("所有工作线程已启动")
        
        # 启动推流状态监控线程
        if self.config.enable_streaming:
            monitor_thread = threading.Thread(
                target=self._stream_monitor_worker,
                daemon=True
            )
            self.threads.append(monitor_thread)
            monitor_thread.start()
    
    def stop(self):
        """停止系统"""
        if not self.running:
            return
        
        logger.info("正在停止数字人段落系统...")
        self.running = False
        
        # 停止异步推流
        if self.config.enable_streaming:
            self.async_streamer.stop()
        
        # 等待所有线程结束
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.threads = []
        logger.info("数字人段落系统已停止")
    
    def _text_generation_worker(self):
        """文本生成工作线程"""
        logger.info("文本生成线程启动")
        
        while self.running:
            try:
                # 检查队列是否已满
                if self.text_queue.full():
                    time.sleep(1)
                    continue
                
                # 生成段落话术
                paragraph = self.deepseek_client.generate_paragraph_script(
                    self.config.product_info,
                    self.config.paragraph_length
                )
                
                # 添加到队列
                self.text_queue.put(paragraph)
                logger.info(f"生成段落话术，当前队列大小: {self.text_queue.qsize()}/{self.config.text_queue_size}")
                
                # 等待指定间隔
                time.sleep(self.config.paragraph_interval)
                
            except Exception as e:
                logger.error(f"文本生成异常: {e}")
                time.sleep(5)
    
    def _video_generation_worker(self, worker_id: int):
        """视频生成工作线程"""
        logger.info(f"视频生成线程 {worker_id} 启动")
        
        while self.running:
            try:
                # 从队列获取文本
                try:
                    text = self.text_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 生成唯一ID
                base_name = self.generator.generate_unique_id(text)
                logger.info(f"工作线程 {worker_id} 开始处理段落，ID: {base_name}")
                
                # 生成音频
                audio_path = self.generator.generate_paragraph_audio(text, base_name)
                if not audio_path:
                    logger.error(f"工作线程 {worker_id} 音频生成失败")
                    continue
                
                # 生成视频
                video_path = self.generator.generate_video(audio_path, text, base_name)
                if not video_path:
                    logger.error(f"工作线程 {worker_id} 视频生成失败")
                    continue
                
                logger.info(f"工作线程 {worker_id} 完成段落处理: {video_path}")
                
                # 立即添加到异步推流队列，不阻塞继续下一段推理
                if self.config.enable_streaming:
                    task_id = self.async_streamer.add_stream_task(video_path, audio_path)
                    if task_id:
                        logger.info(f"工作线程 {worker_id} 推流任务已添加: {task_id}")
                        logger.info(f"工作线程 {worker_id} 立即继续下一段推理...")
                    else:
                        logger.error(f"工作线程 {worker_id} 添加推流任务失败")
                
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 异常: {e}")
                time.sleep(1)
    
    def _stream_monitor_worker(self):
        """推流状态监控线程"""
        logger.info("推流状态监控线程启动")
        
        while self.running:
            try:
                # 每30秒输出一次推流状态
                time.sleep(30)
                
                if self.config.enable_streaming:
                    queue_info = self.async_streamer.get_queue_info()
                    logger.info(f"推流状态监控: {queue_info}")
                
            except Exception as e:
                logger.error(f"推流状态监控异常: {e}")
                time.sleep(5)
        
        logger.info("推流状态监控线程已退出")
    
    def generate_single_paragraph(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """生成单个段落视频"""
        try:
            # 生成唯一ID
            base_name = self.generator.generate_unique_id(text)
            logger.info(f"开始生成单个段落视频，ID: {base_name}")
            
            # 生成音频
            audio_path = self.generator.generate_paragraph_audio(text, base_name)
            if not audio_path:
                logger.error("音频生成失败")
                return None
            
            # 生成视频
            video_path = self.generator.generate_video(audio_path, text, base_name)
            if not video_path:
                logger.error("视频生成失败")
                return None
            
            # 如果指定了输出路径，复制文件
            if output_path:
                import shutil
                shutil.copy2(video_path, output_path)
                logger.info(f"视频已复制到指定路径: {output_path}")
                return output_path
            
            return video_path
            
        except Exception as e:
            logger.error(f"生成单个段落视频异常: {e}")
            return None