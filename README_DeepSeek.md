# 数字人直播系统 - DeepSeek AI版本

## 🎯 功能特点

- **AI自动生成话术**: 使用DeepSeek API自动生成连续的直播带货话术
- **WeNet特征提取**: 使用WeNet替代HuBERT，提升特征提取速度
- **连续视频推流**: 按句子逐一生成数字人视频并实时推流
- **音视频同步**: 完美同步TTS语音和数字人视频
- **自动化运行**: 系统自动生成话术，无需人工干预

## 🚀 快速开始

### 1. 配置DeepSeek API

通过环境变量设置 DeepSeek API 密钥（不在配置文件中保存密钥）：

- 临时（当前终端会话）：
```bash
export DEEPSEEK_API_KEY="sk-your-actual-deepseek-api-key-here"
```

- 永久（追加到 ~/.bashrc 并加载）：
```bash
echo 'export DEEPSEEK_API_KEY="sk-your-actual-deepseek-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

配置项仍在 `config.json` 中维护，但不包含密钥：
```json
{
  "deepseek_url": "https://api.deepseek.com/v1/chat/completions",
  "tts_url": "http://127.0.0.1:9880/tts",
  "reference_audio": "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC",
  "reference_text": "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后",
  "dataset_dir": "input/mxbc_0913/",
  "checkpoint_path": "checkpoint/195.pth",
  "udp_port": 1234,
  "temp_dir": "temp",
  "script_length": 10,
  "script_interval": 30.0
}
```

### 2. 启动系统

```bash
python3 digital_human_deepseek.py
```

### 3. 设置VLC播放器

在VLC中打开网络流：`udp://@172.18.0.1:1234`

## 📋 系统架构

```
DeepSeek API → 话术生成 → TTS音频 → WeNet特征 → 数字人推理 → 视频推流
     ↓              ↓           ↓           ↓            ↓
   AI话术        语音合成    特征提取    视频生成      UDP推流
```

## ⚙️ 配置说明

### config.json 参数详解

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `deepseek_api_key` | DeepSeek API密钥 | 使用环境变量 DEEPSEEK_API_KEY，不在配置文件中保存 |
| `script_length` | 每次生成的句子数量 | 10 |
| `script_interval` | 生成新话术的间隔(秒) | 30.0 |
| `udp_port` | UDP推流端口 | 1234 |
| `tts_url` | TTS服务地址 | http://127.0.0.1:9880/tts |

### 系统要求

- Python 3.8+
- PyTorch 2.6.0+
- FFmpeg (支持libopenh264)
- 运行中的TTS服务
- DeepSeek API访问权限

## 🎬 使用流程

### 自动模式（推荐）

1. 启动系统后输入产品信息
2. 系统自动调用DeepSeek API生成话术
3. 自动进行TTS合成和数字人视频生成
4. 实时推流到VLC播放器

### 手动模式

- 在运行过程中可以手动输入文本
- 手动文本会立即加入生成队列
- 支持与AI生成话术混合使用

## 📊 性能优化

### WeNet vs HuBERT

- **WeNet**: 更快的特征提取速度
- **帧率**: WeNet使用20fps，HuBERT使用25fps
- **特征形状**: WeNet `[128,16,32]`，HuBERT `[16,32,32]`

### 网络优化

- UDP包大小: 512字节（提高兼容性）
- 视频比特率: 1000k（平衡质量和带宽）
- 音频比特率: 64k（优化传输）

## 🔧 故障排除

### 常见问题

1. **DeepSeek API调用失败**
   - 检查是否已设置环境变量：`echo $DEEPSEEK_API_KEY`
   - 确认API密钥是否正确有效
   - 确认网络连接正常
   - 查看API配额是否充足

2. **VLC无法接收视频**
   - 确认使用WSL地址: `172.18.0.1:1234`
   - 检查防火墙设置
   - 尝试重启VLC

3. **WeNet特征提取失败**
   - 检查依赖库是否完整安装
   - 确认音频文件格式正确
   - 查看错误日志详情

### 日志查看

系统会输出详细的运行日志，包括：
- DeepSeek API调用状态
- TTS音频生成进度
- WeNet特征提取时间
- 视频生成和推流状态

## 🎯 自定义话术

### 修改提示词

在 `DeepSeekClient.generate_live_script()` 方法中可以自定义提示词：

```python
prompt = f"""
你是一个专业的直播带货主播，正在为"{product_info}"进行直播销售。
请生成{self.config.script_length}句自然流畅的直播话术...
"""
```

### 话术风格调整

- 修改 `temperature` 参数控制创意度
- 调整 `script_length` 控制每批生成数量
- 设置 `script_interval` 控制生成频率

## 📈 扩展功能

### 添加新的AI模型

可以轻松替换DeepSeek为其他AI模型：

1. 修改 `DeepSeekClient` 类
2. 更新API调用逻辑
3. 调整提示词格式

### 集成更多TTS引擎

支持集成其他TTS服务：

1. 修改 `TTSClient` 类
2. 更新音频生成接口
3. 调整音频格式处理

## 🔒 安全注意事项

- 不要在代码中硬编码API密钥
- 使用配置文件管理敏感信息
- 定期更新API密钥
- 监控API使用量和费用

## 📞 技术支持

如遇到问题，请检查：

1. 系统日志输出
2. 配置文件格式
3. 网络连接状态
4. 依赖库版本

---

**注意**: 请确保已正确配置DeepSeek API密钥，否则系统将使用备用话术运行。