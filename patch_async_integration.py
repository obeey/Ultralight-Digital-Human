#!/usr/bin/env python3
"""
异步推流集成补丁
修改现有系统以使用真正异步的推流
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

def patch_dh_streamer():
    """替换原有的推流器为异步版本"""
    try:
        # 备份原文件
        original_file = "agent/dh_streamer.py"
        backup_file = "agent/dh_streamer_sync_backup.py"
        
        if os.path.exists(original_file):
            if not os.path.exists(backup_file):
                import shutil
                shutil.copy2(original_file, backup_file)
                logger.info(f"已备份原文件: {backup_file}")
            
            # 替换为异步版本
            async_file = "agent/dh_streamer_async.py"
            if os.path.exists(async_file):
                import shutil
                shutil.copy2(async_file, original_file)
                logger.info("已将异步推流器替换为默认推流器")
                return True
            else:
                logger.error(f"异步推流器文件不存在: {async_file}")
                return False
        else:
            logger.error(f"原推流器文件不存在: {original_file}")
            return False
            
    except Exception as e:
        logger.error(f"替换推流器失败: {e}")
        return False

def create_async_wrapper():
    """创建异步包装器，确保兼容性"""
    wrapper_content = '''#!/usr/bin/env python3
"""
异步推流包装器 - 确保与现有系统兼容
"""

import logging
from .dh_streamer_async import AsyncUDPStreamer, UDPStreamer as AsyncUDPStreamerCompat

logger = logging.getLogger(__name__)

# 导出异步推流器作为默认推流器
UDPStreamer = AsyncUDPStreamerCompat

logger.info("已加载异步推流器")
'''
    
    try:
        with open("agent/dh_streamer.py", "w", encoding="utf-8") as f:
            f.write(wrapper_content)
        logger.info("已创建异步推流包装器")
        return True
    except Exception as e:
        logger.error(f"创建包装器失败: {e}")
        return False

def verify_async_integration():
    """验证异步集成是否成功"""
    try:
        # 测试导入
        from agent.dh_streamer import UDPStreamer
        from agent.dh_streamer_async import AsyncUDPStreamer
        
        logger.info("异步推流器导入成功")
        
        # 创建测试配置
        from dataclasses import dataclass
        @dataclass
        class TestConfig:
            udp_port: int = 1234
            stream_loop: bool = False
            output_dir: str = "output"
            temp_dir: str = "temp"
        
        config = TestConfig()
        
        # 测试创建推流器
        streamer = UDPStreamer(config)
        logger.info("异步推流器创建成功")
        
        # 测试异步推流器
        async_streamer = AsyncUDPStreamer(config)
        async_streamer.start()
        logger.info("异步推流器启动成功")
        
        # 清理
        async_streamer.stop()
        streamer.stop()
        
        logger.info("异步集成验证成功")
        return True
        
    except Exception as e:
        logger.error(f"异步集成验证失败: {e}")
        return False

def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("开始异步推流集成...")
    
    # 步骤1: 创建异步包装器
    if create_async_wrapper():
        logger.info("✓ 异步包装器创建成功")
    else:
        logger.error("✗ 异步包装器创建失败")
        return False
    
    # 步骤2: 验证集成
    if verify_async_integration():
        logger.info("✓ 异步集成验证成功")
    else:
        logger.error("✗ 异步集成验证失败")
        return False
    
    logger.info("异步推流集成完成！")
    logger.info("现在可以使用以下命令测试:")
    logger.info("python test_async_streaming.py")
    logger.info("python digital_human_integrated_async.py --mode single --text '测试异步推流'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)