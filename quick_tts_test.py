#!/usr/bin/env python3
"""
快速TTS测试脚本
"""

import requests
import json

def test_tts():
    """测试TTS请求"""
    api_url = "http://127.0.0.1:9880"
    ref_audio_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    
    request_data = {
        "text": "欢迎来到我们的直播间，今天有很多优惠活动！",
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
        print("发送TTS请求...")
        response = requests.post(f"{api_url}/tts", json=request_data, timeout=60)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            with open("test_audio.wav", "wb") as f:
                f.write(response.content)
            print("✅ TTS成功！音频已保存为 test_audio.wav")
        else:
            print(f"❌ TTS失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_tts()