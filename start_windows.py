#!/usr/bin/env python3
"""
Windows 10专用启动脚本
直接在Windows下运行，与OBS在同一系统
"""

import asyncio
import json
import sys
import os
import subprocess
import platform
from live_stream_windows import WindowsLiveStreamSystem, StreamConfig
from env_utils import load_env_file, check_required_env

def detect_windows():
    """检测是否在Windows环境中运行"""
    return platform.system().lower() == 'windows'

def check_obs_virtual_camera():
    """检查OBS虚拟摄像头是否可用"""
    try:
        # 检查OBS是否安装
        obs_paths = [
            "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
            "C:/Program Files (x86)/obs-studio/bin/32bit/obs32.exe",
            os.path.expanduser("~/AppData/Local/obs-studio/bin/64bit/obs64.exe")
        ]
        
        obs_installed = any(os.path.exists(path) for path in obs_paths)
        
        if obs_installed:
            print("✅ 检测到OBS Studio")
            print("💡 请在OBS中启用虚拟摄像头功能")
            return True
        else:
            print("⚠️  未检测到OBS Studio，请先安装")
            return False
            
    except Exception as e:
        print(f"检查OBS时出错: {e}")
        return False

def setup_windows_environment():
    """设置Windows环境"""
    print("🔧 设置Windows环境...")
    
    # 创建临时目录
    temp_dirs = ["temp", "C:/temp/stream"]
    for dir_path in temp_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 创建目录: {dir_path}")
        except Exception as e:
            print(f"⚠️  创建目录失败 {dir_path}: {e}")
    
    return True

def load_windows_config(config_path: str = "windows_config.json") -> StreamConfig:
    """加载Windows专用配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return StreamConfig(
            deepseek_base_url=config_data.get("deepseek_base_url", "https://api.deepseek.com"),
            gpt_sovits_path=config_data.get("gpt_sovits_path", "../GPT-SoVITS"),
            output_mode=config_data.get("output_mode", "virtual_camera"),
            rtmp_url=config_data.get("rtmp_url", "rtmp://localhost:1935/live/stream"),
            http_port=config_data.get("http_port", 8080),
            http_host=config_data.get("http_host", "localhost"),
            virtual_camera_device=config_data.get("virtual_camera_name", "OBS Virtual Camera"),
            output_dir=config_data.get("output_dir", "C:/temp/stream"),
            buffer_size=config_data.get("buffer_size", 10),
            max_workers=config_data.get("max_workers", 4),
            video_resolution=config_data.get("video_resolution", "1920x1080"),
            video_fps=config_data.get("video_fps", 30)
        )
    except FileNotFoundError:
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        return StreamConfig(output_mode="virtual_camera")
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        sys.exit(1)

async def main():
    """主函数"""
    print("🚀 Windows 10 实时直播流系统")
    print("=" * 40)
    
    # 检测Windows环境
    if not detect_windows():
        print("❌ 此脚本仅支持Windows系统")
        sys.exit(1)
    
    print("✅ 检测到Windows系统")
    
    # 设置Windows环境
    setup_windows_environment()
    
    # 加载环境变量
    load_env_file()
    
    # 检查环境变量
    if not check_required_env():
        sys.exit(1)
    
    # 检查FFmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg 已安装")
        else:
            print("❌ FFmpeg未正确安装")
            print("请从 https://ffmpeg.org/download.html 下载并安装FFmpeg")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ 未找到FFmpeg")
        print("请从 https://ffmpeg.org/download.html 下载并安装FFmpeg")
        print("并将FFmpeg添加到系统PATH环境变量")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg响应超时")
        sys.exit(1)
    
    # 加载Windows配置
    config = load_windows_config()
    
    # 检查GPT-SoVITS路径
    if not os.path.exists(config.gpt_sovits_path):
        print(f"❌ GPT-SoVITS路径不存在: {config.gpt_sovits_path}")
        print("请确保GPT-SoVITS已正确安装")
        sys.exit(1)
    
    print("✅ 配置检查完成")
    
    # 根据输出模式进行设置
    if config.output_mode == "virtual_camera":
        print("📹 虚拟摄像头模式")
        if check_obs_virtual_camera():
            print("💡 使用方法:")
            print("   1. 启动OBS Studio")
            print("   2. 在OBS中启动虚拟摄像头")
            print("   3. 在其他软件中选择'OBS Virtual Camera'作为摄像头")
        else:
            print("⚠️  建议先安装并配置OBS Studio")
            
    elif config.output_mode == "rtmp":
        print(f"📡 RTMP推流模式: {config.rtmp_url}")
        print("💡 在OBS中添加媒体源，URL设为RTMP地址")
        
    elif config.output_mode == "file":
        print(f"📁 文件输出模式: {config.output_dir}")
        print("💡 在OBS中添加媒体源，选择输出目录中的视频文件")
    
    # 创建系统实例
    system = WindowsLiveStreamSystem(config)
    
    # 获取直播主题
    topic = input("\n请输入直播主题 (默认: 人工智能的发展趋势): ").strip()
    if not topic:
        topic = "人工智能的发展趋势"
    
    print(f"\n📺 开始直播: {topic}")
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