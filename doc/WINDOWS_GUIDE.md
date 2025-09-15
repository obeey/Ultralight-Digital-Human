# Windows 10 使用指南

## 🎯 简化方案
直接在Windows 10下运行直播流系统，与OBS在同一系统中，无需WSL或虚拟机。

## 🔧 环境准备

### 1. 安装必需软件
- **Python 3.8+**: https://www.python.org/downloads/
- **FFmpeg**: https://ffmpeg.org/download.html
- **OBS Studio**: https://obsproject.com/

### 2. 配置环境变量
```cmd
# 方法1: 设置系统环境变量
set DEEPSEEK_API_KEY=your_api_key_here

# 方法2: 创建.env文件
copy .env.example .env
# 编辑.env文件，填入API密钥
```

### 3. 安装Python依赖
```cmd
pip install -r requirements.txt
```

## 🚀 快速启动

### 方法1: 一键启动（推荐）
```cmd
start_windows.bat
```

### 方法2: 手动启动
```cmd
python start_windows.py
```

## 📹 OBS配置

### UDP流模式（推荐）
1. **在OBS中添加媒体源**
2. **设置URL**: `udp://localhost:1234`
3. **取消勾选"本地文件"**

### 文件模式（最简单）
1. **在OBS中添加媒体源**
2. **选择文件**: `C:\temp\stream\stream_000001.mp4`
3. **勾选"循环"**

## ⚙️ 配置选项

编辑 `windows_config.json`:

```json
{
  "output_mode": "udp",  // udp/file/rtmp
  "video_resolution": "1920x1080",
  "video_fps": 30,
  "buffer_size": 10
}
```

### 输出模式说明
- **udp**: UDP流，OBS通过媒体源接收（推荐）
- **file**: 文件输出，OBS读取视频文件
- **rtmp**: RTMP推流（需要RTMP服务器）

## 🔍 故障排除

### Python相关
```cmd
# 检查Python版本
python --version

# 检查pip
pip --version

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

### FFmpeg相关
```cmd
# 检查FFmpeg
ffmpeg -version

# 如果提示找不到命令，需要：
# 1. 下载FFmpeg: https://ffmpeg.org/download.html
# 2. 解压到C:\ffmpeg
# 3. 将C:\ffmpeg\bin添加到系统PATH
```

### 性能优化
1. **关闭不必要的后台程序**
2. **确保有足够的磁盘空间**
3. **调整视频分辨率和帧率**

## 💡 使用技巧

### 1. 多开OBS场景
- 可以在OBS中创建多个场景
- 一个场景用于接收直播流
- 其他场景用于添加overlay、文字等

### 2. 录制和直播同时进行
- OBS可以同时录制和推流
- 直播流系统提供视频源
- OBS负责最终的直播推送

### 3. 自定义视频效果
- 在OBS中添加滤镜
- 调整颜色、亮度等
- 添加背景音乐

## 📊 性能参考

| 配置 | CPU使用率 | 内存使用 | 推荐场景 |
|------|-----------|----------|----------|
| 1080p@30fps | 15-25% | 2-4GB | 高质量直播 |
| 720p@30fps | 10-20% | 1-3GB | 标准直播 |
| 480p@30fps | 5-15% | 1-2GB | 低配置电脑 |

## 🎮 完整工作流程

1. **准备阶段**:
   ```cmd
   # 设置API密钥
   set DEEPSEEK_API_KEY=your_key
   
   # 启动系统
   start_windows.bat
   ```

2. **OBS配置**:
   - 启动OBS Studio
   - 添加媒体源（UDP流或文件）
   - 添加场景和源

3. **开始直播**:
   - 在直播流系统中输入主题
   - 系统自动生成内容
   - OBS接收视频流并推送到直播平台

这样就实现了完整的AI驱动直播流程！