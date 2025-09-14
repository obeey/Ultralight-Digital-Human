#!/usr/bin/env python3
"""
WSL UDP推流修复方案
解决WSL到Windows的UDP流传输问题
"""

import subprocess
import socket
import time
import os

def get_wsl_ip():
    """获取WSL的IP地址"""
    try:
        # 获取WSL的IP地址
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        wsl_ip = result.stdout.strip().split()[0]
        print(f"🌐 WSL IP地址: {wsl_ip}")
        return wsl_ip
    except:
        print("⚠️ 无法获取WSL IP，使用localhost")
        return "127.0.0.1"

def get_windows_ip():
    """获取Windows主机IP"""
    try:
        # 通过路由表获取Windows主机IP
        result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'default via' in line:
                windows_ip = line.split()[2]
                print(f"🖥️ Windows主机IP: {windows_ip}")
                return windows_ip
    except:
        pass
    
    print("⚠️ 无法获取Windows IP，使用默认")
    return "172.20.240.1"  # WSL2默认网关

def test_network_connectivity(target_ip, port):
    """测试网络连通性"""
    print(f"🔍 测试到 {target_ip}:{port} 的连通性...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # 发送测试数据
        test_data = b"UDP_CONNECTIVITY_TEST"
        sock.sendto(test_data, (target_ip, port))
        print(f"✅ UDP数据发送成功到 {target_ip}:{port}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def create_test_video():
    """创建测试视频"""
    print("🎬 创建WSL测试视频...")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc2=duration=15:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=800:duration=15",
        "-vf", "drawtext=text='WSL UDP Test %{localtime}':fontcolor=yellow:fontsize=36:x=10:y=10",
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-pix_fmt", "yuv420p",
        "-t", "15",
        "wsl_test.mp4"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ WSL测试视频创建成功")
        return "wsl_test.mp4"
    else:
        print(f"❌ 视频创建失败: {result.stderr}")
        return None

def push_udp_stream_to_windows(video_path, target_ip="0.0.0.0", port=1234):
    """推送UDP流到Windows"""
    print(f"📡 推送UDP流到 {target_ip}:{port}")
    
    # 使用广播地址，让Windows更容易接收
    cmd = [
        "ffmpeg", "-y",
        "-re",
        "-i", video_path,
        "-c:v", "libopenh264",
        "-c:a", "libmp3lame",
        "-f", "mpegts",
        "-pix_fmt", "yuv420p",
        "-loglevel", "info",
        f"udp://{target_ip}:{port}?pkt_size=1316&buffer_size=65536"
    ]
    
    print("📤 执行推流命令:")
    print(" ".join(cmd))
    print("\n💡 在Windows VLC中使用以下URL:")
    print(f"   udp://@:{port}")
    print(f"   或: udp://0.0.0.0:{port}")
    print("⏰ 推流15秒...\n")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # 显示关键输出
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
                elif "error" in output.lower() or "warning" in output.lower():
                    print(f"⚠️ {output.strip()}")
        
        rc = process.poll()
        print(f"\n📋 推流完成，退出码: {rc}")
        return rc == 0
        
    except Exception as e:
        print(f"❌ 推流异常: {e}")
        return False

def setup_windows_port_forwarding():
    """设置Windows端口转发（需要管理员权限）"""
    wsl_ip = get_wsl_ip()
    
    print("🔧 Windows端口转发设置（需要在Windows管理员命令提示符中运行）:")
    print(f"netsh interface portproxy add v4tov4 listenport=1234 listenaddress=0.0.0.0 connectport=1234 connectaddress={wsl_ip}")
    print("删除转发规则:")
    print("netsh interface portproxy delete v4tov4 listenport=1234 listenaddress=0.0.0.0")

def main():
    """主函数"""
    print("🚀 WSL UDP推流修复工具")
    print("=" * 50)
    
    # 获取网络信息
    wsl_ip = get_wsl_ip()
    windows_ip = get_windows_ip()
    
    # 创建测试视频
    video_path = create_test_video()
    if not video_path:
        return False
    
    print("\n选择推流目标:")
    print("1. 广播到所有接口 (推荐)")
    print("2. 推送到localhost")
    print("3. 推送到Windows主机IP")
    print("4. 显示端口转发设置")
    
    choice = input("请选择 (1-4): ").strip()
    
    try:
        if choice == "1":
            # 广播模式
            success = push_udp_stream_to_windows(video_path, "0.0.0.0", 1234)
        elif choice == "2":
            # 本地模式
            success = push_udp_stream_to_windows(video_path, "127.0.0.1", 1234)
        elif choice == "3":
            # Windows主机模式
            success = push_udp_stream_to_windows(video_path, windows_ip, 1234)
        elif choice == "4":
            # 显示端口转发设置
            setup_windows_port_forwarding()
            return True
        else:
            print("❌ 无效选择")
            return False
        
        if success:
            print("\n🎉 WSL UDP推流完成！")
            print("如果在Windows VLC中看到带时间戳的测试视频，说明推流成功")
            print("\n📋 VLC接收URL:")
            print("   udp://@:1234")
            print("   udp://0.0.0.0:1234")
        else:
            print("\n❌ WSL UDP推流失败")
            print("可能需要配置Windows防火墙或端口转发")
        
        return success
        
    finally:
        # 清理测试文件
        if os.path.exists(video_path):
            os.remove(video_path)

if __name__ == "__main__":
    main()