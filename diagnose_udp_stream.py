#!/usr/bin/env python3
"""
UDP推流诊断工具
帮助诊断UDP推流问题
"""

import subprocess
import socket
import time
import threading
import os

def check_udp_port():
    """检查UDP端口是否可用"""
    print("🔍 检查UDP端口1234...")
    
    try:
        # 尝试绑定UDP端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('localhost', 1234))
        sock.close()
        print("✅ UDP端口1234可用")
        return True
    except OSError as e:
        print(f"❌ UDP端口1234不可用: {e}")
        return False

def create_test_stream():
    """创建测试流"""
    print("🎬 创建测试流...")
    
    # 创建一个带有时间戳的测试视频
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=duration=30:size=1280x720:rate=30",
        "-vf", "drawtext=text='UDP Test %{localtime}':fontcolor=white:fontsize=48:x=10:y=10",
        "-f", "lavfi",
        "-i", "sine=frequency=1000:duration=30",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-pix_fmt", "yuv420p",
        "-t", "30",
        "udp_test_stream.mp4"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 测试流创建成功")
        return "udp_test_stream.mp4"
    else:
        print(f"❌ 测试流创建失败: {result.stderr}")
        return None

def monitor_udp_traffic():
    """监控UDP流量"""
    print("📊 监控UDP流量...")
    
    def monitor():
        try:
            # 使用netstat监控UDP连接
            cmd = ["netstat", "-u", "-n"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if "1234" in result.stdout:
                print("✅ 检测到UDP端口1234的活动")
            else:
                print("⚠️ 未检测到UDP端口1234的活动")
                
        except Exception as e:
            print(f"❌ 监控失败: {e}")
    
    # 在后台运行监控
    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.daemon = True
    monitor_thread.start()

def test_udp_stream_with_monitoring():
    """带监控的UDP推流测试"""
    print("📡 开始带监控的UDP推流测试...")
    
    video_path = create_test_stream()
    if not video_path:
        return False
    
    # 启动监控
    monitor_udp_traffic()
    
    print("🚀 开始UDP推流...")
    print("💡 请在VLC中打开网络流: udp://@:1234")
    print("💡 或者使用命令: vlc udp://@:1234")
    print("⏰ 推流将持续30秒...")
    
    # UDP推流命令，添加更多调试信息
    cmd = [
        "ffmpeg", "-y",
        "-re",  # 实时播放
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-loglevel", "info",  # 显示详细日志
        "udp://127.0.0.1:1234?pkt_size=1316&buffer_size=65536"
    ]
    
    try:
        print("📤 FFmpeg命令:")
        print(" ".join(cmd))
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 实时显示FFmpeg输出
        output_lines = []
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                output_lines.append(output.strip())
                if len(output_lines) <= 10:  # 只显示前10行
                    print(f"FFmpeg: {output.strip()}")
        
        rc = process.poll()
        
        if rc == 0:
            print("✅ UDP推流完成")
        else:
            print(f"⚠️ FFmpeg退出码: {rc}")
            
        return True
        
    except Exception as e:
        print(f"❌ UDP推流异常: {e}")
        return False
    
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

def test_vlc_reception():
    """测试VLC接收"""
    print("📺 测试VLC接收...")
    
    # 检查VLC是否安装
    try:
        result = subprocess.run(["vlc", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ VLC已安装")
            
            print("🚀 尝试自动启动VLC接收UDP流...")
            print("💡 如果VLC没有自动打开，请手动打开: vlc udp://@:1234")
            
            # 尝试启动VLC
            try:
                vlc_cmd = ["vlc", "udp://@:1234", "--intf", "dummy"]
                vlc_process = subprocess.Popen(vlc_cmd)
                print("✅ VLC已启动")
                return vlc_process
            except:
                print("⚠️ 无法自动启动VLC，请手动启动")
                return None
        else:
            print("❌ VLC未安装")
            return None
            
    except FileNotFoundError:
        print("❌ VLC未找到，请安装VLC: sudo apt install vlc")
        return None

def main():
    """主函数"""
    print("🚀 UDP推流诊断工具")
    print("=" * 40)
    
    # 1. 检查UDP端口
    if not check_udp_port():
        print("请检查是否有其他程序占用了UDP端口1234")
        return False
    
    # 2. 测试VLC
    vlc_process = test_vlc_reception()
    
    # 等待用户准备
    input("按Enter键开始推流测试...")
    
    # 3. 开始推流测试
    success = test_udp_stream_with_monitoring()
    
    # 清理VLC进程
    if vlc_process:
        try:
            vlc_process.terminate()
            print("🗑️ 关闭VLC")
        except:
            pass
    
    if success:
        print("\n🎉 UDP推流诊断完成！")
        print("如果您在VLC中看到了带时间戳的测试视频，说明推流正常工作")
        print("如果没有看到视频，可能的原因:")
        print("1. 防火墙阻止了UDP流量")
        print("2. VLC配置问题")
        print("3. 网络配置问题")
    else:
        print("\n❌ UDP推流诊断失败")
    
    return success

if __name__ == "__main__":
    main()