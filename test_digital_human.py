#!/usr/bin/env python3
"""
测试数字人系统
"""

import os
import sys
import time
import subprocess
from digital_human_system import DigitalHumanConfig, TTSClient, DigitalHumanGenerator

def test_prerequisites():
    """测试前置条件"""
    print("🔍 检查前置条件...")
    
    config = DigitalHumanConfig()
    issues = []
    
    # 检查数据集目录
    if not os.path.exists(config.dataset_dir):
        issues.append(f"数据集目录不存在: {config.dataset_dir}")
    else:
        print(f"✅ 数据集目录存在: {config.dataset_dir}")
    
    # 检查模型检查点
    if not os.path.exists(config.checkpoint_path):
        issues.append(f"模型检查点不存在: {config.checkpoint_path}")
    else:
        print(f"✅ 模型检查点存在: {config.checkpoint_path}")
    
    # 检查HuBERT脚本
    if not os.path.exists("data_utils/hubert.py"):
        issues.append("HuBERT脚本不存在: data_utils/hubert.py")
    else:
        print("✅ HuBERT脚本存在")
    
    # 检查推理脚本
    if not os.path.exists("inference.py"):
        issues.append("推理脚本不存在: inference.py")
    else:
        print("✅ 推理脚本存在")
    
    # 检查参考音频
    ref_audio = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    if not os.path.exists(ref_audio):
        issues.append(f"参考音频不存在: {ref_audio}")
    else:
        print("✅ 参考音频存在")
    
    if issues:
        print("\n❌ 发现问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("\n✅ 所有前置条件检查通过")
    return True

def test_tts():
    """测试TTS生成"""
    print("\n🎤 测试TTS生成...")
    
    config = DigitalHumanConfig()
    tts_client = TTSClient(config)
    
    test_text = "欢迎来到蜜雪冰城直播间，今天有很多优惠活动"
    
    try:
        audio_path = tts_client.generate_audio(test_text)
        
        if audio_path and os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            print(f"✅ TTS生成成功: {audio_path} ({size} 字节)")
            return audio_path
        else:
            print("❌ TTS生成失败")
            return None
            
    except Exception as e:
        print(f"❌ TTS测试异常: {e}")
        return None

def test_digital_human_generation(audio_path):
    """测试数字人视频生成"""
    print("\n🤖 测试数字人视频生成...")
    
    if not audio_path:
        print("❌ 没有音频文件，跳过测试")
        return None
    
    config = DigitalHumanConfig()
    generator = DigitalHumanGenerator(config)
    
    try:
        video_path = generator.generate_video(audio_path, "测试文本")
        
        if video_path and os.path.exists(video_path):
            size = os.path.getsize(video_path)
            print(f"✅ 数字人视频生成成功: {video_path} ({size} 字节)")
            return video_path
        else:
            print("❌ 数字人视频生成失败")
            return None
            
    except Exception as e:
        print(f"❌ 数字人视频生成异常: {e}")
        return None

def test_udp_stream(video_path):
    """测试UDP推流"""
    print("\n📡 测试UDP推流...")
    
    if not video_path:
        print("❌ 没有视频文件，跳过测试")
        return False
    
    try:
        print("🚀 开始推流测试...")
        print("💡 请在VLC中打开: udp://@:1234")
        
        cmd = [
            "ffmpeg", "-y",
            "-re",  # 实时播放
            "-i", video_path,
            "-c:v", "libopenh264",
            "-c:a", "libmp3lame",
            "-f", "mpegts",
            "-pix_fmt", "yuv420p",
            "-t", "10",  # 只推流10秒
            "udp://127.0.0.1:1234?pkt_size=1316"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ UDP推流测试成功")
            return True
        else:
            print(f"❌ UDP推流测试失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ UDP推流测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 数字人系统测试")
    print("=" * 40)
    
    # 测试前置条件
    if not test_prerequisites():
        print("\n❌ 前置条件检查失败，请先解决问题")
        return False
    
    # 测试TTS
    audio_path = test_tts()
    
    # 测试数字人视频生成
    video_path = test_digital_human_generation(audio_path)
    
    # 测试UDP推流
    stream_success = test_udp_stream(video_path)
    
    # 总结
    print("\n📋 测试总结:")
    print("=" * 40)
    
    if audio_path:
        print("✅ TTS生成: 正常")
    else:
        print("❌ TTS生成: 失败")
    
    if video_path:
        print("✅ 数字人视频生成: 正常")
    else:
        print("❌ 数字人视频生成: 失败")
    
    if stream_success:
        print("✅ UDP推流: 正常")
    else:
        print("❌ UDP推流: 失败")
    
    if audio_path and video_path and stream_success:
        print("\n🎉 所有测试通过！数字人系统可以正常使用")
        print("运行命令: python3 digital_human_system.py")
        return True
    else:
        print("\n⚠️ 部分测试失败，请检查相关组件")
        return False

if __name__ == "__main__":
    main()