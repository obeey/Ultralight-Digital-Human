# WSL Ubuntu + Windows OBS 使用指南

## 🎯 场景说明
- **WSL Ubuntu**: 运行直播流生成系统
- **Windows 10**: 运行OBS Studio
- **目标**: WSL生成的视频流被Windows OBS接收并直播

## 🔧 支持的解决方案

### 方案1: UDP流 (🌟 新增推荐)
**优点**: 延迟最低，无需额外服务器，OBS原生支持，配置最简单
**缺点**: 无

#### 设置步骤:
1. **启动WSL流系统**:
   ```bash
   # 设置环境变量
   export DEEPSEEK_API_KEY=your_api_key
   
   # 启动UDP模式 (默认配置)
   python3 start_wsl_stream.py
   ```

2. **OBS设置**:
   - 添加来源 → 媒体源
   - **取消勾选"本地文件"**
   - 输入: `udp://localhost:1234`
   - ✅ 完成！OBS将直接接收WSL发送的UDP流

### 方案2: RTMP推流
**优点**: 实时性好，延迟低，OBS原生支持
**缺点**: 需要RTMP服务器

#### 设置步骤:
1. **安装RTMP服务器** (选择一种):
   ```bash
   # 方法1: 使用SRS (推荐)
   docker run --rm -it -p 1935:1935 -p 1985:1985 -p 8080:8080 ossrs/srs:4
   
   # 方法2: 使用nginx-rtmp
   sudo apt install nginx libnginx-mod-rtmp
   ```

2. **启动WSL流系统**:
   ```bash
   # 设置环境变量
   export DEEPSEEK_API_KEY=your_api_key
   
   # 启动RTMP模式
   python3 start_wsl_stream.py
   ```

3. **OBS设置**:
   - 添加来源 → 媒体源
   - 输入: `rtmp://localhost:1935/live/stream`
   - 取消勾选"本地文件"

### 方案3: HTTP-FLV流
**优点**: 无需额外服务器，通过浏览器源接收
**缺点**: 延迟稍高

#### 设置步骤:
1. **修改配置**:
   ```json
   {
     "output_mode": "http_flv",
     "http_port": 8080
   }
   ```

2. **启动系统**:
   ```bash
   python3 start_wsl_stream.py
   ```

3. **OBS设置**:
   - 添加来源 → 浏览器
   - URL: `http://localhost:8080/stream/stream.m3u8`
   - 宽度: 1920, 高度: 1080

### 方案4: 文件共享
**优点**: 最简单，无需网络配置
**缺点**: 不是实时流，有延迟

#### 设置步骤:
1. **修改配置**:
   ```json
   {
     "output_mode": "file",
     "output_dir": "/mnt/c/temp/stream"
   }
   ```

2. **启动系统**:
   ```bash
   python3 start_wsl_stream.py
   ```

3. **OBS设置**:
   - 添加来源 → 媒体源
   - 选择文件: `C:\temp\stream\stream_000001.mp4`
   - 勾选"循环"

## 🚀 快速开始

### 1. 环境准备
```bash
# WSL Ubuntu中
sudo apt update
sudo apt install ffmpeg python3-pip

# 安装Python依赖
pip3 install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑.env文件，设置DEEPSEEK_API_KEY
```

### 2. 选择输出模式
```bash
# UDP模式 (🌟 新推荐，默认配置)
python3 start_wsl_stream.py

# 或编辑wsl_config.json选择其他模式:
# "output_mode": "udp"    # UDP流 (推荐)
# "output_mode": "rtmp"   # RTMP推流
# "output_mode": "http_flv" # HTTP-FLV流
# "output_mode": "file"   # 文件输出
```

### 3. OBS配置
根据选择的模式，按上述步骤配置OBS源

## 🔍 故障排除

### RTMP连接问题
```bash
# 检查端口是否开放
netstat -tlnp | grep 1935

# 测试RTMP服务器
ffmpeg -re -i test.mp4 -c copy -f flv rtmp://localhost:1935/live/test
```

### WSL网络问题
```bash
# 获取WSL IP地址
ip addr show eth0

# Windows中访问WSL服务
# 使用WSL IP地址而不是localhost
```

### 性能优化
```bash
# 增加WSL内存限制
# 在Windows中创建 %UserProfile%\.wslconfig
[wsl2]
memory=4GB
processors=4
```

## 📊 性能对比

| 方案 | 延迟 | 稳定性 | 配置难度 | 推荐度 |
|------|------|--------|----------|--------|
| UDP流 | 极低 | 高 | 极低 | ⭐⭐⭐⭐⭐ |
| RTMP | 低 | 高 | 中 | ⭐⭐⭐⭐ |
| HTTP-FLV | 中 | 中 | 低 | ⭐⭐⭐ |
| 文件共享 | 高 | 高 | 低 | ⭐⭐ |

## 💡 最佳实践

1. **🌟 推荐使用UDP流方案**，延迟最低，配置最简单
2. **确保WSL和Windows防火墙设置正确**
3. **监控系统资源使用情况**
4. **定期清理临时文件**
5. **使用SSD存储提高性能**

## 🚀 UDP流快速设置指南

### WSL端设置:
```bash
# 1. 确保配置文件正确
cat wsl_config.json  # 确认 "output_mode": "udp"

# 2. 启动系统
python3 start_wsl_stream.py
```

### Windows OBS端设置:
1. 打开OBS Studio
2. 点击"来源"区域的"+"
3. 选择"媒体源"
4. **重要**: 取消勾选"本地文件"
5. 在"输入"框中填入: `udp://localhost:1234`
6. 点击"确定"

### 验证连接:
- WSL终端应显示: "✅ UDP流已启动"
- OBS中应能看到视频流
- 延迟应该非常低（< 100ms）

## 🔧 故障排除

### UDP连接问题
```bash
# 检查端口是否被占用
netstat -tulnp | grep 1234

# 测试UDP端口连通性
nc -u localhost 1234
```

### 如果UDP不工作，可以尝试其他端口:
```json
{
  "output_mode": "udp",
  "udp_host": "localhost", 
  "udp_port": 5000
}
```
然后在OBS中使用: `udp://localhost:5000`