#!/bin/bash
# 快速启动脚本

echo "🚀 UDH实时直播流系统 - 快速启动"
echo "=================================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 1 ]]; then
    echo "✅ Python版本: $(python3 --version)"
else
    echo "❌ 需要Python 3.8+，当前版本: $(python3 --version)"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

# 设置虚拟摄像头
echo "📹 设置虚拟摄像头..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    chmod +x setup_virtual_camera.sh
    ./setup_virtual_camera.sh
else
    echo "⚠️  非Linux系统，请手动配置虚拟摄像头"
fi

# 检查配置
echo "⚙️  检查配置..."
if [ ! -f "config.json" ]; then
    echo "❌ config.json不存在"
    exit 1
fi

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ] && [ ! -f ".env" ]; then
    echo "❌ 请设置环境变量 DEEPSEEK_API_KEY 或创建 .env 文件"
    echo "   可以复制 .env.example 为 .env 并填入实际值"
    exit 1
fi

# 运行测试
echo "🧪 运行组件测试..."
python3 test_components.py

echo ""
echo "🎬 准备启动直播系统..."
echo "按任意键继续，或Ctrl+C取消"
read -n 1 -s

# 启动系统
echo "🔴 启动直播..."
python3 start_stream.py