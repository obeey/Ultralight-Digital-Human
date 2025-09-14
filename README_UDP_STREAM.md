# WSL UDP流直播系统使用指南

## 🎯 功能说明

现在项目已支持在WSL环境下向UDP端口发送音视频流，Windows上的OBS可以直接接收这个UDP流，实现最低延迟的直播效果。

## 🚀 快速开始

### 1. 环境准备

```bash
# 在WSL中安装依赖
sudo apt update
sudo apt install ffmpeg python3-pip

# 安装Python依赖
pip3 install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑.env文件，设置DEEPSEEK_API_KEY
```

### 2. 配置文件

WSL配置文件 `wsl_config.json` 已默认设置为UDP模式：

```json
{
  "output_mode": "udp",
  "udp_host": "localhost",
  "udp_port": 1234
}
```

### 3. 启动系统

```bash
# 启动WSL直播系统
python3 start_wsl_stream.py
```

### 4. OBS设置

1. 打开Windows上的OBS Studio
2. 添加来源 → 媒体源
3. **重要**: 取消勾选"本地文件"
4. 在"输入"框中填入: `udp://localhost:1234`
5. 点击"确定"

## 🧪 测试UDP连接

使用测试脚本验证UDP流是否正常工作：

```bash
# 运行UDP流测试
python3 test_udp_stream.py
```

## 📊 支持的输出模式

| 模式 | 配置值 | 延迟 | 推荐度 | 说明 |
|------|--------|------|--------|------|
| UDP流 | `"udp"` | 极低 | ⭐⭐⭐⭐⭐ | 直接发送到OBS，无需中间服务器 |
| RTMP | `"rtmp"` | 低 | ⭐⭐⭐⭐ | 需要RTMP服务器 |
| HTTP-FLV | `"http_flv"` | 中 | ⭐⭐⭐ | 通过浏览器源接收 |
| 文件输出 | `"file"` | 高 | ⭐⭐ | 保存为文件 |

## 🔧 配置选项

在 `wsl_config.json` 中可以修改以下UDP相关配置：

```json
{
  "output_mode": "udp",
  "udp_host": "localhost",    // UDP目标主机
  "udp_port": 1234,          // UDP端口号
  "video_resolution": "1920x1080",  // 视频分辨率
  "video_fps": 30            // 视频帧率
}
```

## 🔍 故障排除

### 1. UDP连接问题

```bash
# 检查端口是否被占用
netstat -tulnp | grep 1234

# 尝试其他端口
# 修改wsl_config.json中的udp_port，然后在OBS中使用对应端口
```

### 2. 防火墙问题

```bash
# Windows防火墙可能阻止UDP连接
# 在Windows防火墙中允许端口1234的UDP连接
```

### 3. WSL网络问题

```bash
# 获取WSL IP地址
ip addr show eth0

# 如果localhost不工作，尝试使用WSL的实际IP地址
# 在OBS中使用: udp://[WSL_IP]:1234
```

## 💡 最佳实践

1. **使用UDP模式获得最低延迟**
2. **确保WSL和Windows防火墙正确配置**
3. **监控系统资源使用情况**
4. **使用SSD存储提高性能**
5. **定期清理临时文件**

## 🆚 与Windows版本的区别

| 特性 | Windows版本 | WSL版本 |
|------|-------------|---------|
| UDP流 | ✅ 支持 | ✅ 支持 |
| 虚拟摄像头 | ✅ 支持 | ❌ 不支持 |
| RTMP推流 | ✅ 支持 | ✅ 支持 |
| 文件输出 | ✅ 支持 | ✅ 支持 |
| 路径格式 | Windows路径 | Linux路径 |

## 📝 使用示例

```bash
# 1. 启动WSL系统
python3 start_wsl_stream.py

# 2. 输入直播主题
请输入直播主题 (默认: 人工智能的发展趋势): 今天聊聊机器学习

# 3. 系统输出
✅ 检测到WSL环境
✅ FFmpeg 已安装
✅ 配置检查完成
📡 UDP流模式: localhost:1234
💡 在Windows OBS中添加媒体源:
   取消勾选'本地文件'
   输入: udp://localhost:1234
   ✅ 这样Windows OBS可以直接接收WSL发送的UDP流!

📺 开始直播: 今天聊聊机器学习
按 Ctrl+C 停止直播
```

## 🎬 完整工作流程

1. **WSL端**: 运行 `python3 start_wsl_stream.py`
2. **系统**: 生成AI内容 → 转换为语音 → 创建视频 → 推送UDP流
3. **Windows端**: OBS接收UDP流 → 直播到平台

这样就实现了WSL和Windows之间的无缝音视频流传输！