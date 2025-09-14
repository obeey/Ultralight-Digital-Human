#!/usr/bin/env python3
"""
测试修复后的音频推流
"""

import subprocess
import os

def test_audio_video_stream():
    """测试音视频合并推流"""
    
    # 查找最新的音频和视频文件
    if not os.path.exists("temp"):
        print("❌ temp目录不存在")
        return
    
    files = os.listdir("temp")
    audio_files = [f for f in files if f.endswith('.wav') and 'audio_' in f]
    video_files = [f for f in files if f.endswith('.mp4') and 'audio_' in f]
    
    if not audio_files or not video_files:
        print("❌ 没有找到音频或视频文件")
        print(f"音频文件: {audio_files}")
        print(f"视频文件: {video_files}")
        return
    
    # 使用最新的文件
    latest_audio = max([os.path.join("temp", f) for f in audio_files], key=os.path.getmtime)
    latest_video = max([os.path.join("temp", f) for f in video_files], key=os.path.getmtime)
    
    print(f"🎵 音频文件: {latest_audio}")
    print(f"📹 视频文件: {latest_video}")
    
    # 检查音频文件信息
    print("\n🔍 检查音频文件信息...")
    cmd_info = ["ffmpeg", "-i", latest_audio]
    result = subprocess.run(cmd_info, capture_output=True, text=True)
    print("音频信息:")
    print(result.stderr)
    
    print("\n📺 请在VLC中打开: udp://@172.18.0.1:1234")
    input("准备好后按Enter开始推流...")
    
    # 修复后的推流命令
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", latest_video,  # 视频输入
        "-i", latest_audio,  # 音频输入
        "-c:v", "libopenh264",  # 重新编码MJPEG为H.264
        "-b:v", "2000k",        # 视频比特率
        "-maxrate", "2500k",    # 最大比特率
        "-bufsize", "5000k",    # 缓冲区大小
        "-g", "50",             # GOP大小
        "-r", "25",             # 帧率
        "-c:a", "libmp3lame",   # 音频编码
        "-b:a", "128k",         # 音频比特率
        "-ar", "32000",         # 音频采样率匹配源文件
        "-ac", "1",             # 单声道
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-shortest",  # 以最短的流为准
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("🚀 开始音视频合并推流...")
        print("命令:", " ".join(cmd))
        result = subprocess.run(cmd, timeout=30)
        
        if result.returncode == 0:
            print("✅ 推流成功!")
        else:
            print("❌ 推流失败")
            
    except subprocess.TimeoutExpired:
        print("⏰ 推流超时")
    except Exception as e:
        print(f"❌ 推流异常: {e}")

if __name__ == "__main__":
    test_audio_video_stream()