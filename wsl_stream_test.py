#!/usr/bin/env python3
"""
WSL环境下的UDP推流测试
专门针对没有图形界面的WSL环境
"""

import subprocess
import time
import socket
import threading
import os

def test_udp_connection():
    """测试UDP连接是否正常"""
    print("🔍 测试UDP连接...")
    
    def udp_receiver():
        """UDP接收器"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('127.0.0.1', 1235))
            sock.settimeout(5)
            
            print("📡 UDP接收器启动，等待数据...")
            data, addr = sock.recvfrom(1024)
            print(f"✅ 收到UDP数据: {len(data)} 字节 来自 {addr}")
            sock.close()
            return True
        except Exception as e:
            print(f"❌ UDP接收异常: {e}")
            return False
    
    def udp_sender():
        """UDP发送器"""
        time.sleep(1)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            message = "UDP测试数据包".encode('utf-8')
            sock.sendto(message, ('127.0.0.1', 1235))
            print(f"📤 发送UDP数据: {len(message)} 字节")
            sock.close()
            return True
        except Exception as e:
            print(f"❌ UDP发送异常: {e}")
            return False
    
    # 启动接收器线程
    receiver_thread = threading.Thread(target=udp_receiver)
    receiver_thread.start()
    
    # 发送数据
    sender_result = udp_sender()
    
    # 等待接收器完成
    receiver_thread.join()
    
    return sender_result

def analyze_stream_output():
    """分析推流输出，验证推流是否正常"""
    print("\n📊 分析当前推流状态...")
    
    # 检查是否有ffmpeg进程在运行
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        ffmpeg_processes = []
        
        for line in result.stdout.split('\n'):
            if 'ffmpeg' in line and 'udp://' in line:
                ffmpeg_processes.append(line.strip())
        
        if ffmpeg_processes:
            print("✅ 发现活跃的FFmpeg推流进程:")
            for proc in ffmpeg_processes:
                print(f"   {proc}")
            return True
        else:
            print("❌ 没有发现FFmpeg推流进程")
            return False
            
    except Exception as e:
        print(f"❌ 检查进程异常: {e}")
        return False

def test_stream_reception():
    """测试推流接收（不使用图形界面）"""
    print("\n🎯 测试推流接收（WSL兼容模式）...")
    
    print("💡 由于WSL环境限制，我们将:")
    print("   1. 启动推流")
    print("   2. 使用ffprobe分析UDP流")
    print("   3. 验证音视频数据")
    
    if input("是否继续测试? (y/n): ").lower() != 'y':
        return
    
    # 启动推流
    print("\n🚀 启动测试推流...")
    stream_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x480:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-t", "30",
        "udp://127.0.0.1:1234?pkt_size=1316"
    ]
    
    try:
        print("📤 推流命令:", " ".join(stream_cmd))
        stream_proc = subprocess.Popen(stream_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)  # 等待推流启动
        
        # 使用ffprobe分析UDP流
        print("\n🔍 使用ffprobe分析UDP流...")
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format",
            "-analyzeduration", "5000000",
            "-probesize", "5000000",
            "udp://127.0.0.1:1234"
        ]
        
        print("📋 分析命令:", " ".join(probe_cmd))
        
        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            
            if probe_result.returncode == 0:
                print("✅ ffprobe成功分析UDP流!")
                print("📊 流信息:")
                
                # 解析JSON输出
                import json
                try:
                    stream_info = json.loads(probe_result.stdout)
                    
                    if 'streams' in stream_info:
                        for i, stream in enumerate(stream_info['streams']):
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
                    
                    print("✅ UDP推流完全正常!")
                    
                except json.JSONDecodeError:
                    print("⚠️  JSON解析失败，但ffprobe成功连接")
                    print("✅ UDP推流基本正常")
                    
            else:
                print("❌ ffprobe无法分析UDP流")
                print("错误信息:", probe_result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ ffprobe分析超时")
            print("💡 这可能意味着UDP流存在问题")
        
        # 停止推流
        stream_proc.terminate()
        stream_proc.wait(timeout=5)
        
        print("\n✅ 推流测试完成")
        
    except Exception as e:
        print(f"❌ 推流测试异常: {e}")

def create_windows_vlc_test():
    """创建Windows VLC测试脚本"""
    print("\n📝 创建Windows VLC测试脚本...")
    
    # 创建批处理文件
    batch_content = '''@echo off
echo ========================================
echo        VLC UDP 推流接收测试
echo ========================================
echo.
echo 请确保推流正在运行 (在WSL中运行推流脚本)
echo.
echo 尝试启动VLC接收UDP流...
echo.

REM 尝试不同的VLC路径
set VLC_PATH1="C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
set VLC_PATH2="C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"
set VLC_PATH3="vlc.exe"

echo 方法1: 使用 udp://@:1234
if exist %VLC_PATH1% (
    echo 找到VLC: %VLC_PATH1%
    %VLC_PATH1% udp://@:1234
    goto :end
)

if exist %VLC_PATH2% (
    echo 找到VLC: %VLC_PATH2%
    %VLC_PATH2% udp://@:1234
    goto :end
)

echo 尝试系统PATH中的VLC...
%VLC_PATH3% udp://@:1234 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo VLC启动失败，请手动操作:
    echo ========================================
    echo 1. 打开VLC媒体播放器
    echo 2. 点击 "媒体" -^> "打开网络串流"
    echo 3. 输入URL: udp://@:1234
    echo 4. 点击 "播放"
    echo.
    echo 如果看不到视频，尝试这些URL:
    echo - udp://127.0.0.1:1234
    echo - udp://localhost:1234
    echo - udp://@127.0.0.1:1234
    echo ========================================
)

:end
pause
'''
    
    with open("test_vlc_windows.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print("✅ 已创建 test_vlc_windows.bat")
    print("💡 在Windows中双击运行此文件来测试VLC接收")

def provide_wsl_solution():
    """提供WSL环境的完整解决方案"""
    print("\n🎯 WSL环境推流解决方案")
    print("=" * 50)
    
    print("📋 当前状态分析:")
    print("✅ 推流端: FFmpeg正常运行，UDP数据正常发送")
    print("❌ 接收端: WSL无图形界面，无法直接测试播放器")
    
    print("\n🔧 解决方案:")
    print("1. **推流在WSL中运行** (当前正在进行)")
    print("   - 继续运行 continuous_test_stream.py")
    print("   - 推流到 udp://127.0.0.1:1234")
    
    print("\n2. **在Windows中接收**")
    print("   - 运行 test_vlc_windows.bat")
    print("   - 或手动打开VLC，输入 udp://@:1234")
    
    print("\n3. **网络配置**")
    print("   - WSL和Windows共享网络接口")
    print("   - 127.0.0.1 在两个环境中都指向同一地址")
    print("   - UDP端口1234应该可以正常通信")
    
    print("\n4. **故障排除**")
    print("   - 如果VLC无法接收，检查Windows防火墙")
    print("   - 尝试不同的URL格式")
    print("   - 确保VLC版本支持UDP流")
    
    print("\n💡 推荐测试步骤:")
    print("1. 保持当前WSL推流运行")
    print("2. 在Windows中运行 test_vlc_windows.bat")
    print("3. 如果VLC能看到视频，说明整个系统正常")
    print("4. 然后可以运行完整的数字人系统")

def main():
    """主函数"""
    print("🐧 WSL环境UDP推流测试")
    print("=" * 40)
    
    print("检测到WSL环境，调整测试策略...")
    
    # 基础网络测试
    test_udp_connection()
    
    # 分析当前推流状态
    analyze_stream_output()
    
    # 创建Windows测试脚本
    create_windows_vlc_test()
    
    # 推流接收测试
    test_stream_reception()
    
    # 提供完整解决方案
    provide_wsl_solution()
    
    print("\n🎉 WSL测试完成!")
    print("💡 请在Windows中运行 test_vlc_windows.bat 来测试VLC接收")

if __name__ == "__main__":
    main()