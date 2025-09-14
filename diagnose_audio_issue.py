#!/usr/bin/env python3
"""
诊断音频问题的详细脚本
"""

import subprocess
import os
import time

def diagnose_audio_issue():
    """诊断音频问题"""
    
    print("🔍 诊断音频问题")
    print("=" * 50)
    
    # 1. 检查文件
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
    
    # 2. 详细检查音频文件
    print("\n🔍 详细检查音频文件...")
    cmd_audio = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", latest_audio]
    try:
        result = subprocess.run(cmd_audio, capture_output=True, text=True)
        print("音频流信息:")
        print(result.stdout)
    except Exception as e:
        print(f"检查音频失败: {e}")
    
    # 3. 详细检查视频文件
    print("\n🔍 详细检查视频文件...")
    cmd_video = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", latest_video]
    try:
        result = subprocess.run(cmd_video, capture_output=True, text=True)
        print("视频流信息:")
        print(result.stdout)
    except Exception as e:
        print(f"检查视频失败: {e}")
    
    # 4. 测试不同的推流方案
    print("\n🧪 测试方案1: 标准UDP推流")
    test_standard_udp(latest_video, latest_audio)
    
    print("\n🧪 测试方案2: 较小的UDP包")
    test_small_udp_packets(latest_video, latest_audio)
    
    print("\n🧪 测试方案3: 保存到文件验证")
    test_save_to_file(latest_video, latest_audio)

def test_standard_udp(video_path, audio_path):
    """测试标准UDP推流"""
    print("📺 VLC设置: udp://@172.18.0.1:1234")
    
    if input("准备好VLC后按y继续: ").lower() != 'y':
        return
    
    cmd = [
        "ffmpeg", "-y", "-v", "verbose",  # 增加详细输出
        "-re",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libopenh264",
        "-b:v", "1500k",  # 降低比特率
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        "-ar", "32000",
        "-ac", "1",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("🚀 开始标准UDP推流...")
        result = subprocess.run(cmd, timeout=15, capture_output=True, text=True)
        print("推流输出:")
        print(result.stderr[-1000:])  # 显示最后1000字符
    except Exception as e:
        print(f"推流异常: {e}")

def test_small_udp_packets(video_path, audio_path):
    """测试较小的UDP包"""
    print("📺 VLC设置: udp://@172.18.0.1:1235")
    
    if input("准备好VLC端口1235后按y继续: ").lower() != 'y':
        return
    
    cmd = [
        "ffmpeg", "-y",
        "-re",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libopenh264",
        "-b:v", "1000k",  # 更低比特率
        "-c:a", "libmp3lame",
        "-b:a", "64k",    # 更低音频比特率
        "-ar", "32000",
        "-ac", "1",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "udp://172.18.0.1:1235?pkt_size=512"  # 更小的包
    ]
    
    try:
        print("🚀 开始小包UDP推流...")
        result = subprocess.run(cmd, timeout=15)
    except Exception as e:
        print(f"推流异常: {e}")

def test_save_to_file(video_path, audio_path):
    """保存到文件验证音视频合并"""
    output_file = "temp/test_merged.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",  # 使用标准H.264编码器
        "-c:a", "aac",      # 使用AAC音频编码
        "-b:v", "2000k",
        "-b:a", "128k",
        "-ar", "32000",
        "-ac", "1",
        "-shortest",
        output_file
    ]
    
    try:
        print("💾 保存合并文件到temp/test_merged.mp4...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 文件保存成功!")
            print("🎬 请用播放器打开temp/test_merged.mp4检查音视频是否正常")
            
            # 检查输出文件信息
            cmd_check = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", output_file]
            result_check = subprocess.run(cmd_check, capture_output=True, text=True)
            print("合并文件流信息:")
            print(result_check.stdout)
        else:
            print("❌ 文件保存失败")
            print(result.stderr)
            
    except Exception as e:
        print(f"保存异常: {e}")

if __name__ == "__main__":
    diagnose_audio_issue()