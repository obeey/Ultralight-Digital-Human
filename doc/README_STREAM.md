# 蜜雪冰城数字人直播流服务

这是一个基于UDH项目的数字人直播流服务，专门为蜜雪冰城产品销售定制。

## 功能特点

- 🎯 **固定参数**: `--asr hubert --dataset input/mxbc/ --checkpoint checkpoint/195.pth`
- 🤖 **AI内容生成**: 集成Deep Seek API生成蜜雪冰城销售话术
- 📺 **RTMP流输出**: 支持OBS等直播软件接收
- 🍹 **产品库**: 内置蜜雪冰城饮料产品信息
- 🔄 **实时流媒体**: 25fps高质量视频流

## 快速开始

### 1. 环境准备

```bash
# 运行设置脚本
chmod +x setup_stream.sh
./setup_stream.sh
```

### 2. 配置API密钥

```bash
# 设置Deep Seek API密钥
export DEEPSEEK_API_KEY="your_api_key_here"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

### 3. 启动RTMP服务器（可选）

如果使用本地RTMP服务器：

```bash
# 使用Docker启动RTMP服务器
docker run -d -p 1935:1935 -p 8080:8080 tiangolo/nginx-rtmp

# 或者使用其他RTMP服务器
# 如：推流到B站、抖音等平台
```

### 4. 启动数字人流服务

```bash
# 使用默认配置启动
./start_mixue_stream.sh

# 或者手动启动
python3 start_stream.py --rtmp_url rtmp://localhost:1935/live/stream
```

### 5. 在OBS中配置

1. 打开OBS Studio
2. 添加源 → 媒体源
3. 取消勾选"本地文件"
4. 输入: `rtmp://localhost:1935/live/stream`
5. 确定

## 文件结构

```
UDH/
├── start_stream.py          # 简化版流服务主程序
├── digital_human_stream.py  # 完整版流服务（备用）
├── setup_stream.sh          # 环境设置脚本
├── start_mixue_stream.sh    # 启动脚本
├── README_STREAM.md         # 本文档
├── input/mxbc/             # 数据集目录
│   ├── full_body_img/      # 全身图像
│   └── landmarks/          # 关键点文件
└── checkpoint/195.pth      # 模型权重文件
```

## 配置参数

### 固定参数
- `--asr`: hubert (音频特征提取模型)
- `--dataset`: input/mxbc/ (数据集路径)
- `--checkpoint`: checkpoint/195.pth (模型权重)

### 可配置参数
- `--rtmp_url`: RTMP推流地址 (默认: rtmp://localhost:1935/live/stream)

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | Deep Seek API密钥 | 必需 |
| `DEEPSEEK_BASE_URL` | Deep Seek API地址 | https://api.deepseek.com |

## 产品库

内置蜜雪冰城产品：
- 柠檬水 (4元) - 清爽解腻，酸甜可口
- 珍珠奶茶 (6元) - Q弹珍珠，香浓奶茶
- 芋泥啵啵茶 (9元) - 浓郁芋香，啵啵口感
- 草莓奶昔 (8元) - 新鲜草莓，丝滑奶昔
- 冰淇淋 (2元) - 经典甜筒，童年回忆
- 摇摇奶昔 (7元) - 多种口味，摇出惊喜

## 故障排除

### 1. 数字人不动或显示黑屏
- 检查数据集路径: `input/mxbc/full_body_img/` 和 `input/mxbc/landmarks/`
- 确保图像和关键点文件匹配

### 2. RTMP推流失败
- 检查FFmpeg是否安装: `ffmpeg -version`
- 确认RTMP服务器运行状态
- 检查网络连接和防火墙设置

### 3. API调用失败
- 验证DEEPSEEK_API_KEY是否正确
- 检查网络连接
- 查看日志中的错误信息

### 4. OBS无法接收流
- 确认RTMP URL正确
- 检查OBS媒体源设置
- 尝试刷新或重新添加源

## 性能优化

- **CPU使用**: 调整FFmpeg编码参数 `-preset ultrafast`
- **内存使用**: 限制加载的图像数量（当前限制100张）
- **网络带宽**: 调整视频分辨率和帧率

## 扩展功能

### 自定义RTMP地址
```bash
# 推流到B站
python3 start_stream.py --rtmp_url rtmp://live-push.bilivideo.com/live-bvc/YOUR_STREAM_KEY

# 推流到抖音
python3 start_stream.py --rtmp_url rtmp://push-rtmp-f220.douyincdn.com/stage/YOUR_STREAM_KEY
```

### 自定义产品库
编辑 `start_stream.py` 中的 `self.products` 列表，添加新的销售话术。

## 技术支持

如遇问题，请检查：
1. 所有依赖是否正确安装
2. 数据集和模型文件是否存在
3. 环境变量是否正确设置
4. 日志输出中的错误信息

## 更新日志

- v1.0: 基础流媒体功能
- v1.1: 集成Deep Seek API
- v1.2: 优化人脸裁剪逻辑
- v1.3: 添加蜜雪冰城产品库