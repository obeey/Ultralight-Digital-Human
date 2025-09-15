#!/usr/bin/env python3
"""
数字人段落生成系统 - 异步推流版
- 推理和推流完全分离
- 推理完成后立即返回，不等待推流
- 专门的推流线程处理视频缓冲池
- 支持推流队列管理和状态监控
"""

import os
import sys
import time
import logging
import argparse
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import queue
import shutil
import threading
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 导入自定义模块
try:
    from agent import (
        DigitalHumanConfig,
        DeepSeekClient,
        DigitalHumanGenerator,
        DigitalHumanParagraphSystem
    )
    # 导入真正异步的推流器
    from agent.dh_streamer_async import AsyncUDPStreamer
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    logger.error("请确保agent目录存在且包含所有必要模块")
    sys.exit(1)

class StreamStatus(Enum):
    """推流状态枚举"""
    PENDING = "pending"      # 等待推流
    STREAMING = "streaming"  # 推流中
    COMPLETED = "completed"  # 推流完成
    FAILED = "failed"        # 推流失败
    TIMEOUT = "timeout"      # 推流超时

@dataclass
class StreamTask:
    """推流任务"""
    task_id: str
    video_path: str
    audio_path: str
    created_time: float
    status: StreamStatus = StreamStatus.PENDING
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class AsyncStreamManager:
    """异步推流管理器 - 使用真正异步的推流器"""
    
    def __init__(self, config, max_queue_size=100, stream_timeout=300):
        self.config = config
        self.max_queue_size = max_queue_size
        self.stream_timeout = stream_timeout
        
        # 使用真正异步的推流器
        self.async_streamer = AsyncUDPStreamer(
            config, 
            max_concurrent_streams=3, 
            stream_timeout=stream_timeout
        )
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'timeout_tasks': 0
        }
    
    def start(self):
        """启动推流管理器"""
        self.async_streamer.start()
        logger.info("异步推流管理器已启动")
    
    def stop(self):
        """停止推流管理器"""
        logger.info("正在停止推流管理器...")
        self.async_streamer.stop()
        logger.info("推流管理器已停止")
    
    def add_stream_task(self, video_path: str, audio_path: str, task_id: Optional[str] = None) -> str:
        """添加推流任务，立即返回任务ID"""
        # 直接使用异步推流器添加任务
        task_id = self.async_streamer.add_stream_task(video_path, audio_path)
        
        if task_id:
            self.stats['total_tasks'] += 1
            logger.info(f"推流任务已添加: {task_id} -> {video_path}")
        else:
            logger.error(f"添加推流任务失败: {video_path}")
        
        return task_id
    
    def get_task_status(self, task_id: str):
        """获取任务状态"""
        return self.async_streamer.get_task_status(task_id)
    
    def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        queue_info = self.async_streamer.get_queue_info()
        queue_info.update(self.stats)
        return queue_info
    


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="数字人段落生成系统 - 异步推流版")
    
    # 基本参数
    parser.add_argument("--config", type=str, default="config.json",
                        help="配置文件路径")
    parser.add_argument("--mode", type=str, choices=["continuous", "single", "file"],
                        default="continuous", help="运行模式")
    
    # 单次生成模式参数
    parser.add_argument("--text", type=str, help="单次生成模式下的文本内容")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    # 文件模式参数
    parser.add_argument("--output-dir", type=str, help="批量生成的输出目录")
    
    # 推流参数
    parser.add_argument("--no-stream", action="store_true", help="禁用UDP推流")
    parser.add_argument("--enable-stream", action="store_true", help="在file模式下启用UDP推流")
    parser.add_argument("--port", type=int, default=1234, help="UDP推流端口")
    parser.add_argument("--stream-timeout", type=int, default=300, help="单个推流任务超时时间(秒)")
    parser.add_argument("--max-queue-size", type=int, default=100, help="推流队列最大大小")
    
    # 产品信息
    parser.add_argument("--product", type=str, help="产品信息")
    
    return parser.parse_args()

