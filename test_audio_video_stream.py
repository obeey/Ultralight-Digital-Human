#!/usr/bin/env python3
"""
测试音视频合并推流
"""

import os
import subprocess
import requests
import json
import time

def test_tts_generation():
    """测试TTS生成"""
    print("🎤 测试TTS生成...")
    
    data = {
        "text": "欢迎来到蜜雪冰城直播间，今天有很多优惠活动！",
        "text_lang": "zh",
        "ref_audio_path": "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC",
        "prompt_text": "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后",
        "prompt_lang": "zh",
        "top_k": 5,
        "top_p": 1.0,
        "temperature": 1.0,
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
        "repetition_penalty": 1.35
    }
    
    try:
        response = requests.post("http://127.0.0.1:9880/tts", json=data, timeout=30)
        
        if response.status_code == 200:
            audio_path = "temp/test_audio.wav"
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ TTS生成成功: {audio_path}")
            return audio_path
        else:
            print(f"❌ TTS失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ TTS异常: {e}")
        return None

def test_hubert_extraction(audio_path):
    """测试HuBERT特征提取"""
    print("🤖 测试HuBERT特征提取...")
    
    try:
        cmd = ["python3", "hubert_torch28_fix.py", "--wav", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        hubert_path = audio_path.replace('.wav', '_hu.npy')
        
        if result.returncode == 0 and os.path.exists(hubert_path):
            print(f"✅ HuBERT特征提取成功: {hubert_path}")
            return hubert_path
        else:
            print(f"❌ HuBERT特征提取失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ HuBERT异常: {e}")
        return None

def test_digital_human_inference(hubert_path):
    """测试数字人推理"""
    print("🎬 测试数字人推理...")
    
    try:
        video_path = hubert_path.replace('_hu.npy', '.mp4')
        
        cmd = [
            "python", "inference.py",
            "--asr", "hubert",
            "--dataset", "input/mxbc_0913/",
            "--audio_feat", hubert_path,
            "--checkpoint", "checkpoint/195.pth",
            "--save_path", video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(video_path):
            print(f"✅ 数字人推理成功: {video_path}")
            return video_path
        else:
            print(f"❌ 数字人推理失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 数字人推理异常: {e}")
        return None

def test_audio_video_merge_stream(video_path, audio_path):
    """测试音视频合并推流"""
    print("📡 测试音视频合并推流...")
    
    try:
        print("请在VLC中打开: udp://@:1234")
        input("准备好后按Enter开始推流...")
        
        cmd = [
            "ffmpeg", "-y",
            "-re",  # 实时播放
            "-i", video_path,  # 视频输入
            "-i", audio_path,  # 音频输入
            "-c:v", "libopenh264",
            "-c:a", "libmp3lame",
            "-f", "mpegts",
            "-pix_fmt", "yuv420p",
            "-shortest",  # 以最短的流为准
            "-loglevel", "info",
            "udp://127.0.0.1:1234?pkt_size=1316"
        ]
        
        print("🚀 开始推流...")
        print("📤 执行命令:")
        print(" ".join(cmd))
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ 音视频合并推流成功！")
            return True
        else:
            print(f"❌ 推流失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 推流异常: {e}")
        return False

def analyze_files(video_path, audio_path):
    """分析文件信息"""
    print("\n📋 文件分析:")
    print("=" * 40)
    
    # 分析视频文件
    if os.path.exists(video_path):
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                print(f"📹 视频文件: {video_path}")
                print(f"   流数量: {len(data.get('streams', []))}")
                for i, stream in enumerate(data.get('streams', [])):
                    print(f"   流{i}: {stream.get('codec_type')} ({stream.get('codec_name')})")
            else:
                print(f"❌ 无法分析视频文件: {video_path}")
        except Exception as e:
            print(f"❌ 视频分析异常: {e}")
    
    # 分析音频文件
    if os.path.exists(audio_path):
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", audio_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                print(f"🎵 音频文件: {audio_path}")
                print(f"   流数量: {len(data.get('streams', []))}")
                for i, stream in enumerate(data.get('streams', [])):
                    print(f"   流{i}: {stream.get('codec_type')} ({stream.get('codec_name')})")
            else:
                print(f"❌ 无法分析音频文件: {audio_path}")
        except Exception as e:
            print(f"❌ 音频分析异常: {e}")

def main():
    """主函数"""
    print("🧪 音视频合并推流测试")
    print("=" * 40)
    
    # 确保temp目录存在
    os.makedirs("temp", exist_ok=True)
    
    # 步骤1: 生成TTS音频
    audio_path = test_tts_generation()
    if not audio_path:
        print("❌ TTS生成失败，停止测试")
        return
    
    # 步骤2: 提取HuBERT特征
    hubert_path = test_hubert_extraction(audio_path)
    if not hubert_path:
        print("❌ HuBERT特征提取失败，停止测试")
        return
    
    # 步骤3: 数字人推理
    video_path = test_digital_human_inference(hubert_path)
    if not video_path:
        print("❌ 数字人推理失败，停止测试")
        return
    
    # 步骤4: 分析文件
    analyze_files(video_path, audio_path)
    
    # 步骤5: 测试音视频合并推流
    success = test_audio_video_merge_stream(video_path, audio_path)
    
    print("\n🎉 测试完成！")
    print("=" * 40)
    if success:
        print("✅ 所有测试通过")
        print("💡 如果在VLC中看到了有声音的数字人视频，说明系统正常工作")
    else:
        print("❌ 部分测试失败")
    
    print(f"\n📁 生成的文件:")
    print(f"   音频: {audio_path}")
    print(f"   视频: {video_path}")
    print(f"   特征: {hubert_path}")

if __name__ == "__main__":
    main()