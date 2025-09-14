#!/usr/bin/env python3
"""
测试WeNet特征提取速度
"""

import time
import subprocess
import os

def test_wenet_extraction():
    """测试WeNet特征提取"""
    
    # 查找最新的音频文件
    if not os.path.exists("temp"):
        print("❌ temp目录不存在")
        return
    
    files = os.listdir("temp")
    audio_files = [f for f in files if f.endswith('.wav') and 'audio_' in f]
    
    if not audio_files:
        print("❌ 没有找到音频文件")
        print("请先运行数字人系统生成一些音频文件")
        return
    
    # 使用最新的音频文件
    latest_audio = max([os.path.join("temp", f) for f in audio_files], key=os.path.getmtime)
    print(f"🎵 测试音频文件: {latest_audio}")
    
    # 测试WeNet特征提取
    print("\n🚀 开始WeNet特征提取...")
    start_time = time.time()
    
    cmd = ["python", "data_utils/wenet_infer.py", latest_audio]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        end_time = time.time()
        extraction_time = end_time - start_time
        
        print(f"⏱️ WeNet特征提取耗时: {extraction_time:.2f}秒")
        
        if result.returncode == 0:
            print("✅ WeNet特征提取成功!")
            
            # 检查生成的特征文件
            wenet_file = latest_audio.replace('.wav', '_wenet.npy')
            if os.path.exists(wenet_file):
                print(f"📁 特征文件: {wenet_file}")
                
                # 检查文件大小
                file_size = os.path.getsize(wenet_file)
                print(f"📊 文件大小: {file_size} bytes")
                
                # 加载并检查特征形状
                import numpy as np
                features = np.load(wenet_file)
                print(f"🔍 特征形状: {features.shape}")
                
            else:
                print("❌ 特征文件未生成")
        else:
            print("❌ WeNet特征提取失败")
            print("错误输出:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")

def compare_with_hubert():
    """与HuBERT进行速度对比"""
    
    # 查找最新的音频文件
    if not os.path.exists("temp"):
        print("❌ temp目录不存在")
        return
    
    files = os.listdir("temp")
    audio_files = [f for f in files if f.endswith('.wav') and 'audio_' in f]
    
    if not audio_files:
        print("❌ 没有找到音频文件")
        return
    
    latest_audio = max([os.path.join("temp", f) for f in audio_files], key=os.path.getmtime)
    print(f"\n🔄 对比测试音频文件: {latest_audio}")
    
    # 测试HuBERT
    print("\n🧪 测试HuBERT特征提取...")
    start_time = time.time()
    
    cmd_hubert = ["python", "hubert_torch28_fix.py", "--wav", latest_audio]
    
    try:
        result_hubert = subprocess.run(cmd_hubert, capture_output=True, text=True, cwd=os.getcwd())
        hubert_time = time.time() - start_time
        
        print(f"⏱️ HuBERT特征提取耗时: {hubert_time:.2f}秒")
        
        if result_hubert.returncode == 0:
            print("✅ HuBERT特征提取成功!")
        else:
            print("❌ HuBERT特征提取失败")
            
    except Exception as e:
        print(f"❌ HuBERT测试异常: {e}")
        hubert_time = float('inf')
    
    # 测试WeNet
    print("\n🧪 测试WeNet特征提取...")
    start_time = time.time()
    
    cmd_wenet = ["python", "data_utils/wenet_infer.py", latest_audio]
    
    try:
        result_wenet = subprocess.run(cmd_wenet, capture_output=True, text=True, cwd=os.getcwd())
        wenet_time = time.time() - start_time
        
        print(f"⏱️ WeNet特征提取耗时: {wenet_time:.2f}秒")
        
        if result_wenet.returncode == 0:
            print("✅ WeNet特征提取成功!")
        else:
            print("❌ WeNet特征提取失败")
            
    except Exception as e:
        print(f"❌ WeNet测试异常: {e}")
        wenet_time = float('inf')
    
    # 对比结果
    print("\n📊 速度对比结果:")
    print(f"HuBERT: {hubert_time:.2f}秒")
    print(f"WeNet:  {wenet_time:.2f}秒")
    
    if wenet_time < hubert_time:
        speedup = hubert_time / wenet_time
        print(f"🚀 WeNet比HuBERT快 {speedup:.2f}倍!")
    elif hubert_time < wenet_time:
        slowdown = wenet_time / hubert_time
        print(f"⚠️ WeNet比HuBERT慢 {slowdown:.2f}倍")
    else:
        print("⚖️ 两者速度相当")

if __name__ == "__main__":
    print("🧪 WeNet特征提取速度测试")
    print("=" * 40)
    
    # 基础测试
    test_wenet_extraction()
    
    # 对比测试
    compare_with_hubert()