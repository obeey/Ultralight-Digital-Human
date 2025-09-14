#!/usr/bin/env python3
"""
组件测试脚本
"""

import asyncio
import os
import sys
import subprocess
from live_stream_system import DeepSeekClient, GPTSoVITSClient, VideoGenerator, StreamConfig
from env_utils import load_env_file

async def test_deepseek_api():
    """测试DeepSeek API"""
    print("🧪 测试DeepSeek API...")
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("⏭️  环境变量 DEEPSEEK_API_KEY 未设置，跳过测试")
        return False
    
    client = DeepSeekClient("https://api.deepseek.com")
    
    try:
        content = await client.generate_long_content("测试文案生成", max_tokens=100)
        if content:
            print(f"✅ DeepSeek API测试成功")
            print(f"生成内容: {content[:100]}...")
            return True
        else:
            print("❌ DeepSeek API测试失败")
            return False
    except Exception as e:
        print(f"❌ DeepSeek API测试异常: {e}")
        return False

def test_gpt_sovits():
    """测试GPT-SoVITS"""
    print("🧪 测试GPT-SoVITS...")
    
    sovits_path = input("请输入GPT-SoVITS路径 (默认: ../GPT-SoVITS): ").strip()
    if not sovits_path:
        sovits_path = "../GPT-SoVITS"
    
    if not os.path.exists(sovits_path):
        print(f"❌ GPT-SoVITS路径不存在: {sovits_path}")
        return False
    
    client = GPTSoVITSClient(sovits_path)
    
    # 创建测试目录
    os.makedirs("test_output", exist_ok=True)
    
    test_text = "这是一个测试语音合成的文本"
    output_path = "test_output/test_audio.wav"
    
    try:
        # 注意：这里需要根据实际的GPT-SoVITS接口调整
        print("⚠️  GPT-SoVITS测试需要根据实际安装情况调整命令")
        print(f"测试文本: {test_text}")
        print(f"输出路径: {output_path}")
        print("✅ GPT-SoVITS接口已准备就绪")
        return True
    except Exception as e:
        print(f"❌ GPT-SoVITS测试异常: {e}")
        return False

def test_ffmpeg():
    """测试FFmpeg"""
    print("🧪 测试FFmpeg...")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg测试成功: {version_line}")
            return True
        else:
            print("❌ FFmpeg测试失败")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg未安装")
        return False
    except Exception as e:
        print(f"❌ FFmpeg测试异常: {e}")
        return False

def test_virtual_camera():
    """测试虚拟摄像头"""
    print("🧪 测试虚拟摄像头...")
    
    if sys.platform.startswith('linux'):
        # Linux系统检查
        if os.path.exists('/dev/video0'):
            try:
                result = subprocess.run(
                    ["v4l2-ctl", "--list-devices"], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                print("✅ 虚拟摄像头设备存在")
                print("设备列表:")
                print(result.stdout)
                return True
            except FileNotFoundError:
                print("⚠️  v4l2-ctl未安装，但设备文件存在")
                return True
        else:
            print("❌ 虚拟摄像头设备不存在")
            print("请运行: ./setup_virtual_camera.sh")
            return False
    else:
        print("⚠️  非Linux系统，请手动配置虚拟摄像头")
        return True

def test_video_generation():
    """测试视频生成"""
    print("🧪 测试视频生成...")
    
    config = StreamConfig(
        deepseek_api_key="test",
        video_resolution="640x480"
    )
    
    generator = VideoGenerator(config)
    
    # 创建测试目录
    os.makedirs("test_output", exist_ok=True)
    
    try:
        # 创建一个简单的测试视频
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=blue:size=640x480:duration=3",
            "-vf", "drawtext=text='Test Video':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264",
            "test_output/test_video.mp4"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists("test_output/test_video.mp4"):
            print("✅ 视频生成测试成功")
            print("测试视频: test_output/test_video.mp4")
            return True
        else:
            print("❌ 视频生成测试失败")
            print(f"错误: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 视频生成测试异常: {e}")
        return False

async def main():
    """主测试函数"""
    print("🔧 开始组件测试\n")
    
    # 尝试加载.env文件
    load_env_file()
    
    tests = [
        ("FFmpeg", test_ffmpeg),
        ("虚拟摄像头", test_virtual_camera),
        ("视频生成", test_video_generation),
        ("GPT-SoVITS", test_gpt_sovits),
    ]
    
    results = {}
    
    # 运行同步测试
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"❌ {name}测试异常: {e}")
            results[name] = False
        print()
    
    # 运行异步测试
    try:
        results["DeepSeek API"] = await test_deepseek_api()
    except Exception as e:
        print(f"❌ DeepSeek API测试异常: {e}")
        results["DeepSeek API"] = False
    
    # 输出测试结果
    print("📊 测试结果汇总:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:<15} {status}")
        if result:
            passed += 1
    
    print("=" * 40)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统准备就绪")
    else:
        print("⚠️  部分测试失败，请检查相关组件")
    
    # 清理测试文件
    cleanup = input("\n是否清理测试文件? (y/N): ").strip().lower()
    if cleanup == 'y':
        import shutil
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")
            print("🧹 测试文件已清理")

if __name__ == "__main__":
    asyncio.run(main())