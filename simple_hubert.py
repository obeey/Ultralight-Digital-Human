#!/usr/bin/env python3
"""
简化版HuBERT特征提取
使用预计算特征或简化处理
"""

import numpy as np
import librosa
import soundfile as sf
from argparse import ArgumentParser
import os
import sys

def extract_simple_audio_features(audio_path, output_path):
    """提取简化的音频特征作为HuBERT的替代"""
    try:
        # 读取音频
        audio, sr = sf.read(audio_path)
        
        # 重采样到16kHz
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        
        # 如果是立体声，转为单声道
        if audio.ndim == 2:
            audio = audio[:, 0]
        
        # 提取MFCC特征作为HuBERT的简化替代
        # HuBERT输出维度是1024，我们创建相似的特征
        n_mfcc = 13
        hop_length = 320  # 与HuBERT的stride保持一致
        
        # 提取MFCC特征
        mfcc = librosa.feature.mfcc(
            y=audio, 
            sr=16000, 
            n_mfcc=n_mfcc,
            hop_length=hop_length,
            n_fft=2048
        )
        
        # 转置并扩展到1024维
        mfcc = mfcc.T  # [time, n_mfcc]
        
        # 通过重复和填充扩展到1024维
        repeat_factor = 1024 // n_mfcc
        remainder = 1024 % n_mfcc
        
        expanded_features = np.tile(mfcc, (1, repeat_factor))
        if remainder > 0:
            expanded_features = np.concatenate([
                expanded_features, 
                mfcc[:, :remainder]
            ], axis=1)
        
        # 确保第一维是偶数（与原始HuBERT处理保持一致）
        if expanded_features.shape[0] % 2 == 1:
            expanded_features = expanded_features[:-1]
        
        # 重塑为HuBERT期望的格式 [T//2, 2, 1024]
        reshaped_features = expanded_features.reshape(-1, 2, 1024)
        
        # 保存特征
        np.save(output_path, reshaped_features.astype(np.float32))
        
        print(f"简化音频特征已保存: {output_path}")
        print(f"特征形状: {reshaped_features.shape}")
        
        return True
        
    except Exception as e:
        print(f"特征提取失败: {e}")
        return False

def main():
    """主函数"""
    parser = ArgumentParser()
    parser.add_argument('--wav', type=str, required=True, help='输入wav文件路径')
    args = parser.parse_args()
    
    wav_name = args.wav
    
    if not os.path.exists(wav_name):
        print(f"错误: 音频文件不存在: {wav_name}")
        sys.exit(1)
    
    output_path = wav_name.replace('.wav', '_hu.npy')
    
    print(f"处理音频文件: {wav_name}")
    print("使用简化特征提取（MFCC替代HuBERT）...")
    
    if extract_simple_audio_features(wav_name, output_path):
        print("特征提取完成")
        sys.exit(0)
    else:
        print("特征提取失败")
        sys.exit(1)

if __name__ == "__main__":
    main()