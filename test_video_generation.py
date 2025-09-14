#!/usr/bin/env python3
"""
测试视频生成修复
"""

import subprocess
import os
import time

def test_video_generation():
    """测试视频生成"""
    print("🎬 测试视频生成...")
    
    # 创建测试音频文件
    audio_path = "test_audio.wav"
    video_path = "test_video.mp4"
    
    # 生成测试音频（1秒的静音）
    audio_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=mono:sample_rate=32000",
        "-t", "3",
        audio_path
    ]
    
    print("📢 生成测试音频...")
    result = subprocess.run(audio_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 测试音频生成失败: {result.stderr}")
        return False
    
    print("✅ 测试音频生成成功")
    
    # 测试视频生成
    text = "测试文本内容"
    duration = 3.0
    
    video_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1920x1080:d={duration}",
        "-i", audio_path,
        "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-shortest",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    
    print("🎬 生成测试视频...")
    result = subprocess.run(video_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 视频生成成功！")
        if os.path.exists(video_path):
            size = os.path.getsize(video_path)
            print(f"📊 视频文件大小: {size} 字节")
        return True
    else:
        print(f"❌ 视频生成失败: {result.stderr}")
        
        # 尝试备用方法
        print("🔄 尝试备用方法...")
        backup_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s=1920x1080:d={duration}",
            "-i", audio_path,
            "-c:v", "mpeg4",
            "-c:a", "libmp3lame",
            "-shortest",
            "-pix_fmt", "yuv420p",
            video_path
        ]
        
        result2 = subprocess.run(backup_cmd, capture_output=True, text=True)
        if result2.returncode == 0:
            print("✅ 备用方法成功！")
            return True
        else:
            print(f"❌ 备用方法也失败: {result2.stderr}")
            return False

def cleanup():
    """清理测试文件"""
    for file in ["test_audio.wav", "test_video.mp4"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 清理文件: {file}")

if __name__ == "__main__":
    try:
        success = test_video_generation()
        if success:
            print("\n🎉 视频生成测试通过！")
        else:
            print("\n❌ 视频生成测试失败")
    finally:
        cleanup()