#!/bin/bash
# 启动简单的RTMP服务器

echo "🚀 启动RTMP服务器"

# 检查Docker是否可用
if command -v docker &> /dev/null; then
    echo "使用Docker启动SRS RTMP服务器..."
    docker run --rm -d --name srs-server \
        -p 1935:1935 \
        -p 1985:1985 \
        -p 8080:8080 \
        ossrs/srs:4
    
    if [ $? -eq 0 ]; then
        echo "✅ SRS RTMP服务器已启动"
        echo "📡 RTMP推流地址: rtmp://localhost:1935/live/stream"
        echo "🌐 HTTP-FLV播放地址: http://localhost:8080/live/stream.flv"
        echo "🎮 管理界面: http://localhost:1985"
    else
        echo "❌ SRS服务器启动失败"
    fi
else
    echo "❌ Docker未安装，请手动安装RTMP服务器"
    echo "推荐使用以下方法之一:"
    echo "1. 安装Docker并运行SRS"
    echo "2. 安装nginx-rtmp: sudo apt install nginx libnginx-mod-rtmp"
    echo "3. 使用OBS Studio内置的RTMP服务器"
fi