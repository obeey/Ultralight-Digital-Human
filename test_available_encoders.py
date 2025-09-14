#!/usr/bin/env python3
"""
测试可用的编码器并保存合并文件
"""

import subprocess
import os

def test_with_available_encoders():
    """使用可用的编码器测试"""
    
    # 查找文件
    if not os.path.exists("temp"):
        print("❌ temp目录不存在")
        return
    
    files = os.listdir("temp")
    audio_files = [f for f in files if f.endswith('.wav') and 'audio_' in f]
    video_files = [f for f in files if f.endswith('.mp4') and 'audio_' in f]
    
    if not audio_files or not video_files:
        print("❌ 没有找到音频或视频文件")
        return
    
    latest_audio = max([os.path.join("temp", f) for f in audio_files], key=os.path.getmtime)
    latest_video = max([os.path.join("temp", f) for f in video_files], key=os.path.getmtime)
    
    print(f"🎵 音频文件: {latest_audio}")
    print(f"📹 视频文件: {latest_video}")
    
    # 测试1: 使用libopenh264 + libmp3lame保存文件
    print("\n🧪 测试1: 保存为MP4文件 (libopenh264 + libmp3lame)")
    output_file1 = "temp/test_merged_h264.mp4"
    
    cmd1 = [
        "ffmpeg", "-y",
        "-i", latest_video,
        "-i", latest_audio,
        "-c:v", "libopenh264",  # 使用可用的H.264编码器
        "-c:a", "libmp3lame",   # 使用MP3音频编码
        "-b:v", "2000k",
        "-b:a", "128k",
        "-ar", "32000",
        "-ac", "1",
        "-shortest",
        output_file1
    ]
    
    try:
        result1 = subprocess.run(cmd1, capture_output=True, text=True)
        if result1.returncode == 0:
            print("✅ MP4文件保存成功!")
            print(f"📁 文件位置: {output_file1}")
            
            # 检查文件信息
            cmd_check = ["ffprobe", "-v", "quiet", "-show_streams", output_file1]
            result_check = subprocess.run(cmd_check, capture_output=True, text=True)
            print("文件流信息:")
            print(result_check.stdout)
            
        else:
            print("❌ MP4文件保存失败")
            print(result1.stderr)
    except Exception as e:
        print(f"保存异常: {e}")
    
    # 测试2: 直接用VLC播放保存的文件
    if os.path.exists(output_file1):
        print(f"\n🎬 请用VLC直接播放文件: {output_file1}")
        print("检查是否有音频和视频")
        input("播放完成后按Enter继续...")
    
    # 测试3: 使用TCP推流而不是UDP
    print("\n🧪 测试3: TCP推流 (端口8554)")
    print("📺 VLC设置: tcp://172.18.0.1:8554")
    
    if input("准备好VLC TCP连接后按y继续: ").lower() == 'y':
        cmd_tcp = [
            "ffmpeg", "-y",
            "-re",
            "-i", latest_video,
            "-i", latest_audio,
            "-c:v", "libopenh264",
            "-b:v", "1500k",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            "-ar", "32000",
            "-ac", "1",
            "-f", "mpegts",
            "-shortest",
            "tcp://172.18.0.1:8554?listen=1"  # TCP监听模式
        ]
        
        try:
            print("🚀 开始TCP推流...")
            result_tcp = subprocess.run(cmd_tcp, timeout=20)
        except Exception as e:
            print(f"TCP推流异常: {e}")
    
    # 测试4: 检查VLC是否能接收UDP音频
    print("\n🧪 测试4: 单独推流音频测试")
    print("📺 VLC设置: udp://@172.18.0.1:1236")
    
    if input("准备好VLC音频测试后按y继续: ").lower() == 'y':
        cmd_audio_only = [
            "ffmpeg", "-y",
            "-re",
            "-i", latest_audio,
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            "-ar", "32000",
            "-ac", "1",
            "-f", "mp3",
            "udp://172.18.0.1:1236"
        ]
        
        try:
            print("🚀 开始音频推流...")
            result_audio = subprocess.run(cmd_audio_only, timeout=15)
        except Exception as e:
            print(f"音频推流异常: {e}")

if __name__ == "__main__":
    test_with_available_encoders()