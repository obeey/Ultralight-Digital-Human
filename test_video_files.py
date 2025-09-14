#!/usr/bin/env python3
"""
测试视频文件生成
生成几个测试视频文件供检查
"""

import os
import sys
import asyncio
import threading
import time
from live_stream_system import LiveStreamSystem, StreamConfig

async def generate_test_videos():
    """生成测试视频文件"""
    print("🎬 生成测试视频文件...")
    
    # 创建配置
    config = StreamConfig(
        output_mode="file",  # 使用文件输出模式
        output_dir="temp",
        buffer_size=5,
        max_workers=2
    )
    
    # 创建系统
    system = LiveStreamSystem(config)
    
    # 添加测试文本
    test_texts = [
        "欢迎来到我们的直播间！今天有很多优惠活动等着大家！",
        "请点击右下角的小黄车查看商品详情。",
        "现在下单还有额外的优惠券可以领取！",
        "感谢大家的支持，我们会继续为大家带来更多好产品。"
    ]
    
    print("📝 添加测试文本...")
    for i, text in enumerate(test_texts):
        system.stream_buffer.add_text(text)
        print(f"   {i+1}. {text}")
    
    print("🔧 启动音视频生成...")
    
    # 启动音视频生成线程
    av_thread = threading.Thread(target=system._audio_video_generation_loop)
    av_thread.daemon = True
    av_thread.start()
    
    # 等待视频生成
    print("⏳ 等待视频生成完成...")
    generated_count = 0
    max_wait = 120  # 最多等待2分钟
    
    for i in range(max_wait):
        # 检查temp目录中的文件
        if os.path.exists("temp"):
            video_files = [f for f in os.listdir("temp") if f.endswith('.mp4')]
            audio_files = [f for f in os.listdir("temp") if f.endswith('.wav')]
            
            if len(video_files) > generated_count:
                generated_count = len(video_files)
                print(f"✅ 已生成 {generated_count} 个视频文件")
                
                # 显示最新生成的文件
                if video_files:
                    latest_video = sorted(video_files)[-1]
                    video_path = os.path.join("temp", latest_video)
                    if os.path.exists(video_path):
                        size = os.path.getsize(video_path)
                        print(f"   📁 {latest_video} ({size} 字节)")
            
            # 如果生成了足够的视频就停止
            if len(video_files) >= len(test_texts):
                print(f"🎉 完成！共生成 {len(video_files)} 个视频文件")
                break
        
        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"⏳ 等待中... ({i}秒)")
    
    # 停止系统
    system.stop_streaming()
    
    # 列出生成的文件
    if os.path.exists("temp"):
        print("\n📋 生成的文件列表:")
        for file in sorted(os.listdir("temp")):
            file_path = os.path.join("temp", file)
            size = os.path.getsize(file_path)
            print(f"   📁 {file} ({size} 字节)")
        
        print(f"\n💡 请检查 temp/ 目录中的文件")
        print("   - .wav 文件是TTS生成的音频")
        print("   - .mp4 文件是最终的视频文件")
        
        return True
    else:
        print("❌ 没有生成任何文件")
        return False

def check_tts_service():
    """检查TTS服务"""
    print("🔍 检查TTS服务...")
    
    try:
        import requests
        response = requests.get("http://127.0.0.1:9880/", timeout=5)
        print("✅ TTS服务正在运行")
        return True
    except:
        print("❌ TTS服务未运行")
        print("请先启动GPT-SoVITS服务:")
        print("cd /mnt/e/CYC/projects/live-selling/GPT-SoVITS && python api_v2.py")
        return False

async def main():
    """主函数"""
    print("🚀 测试视频文件生成")
    print("=" * 40)
    
    # 检查TTS服务
    if not check_tts_service():
        return False
    
    # 创建temp目录
    os.makedirs("temp", exist_ok=True)
    
    # 生成测试视频
    success = await generate_test_videos()
    
    if success:
        print("\n🎉 测试完成！")
        print("请检查temp目录中的视频文件是否正确生成")
    else:
        print("\n❌ 测试失败")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())