def validate_arguments(args):
    """验证命令行参数"""
    if not os.path.exists(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        return False
    
    if args.mode == "single" and not args.text:
        logger.error("单次生成模式需要提供文本参数 --text")
        return False
    
    if args.port < 1 or args.port > 65535:
        logger.error(f"端口号无效: {args.port}")
        return False
    
    if args.stream_timeout < 10:
        logger.error(f"推流超时时间过短: {args.stream_timeout}秒")
        return False
    
    if args.max_queue_size < 1:
        logger.error(f"队列大小无效: {args.max_queue_size}")
        return False
    
    return True

def run_single_mode_async(config_path: str, text: str, output_path: Optional[str] = None,
                         enable_stream: bool = True, stream_manager: Optional[AsyncStreamManager] = None):
    """异步单次生成模式 - 推理完成立即返回"""
    logger.info(f"启动异步单次生成: {text[:30]}...")
    
    try:
        # 加载配置
        config = DigitalHumanConfig.from_config_file(config_path)
        
        # 创建生成器
        generator = DigitalHumanGenerator(config)
        
        # 生成唯一ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        base_name = f"{timestamp}_{text_hash}"
        
        # 生成音频
        logger.info("开始生成音频...")
        audio_path = generator.generate_paragraph_audio(text, base_name)
        if not audio_path:
            logger.error("音频生成失败")
            return None
        
        logger.info(f"音频生成成功: {audio_path}")
        
        # 生成视频
        logger.info("开始生成视频...")
        video_path = generator.generate_video(audio_path, text, base_name)
        if not video_path:
            logger.error("视频生成失败")
            return None
        
        logger.info(f"视频生成成功: {video_path}")
        
        # 如果指定了输出路径，复制文件
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                shutil.copy2(video_path, output_path)
                logger.info(f"视频已复制到: {output_path}")
                video_path = output_path
            except Exception as e:
                logger.error(f"复制文件失败: {e}")
                return None
        
        # 推理完成，如果启用推流则添加到推流队列，立即返回
        if enable_stream and stream_manager:
            task_id = stream_manager.add_stream_task(video_path, audio_path)
            if task_id:
                logger.info(f"视频已添加到推流队列: {task_id}")
                logger.info(f"推理完成，立即返回继续下一段: {video_path}")
            else:
                logger.error("添加推流任务失败")
        else:
            logger.info("推流已禁用，仅生成本地文件")
        
        return video_path
        
    except Exception as e:
        logger.error(f"异步生成异常: {e}")
        return None

def run_continuous_mode_async(config_path: str, disable_stream: bool = False,
                             udp_port: Optional[int] = None, product_info: Optional[str] = None,
                             stream_timeout: int = 300, max_queue_size: int = 100):
    """异步连续生成模式"""
    logger.info("启动异步连续生成模式")
    
    system = None
    stream_manager = None
    
    try:
        # 加载配置
        config = DigitalHumanConfig.from_config_file(config_path)
        
        # 更新配置
        if udp_port:
            config.udp_port = udp_port
        
        if product_info:
            config.product_info = product_info
        
        # 启动推流管理器
        if not disable_stream:
            stream_manager = AsyncStreamManager(config, max_queue_size, stream_timeout)
            stream_manager.start()
            logger.info("异步推流管理器已启动")
        
        # 创建并启动数字人系统
        system = DigitalHumanParagraphSystem(config_path)
        system.config = config
        
        # 如果有推流管理器，需要修改系统以使用异步推流
        # 这里需要根据实际的DigitalHumanParagraphSystem实现来调整
        
        system.start()
        logger.info("数字人系统已启动")
        
        # 定期输出推流队列状态
        last_status_time = time.time()
        
        while True:
            time.sleep(1)
            
            # 每30秒输出一次状态
            if stream_manager and time.time() - last_status_time > 30:
                queue_info = stream_manager.get_queue_info()
                logger.info(f"推流队列状态: {queue_info}")
                last_status_time = time.time()
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    except Exception as e:
        logger.error(f"异步连续生成异常: {e}")
    finally:
        # 停止系统
        if system:
            try:
                system.stop()
                logger.info("数字人系统已停止")
            except Exception as e:
                logger.error(f"停止数字人系统出错: {e}")
        
        # 停止推流管理器
        if stream_manager:
            try:
                stream_manager.stop()
                logger.info("推流管理器已停止")
            except Exception as e:
                logger.error(f"停止推流管理器出错: {e}")

def main():
    """主函数"""
    try:
        args = parse_arguments()
        
        if not validate_arguments(args):
            logger.error("参数验证失败")
            sys.exit(1)
        
        logger.info(f"启动异步数字人系统 - 模式: {args.mode}")
        logger.info(f"推流队列大小: {args.max_queue_size}")
        logger.info(f"推流超时: {args.stream_timeout}秒")
        
        if args.mode == "single":
            # 创建推流管理器
            stream_manager = None
            if not args.no_stream:
                config = DigitalHumanConfig.from_config_file(args.config)
                if args.port:
                    config.udp_port = args.port
                stream_manager = AsyncStreamManager(config, args.max_queue_size, args.stream_timeout)
                stream_manager.start()
            
            try:
                result = run_single_mode_async(
                    args.config,
                    args.text,
                    args.output,
                    enable_stream=not args.no_stream,
                    stream_manager=stream_manager
                )
                
                if result:
                    logger.info(f"异步生成成功: {result}")
                    
                    # 如果有推流，等待一段时间让推流完成
                    if stream_manager:
                        logger.info("等待推流完成...")
                        time.sleep(5)  # 给推流一些时间
                        queue_info = stream_manager.get_queue_info()
                        logger.info(f"最终推流状态: {queue_info}")
                else:
                    logger.error("异步生成失败")
                    sys.exit(1)
            finally:
                if stream_manager:
                    stream_manager.stop()
        
        elif args.mode == "continuous":
            run_continuous_mode_async(
                args.config,
                disable_stream=args.no_stream,
                udp_port=args.port,
                product_info=args.product,
                stream_timeout=args.stream_timeout,
                max_queue_size=args.max_queue_size
            )
        
        # file模式类似，这里省略实现
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()