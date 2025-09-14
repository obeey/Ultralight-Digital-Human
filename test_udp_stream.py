#!/usr/bin/env python3
"""
测试UDP推流
创建一个简单的测试视频并通过UDP推流
"""

import subprocess
import time
import os
import threading

def create_test_video():
    """创建测试视频"""
    print("🎬 创建测试视频...")
    
    # 创建一个10秒的测试视频，带有时间戳
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=duration=10:size=1280x720:rate=30",
        "-f", "lavfi", 
        "-i", "sine=frequency=1000:duration=10",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-pix_fmt", "yuv420p",
        "test_video.mp4"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 测试视频创建成功")
        return "test_video.mp4"
    else:
        print(f"❌ 测试视频创建失败: {result.stderr}")
        return None

def test_udp_stream_simple():
    """测试简单的UDP推流"""
    print("📡 测试简单UDP推流...")
    
    video_path = create_test_video()
    if not video_path:
        return False
    
    # 简单的UDP推流命令
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://localhost:1234?pkt_size=1316"
    ]
    
    print("🚀 开始UDP推流...")
    print("💡 请在VLC中打开: udp://localhost:1234")
    print("⏰ 推流将持续10秒...")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待10秒
        time.sleep(12)
        
        # 终止进程
        process.terminate()
        process.wait()
        
        print("✅ UDP推流测试完成")
        return True
        
    except Exception as e:
        print(f"❌ UDP推流失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        if os.path.exists(video_path):
            os.remove(video_path)

def test_udp_stream_loop():
    """测试循环UDP推流"""
    print("🔄 测试循环UDP推流...")
    
    video_path = create_test_video()
    if not video_path:
        return False
    
    # 循环推流命令
    cmd = [
        "ffmpeg", "-y",
        "-re",
        "-stream_loop", "-1",  # 无限循环
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://localhost:1234?pkt_size=1316"
    ]
    
    print("🚀 开始循环UDP推流...")
    print("💡 请在VLC中打开: udp://localhost:1234")
    print("⏰ 推流将循环播放，按Ctrl+C停止...")
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待用户中断
        while True:
            time.sleep(1)
            if process.poll() is not None:
                break
        
    except KeyboardInterrupt:
        print("\n🛑 用户停止推流")
        process.terminate()
        process.wait()
        
    except Exception as e:
        print(f"❌ 循环推流失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        if os.path.exists(video_path):
            os.remove(video_path)
    
    return True

def main():
    """主函数"""
    print("🚀 UDP推流测试")
    print("=" * 40)
    
    print("选择测试模式:")
    print("1. 简单推流测试 (10秒)")
    print("2. 循环推流测试 (持续)")
    
    choice = input("请选择 (1 或 2): ").strip()
    
    if choice == "1":
        success = test_udp_stream_simple()
    elif choice == "2":
        success = test_udp_stream_loop()
    else:
        print("❌ 无效选择")
        return False
    
    if success:
        print("🎉 UDP推流测试完成！")
    else:
        print("❌ UDP推流测试失败")
    
    return success

if __name__ == "__main__":
    main()