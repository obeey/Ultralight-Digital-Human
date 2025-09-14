#!/usr/bin/env python3
"""
测试完整的直播系统
包括TTS、视频生成和UDP推流
"""

import asyncio
import os
import sys
import time
import subprocess
import threading
from live_stream_system import LiveStreamSystem, StreamConfig

def check_tts_service():
    """检查TTS服务是否运行"""
    print("🔍 检查TTS服务...")
    
    try:
        import requests
        response = requests.get("http://127.0.0.1:9880/", timeout=5)
        print("✅ TTS服务正在运行")
        return True
    except:
        print("❌ TTS服务未运行")
        print("请先启动GPT-SoVITS服务:")
        print("cd /mnt/e/CYC/projects/live-selling/GPT-SoVITS && python api_v2.py")
        return False

def check_reference_audio():
    """检查参考音频文件"""
    print("🔍 检查参考音频文件...")
    
    ref_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    if os.path.exists(ref_path):
        print("✅ 参考音频文件存在")
        return True
    else:
        print(f"❌ 参考音频文件不存在: {ref_path}")
        return False

async def test_short_stream():
    """测试短时间直播流"""
    print("🚀 开始短时间直播测试...")
    
    # 配置
    config = StreamConfig(
        output_mode="udp",
        udp_host="localhost",
        udp_port=1234,
        buffer_size=3,  # 小缓冲区用于测试
        max_workers=2
    )
    
    # 创建系统
    system = LiveStreamSystem(config)
    
    # 手动添加一些测试内容到缓冲区
    test_texts = [
        "欢迎来到我们的直播间！",
        "今天有很多优惠活动等着大家！",
        "请点击右下角的小黄车查看商品！"
    ]
    
    print("📝 添加测试文本到缓冲区...")
    for text in test_texts:
        system.stream_buffer.add_text(text)
    
    print("🎬 启动音视频生成...")
    # 启动音视频生成线程
    av_thread = threading.Thread(target=system._audio_video_generation_loop)
    av_thread.daemon = True
    av_thread.start()
    
    # 等待一些视频生成
    print("⏳ 等待视频生成...")
    for i in range(30):  # 等待30秒
        if system.stream_buffer.video_queue.qsize() > 0:
            print(f"✅ 已生成 {system.stream_buffer.video_queue.qsize()} 个视频")
            break
        time.sleep(1)
        if i % 5 == 0:
            print(f"⏳ 等待中... ({i}秒)")
    
    if system.stream_buffer.video_queue.qsize() == 0:
        print("❌ 没有生成任何视频，测试失败")
        system.stop_streaming()
        return False
    
    print("📡 启动UDP推流...")
    print("💡 请在VLC中打开: udp://localhost:1234")
    
    # 启动UDP推流
    stream_thread = threading.Thread(target=system._udp_stream_loop)
    stream_thread.daemon = True
    stream_thread.start()
    
    # 运行30秒
    print("⏰ 推流将运行30秒...")
    for i in range(30):
        time.sleep(1)
        if i % 10 == 0:
            video_count = system.stream_buffer.video_queue.qsize()
            print(f"📊 缓冲区视频数量: {video_count}")
    
    print("🛑 停止测试...")
    system.stop_streaming()
    
    print("✅ 短时间直播测试完成！")
    return True

def create_simple_test_video():
    """创建简单的测试视频用于验证推流"""
    print("🎬 创建简单测试视频...")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=duration=5:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=5",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-pix_fmt", "yuv420p",
        "simple_test.mp4"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 测试视频创建成功")
        return "simple_test.mp4"
    else:
        print(f"❌ 测试视频创建失败: {result.stderr}")
        return None

def test_simple_udp_push():
    """测试简单的UDP推流"""
    print("📡 测试简单UDP推流...")
    
    video_path = create_simple_test_video()
    if not video_path:
        return False
    
    print("🚀 开始推流...")
    print("💡 请在VLC中打开: udp://localhost:1234")
    
    cmd = [
        "ffmpeg", "-y",
        "-re",
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://localhost:1234?pkt_size=1316"
    ]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(7)  # 推流7秒
        process.terminate()
        process.wait()
        
        print("✅ 简单UDP推流测试完成")
        return True
        
    except Exception as e:
        print(f"❌ UDP推流失败: {e}")
        return False
    
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

async def main():
    """主测试函数"""
    print("🚀 直播系统完整测试")
    print("=" * 50)
    
    # 检查前置条件
    if not check_reference_audio():
        return False
    
    print("\n选择测试模式:")
    print("1. 简单UDP推流测试 (不需要TTS)")
    print("2. 完整直播系统测试 (需要TTS服务)")
    
    choice = input("请选择 (1 或 2): ").strip()
    
    if choice == "1":
        success = test_simple_udp_push()
    elif choice == "2":
        if not check_tts_service():
            return False
        success = await test_short_stream()
    else:
        print("❌ 无效选择")
        return False
    
    if success:
        print("\n🎉 测试完成！")
        print("如果在VLC中看到了视频，说明推流正常工作")
    else:
        print("\n❌ 测试失败")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())