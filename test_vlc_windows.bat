@echo off
echo ========================================
echo        VLC UDP 推流接收测试
echo ========================================
echo.
echo 请确保推流正在运行 (在WSL中运行推流脚本)
echo.
echo 尝试启动VLC接收UDP流...
echo.

REM 尝试不同的VLC路径
set VLC_PATH1="C:\Program Files\VideoLAN\VLC\vlc.exe"
set VLC_PATH2="C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
set VLC_PATH3="vlc.exe"

echo 方法1: 使用 udp://@172.18.0.1:1234 (WSL网络地址)
if exist %VLC_PATH1% (
    echo 找到VLC: %VLC_PATH1%
    %VLC_PATH1% udp://@172.18.0.1:1234
    goto :end
)

if exist %VLC_PATH2% (
    echo 找到VLC: %VLC_PATH2%
    %VLC_PATH2% udp://@172.18.0.1:1234
    goto :end
)

echo 尝试系统PATH中的VLC...
%VLC_PATH3% udp://@172.18.0.1:1234 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo VLC启动失败，请手动操作:
    echo ========================================
    echo 1. 打开VLC媒体播放器
    echo 2. 点击 "媒体" -^> "打开网络串流"
    echo 3. 输入URL: udp://@172.18.0.1:1234
    echo 4. 点击 "播放"
    echo.
    echo 如果看不到视频，尝试这些URL:
    echo - udp://172.18.0.1:1234
    echo - udp://@172.18.0.1:1234
    echo - udp://@:1234
    echo ========================================
)

:end
pause
