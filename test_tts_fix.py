#!/usr/bin/env python3
"""
测试TTS修复脚本
用于验证GPT-SoVITS TTS API调用是否正常工作
"""

import os
import sys
import requests
import json
import time

def test_tts_connection():
    """测试TTS服务连接"""
    api_url = "http://127.0.0.1:9880"
    
    print("🔍 测试TTS服务连接...")
    
    try:
        # 测试服务是否运行
        response = requests.get(f"{api_url}/", timeout=5)
        print("✅ TTS服务正在运行")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ TTS服务未运行，请先启动GPT-SoVITS API服务")
        print("启动命令: cd /mnt/e/CYC/projects/live-selling/GPT-SoVITS && python api_v2.py")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def find_reference_audio():
    """查找参考音频文件"""
    ref_audio_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    
    print("🔍 检查参考音频文件...")
    
    if os.path.exists(ref_audio_path):
        print(f"✅ 找到参考音频: {ref_audio_path}")
        return ref_audio_path
    else:
        print(f"❌ 参考音频文件不存在: {ref_audio_path}")
        return None

def test_tts_request(ref_audio_path):
    """测试TTS请求"""
    api_url = "http://127.0.0.1:9880"
    
    print("🔍 测试TTS请求...")
    
    # 按照修复后的格式发送请求
    request_data = {
        "text": "这是一个测试文本，用于验证TTS功能是否正常工作。",
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
    
    print("📤 发送TTS请求...")
    print(f"请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{api_url}/tts",
            json=request_data,
            timeout=60
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 保存测试音频
            output_path = "test_output.wav"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ TTS请求成功！音频已保存到: {output_path}")
            print(f"📊 音频文件大小: {len(response.content)} 字节")
            return True
        else:
            print(f"❌ TTS请求失败")
            print(f"错误响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ TTS请求异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 GPT-SoVITS TTS修复测试")
    print("=" * 40)
    
    # 1. 测试服务连接
    if not test_tts_connection():
        return False
    
    # 2. 查找参考音频
    ref_audio_path = find_reference_audio()
    if not ref_audio_path:
        return False
    
    # 3. 测试TTS请求
    if not test_tts_request(ref_audio_path):
        return False
    
    print("\n🎉 所有测试通过！TTS修复成功！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)