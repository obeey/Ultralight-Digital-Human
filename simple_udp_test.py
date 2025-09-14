#!/usr/bin/env python3
"""
简单UDP推流测试 - 排查VLC接收问题
"""

import subprocess
import time
import os

def test_simple_stream():
    """测试最简单的UDP推流"""
    print("🧪 简单UDP推流测试")
    print("=" * 40)
    
    # 确保temp目录存在
    os.makedirs("temp", exist_ok=True)
    
    print("📺 请在VLC中设置:")
    print("   1. 打开VLC")
    print("   2. 媒体 -> 打开网络串流")
    print("   3. 输入: udp://@:1234")
    print("   4. 点击播放")
    print("   5. 如果没有画面，尝试: udp://127.0.0.1:1234")
    print("   6. 或者尝试: udp://localhost:1234")
    
    input("\n准备好后按Enter开始推流...")
    
    # 方法1: 直接推流彩色测试图案
    print("\n🎬 方法1: 推流彩色测试图案...")
    cmd1 = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=size=640x480:rate=25",
        "-t", "30",  # 30秒
        "-c:v", "libopenh264",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://127.0.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("📤 执行命令:")
        print(" ".join(cmd1))
        print("⏰ 推流30秒...")
        
        result = subprocess.run(cmd1, capture_output=True, text=True, timeout=35)
        
        if result.returncode == 0:
            print("✅ 方法1推流成功")
        else:
            print(f"❌ 方法1推流失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 方法1异常: {e}")
    
    print("\n" + "="*40)
    input("按Enter继续测试方法2...")
    
    # 方法2: 推流带音频的测试
    print("\n🎵 方法2: 推流带音频的彩色图案...")
    cmd2 = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=size=640x480:rate=25",
        "-f", "lavfi", 
        "-i", "sine=frequency=440:duration=30",
        "-t", "30",  # 30秒
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://127.0.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("📤 执行命令:")
        print(" ".join(cmd2))
        print("⏰ 推流30秒...")
        
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=35)
        
        if result.returncode == 0:
            print("✅ 方法2推流成功")
        else:
            print(f"❌ 方法2推流失败: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 方法2异常: {e}")
    
    print("\n" + "="*40)
    input("按Enter继续测试方法3...")
    
    # 方法3: 使用不同的UDP地址
    print("\n🌐 方法3: 测试不同UDP地址...")
    addresses = [
        "udp://127.0.0.1:1234",
        "udp://localhost:1234", 
        "udp://0.0.0.0:1234"
    ]
    
    for addr in addresses:
        print(f"\n📡 测试地址: {addr}")
        print(f"💡 VLC中使用: {addr.replace('127.0.0.1', '@').replace('localhost', '@').replace('0.0.0.0', '@')}")
        
        cmd3 = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc2=size=640x480:rate=25",
            "-t", "10",  # 10秒
            "-c:v", "libopenh264",
            "-f", "mpegts",
            "-pix_fmt", "yuv420p",
            f"{addr}?pkt_size=1316"
        ]
        
        try:
            result = subprocess.run(cmd3, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print(f"✅ {addr} 推流成功")
            else:
                print(f"❌ {addr} 推流失败")
                
        except Exception as e:
            print(f"❌ {addr} 异常: {e}")
        
        time.sleep(2)
    
    print("\n🎉 测试完成!")
    print("💡 如果VLC仍然看不到视频，请检查:")
    print("   1. VLC版本是否支持UDP流")
    print("   2. 防火墙是否阻止UDP端口1234")
    print("   3. 尝试使用其他播放器(如ffplay)")
    print("   4. 检查网络接口配置")

def test_with_ffplay():
    """使用ffplay测试UDP接收"""
    print("\n🎮 使用ffplay测试UDP接收...")
    print("💡 这将在Linux中直接播放UDP流")
    
    if input("是否测试ffplay? (y/n): ").lower() == 'y':
        # 启动推流
        print("🚀 启动推流...")
        cmd_stream = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc2=size=640x480:rate=25",
            "-f", "lavfi", 
            "-i", "sine=frequency=440:duration=60",
            "-c:v", "libopenh264",
            "-c:a", "libmp3lame",
            "-f", "mpegts",
            "-pix_fmt", "yuv420p",
            "udp://127.0.0.1:1234?pkt_size=1316"
        ]
        
        # 启动接收
        cmd_play = [
            "ffplay", "-i", "udp://127.0.0.1:1234"
        ]
        
        print("📤 推流命令:", " ".join(cmd_stream))
        print("📺 播放命令:", " ".join(cmd_play))
        print("⏰ 将同时启动推流和播放...")
        
        try:
            # 启动推流进程
            stream_proc = subprocess.Popen(cmd_stream)
            time.sleep(2)  # 等待推流启动
            
            # 启动播放进程
            play_proc = subprocess.Popen(cmd_play)
            
            print("✅ 推流和播放已启动")
            print("💡 如果看到视频窗口，说明UDP推流正常")
            print("⏰ 测试将运行30秒...")
            
            time.sleep(30)
            
            # 停止进程
            play_proc.terminate()
            stream_proc.terminate()
            
            print("✅ ffplay测试完成")
            
        except Exception as e:
            print(f"❌ ffplay测试异常: {e}")

if __name__ == "__main__":
    test_simple_stream()
    test_with_ffplay()