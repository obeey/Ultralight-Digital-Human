#!/usr/bin/env python3
"""
持续推流测试 - 不停推送测试音视频
"""

import os
import subprocess
import time
import threading
import signal
import sys

class ContinuousStreamer:
    def __init__(self):
        self.streaming = False
        self.process = None
        
    def create_test_content(self):
        """创建测试音视频内容"""
        print("🎬 创建测试音视频内容...")
        
        # 创建测试音频 (5秒，440Hz正弦波)
        audio_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=5",
            "-ar", "44100",
            "-ac", "1",
            "temp/test_audio_loop.wav"
        ]
        
        # 创建测试视频 (5秒，彩色条纹 + 时间戳)
        video_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "testsrc2=duration=5:size=1280x720:rate=25",
            "-vf", "drawtext=text='测试推流':fontcolor=white:fontsize=48:x=50:y=50",
            "-c:v", "libopenh264",
            "-pix_fmt", "yuv420p",
            "temp/test_video_loop.mp4"
        ]
        
        try:
            # 生成音频
            result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"❌ 音频生成失败: {result.stderr}")
                return False
            
            # 生成视频
            result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"❌ 视频生成失败: {result.stderr}")
                return False
            
            print("✅ 测试音视频内容创建成功")
            return True
            
        except Exception as e:
            print(f"❌ 创建测试内容异常: {e}")
            return False
    
    def start_continuous_stream(self):
        """开始持续推流"""
        print("🚀 开始持续推流测试...")
        print("📺 请在VLC中打开: udp://@:1234")
        print("💡 VLC设置:")
        print("   1. 打开VLC")
        print("   2. 媒体 -> 打开网络串流")
        print("   3. 输入: udp://@:1234")
        print("   4. 点击播放")
        print("⏰ 推流将每5秒循环一次，按Ctrl+C停止")
        print("-" * 50)
        
        self.streaming = True
        
        # 使用FFmpeg循环推流
        cmd = [
            "ffmpeg",
            "-re",  # 实时播放
            "-stream_loop", "-1",  # 无限循环
            "-i", "temp/test_video_loop.mp4",  # 视频输入
            "-stream_loop", "-1",  # 无限循环
            "-i", "temp/test_audio_loop.wav",  # 音频输入
            "-c:v", "libopenh264",  # 使用可用的H.264编码器
            "-b:v", "2000k",        # 视频比特率
            "-maxrate", "2500k",    # 最大比特率
            "-bufsize", "5000k",    # 缓冲区大小
            "-g", "50",             # GOP大小 (关键帧间隔)
            "-r", "25",             # 帧率
            "-c:a", "libmp3lame",   # 使用MP3音频编码
            "-b:a", "128k",         # 音频比特率
            "-ar", "44100",         # 音频采样率
            "-f", "mpegts",         # 输出格式
            "-pix_fmt", "yuv420p",  # 像素格式
            "-shortest",            # 以最短流为准
            "-loglevel", "info",    # 日志级别
            "udp://172.18.0.1:1234?pkt_size=1316"  # UDP输出
        ]
        
        try:
            print("📤 执行推流命令:")
            print(" ".join(cmd))
            print("-" * 50)
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 实时显示FFmpeg输出
            for line in iter(self.process.stdout.readline, ''):
                if not self.streaming:
                    break
                print(f"FFmpeg: {line.strip()}")
            
        except Exception as e:
            print(f"❌ 推流异常: {e}")
        finally:
            self.stop_stream()
    
    def stop_stream(self):
        """停止推流"""
        print("\n🛑 停止推流...")
        self.streaming = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"⚠️ 停止进程异常: {e}")
        
        print("✅ 推流已停止")

def signal_handler(signum, frame):
    """信号处理器"""
    print("\n收到停止信号...")
    streamer.stop_stream()
    sys.exit(0)

def test_network_connectivity():
    """测试网络连通性"""
    print("🔍 测试网络连通性...")
    
    # 测试本地UDP端口
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 1234))
        sock.close()
        print("✅ UDP端口1234可用")
        return True
    except Exception as e:
        print(f"❌ UDP端口1234不可用: {e}")
        return False

def main():
    """主函数"""
    global streamer
    
    print("🧪 持续推流测试")
    print("=" * 50)
    
    # 确保temp目录存在
    os.makedirs("temp", exist_ok=True)
    
    # 测试网络
    if not test_network_connectivity():
        print("❌ 网络测试失败，请检查网络配置")
        return
    
    # 创建推流器
    streamer = ContinuousStreamer()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建测试内容
    if not streamer.create_test_content():
        print("❌ 创建测试内容失败")
        return
    
    print("\n准备开始推流测试...")
    input("按Enter键开始推流...")
    
    # 开始持续推流
    try:
        streamer.start_continuous_stream()
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        streamer.stop_stream()
        print("测试结束")

if __name__ == "__main__":
    main()