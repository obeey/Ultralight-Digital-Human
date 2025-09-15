#!/usr/bin/env python3
"""
数字人段落生成系统 - 整合版
- 按段落连续生成
- 支持文件输出
- 支持UDP推流
"""

import os
import sys
import time
import logging
import argparse
import hashlib
from datetime import datetime
from typing import Optional
import queue
import shutil

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
        UDPStreamer,
        DigitalHumanParagraphSystem
    )
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    logger.error("请确保agent目录存在且包含所有必要模块")
    sys.exit(1)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="数字人段落生成系统")
    
    # 基本参数
    parser.add_argument("--config", type=str, default="config.json",
                        help="配置文件路径")
    parser.add_argument("--mode", type=str, choices=["continuous", "single", "file"],
                        default="continuous", help="运行模式: continuous(连续生成), single(单次生成), file(从文件生成)")
    
    # 单次生成模式参数
    parser.add_argument("--text", type=str, help="单次生成模式下的文本内容")
    parser.add_argument("--output", type=str, help="输出文件路径")
    
    # 文件模式参数
    parser.add_argument("--output-dir", type=str, help="批量生成的输出目录")
    
    # 推流参数
    parser.add_argument("--no-stream", action="store_true", help="禁用UDP推流")
    parser.add_argument("--enable-stream", action="store_true", help="在file模式下启用UDP推流")
    parser.add_argument("--port", type=int, default=1234, help="UDP推流端口")
    
    # 产品信息
    parser.add_argument("--product", type=str, help="产品信息")
    
    return parser.parse_args()

