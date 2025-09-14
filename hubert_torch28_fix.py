#!/usr/bin/env python3
"""
修复torch 2.8.0兼容性的HuBERT特征提取脚本
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

# 设置环境变量来解决torch.load安全问题
os.environ['TORCH_LOAD_WEIGHTS_ONLY'] = 'False'

import torch
# 临时禁用安全检查
torch.serialization.add_safe_globals(['collections.OrderedDict'])

import numpy as np
import soundfile as sf
import librosa
from argparse import ArgumentParser

def load_hubert_models():
    """安全加载HuBERT模型"""
    try:
        # 临时修改torch.load的安全设置
        original_load = torch.load
        
        def safe_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        
        torch.load = safe_load
        
        from transformers import Wav2Vec2Processor, HubertModel
        
        print("Loading the Wav2Vec2 Processor...")
        processor = Wav2Vec2Processor.from_pretrained(
            "facebook/hubert-large-ls960-ft",
            trust_remote_code=True
        )
        
        print("Loading the HuBERT Model...")
        model = HubertModel.from_pretrained(
            "facebook/hubert-large-ls960-ft",
            trust_remote_code=True,
            torch_dtype=torch.float32
        )
        
        # 恢复原始torch.load
        torch.load = original_load
        
        return processor, model
        
    except Exception as e:
        print(f"模型加载失败: {e}")
        print("尝试使用本地缓存...")
        
        try:
            processor = Wav2Vec2Processor.from_pretrained(
                "facebook/hubert-large-ls960-ft",
                local_files_only=True,
                trust_remote_code=True
            )
            model = HubertModel.from_pretrained(
                "facebook/hubert-large-ls960-ft",
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            return processor, model
        except Exception as e2:
            print(f"本地缓存加载也失败: {e2}")
            raise e

# 全局变量
wav2vec2_processor = None
hubert_model = None

def get_hubert_from_16k_wav(wav_16k_name):
    """从16k wav文件提取HuBERT特征"""
    speech_16k, _ = sf.read(wav_16k_name)
    hubert = get_hubert_from_16k_speech(speech_16k)
    return hubert

@torch.no_grad()
def get_hubert_from_16k_speech(speech, device="cuda:0" if torch.cuda.is_available() else "cpu"):
    """从16k语音提取HuBERT特征"""
    global hubert_model, wav2vec2_processor
    
    # 确保模型已加载
    if hubert_model is None or wav2vec2_processor is None:
        wav2vec2_processor, hubert_model = load_hubert_models()
    
    hubert_model = hubert_model.to(device)
    
    if speech.ndim == 2:
        speech = speech[:, 0]  # [T, 2] ==> [T,]
    
    input_values_all = wav2vec2_processor(
        speech, 
        return_tensors="pt", 
        sampling_rate=16000
    ).input_values  # [1, T]
    input_values_all = input_values_all.to(device)
    
    # 处理长音频序列的逻辑
    kernel = 400
    stride = 320
    clip_length = stride * 1000
    num_iter = input_values_all.shape[1] // clip_length
    expected_T = (input_values_all.shape[1] - (kernel-stride)) // stride
    res_lst = []
    
    for i in range(num_iter):
        if i == 0:
            start_idx = 0
            end_idx = clip_length - stride + kernel
        else:
            start_idx = clip_length * i
            end_idx = start_idx + (clip_length - stride + kernel)
        
        input_values = input_values_all[:, start_idx: end_idx]
        hidden_states = hubert_model.forward(input_values).last_hidden_state  # [B=1, T=pts//320, hid=1024]
        res_lst.append(hidden_states[0])
    
    if num_iter > 0:
        input_values = input_values_all[:, clip_length * num_iter:]
    else:
        input_values = input_values_all
    
    # 如果最后一批的长度足够，处理它
    if input_values.shape[1] >= kernel:
        hidden_states = hubert_model(input_values).last_hidden_state  # [B=1, T=pts//320, hid=1024]
        res_lst.append(hidden_states[0])
    
    ret = torch.cat(res_lst, dim=0).cpu()  # [T, 1024]
    
    # 确保维度正确
    if abs(ret.shape[0] - expected_T) <= 1:
        if ret.shape[0] < expected_T:
            ret = torch.nn.functional.pad(ret, (0,0,0,expected_T-ret.shape[0]))
        else:
            ret = ret[:expected_T]
    
    return ret

def make_even_first_dim(tensor):
    """确保第一维是偶数"""
    size = list(tensor.size())
    if size[0] % 2 == 1:
        size[0] -= 1
        return tensor[:size[0]]
    return tensor

def main():
    """主函数"""
    parser = ArgumentParser()
    parser.add_argument('--wav', type=str, required=True, help='输入wav文件路径')
    args = parser.parse_args()
    
    wav_name = args.wav
    
    if not os.path.exists(wav_name):
        print(f"错误: 音频文件不存在: {wav_name}")
        sys.exit(1)
    
    try:
        print(f"处理音频文件: {wav_name}")
        
        # 读取音频并重采样到16kHz
        speech, sr = sf.read(wav_name)
        if sr != 16000:
            speech_16k = librosa.resample(speech, orig_sr=sr, target_sr=16000)
            print(f"重采样: {sr}Hz -> 16000Hz")
        else:
            speech_16k = speech
        
        print("提取HuBERT特征...")
        
        # 提取HuBERT特征
        hubert_hidden = get_hubert_from_16k_speech(speech_16k)
        
        # 处理维度
        hubert_hidden = make_even_first_dim(hubert_hidden).reshape(-1, 2, 1024)
        
        # 保存特征
        output_path = wav_name.replace('.wav', '_hu.npy')
        np.save(output_path, hubert_hidden.detach().numpy())
        
        print(f"HuBERT特征已保存: {output_path}")
        print(f"特征形状: {hubert_hidden.detach().numpy().shape}")
        
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()