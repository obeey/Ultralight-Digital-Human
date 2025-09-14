#!/bin/bash
# 设置虚拟摄像头环境

echo "设置虚拟摄像头环境..."

# 检查是否为Linux系统
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到Linux系统，安装v4l2loopback..."
    
    # 安装v4l2loopback
    sudo apt update
    sudo apt install -y v4l2loopback-dkms v4l2loopback-utils
    
    # 加载v4l2loopback模块
    sudo modprobe v4l2loopback devices=1 video_nr=0 card_label="Virtual Camera" exclusive_caps=1
    
    # 检查虚拟摄像头设备
    if [ -e /dev/video0 ]; then
        echo "虚拟摄像头设备 /dev/video0 创建成功"
        v4l2-ctl --list-devices
    else
        echo "虚拟摄像头设备创建失败"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到macOS系统"
    echo "请手动安装OBS Studio并启用虚拟摄像头功能"
    echo "或者使用其他虚拟摄像头软件如CamTwist"
    
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    echo "检测到Windows系统"
    echo "请安装OBS Studio并启用虚拟摄像头插件"
    echo "或者使用其他虚拟摄像头软件"
    
else
    echo "未知操作系统: $OSTYPE"
    exit 1
fi

echo "虚拟摄像头环境设置完成"