#!/usr/bin/env python3
"""
使用生成的视频文件测试UDP推流
"""

import subprocess
import os
import time

def test_udp_stream_with_generated_video():
    """使用生成的视频测试UDP推流"""
    print("📡 使用生成的视频测试UDP推流...")
    
    video_path = "temp/debug_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        print("请先运行: python3 debug_generation.py")
        return False
    
    size = os.path.getsize(video_path)
    print(f"📁 使用视频文件: {video_path} ({size} 字节)")
    
    print("🚀 开始UDP推流...")
    print("💡 请在Windows VLC中打开:")
    print("   1. 媒体 -> 打开网络串流")
    print("   2. 输入: udp://@:1234")
    print("   3. 点击播放")
    print("⏰ 推流将持续约8秒...")
    
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-loglevel", "info",
        "udp://127.0.0.1:1234?pkt_size=1316"
    ]
    
    print("📤 执行推流命令:")
    print(" ".join(cmd))
    print()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 显示FFmpeg输出
        frame_count = 0
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                if "frame=" in output:
                    frame_count += 1
                    if frame_count % 30 == 0:  # 每30帧显示一次
                        print(f"📊 {output.strip()}")
                elif any(keyword in output.lower() for keyword in ["error", "warning", "failed"]):
                    print(f"⚠️ {output.strip()}")
        
        rc = process.poll()
        print(f"\n📋 推流完成，退出码: {rc}")
        
        if rc == 0:
            print("✅ UDP推流成功完成！")
            print("如果在VLC中看到了带文字的黑色背景视频，说明整个流程正常工作")
        else:
            print("❌ UDP推流失败")
        
        return rc == 0
        
    except Exception as e:
        print(f"❌ 推流异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 使用生成视频测试UDP推流")
    print("=" * 40)
    
    # 检查生成的视频文件
    if not os.path.exists("temp/debug_video.mp4"):
        print("❌ 找不到生成的视频文件")
        print("请先运行: python3 debug_generation.py")
        return False
    
    # 等待用户准备VLC
    print("请先在Windows上准备VLC:")
    print("1. 打开VLC媒体播放器")
    print("2. 点击 媒体 -> 打开网络串流")
    print("3. 在URL框中输入: udp://@:1234")
    print("4. 先不要点播放，等推流开始后再点")
    
    input("\n准备好后按Enter键开始推流...")
    
    # 开始推流测试
    success = test_udp_stream_with_generated_video()
    
    if success:
        print("\n🎉 测试完成！")
        print("如果您在VLC中看到了视频，说明:")
        print("✅ TTS生成正常")
        print("✅ 视频生成正常") 
        print("✅ UDP推流正常")
        print("✅ 整个直播系统可以正常工作")
    else:
        print("\n❌ 推流测试失败")
        print("可能的原因:")
        print("1. VLC配置问题")
        print("2. 网络配置问题")
        print("3. 防火墙阻止")
    
    return success

if __name__ == "__main__":
    main()