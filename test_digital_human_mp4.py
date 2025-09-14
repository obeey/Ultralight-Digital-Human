#!/usr/bin/env python3
"""
直接测试数字人推理生成的mp4推流
"""

import subprocess
import os
import time

def find_digital_human_videos():
    """查找数字人生成的mp4文件"""
    print("🔍 查找数字人生成的mp4文件...")
    
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        print("❌ temp目录不存在")
        return []
    
    mp4_files = []
    for file in os.listdir(temp_dir):
        if file.endswith('.mp4') and 'audio_' in file:
            mp4_path = os.path.join(temp_dir, file)
            mp4_files.append(mp4_path)
    
    if mp4_files:
        print(f"✅ 找到 {len(mp4_files)} 个数字人mp4文件:")
        for i, file in enumerate(mp4_files):
            print(f"   {i+1}. {file}")
    else:
        print("❌ 没有找到数字人mp4文件")
    
    return mp4_files

def analyze_mp4_file(mp4_path):
    """分析mp4文件的详细信息"""
    print(f"\n📊 分析文件: {mp4_path}")
    
    # 使用ffprobe分析文件
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", mp4_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            
            print("📋 文件信息:")
            if 'format' in info:
                duration = info['format'].get('duration', 'unknown')
                size = info['format'].get('size', 'unknown')
                print(f"   时长: {duration}秒")
                print(f"   大小: {size}字节")
            
            if 'streams' in info:
                print("📺 流信息:")
                for i, stream in enumerate(info['streams']):
                    codec_type = stream.get('codec_type', 'unknown')
                    codec_name = stream.get('codec_name', 'unknown')
                    print(f"   流 {i}: {codec_type} ({codec_name})")
                    
                    if codec_type == 'video':
                        width = stream.get('width', 'unknown')
                        height = stream.get('height', 'unknown')
                        fps = stream.get('r_frame_rate', 'unknown')
                        print(f"      分辨率: {width}x{height}")
                        print(f"      帧率: {fps}")
                    elif codec_type == 'audio':
                        sample_rate = stream.get('sample_rate', 'unknown')
                        channels = stream.get('channels', 'unknown')
                        print(f"      采样率: {sample_rate}Hz")
                        print(f"      声道数: {channels}")
            
            return True
        else:
            print(f"❌ 分析失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 分析异常: {e}")
        return False

def stream_mp4_file(mp4_path):
    """推流mp4文件"""
    print(f"\n🚀 推流文件: {mp4_path}")
    
    # 检查文件是否存在
    if not os.path.exists(mp4_path):
        print(f"❌ 文件不存在: {mp4_path}")
        return False
    
    print("📺 VLC接收设置:")
    print("   URL: udp://@172.18.0.1:1234")
    print("   或尝试: udp://172.18.0.1:1234")
    
    if input("准备好VLC后按Enter开始推流..."):
        pass
    
    # 推流命令 - 直接推流mp4文件
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", mp4_path,  # 输入文件
        "-c", "copy",    # 直接复制流，不重新编码
        "-f", "mpegts",  # 输出格式
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    print("📤 推流命令:")
    print(" ".join(cmd))
    print("-" * 50)
    
    try:
        # 启动推流
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
            print("✅ 推流完成")
        else:
            print(f"❌ 推流失败，退出码: {return_code}")
            
    except KeyboardInterrupt:
        print("\n🛑 用户停止推流")
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"❌ 推流异常: {e}")

