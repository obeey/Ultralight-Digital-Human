@echo off
echo 🔧 Windows 10 环境安装脚本
echo ================================

REM 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo ⚠️  建议以管理员身份运行此脚本
)

echo 📦 安装Python依赖...
pip install -r requirements.txt

echo 📁 创建必要目录...
if not exist "temp" mkdir temp
if not exist "C:\temp\stream" mkdir "C:\temp\stream"

echo 📋 复制配置文件...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env"
        echo ✅ 已创建 .env 文件，请编辑并填入API密钥
    )
)

if not exist "windows_config.json" (
    echo ❌ windows_config.json 不存在
) else (
    echo ✅ 配置文件已就绪
)

echo.
echo 🎉 安装完成！
echo.
echo 📝 下一步：
echo 1. 编辑 .env 文件，设置 DEEPSEEK_API_KEY
echo 2. 确保已安装 FFmpeg 并添加到 PATH
echo 3. 安装 OBS Studio
echo 4. 运行 start_windows.bat 启动系统
echo.

pause