#!/usr/bin/env python3
"""
环境变量加载工具
支持从.env文件加载环境变量
"""

import os
from pathlib import Path

def load_env_file(env_path: str = ".env"):
    """从.env文件加载环境变量"""
    env_file = Path(env_path)
    
    if not env_file.exists():
        return False
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
        
        print(f"✅ 已从 {env_path} 加载环境变量")
        return True
    except Exception as e:
        print(f"❌ 加载环境变量失败: {e}")
        return False

def check_required_env():
    """检查必需的环境变量"""
    required_vars = ['DEEPSEEK_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必需的环境变量:")
        for var in missing_vars:
            print(f"   {var}")
        print("\n请设置这些环境变量或创建.env文件")
        return False
    
    print("✅ 所有必需的环境变量已设置")
    return True

if __name__ == "__main__":
    # 尝试加载.env文件
    load_env_file()
    
    # 检查必需的环境变量
    check_required_env()