def validate_arguments(args):
    """验证命令行参数"""
    # 验证配置文件
    if not os.path.exists(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        return False
    
    # 验证单次生成模式参数
    if args.mode == "single" and not args.text:
        logger.error("单次生成模式需要提供文本参数 --text")
        return False
    
    # 验证端口范围
    if args.port < 1 or args.port > 65535:
        logger.error(f"端口号无效: {args.port}，应在1-65535范围内")
        return False
    
    # 验证输出路径
    if args.output and os.path.dirname(args.output):
        output_dir = os.path.dirname(args.output)
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            except Exception as e:
                logger.error(f"无法创建输出目录 {output_dir}: {e}")
                return False
    
    return True

def run_continuous_mode(config_path: str, disable_stream: bool = False, 
                       udp_port: Optional[int] = None, product_info: Optional[str] = None):
    """连续生成模式"""
    logger.info("启动连续生成模式")
    
    system = None
    
    try:
        # 验证配置文件
        if not os.path.exists(config_path):
            logger.error(f"配置文件不存在: {config_path}")
            return
        
        # 创建系统实例
        system = DigitalHumanParagraphSystem(config_path)
        
        # 更新配置
        if disable_stream:
            system.config.enable_streaming = False
            logger.info("UDP推流已禁用")
        
        if udp_port:
            system.config.udp_port = udp_port
            logger.info(f"UDP端口设置为: {udp_port}")
        
        if product_info:
            system.config.product_info = product_info
            logger.info(f"产品信息已设置: {product_info[:50]}...")
        
        # 启动系统
        logger.info("正在启动数字人系统...")
        system.start()
        
        # 保持运行
        logger.info("系统已启动，按Ctrl+C停止...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    except Exception as e:
        logger.error(f"连续生成模式异常: {e}")
    finally:
        # 停止系统
        if system:
            try:
                system.stop()
                logger.info("系统已停止")
            except Exception as e:
                logger.error(f"停止系统时出错: {e}")

def run_single_mode(config_path: str, text: str, output_path: Optional[str] = None,
                   enable_stream: bool = True, udp_port: Optional[int] = None):
    """单次生成模式"""
    logger.info(f"启动单次生成模式: {text[:30]}...")
    
    generator = None
    streamer = None
    
    try:
        # 加载配置
        config = DigitalHumanConfig.from_config_file(config_path)
        
        # 更新配置
        if udp_port:
            config.udp_port = udp_port
        
        config.enable_streaming = enable_stream
        
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
                logger.info(f"视频已复制到指定路径: {output_path}")
                video_path = output_path
            except Exception as e:
                logger.error(f"复制文件失败: {e}")
                return None
        
        # 如果启用推流
        if enable_stream:
            try:
                logger.info(f"开始UDP推流: {video_path}")
                streamer = UDPStreamer(config)
                
                # 使用正确的方法进行推流
                video_queue = queue.Queue()
                video_queue.put((video_path, audio_path))
                
                # 启动推流
                streamer.start_stream(video_queue)
                
                # 等待推流完成
                logger.info("推流进行中，按Ctrl+C停止...")
                while not video_queue.empty():
                    time.sleep(0.1)
                
                logger.info("推流完成")
                
            except Exception as e:
                logger.error(f"推流失败: {e}")
            finally:
                if streamer:
                    streamer.stop_stream()
        
        logger.info(f"单次生成完成: {video_path}")
        return video_path
        
    except Exception as e:
        logger.error(f"单次生成模式异常: {e}")
        return None
    finally:
        # 清理资源
        if streamer:
            try:
                streamer.stop()
            except:
                pass

def run_file_mode(config_path: str, output_dir: Optional[str] = None, 
                 enable_stream: bool = True, udp_port: Optional[int] = None,
                 product_info: Optional[str] = None):
    """文件模式 - 批量生成(话术由API生成)"""
    logger.info("启动文件批量生成模式")
    
    system = None
    
    try:
        # 验证配置文件
        if not os.path.exists(config_path):
            logger.error(f"配置文件不存在: {config_path}")
            return
        
        # 加载配置
        config = DigitalHumanConfig.from_config_file(config_path)
        
        # 更新配置
        config.enable_streaming = enable_stream
        
        if udp_port:
            config.udp_port = udp_port
            logger.info(f"UDP端口设置为: {udp_port}")
            
        if product_info:
            config.product_info = product_info
            logger.info(f"产品信息已设置: {product_info[:50]}...")
            
        if output_dir:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            config.output_dir = output_dir
            logger.info(f"输出目录设置为: {output_dir}")
        
        if not enable_stream:
            logger.info("UDP推流已禁用")
        
        # 创建系统实例并应用配置
        system = DigitalHumanParagraphSystem(config_path)
        system.config = config  # 应用更新后的配置
        
        # 生成多段话术和视频
        logger.info("开始批量生成数字人视频...")
        system.start()
        
        # 保持运行直到用户中断
        logger.info("批量生成中，按Ctrl+C停止...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号")
    except Exception as e:
        logger.error(f"批量生成异常: {e}")
    finally:
        if system:
            try:
                system.stop()
                logger.info("批量生成模式已停止")
            except Exception as e:
                logger.error(f"停止系统时出错: {e}")

def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 验证参数
        if not validate_arguments(args):
            logger.error("参数验证失败")
            sys.exit(1)
        
        logger.info(f"启动数字人系统 - 模式: {args.mode}")
        logger.info(f"配置文件: {args.config}")
        
        # 根据模式显示推流状态
        if args.mode == "file":
            stream_status = "启用" if (args.enable_stream and not args.no_stream) else "禁用"
            logger.info(f"UDP推流: {stream_status} (file模式默认禁用)")
        else:
            stream_status = "禁用" if args.no_stream else "启用"
            logger.info(f"UDP推流: {stream_status}")
            
        logger.info(f"UDP端口: {args.port}")
        
        # 根据模式运行
        if args.mode == "continuous":
            run_continuous_mode(
                args.config,
                disable_stream=args.no_stream,
                udp_port=args.port,
                product_info=args.product
            )
        elif args.mode == "single":
            result = run_single_mode(
                args.config,
                args.text,
                args.output,
                enable_stream=not args.no_stream,
                udp_port=args.port
            )
            if result:
                logger.info(f"单次生成成功: {result}")
            else:
                logger.error("单次生成失败")
                sys.exit(1)
        elif args.mode == "file":
            # file模式默认禁用推流，专注于本地文件保存
            # 只有明确使用--enable-stream参数时才启用推流
            enable_stream_for_file = args.enable_stream and not args.no_stream
            run_file_mode(
                args.config,
                output_dir=args.output_dir,
                enable_stream=enable_stream_for_file,
                udp_port=args.port,
                product_info=args.product
            )
            
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()