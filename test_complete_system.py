#!/usr/bin/env python3
"""
完整系统测试脚本
测试TTS + 视频生成的完整流程
"""

import os
import sys
import requests
import subprocess
import time

def test_tts_service():
    """测试TTS服务"""
    print("🔍 测试TTS服务...")
    
    api_url = "http://127.0.0.1:9880"
    ref_audio_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    
    # 检查参考音频文件
    if not os.path.exists(ref_audio_path):
        print(f"❌ 参考音频文件不存在: {ref_audio_path}")
        return False
    
    # 测试TTS请求
    request_data = {
        "text": "这是一个完整的系统测试，验证TTS和视频生成功能。",
        "text_lang": "zh",
        "ref_audio_path": ref_audio_path,
        "aux_ref_audio_paths": [],
        "prompt_lang": "zh",
        "prompt_text": "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后",
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "speed_factor": 1.0,
        "fragment_interval": 0.3,
        "seed": -1,
        "media_type": "wav",
        "streaming_mode": False,
        "parallel_infer": True,
        "repetition_penalty": 1.35,
        "sample_steps": 32,
        "super_sampling": False
    }
    
    try:
        response = requests.post(f"{api_url}/tts", json=request_data, timeout=60)
        
        if response.status_code == 200:
            audio_path = "system_test_audio.wav"
            with open(audio_path, "wb") as f:
                f.write(response.content)
            print(f"✅ TTS生成成功: {audio_path}")
            return audio_path
        else:
            print(f"❌ TTS失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ TTS请求异常: {e}")
        return False

def test_video_generation(audio_path):
    """测试视频生成"""
    print("🎬 测试视频生成...")
    
    if not os.path.exists(audio_path):
        print(f"❌ 音频文件不存在: {audio_path}")
        return False
    
    # 获取音频时长
    try:
        probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
        duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(duration_result.stdout.strip())
        print(f"📊 音频时长: {duration:.2f}秒")
    except:
        duration = 5.0
        print("⚠️ 无法获取音频时长，使用默认5秒")
    
    # 生成视频
    video_path = "system_test_video.mp4"
    text = "系统测试视频"
    
    cmd = [
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
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ 视频生成成功: {video_path}")
        if os.path.exists(video_path):
            size = os.path.getsize(video_path)
            print(f"📊 视频文件大小: {size} 字节")
        return video_path
    else:
        print(f"❌ 视频生成失败: {result.stderr}")
        return False

def cleanup_test_files():
    """清理测试文件"""
    test_files = ["system_test_audio.wav", "system_test_video.mp4"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 清理文件: {file}")

def main():
    """主测试函数"""
    print("🚀 完整系统测试")
    print("=" * 40)
    
    try:
        # 1. 测试TTS
        audio_path = test_tts_service()
        if not audio_path:
            print("❌ TTS测试失败，停止测试")
            return False
        
        # 2. 测试视频生成
        video_path = test_video_generation(audio_path)
        if not video_path:
            print("❌ 视频生成测试失败")
            return False
        
        print("\n🎉 完整系统测试通过！")
        print("✅ TTS生成正常")
        print("✅ 视频生成正常")
        print("✅ 系统可以正常运行")
        
        return True
        
    except Exception as e:
        print(f"❌ 系统测试异常: {e}")
        return False
    
    finally:
        cleanup_test_files()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)