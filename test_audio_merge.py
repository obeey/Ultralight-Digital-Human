#!/usr/bin/env python3
"""
测试音视频合并推流
"""

import subprocess
import os
import time

def create_test_audio():
    """创建测试音频文件"""
    print("🎵 创建测试音频文件...")
    
    # 创建一个3秒的测试音频，匹配数字人视频长度
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=3",
        "-ar", "44100",
        "-ac", "1",
        "temp/test_merge_audio.wav"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 测试音频创建成功")
            return "temp/test_merge_audio.wav"
        else:
            print(f"❌ 测试音频创建失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 创建音频异常: {e}")
        return None

def test_merge_and_stream():
    """测试音视频合并推流"""
    print("\n🎬 测试音视频合并推流...")
    
    video_path = "temp/audio_000000.mp4"
    audio_path = create_test_audio()
    
    if not audio_path or not os.path.exists(video_path):
        print("❌ 缺少测试文件")
        return
    
    print(f"📹 视频文件: {video_path}")
    print(f"🎵 音频文件: {audio_path}")
    
    # 分析文件信息
    print("\n📊 分析文件信息...")
    
    # 视频信息
    cmd_video = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path]
    result_video = subprocess.run(cmd_video, capture_output=True, text=True)
    
    # 音频信息  
    cmd_audio = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", audio_path]
    result_audio = subprocess.run(cmd_audio, capture_output=True, text=True)
    
    if result_video.returncode == 0 and result_audio.returncode == 0:
        print("✅ 文件分析成功")
    else:
        print("❌ 文件分析失败")
        return
    
    print("\n📺 VLC设置提醒:")
    print("URL: udp://@172.18.0.1:1234")
    
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
    
    print("\n📤 合并推流命令:")
    print(" ".join(cmd))
    print("-" * 50)
    
    try:
        print("🚀 开始音视频合并推流...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        print("⏰ 推流已启动，按Ctrl+C停止...")
        
        # 实时显示输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"FFmpeg: {output.strip()}")
        
        return_code = process.poll()
        if return_code == 0:
            print("✅ 音视频合并推流完成")
        else:
            print(f"❌ 推流失败，退出码: {return_code}")
            
    except KeyboardInterrupt:
        print("\n🛑 用户停止推流")
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"❌ 推流异常: {e}")
    
    # 清理测试文件
    if os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"🗑️ 已清理测试音频: {audio_path}")

def test_only_video_stream():
    """测试只推流视频（对比测试）"""
    print("\n🎬 测试只推流视频（对比测试）...")
    
    video_path = "temp/audio_000000.mp4"
    
    if not os.path.exists(video_path):
        print("❌ 视频文件不存在")
        return
    
    print(f"📹 视频文件: {video_path}")
    
    if input("准备好VLC后按Enter开始推流..."):
        pass
    
    # 只推流视频
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", video_path,
        "-c:v", "libopenh264",  # 重新编码MJPEG为H.264
        "-b:v", "2000k",        # 视频比特率
        "-maxrate", "2500k",    # 最大比特率
        "-bufsize", "5000k",    # 缓冲区大小
        "-g", "50",             # GOP大小
        "-r", "25",             # 帧率
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    print("\n📤 视频推流命令:")
    print(" ".join(cmd))
    print("-" * 50)
    
    try:
        print("🚀 开始视频推流...")
        result = subprocess.run(cmd, timeout=30)
        
        if result.returncode == 0:
            print("✅ 视频推流完成")
        else:
            print("❌ 视频推流失败")
            
    except subprocess.TimeoutExpired:
        print("⏰ 推流超时")
    except Exception as e:
        print(f"❌ 推流异常: {e}")

def main():
    """主函数"""
    print("🧪 音视频合并推流测试")
    print("=" * 40)
    
    print("选择测试项目:")
    print("1. 音视频合并推流测试")
    print("2. 只推流视频测试（对比）")
    print("3. 两个都测试")
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == "1":
        test_merge_and_stream()
    elif choice == "2":
        test_only_video_stream()
    elif choice == "3":
        test_merge_and_stream()
        print("\n" + "="*40)
        test_only_video_stream()
    else:
        print("❌ 无效选择")
        return
    
    print("\n🎉 测试完成!")
    print("💡 如果合并推流有声音，说明音频合并正常")
    print("💡 如果只有视频推流没声音，说明问题在音频文件管理")

if __name__ == "__main__":
    main()