def stream_with_reencoding(mp4_path):
    """重新编码后推流"""
    print(f"\n🔄 重新编码推流: {mp4_path}")
    
    print("💡 这次将重新编码视频，可能解决兼容性问题")
    
    if input("是否继续重新编码推流? (y/n): ").lower() != 'y':
        return
    
    # 重新编码推流命令
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", mp4_path,  # 输入文件
        "-c:v", "libopenh264",  # 重新编码视频
        "-b:v", "2000k",        # 视频比特率
        "-maxrate", "2500k",    # 最大比特率
        "-bufsize", "5000k",    # 缓冲区大小
        "-g", "50",             # GOP大小
        "-r", "25",             # 帧率
        "-c:a", "libmp3lame",   # 重新编码音频
        "-b:a", "128k",         # 音频比特率
        "-ar", "44100",         # 音频采样率
        "-f", "mpegts",         # 输出格式
        "-pix_fmt", "yuv420p",  # 像素格式
        "udp://172.18.0.1:1234?pkt_size=1316"
    ]
    
    print("📤 重新编码推流命令:")
    print(" ".join(cmd))
    print("-" * 50)
    
    try:
        # 启动推流
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        print("⏰ 重新编码推流已启动，按Ctrl+C停止...")
        
        # 实时显示输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"FFmpeg: {output.strip()}")
        
        return_code = process.poll()
        if return_code == 0:
            print("✅ 重新编码推流完成")
        else:
            print(f"❌ 重新编码推流失败，退出码: {return_code}")
            
    except KeyboardInterrupt:
        print("\n🛑 用户停止推流")
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"❌ 重新编码推流异常: {e}")

def generate_test_digital_human():
    """生成测试数字人视频"""
    print("\n🤖 生成测试数字人视频...")
    
    if input("是否生成新的数字人视频进行测试? (y/n): ").lower() != 'y':
        return None
    
    try:
        # 运行数字人系统生成一个测试视频
        print("🚀 启动数字人系统...")
        result = subprocess.run(
            ["python3", "test_audio_video_stream.py"], 
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode == 0:
            print("✅ 数字人视频生成成功")
            # 查找最新生成的mp4文件
            mp4_files = find_digital_human_videos()
            if mp4_files:
                # 返回最新的文件
                latest_file = max(mp4_files, key=os.path.getmtime)
                print(f"📁 最新生成的文件: {latest_file}")
                return latest_file
        else:
            print(f"❌ 数字人视频生成失败: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ 数字人生成超时")
    except Exception as e:
        print(f"❌ 数字人生成异常: {e}")
    
    return None

def main():
    """主函数"""
    print("🎬 数字人MP4推流测试")
    print("=" * 40)
    
    # 查找现有的数字人mp4文件
    mp4_files = find_digital_human_videos()
    
    if not mp4_files:
        print("\n💡 没有找到现有的数字人mp4文件")
        new_file = generate_test_digital_human()
        if new_file:
            mp4_files = [new_file]
        else:
            print("❌ 无法生成测试文件，退出")
            return
    
    # 选择要测试的文件
    if len(mp4_files) == 1:
        selected_file = mp4_files[0]
        print(f"\n📁 使用文件: {selected_file}")
    else:
        print("\n📋 选择要测试的文件:")
        for i, file in enumerate(mp4_files):
            print(f"   {i+1}. {file}")
        
        try:
            choice = int(input("请选择文件编号: ")) - 1
            if 0 <= choice < len(mp4_files):
                selected_file = mp4_files[choice]
            else:
                print("❌ 无效选择")
                return
        except ValueError:
            print("❌ 无效输入")
            return
    
    # 分析文件
    if not analyze_mp4_file(selected_file):
        print("❌ 文件分析失败，无法继续")
        return
    
    # 测试推流
    print("\n🎯 推流测试选项:")
    print("1. 直接推流 (不重新编码)")
    print("2. 重新编码推流")
    print("3. 两种方式都测试")
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == "1":
        stream_mp4_file(selected_file)
    elif choice == "2":
        stream_with_reencoding(selected_file)
    elif choice == "3":
        stream_mp4_file(selected_file)
        print("\n" + "="*40)
        stream_with_reencoding(selected_file)
    else:
        print("❌ 无效选择")
        return
    
    print("\n🎉 测试完成!")
    print("💡 如果VLC仍然只有声音没有图像，可能的原因:")
    print("   1. 数字人生成的mp4本身就没有有效的视频流")
    print("   2. VLC解码器设置问题")
    print("   3. 网络传输中视频数据丢失")

if __name__ == "__main__":
    main()