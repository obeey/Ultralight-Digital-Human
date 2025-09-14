#!/usr/bin/env python3
"""
简化的直播流启动脚本
"""

import asyncio
import json
import sys
import os
from live_stream_system import LiveStreamSystem, StreamConfig
from env_utils import load_env_file, check_required_env

def load_config(config_path: str = "config.json") -> StreamConfig:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return StreamConfig(
            deepseek_base_url=config_data.get("deepseek_base_url", "https://api.deepseek.com"),
            gpt_sovits_path=config_data.get("gpt_sovits_path", "../GPT-SoVITS"),
            virtual_camera_device=config_data.get("virtual_camera_device", "/dev/video0"),
            buffer_size=config_data.get("buffer_size", 10),
            max_workers=config_data.get("max_workers", 4),
            video_resolution=config_data.get("video_resolution", "1920x1080"),
            video_fps=config_data.get("video_fps", 30)
        )
    except FileNotFoundError:
        print(f"配置文件 {config_path} 不存在")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        sys.exit(1)

async def main():
    """主函数"""
    print("🚀 启动实时直播流系统")
    
    # 尝试加载.env文件
    load_env_file()
    
    # 检查环境变量
    if not check_required_env():
        sys.exit(1)
    
    # 检查必要的依赖
    try:
        import requests
        print("✅ requests 模块已安装")
    except ImportError:
        print("❌ 请安装 requests: pip install requests")
        sys.exit(1)
    
    # 检查FFmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 请安装 FFmpeg")
        sys.exit(1)
    
    # 加载配置
    config = load_config()
    
    # 检查GPT-SoVITS路径
    if not os.path.exists(config.gpt_sovits_path):
        print(f"❌ GPT-SoVITS路径不存在: {config.gpt_sovits_path}")
        print("请确保GPT-SoVITS已正确安装")
        sys.exit(1)
    
    print("✅ 配置检查完成")
    
    # 创建系统实例
    system = LiveStreamSystem(config)
    
    # 获取直播主题
    topic = input("请输入直播主题 (默认: 人工智能的发展趋势): ").strip()
    if not topic:
        topic = "人工智能的发展趋势"
    
    print(f"📺 开始直播: {topic}")
    print("按 Ctrl+C 停止直播")
    
    try:
        await system.start_streaming(topic)
    except KeyboardInterrupt:
        print("\n🛑 用户停止直播")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
    finally:
        system.stop_streaming()
        print("👋 直播系统已关闭")

if __name__ == "__main__":
    asyncio.run(main())