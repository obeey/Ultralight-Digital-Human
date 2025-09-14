#!/usr/bin/env python3
"""
调试音视频生成过程
逐步检查TTS和视频生成
"""

import os
import sys
import requests
import subprocess
import time

def test_tts_generation():
    """测试TTS生成"""
    print("🔍 测试TTS生成...")
    
    api_url = "http://127.0.0.1:9880"
    ref_audio_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    
    # 检查参考音频
    if not os.path.exists(ref_audio_path):
        print(f"❌ 参考音频不存在: {ref_audio_path}")
        return None
    
    request_data = {
        "text": "这是一个测试文本，用于检查TTS生成是否正常。",
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
        print("📤 发送TTS请求...")
        response = requests.post(f"{api_url}/tts", json=request_data, timeout=60)
        
        if response.status_code == 200:
            audio_path = "temp/debug_audio.wav"
            os.makedirs("temp", exist_ok=True)
            
            with open(audio_path, "wb") as f:
                f.write(response.content)
            
            size = len(response.content)
            print(f"✅ TTS生成成功: {audio_path} ({size} 字节)")
            return audio_path
        else:
            print(f"❌ TTS失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ TTS异常: {e}")
        return None

def test_video_generation(audio_path):
    """测试视频生成"""
    print("🎬 测试视频生成...")
    
    if not os.path.exists(audio_path):
        print(f"❌ 音频文件不存在: {audio_path}")
        return None
    
    # 获取音频时长
    try:
        probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
        duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(duration_result.stdout.strip())
        print(f"📊 音频时长: {duration:.2f}秒")
    except:
        duration = 3.0
        print("⚠️ 无法获取音频时长，使用默认3秒")
    
    # 生成视频
    video_path = "temp/debug_video.mp4"
    text = "调试测试视频"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1280x720:d={duration}",
        "-i", audio_path,
        "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-shortest",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    
    print("📤 执行视频生成命令:")
    print(" ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(video_path):
                size = os.path.getsize(video_path)
                print(f"✅ 视频生成成功: {video_path} ({size} 字节)")
                return video_path
            else:
                print("❌ 视频文件未生成")
                return None
        else:
            print(f"❌ 视频生成失败:")
            print(f"stderr: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 视频生成异常: {e}")
        return None

def check_files():
    """检查生成的文件"""
    print("📋 检查生成的文件...")
    
    if os.path.exists("temp"):
        files = os.listdir("temp")
        if files:
            print("📁 temp目录中的文件:")
            for file in sorted(files):
                file_path = os.path.join("temp", file)
                size = os.path.getsize(file_path)
                print(f"   {file} ({size} 字节)")
        else:
            print("📁 temp目录为空")
    else:
        print("📁 temp目录不存在")

def main():
    """主函数"""
    print("🚀 调试音视频生成过程")
    print("=" * 40)
    
    # 创建temp目录
    os.makedirs("temp", exist_ok=True)
    
    # 1. 测试TTS
    audio_path = test_tts_generation()
    if not audio_path:
        print("❌ TTS测试失败，停止测试")
        return False
    
    # 2. 测试视频生成
    video_path = test_video_generation(audio_path)
    if not video_path:
        print("❌ 视频生成测试失败")
        return False
    
    # 3. 检查文件
    check_files()
    
    print("\n🎉 调试测试完成！")
    print("请检查temp目录中的文件:")
    print("- debug_audio.wav: TTS生成的音频")
    print("- debug_video.mp4: 最终生成的视频")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)