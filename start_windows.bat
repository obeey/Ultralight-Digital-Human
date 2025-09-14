@echo off
echo 🚀 启动 Windows 10 实时直播流系统
echo =====================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到FFmpeg，请先安装FFmpeg并添加到PATH
    echo 下载地址: https://ffmpeg.org/download.html
    pause
    exit /b 1
)

REM 检查配置文件
if not exist "windows_config.json" (
    echo ❌ 配置文件 windows_config.json 不存在
    pause
    exit /b 1
)

REM 检查环境变量文件
if not exist ".env" (
    echo ⚠️  .env 文件不存在，请确保已设置 DEEPSEEK_API_KEY 环境变量
)

echo ✅ 环境检查完成
echo.

REM 启动系统
python start_windows.py

pause