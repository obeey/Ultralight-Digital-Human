# 实时直播流系统

基于DeepSeek API文案生成、GPT-SoVITS语音合成和FFmpeg视频流的实时直播系统。

**🎯 原生支持Windows 10 + OBS Studio** - 详见 [Windows使用指南](WINDOWS_GUIDE.md)

**💡 简化方案**: 直接在Windows下运行，与OBS在同一系统，无需WSL或虚拟机

## 功能特性

- 🤖 **智能文案生成**: 使用DeepSeek API一次性生成长篇直播文案
- 🎵 **语音合成**: 集成GPT-SoVITS进行高质量语音合成
- 📹 **视频流输出**: 支持输出到OBS虚拟摄像头
- ⚡ **实时处理**: 多线程并发处理，空间换时间优化
- 🔄 **缓冲机制**: 预生成内容缓冲，确保流畅播放

## 系统架构

```
DeepSeek API → 文案分割 → 多线程音频生成 → 视频合成 → 虚拟摄像头
     ↓
   缓冲池（预生成内容）
```

## 安装步骤

### 1. 环境准备

```bash
# 安装Python依赖
pip install -r requirements.txt

# 设置虚拟摄像头（Linux）
chmod +x setup_virtual_camera.sh
./setup_virtual_camera.sh
```

### 2. 配置设置

**环境变量配置**（推荐）：
```bash
# 方法1：直接设置环境变量
export DEEPSEEK_API_KEY=your_api_key_here

# 方法2：使用.env文件
cp .env.example .env
# 编辑.env文件，填入实际的API密钥
```

**系统配置**：
编辑 `config.json` 文件调整其他设置：
```json
{
  "gpt_sovits_path": "../GPT-SoVITS",
  "virtual_camera_device": "/dev/video0"
}
```

### 3. 启动系统

**Windows用户（推荐）**:
```cmd
start_windows.bat
```

**Linux用户**:
```bash
./quick_start.sh
```

## 技术方案详解

### 1. 视频流输出方案

**推荐方案**: 虚拟摄像头设备
- Linux: 使用 `v4l2loopback` 创建虚拟摄像头
- Windows: 使用 OBS Virtual Camera 插件
- macOS: 使用 OBS Studio 或 CamTwist

**命令示例**:
```bash
# 创建虚拟摄像头设备
sudo modprobe v4l2loopback devices=1 video_nr=0

# FFmpeg推送视频流
ffmpeg -re -i input.mp4 -f v4l2 /dev/video0
```

### 2. 音频合成集成

- 封装GPT-SoVITS调用接口
- 支持批量文本转语音
- 实现音频缓存机制
- 多线程并发处理

### 3. 文案生成策略

- DeepSeek API一次性生成1500-2000字长篇文案
- 按句子智能分割处理
- 实现文案预生成缓冲池
- 动态补充新内容

### 4. 性能优化

**空间换时间策略**:
- 预生成音视频缓存
- 队列管理系统
- 智能缓冲区监控

**多线程并发**:
- 文案生成线程
- 音频合成线程池
- 视频生成线程
- 流推送线程

## 使用流程

1. **启动阶段**: 生成长篇文案和对应的音视频作为缓冲
2. **运行阶段**: 按句子实时生成音视频流
3. **缓冲管理**: 动态监控缓冲区，及时补充新内容
4. **流输出**: 持续推送到虚拟摄像头设备

## 系统要求

- Python 3.8+
- FFmpeg
- GPT-SoVITS (需要单独安装)
- Linux: v4l2loopback
- 足够的磁盘空间用于缓存

## 故障排除

### 虚拟摄像头问题
```bash
# 检查设备
ls /dev/video*
v4l2-ctl --list-devices

# 重新加载模块
sudo modprobe -r v4l2loopback
sudo modprobe v4l2loopback devices=1 video_nr=0
```

### GPT-SoVITS集成问题
- 确保GPT-SoVITS路径正确
- 检查参考音频文件是否存在
- 验证合成命令参数

### 性能优化建议
- 增加缓冲区大小
- 调整工作线程数量
- 使用SSD存储临时文件
- 监控系统资源使用

## 扩展功能

- 支持多种语音模型
- 添加视频特效和转场
- 实现实时互动功能
- 支持多平台直播推流

## 许可证

MIT License