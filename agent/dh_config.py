#!/usr/bin/env python3
"""
数字人系统配置模块
"""

import os
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DigitalHumanConfig:
    """数字人系统配置"""
    # TTS配置
    tts_url: str = "http://127.0.0.1:9880/tts"
    reference_audio: str = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
    reference_text: str = "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后"
    
    # 推理配置
    checkpoint_path: str = "checkpoint/195.pth"
    dataset_path: str = "input/mxbc_0913/"
    
    # DeepSeek配置
    product_info: str = "蜜雪冰城优惠券"
    auto_start: bool = True
    
    # 段落生成配置
    paragraph_length: int = 200  # 每段话术长度（字符数）
    paragraph_interval: float = 60.0  # 段落生成间隔（秒）
    
    # 并行配置
    parallel_workers: int = 2
    text_queue_size: int = 50
    video_queue_size: int = 10
    
    # 推流配置
    enable_streaming: bool = True
    udp_port: int = 1234
    stream_loop: bool = True    # 循环推流防止中断
    
    # 输出配置
    output_dir: str = "output"
    temp_dir: str = "temp"
    save_to_file: bool = True
    
    @classmethod
    def from_config_file(cls, config_path: str = "config.json"):
        """从配置文件加载"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = f.read()
                if not config_data.strip():
                    logger.warning(f"配置文件 {config_path} 为空，使用默认配置")
                    return cls()
                
                config_dict = json.loads(config_data)
                # 忽略 deepseek_api_key，从环境变量读取
                config_dict.pop('deepseek_api_key', None)
                return cls(**config_dict)
        except FileNotFoundError:
            logger.warning(f"配置文件 {config_path} 不存在，使用默认配置")
            return cls()
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 {config_path} 格式错误: {e}，使用默认配置")
            return cls()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls()