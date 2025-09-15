# 蜜雪冰城数字人外部流服务

这是一个支持外部设备观看的数字人直播流服务，其他电脑可以通过VLC、OBS或浏览器观看。

## 🎯 功能特点

- 📺 **外部访问**: 其他电脑可通过网络观看
- 🌐 **多种协议**: 支持HTTP-HLS和RTMP推流
- 📱 **跨平台**: VLC、OBS、浏览器都可观看
- 🤖 **AI内容**: Deep Seek API生成销售话术
- 🍹 **蜜雪冰城**: 专业饮料销售数字人

## 🚀 快速开始

### 方式1: HTTP流（推荐）
适合VLC播放器、浏览器观看

```bash
# 启动HTTP流服务
python3 stream_to_external.py --mode http --port 8080

# 其他设备观看地址
# http://你的服务器IP:8080/stream.m3u8
```

### 方式2: RTMP推流
推流到外部RTMP服务器

```bash
# 推流到外部服务器
python3 stream_to_external.py --mode rtmp --rtmp_url rtmp://your-server.com/live/stream
```

## 📱 观看方式

### VLC播放器
1. 打开VLC
2. 媒体 → 打开网络串流
3. 输入: `http://服务器IP:8080/stream.m3u8`
4. 播放

### OBS Studio
1. 添加源 → 媒体源
2. 取消勾选"本地文件"
3. 输入: `http://服务器IP:8080/stream.m3u8`
4. 确定

### 浏览器（支持HLS的）
直接访问: `http://服务器IP:8080/stream.m3u8`

### 手机观看
- iOS Safari: 直接打开链接
- Android: 使用VLC或MX Player

## 🔧 配置说明

### 环境变量
```bash
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

### 命令参数
```bash
python3 stream_to_external.py [选项]

选项:
  --mode {http,rtmp}    流模式 (默认: http)
  --port PORT          HTTP端口 (默认: 8080)
  --rtmp_url URL       RTMP服务器地址 (rtmp模式必需)
```

## 📊 使用场景

### 场景1: 局域网观看
```bash
# 服务器启动
python3 stream_to_external.py --mode http --port 8080

# 局域网内其他设备观看
# http://192.168.1.100:8080/stream.m3u8
```

### 场景2: 推流到直播平台
```bash
# 推流到B站
python3 stream_to_external.py --mode rtmp --rtmp_url rtmp://live-push.bilivideo.com/live-bvc/YOUR_KEY

# 推流到抖音
python3 stream_to_external.py --mode rtmp --rtmp_url rtmp://push-rtmp-f220.douyincdn.com/stage/YOUR_KEY
```

### 场景3: 自建RTMP服务器
```bash
# 推流到自己的RTMP服务器
python3 stream_to_external.py --mode rtmp --rtmp_url rtmp://your-server.com:1935/live/stream
```

## 🌐 网络配置

### 防火墙设置
```bash
# 开放HTTP端口
sudo ufw allow 8080

# 开放RTMP端口（如果需要）
sudo ufw allow 1935
```

### 获取服务器IP
```bash
# 查看本机IP
ip addr show
# 或
hostname -I
```

## 🔍 故障排除

### 1. 无法观看流
- 检查防火墙是否开放端口
- 确认IP地址是否正确
- 检查FFmpeg是否安装

### 2. 流断断续续
- 检查网络带宽
- 降低视频分辨率或帧率
- 检查服务器性能

### 3. API调用失败
- 验证DEEPSEEK_API_KEY
- 检查网络连接
- 查看日志错误信息

## 📈 性能优化

### 降低延迟
```bash
# 使用更快的编码预设
# 在代码中修改 '-preset', 'ultrafast'
```

### 调整质量
```bash
# 修改分辨率（在代码中）
# '-s', '1280x720'  # 可改为 '854x480' 或 '640x360'
```

### 网络优化
- 使用有线网络连接
- 确保上行带宽充足
- 考虑使用CDN加速

## 🎬 直播平台配置

### B站直播
1. 获取推流地址和密钥
2. 使用RTMP模式推流
3. 在B站后台开始直播

### 抖音直播
1. 申请直播权限
2. 获取推流地址
3. 配置OBS或直接推流

### YouTube直播
1. 启用直播功能
2. 获取流密钥
3. 推流到YouTube RTMP服务器

## 📝 技术细节

- **视频编码**: H.264
- **分辨率**: 1280x720
- **帧率**: 25fps
- **协议**: HLS (HTTP) / RTMP
- **延迟**: 2-5秒（HLS）/ 1-3秒（RTMP）

## 🆘 技术支持

如遇问题，请检查：
1. FFmpeg是否正确安装
2. 网络连接是否正常
3. 防火墙配置是否正确
4. 数据集文件是否存在
5. 日志中的错误信息