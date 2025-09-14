#!/usr/bin/env python3
"""
最终推流测试和VLC问题解决方案
"""

import subprocess
import time
import os
import threading

def test_digital_human_with_vlc():
    """测试数字人系统与VLC的完整流程"""
    print("🤖 数字人系统 + VLC 完整测试")
    print("=" * 50)
    
    print("📋 测试步骤:")
    print("1. 启动数字人系统")
    print("2. 生成测试视频")
    print("3. 推流到VLC")
    print("4. 验证接收效果")
    
    print("\n📺 VLC设置指南:")
    print("=" * 30)
    print("方法1 (推荐):")
    print("  1. 打开VLC")
    print("  2. 媒体 -> 打开网络串流")
    print("  3. 输入: udp://@:1234")
    print("  4. 点击播放")
    
    print("\n方法2 (备选):")
    print("  1. 打开VLC")
    print("  2. 媒体 -> 打开网络串流") 
    print("  3. 输入: udp://127.0.0.1:1234")
    print("  4. 点击播放")
    
    print("\n方法3 (命令行):")
    print("  在Windows命令行中运行:")
    print("  vlc udp://@:1234")
    
    if input("\n准备好VLC后按Enter开始测试..."):
        pass
    
    # 启动数字人系统测试
    print("\n🚀 启动数字人系统测试...")
    
    try:
        # 运行数字人系统的简化版本
        cmd = ["python3", "test_audio_video_stream.py"]
        
        print("📤 执行命令:", " ".join(cmd))
        print("⏰ 系统将生成完整的数字人视频并推流...")
        print("💡 请在VLC中观察是否有视频显示")
        
        result = subprocess.run(cmd, timeout=300)  # 5分钟超时
        
        if result.returncode == 0:
            print("✅ 数字人系统测试完成")
        else:
            print("❌ 数字人系统测试失败")
            
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
    except Exception as e:
        print(f"❌ 测试异常: {e}")

def create_vlc_batch_file():
    """创建VLC批处理文件"""
    print("\n📝 创建VLC启动脚本...")
    
    # 创建Windows批处理文件
    batch_content = '''@echo off
echo 启动VLC接收UDP流...
echo 如果VLC未在PATH中，请修改下面的路径
"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe" udp://@:1234
pause
'''
    
    with open("start_vlc.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    # 创建Linux脚本
    linux_content = '''#!/bin/bash
echo "启动VLC接收UDP流..."
vlc udp://@:1234 &
echo "VLC已启动，PID: $!"
'''
    
    with open("start_vlc.sh", "w") as f:
        f.write(linux_content)
    
    os.chmod("start_vlc.sh", 0o755)
    
    print("✅ 已创建VLC启动脚本:")
    print("   Windows: start_vlc.bat")
    print("   Linux: start_vlc.sh")

def test_alternative_players():
    """测试其他播放器"""
    print("\n🎮 测试其他播放器...")
    
    players = [
        ("ffplay", ["ffplay", "-i", "udp://127.0.0.1:1234"]),
        ("mpv", ["mpv", "udp://127.0.0.1:1234"]),
    ]
    
    for name, cmd in players:
        print(f"\n📺 测试 {name}...")
        
        if input(f"是否测试 {name}? (y/n): ").lower() == 'y':
            try:
                print(f"🚀 启动 {name}...")
                print("💡 同时需要启动推流，请在另一个终端运行:")
                print("   python3 continuous_test_stream.py")
                
                # 启动播放器
                proc = subprocess.Popen(cmd)
                
                print(f"⏰ {name} 已启动，按Enter停止...")
                input()
                
                proc.terminate()
                print(f"✅ {name} 测试完成")
                
            except FileNotFoundError:
                print(f"❌ {name} 未安装")
            except Exception as e:
                print(f"❌ {name} 测试异常: {e}")

def provide_troubleshooting_guide():
    """提供故障排除指南"""
    print("\n🔧 VLC故障排除指南")
    print("=" * 40)
    
    print("问题1: VLC显示'无法打开MRL'")
    print("解决方案:")
    print("  - 检查URL格式: udp://@:1234")
    print("  - 尝试: udp://127.0.0.1:1234")
    print("  - 确保推流正在运行")
    
    print("\n问题2: VLC连接但无画面")
    print("解决方案:")
    print("  - 工具 -> 首选项 -> 输入/编解码器")
    print("  - 网络缓存设置为1000ms")
    print("  - 重启VLC")
    
    print("\n问题3: 防火墙阻止")
    print("解决方案:")
    print("  - Windows: 允许VLC通过防火墙")
    print("  - Linux: sudo ufw allow 1234/udp")
    
    print("\n问题4: VLC版本问题")
    print("解决方案:")
    print("  - 更新到VLC 3.0+版本")
    print("  - 尝试VLC nightly版本")
    
    print("\n🎯 推荐测试顺序:")
    print("1. 先用ffplay测试 (确认推流正常)")
    print("2. 检查VLC设置")
    print("3. 尝试不同URL格式")
    print("4. 检查防火墙设置")
    print("5. 更新VLC版本")

def main():
    """主函数"""
    print("🎯 最终推流测试和VLC问题解决")
    print("=" * 50)
    
    print("选择测试项目:")
    print("1. 完整数字人系统测试")
    print("2. 创建VLC启动脚本")
    print("3. 测试其他播放器")
    print("4. 查看故障排除指南")
    print("5. 全部执行")
    
    choice = input("\n请选择 (1-5): ").strip()
    
    if choice == "1":
        test_digital_human_with_vlc()
    elif choice == "2":
        create_vlc_batch_file()
    elif choice == "3":
        test_alternative_players()
    elif choice == "4":
        provide_troubleshooting_guide()
    elif choice == "5":
        create_vlc_batch_file()
        provide_troubleshooting_guide()
        test_alternative_players()
        test_digital_human_with_vlc()
    else:
        print("❌ 无效选择")
        return
    
    print("\n🎉 测试完成!")
    print("💡 如果问题仍然存在，建议:")
    print("   1. 检查网络配置")
    print("   2. 尝试其他播放器")
    print("   3. 更新VLC版本")
    print("   4. 联系技术支持")

if __name__ == "__main__":
    main()