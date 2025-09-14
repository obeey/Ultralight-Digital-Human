#!/usr/bin/env python3
"""
UDP推流诊断工具
"""

import subprocess
import socket
import time
import threading

def check_udp_port():
    """检查UDP端口状态"""
    print("🔍 检查UDP端口1234状态...")
    
    try:
        # 检查端口是否被占用
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('127.0.0.1', 1234))
        sock.close()
        print("✅ UDP端口1234可用")
        return True
    except Exception as e:
        print(f"❌ UDP端口1234被占用或不可用: {e}")
        return False

def test_udp_send_receive():
    """测试UDP发送和接收"""
    print("\n🔄 测试UDP发送和接收...")
    
    def udp_server():
        """UDP服务器"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('127.0.0.1', 1235))  # 使用不同端口避免冲突
            sock.settimeout(10)
            
            print("📡 UDP服务器启动，等待数据...")
            data, addr = sock.recvfrom(1024)
            print(f"✅ 收到UDP数据: {data.decode()} 来自 {addr}")
            sock.close()
            return True
        except Exception as e:
            print(f"❌ UDP服务器异常: {e}")
            return False
    
    def udp_client():
        """UDP客户端"""
        time.sleep(1)  # 等待服务器启动
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            message = "UDP测试消息"
            sock.sendto(message.encode(), ('127.0.0.1', 1235))
            print(f"📤 发送UDP数据: {message}")
            sock.close()
            return True
        except Exception as e:
            print(f"❌ UDP客户端异常: {e}")
            return False
    
    # 启动服务器线程
    server_thread = threading.Thread(target=udp_server)
    server_thread.start()
    
    # 启动客户端
    client_result = udp_client()
    
    # 等待服务器完成
    server_thread.join()
    
    return client_result

def check_network_interfaces():
    """检查网络接口"""
    print("\n🌐 检查网络接口...")
    
    try:
        # 获取网络接口信息
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📋 网络接口信息:")
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and ('127.0.0.1' in line or '192.168' in line or '10.' in line):
                    print(f"   {line.strip()}")
        else:
            print("❌ 无法获取网络接口信息")
    except Exception as e:
        print(f"❌ 检查网络接口异常: {e}")

def test_ffplay_receive():
    """测试ffplay接收UDP流"""
    print("\n🎮 测试ffplay接收UDP流...")
    
    print("💡 将启动两个进程:")
    print("   1. FFmpeg推流进程")
    print("   2. FFplay接收进程")
    
    if input("是否继续? (y/n): ").lower() != 'y':
        return
    
    # 推流命令
    stream_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x480:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame", 
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "udp://127.0.0.1:1234?pkt_size=1316"
    ]
    
    # 接收命令
    receive_cmd = [
        "ffplay", "-i", "udp://127.0.0.1:1234", "-autoexit"
    ]
    
    try:
        print("🚀 启动推流...")
        stream_proc = subprocess.Popen(stream_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)  # 等待推流稳定
        
        print("📺 启动ffplay接收...")
        receive_proc = subprocess.Popen(receive_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("⏰ 测试运行15秒...")
        time.sleep(15)
        
        # 停止进程
        receive_proc.terminate()
        stream_proc.terminate()
        
        # 等待进程结束
        receive_proc.wait(timeout=5)
        stream_proc.wait(timeout=5)
        
        print("✅ ffplay测试完成")
        
        # 检查进程退出码
        if receive_proc.returncode == 0:
            print("✅ ffplay成功接收UDP流")
        else:
            print("❌ ffplay接收失败")
            
    except Exception as e:
        print(f"❌ ffplay测试异常: {e}")

def generate_vlc_instructions():
    """生成VLC详细设置说明"""
    print("\n📺 VLC详细设置说明:")
    print("=" * 50)
    
    print("方法1 - 基本设置:")
    print("   1. 打开VLC媒体播放器")
    print("   2. 点击 '媒体' -> '打开网络串流'")
    print("   3. 在URL框中输入: udp://@:1234")
    print("   4. 点击 '播放'")
    
    print("\n方法2 - 高级设置:")
    print("   1. 打开VLC")
    print("   2. 工具 -> 首选项")
    print("   3. 左下角选择 '显示设置: 全部'")
    print("   4. 输入/编解码器 -> 访问模块 -> UDP")
    print("   5. 设置 'UDP接收超时' 为 5000ms")
    print("   6. 保存设置并重启VLC")
    
    print("\n方法3 - 命令行启动:")
    print("   vlc udp://@:1234")
    
    print("\n方法4 - 替代URL格式:")
    print("   - udp://127.0.0.1:1234")
    print("   - udp://localhost:1234")
    print("   - udp://@127.0.0.1:1234")
    
    print("\n🔧 故障排除:")
    print("   1. 检查防火墙设置")
    print("   2. 尝试不同的端口号")
    print("   3. 检查VLC版本 (建议3.0+)")
    print("   4. 尝试其他播放器 (如ffplay, mpv)")

def main():
    """主函数"""
    print("🔧 UDP推流诊断工具")
    print("=" * 40)
    
    # 基础检查
    check_udp_port()
    check_network_interfaces()
    
    # UDP通信测试
    test_udp_send_receive()
    
    # 生成VLC说明
    generate_vlc_instructions()
    
    # ffplay测试
    test_ffplay_receive()
    
    print("\n🎉 诊断完成!")
    print("💡 如果所有测试都通过但VLC仍然无法接收，")
    print("   建议尝试其他播放器或检查VLC配置。")

if __name__ == "__main__":
    main()