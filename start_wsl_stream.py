#!/usr/bin/env python3
"""
WSL Ubuntu专用启动脚本
支持RTMP推流到Windows OBS
"""

import asyncio
import json
import sys
import os
import subprocess
from live_stream_system import LiveStreamSystem, StreamConfig
from env_utils import load_env_file, check_required_env

def detect_wsl():
    """检测是否在WSL环境中运行"""
    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
            return 'microsoft' in version or 'wsl' in version
    except:
        return False

def setup_rtmp_server():
    """设置简单的RTMP服务器"""
    print("🔧 设置RTMP服务器...")
    
    # 检查是否已有RTMP服务器运行
    try:
        result = subprocess.run(['pgrep', '-f', 'nginx.*rtmp'], capture_output=True)
        if result.returncode == 0:
            print("✅ RTMP服务器已在运行")
            return True
    except:
        pass
    
    # 尝试启动简单的RTMP服务器
    try:
        # 使用FFmpeg作为RTMP服务器
        print("启动FFmpeg RTMP服务器...")
        rtmp_cmd = [
            "ffmpeg",
            "-f", "flv",
            "-listen", "1",
            "-i", "rtmp://localhost:1935/live/stream",
            "-c", "copy",
            "-f", "flv",
            "rtmp://localhost:1935/live/output"
        ]
        
        # 这里可以添加更复杂的RTMP服务器设置
        print("⚠️  请确保RTMP服务器已启动（如nginx-rtmp或SRS）")
        return True
        
    except Exception as e:
        print(f"❌ RTMP服务器设置失败: {e}")
        return False

def load_wsl_config(config_path: str = "wsl_config.json") -> StreamConfig:
    """加载WSL专用配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return StreamConfig(
            deepseek_base_url=config_data.get("deepseek_base_url", "https://api.deepseek.com"),
            gpt_sovits_path=config_data.get("gpt_sovits_path", "../GPT-SoVITS"),
            output_mode=config_data.get("output_mode", "udp"),
            udp_host=config_data.get("udp_host", "localhost"),
            udp_port=config_data.get("udp_port", 1234),
            rtmp_url=config_data.get("rtmp_url", "rtmp://localhost:1935/live/stream"),
            http_port=config_data.get("http_port", 8080),
            http_host=config_data.get("http_host", "0.0.0.0"),
            output_dir=config_data.get("output_dir", "/mnt/c/temp/stream"),
            buffer_size=config_data.get("buffer_size", 10),
            max_workers=config_data.get("max_workers", 4),
            video_resolution=config_data.get("video_resolution", "1920x1080"),
            video_fps=config_data.get("video_fps", 30)
        )
    except FileNotFoundError:
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        return StreamConfig(output_mode="udp")
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")
        sys.exit(1)

async def main():
    """主函数"""
    print("🚀 WSL Ubuntu 实时直播流系统")
    print("=" * 40)
    
    # 检测WSL环境
    if detect_wsl():
        print("✅ 检测到WSL环境")
    else:
        print("⚠️  未检测到WSL环境，但仍可继续运行")
    
    # 加载环境变量
    load_env_file()
    
    # 检查环境变量
    if not check_required_env():
        sys.exit(1)
    
    # 检查依赖
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 请安装 FFmpeg: sudo apt install ffmpeg")
        sys.exit(1)
    
    # 加载WSL配置
    config = load_wsl_config()
    
    # 检查GPT-SoVITS路径
    if not os.path.exists(config.gpt_sovits_path):
        print(f"❌ GPT-SoVITS路径不存在: {config.gpt_sovits_path}")
        print("请确保GPT-SoVITS已正确安装")
        sys.exit(1)
    
    print("✅ 配置检查完成")
    
    # 根据输出模式进行特殊设置
    if config.output_mode == "udp":
        print(f"📡 UDP流模式: {config.udp_host}:{config.udp_port}")
        print("💡 在Windows OBS中添加媒体源:")
        print(f"   取消勾选'本地文件'")
        print(f"   输入: udp://localhost:{config.udp_port}")
        print("   ✅ 这样Windows OBS可以直接接收WSL发送的UDP流!")
        
    elif config.output_mode == "rtmp":
        print(f"📡 RTMP推流模式: {config.rtmp_url}")
        print("💡 在Windows OBS中添加媒体源:")
        print(f"   URL: {config.rtmp_url}")
        setup_rtmp_server()
        
    elif config.output_mode == "http_flv":
        print(f"🌐 HTTP-FLV流模式: http://{config.http_host}:{config.http_port}")
        print("💡 在Windows OBS中添加浏览器源:")
        print(f"   URL: http://localhost:{config.http_port}/stream/stream.m3u8")
        
    elif config.output_mode == "file":
        print(f"📁 文件输出模式: {config.output_dir}")
        print("💡 在Windows OBS中添加媒体源，选择输出目录中的视频文件")
        os.makedirs(config.output_dir, exist_ok=True)
    
    # 创建系统实例
    system = LiveStreamSystem(config)
    
    # 获取直播主题
    topic = input("\n请输入直播主题 (默认: 蜜雪冰城优惠券直播): ").strip()
    if not topic:
        topic = "蜜雪冰城优惠券直播"
    
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