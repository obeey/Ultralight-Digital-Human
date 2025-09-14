#!/usr/bin/env python3
"""
调试数字人系统音频问题
"""

import subprocess
import os
import time

def run_digital_human_with_debug():
    """运行数字人系统并调试音频问题"""
    print("🔍 调试数字人系统音频问题")
    print("=" * 50)
    
    print("💡 我们将:")
    print("1. 运行数字人系统生成一个视频")
    print("2. 检查生成的文件")
    print("3. 手动测试音视频合并推流")
    
    if input("是否继续? (y/n): ").lower() != 'y':
        return
    
    print("\n🚀 运行数字人系统...")
    
    try:
        # 运行数字人系统，但只生成一个视频就停止
        process = subprocess.Popen(
            ["python3", "digital_human_system.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        print("⏰ 数字人系统已启动，等待生成视频...")
        
        # 监控输出，等待视频生成
        video_generated = False
        audio_file_path = None
        video_file_path = None
        
        start_time = time.time()
        while time.time() - start_time < 120:  # 2分钟超时
            output = process.stdout.readline()
            if output:
                print(f"系统: {output.strip()}")
                
                # 检查是否生成了视频
                if "数字人视频生成成功" in output:
                    video_generated = True
                    # 提取视频路径
                    if "temp/audio_" in output:
                        video_file_path = output.split(":")[-1].strip()
                
                # 检查音频文件路径
                if "保留音频文件用于推流" in output:
                    audio_file_path = output.split(":")[-1].strip()
                
                # 检查推流状态
                if "合并音频推流" in output:
                    print("✅ 发现音频合并推流!")
                    audio_file_path = output.split(":")[-1].strip()
                
                if "推流视频" in output and "合并音频推流" not in output:
                    print("❌ 只推流视频，没有音频合并!")
                
                # 如果生成了视频，等待一会儿然后停止
                if video_generated and time.time() - start_time > 30:
                    break
        
        # 停止进程
        process.terminate()
        process.wait(timeout=10)
        
        print("\n📊 检查生成的文件...")
        
        # 列出temp目录的文件
        if os.path.exists("temp"):
            files = os.listdir("temp")
            audio_files = [f for f in files if f.endswith('.wav')]
            video_files = [f for f in files if f.endswith('.mp4') and 'audio_' in f]
            
            print(f"📁 temp目录文件:")
            print(f"   音频文件: {audio_files}")
            print(f"   视频文件: {video_files}")
            
            if video_files:
                latest_video = max([os.path.join("temp", f) for f in video_files], key=os.path.getmtime)
                print(f"📹 最新视频: {latest_video}")
                
                # 查找对应的音频文件
                video_base = os.path.basename(latest_video).replace('.mp4', '')
                expected_audio = f"temp/{video_base}.wav"
                
                print(f"🔍 期望的音频文件: {expected_audio}")
                
                if os.path.exists(expected_audio):
                    print("✅ 找到对应的音频文件!")
                    
                    # 手动测试音视频合并推流
                    print("\n🧪 手动测试音视频合并推流...")
                    test_manual_merge(latest_video, expected_audio)
                    
                else:
                    print("❌ 没有找到对应的音频文件!")
                    print("💡 这就是为什么没有声音的原因")
                    
                    # 检查是否有其他音频文件
                    if audio_files:
                        print(f"🔍 发现其他音频文件: {audio_files}")
                        latest_audio = max([os.path.join("temp", f) for f in audio_files], key=os.path.getmtime)
                        print(f"🎵 最新音频: {latest_audio}")
                        
                        # 用最新的音频文件测试
                        test_manual_merge(latest_video, latest_audio)
                    else:
                        print("❌ 完全没有音频文件!")
            else:
                print("❌ 没有找到视频文件!")
        
    except Exception as e:
        print(f"❌ 调试异常: {e}")

def test_manual_merge(video_path, audio_path):
    """手动测试音视频合并"""
    print(f"\n🎬 手动测试音视频合并...")
    print(f"📹 视频: {video_path}")
    print(f"🎵 音频: {audio_path}")
    
    if not os.path.exists(video_path) or not os.path.exists(audio_path):
        print("❌ 文件不存在，无法测试")
        return
    
    print("\n📺 VLC设置: udp://@172.18.0.1:1234")
    
    if input("准备好VLC后按Enter开始推流..."):
        pass
    
    # 合并推流命令
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", video_path,  # 视频输入
        "-i", audio_path,  # 音频输入
        "-c:v", "libopenh264",  # 重新编码MJPEG为H.264
        "-b:v", "2000k",        # 视频比特率
        "-maxrate", "2500k",    # 最大比特率
        "-bufsize", "5000k",    # 缓冲区大小
        "-g", "50",             # GOP大小
        "-r", "25",             # 帧率
        "-c:a", "libmp3lame",   # 音频编码
        "-b:a", "128k",         # 音频比特率
        "-ar", "44100",         # 音频采样率
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-shortest",  # 以最短的流为准
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("🚀 开始手动音视频合并推流...")
        result = subprocess.run(cmd, timeout=30)
        
        if result.returncode == 0:
            print("✅ 手动合并推流成功!")
            print("💡 这说明技术方案正确，问题在数字人系统的文件管理")
        else:
            print("❌ 手动合并推流失败")
            
    except subprocess.TimeoutExpired:
        print("⏰ 推流超时")
    except Exception as e:
        print(f"❌ 推流异常: {e}")

if __name__ == "__main__":
    run_digital_human_with_debug()