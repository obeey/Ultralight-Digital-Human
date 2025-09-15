#!/usr/bin/env python3
"""
网络工具模块 - 自动检测WSL网络接口IP地址
"""

import re
import subprocess
import logging
import socket
import platform
from typing import Optional

logger = logging.getLogger(__name__)

def get_wsl_host_ip() -> Optional[str]:
    """
    自动获取WSL主机的IP地址
    支持多种检测方法，确保在不同环境下都能正确获取IP
    """
    
    # 方法1: 通过/etc/resolv.conf获取（WSL2推荐方法）
    try:
        with open('/etc/resolv.conf', 'r') as f:
            content = f.read()
            # 查找nameserver行
            match = re.search(r'nameserver\s+(\d+\.\d+\.\d+\.\d+)', content)
            if match:
                ip = match.group(1)
                if _validate_ip(ip):
                    logger.info(f"通过/etc/resolv.conf获取WSL主机IP: {ip}")
                    return ip
    except Exception as e:
        logger.debug(f"方法1失败: {e}")
    
    # 方法2: 通过环境变量WSL_HOST_IP
    try:
        import os
        wsl_host_ip = os.environ.get('WSL_HOST_IP')
        if wsl_host_ip and _validate_ip(wsl_host_ip):
            logger.info(f"通过环境变量获取WSL主机IP: {wsl_host_ip}")
            return wsl_host_ip
    except Exception as e:
        logger.debug(f"方法2失败: {e}")
    
    # 方法3: 通过ip route命令获取默认网关
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # 解析输出: default via 172.20.240.1 dev eth0
            match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                ip = match.group(1)
                if _validate_ip(ip):
                    logger.info(f"通过ip route获取WSL主机IP: {ip}")
                    return ip
    except Exception as e:
        logger.debug(f"方法3失败: {e}")
    
    # 方法4: 通过网络接口信息获取
    try:
        result = subprocess.run(['ip', 'addr', 'show'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # 查找eth0接口的网关IP（通常是.1结尾）
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and 'eth0' in result.stdout:
                    match = re.search(r'inet (\d+\.\d+\.\d+)\.\d+/\d+', line)
                    if match:
                        network = match.group(1)
                        gateway_ip = f"{network}.1"
                        if _validate_ip(gateway_ip):
                            logger.info(f"通过网络接口推断WSL主机IP: {gateway_ip}")
                            return gateway_ip
    except Exception as e:
        logger.debug(f"方法4失败: {e}")
    
    # 方法5: 尝试连接常见的WSL主机IP范围
    common_ranges = [
        "172.20.240.1",  # 用户提供的IP
        "172.18.0.1",    # 当前代码中的IP
        "172.16.0.1",
        "192.168.1.1",
        "10.0.0.1"
    ]
    
    for ip in common_ranges:
        if _test_connectivity(ip):
            logger.info(f"通过连通性测试确认WSL主机IP: {ip}")
            return ip
    
    # 如果所有方法都失败，返回默认值
    default_ip = "172.20.240.1"
    logger.warning(f"无法自动检测WSL主机IP，使用默认值: {default_ip}")
    return default_ip

def get_windows_wsl_interface_ip() -> Optional[str]:
    """
    在Windows系统上获取WSL网络接口的IP地址
    通过解析ipconfig命令输出
    """
    try:
        # 执行ipconfig命令
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        
        output = result.stdout
        lines = output.split('\n')
        
        # 查找WSL网络适配器
        wsl_section = False
        for i, line in enumerate(lines):
            # 检测WSL网络适配器标识
            if 'vEthernet (WSL)' in line or 'WSL' in line:
                wsl_section = True
                continue
            
            # 如果在WSL部分，查找IPv4地址
            if wsl_section and 'IPv4 Address' in line:
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    ip = match.group(1)
                    if _validate_ip(ip):
                        logger.info(f"通过Windows ipconfig获取WSL接口IP: {ip}")
                        return ip
            
            # 如果遇到下一个适配器，退出WSL部分
            if wsl_section and line.strip() and 'adapter' in line.lower():
                wsl_section = False
    
    except Exception as e:
        logger.debug(f"Windows WSL接口IP检测失败: {e}")
    
    return None

def _validate_ip(ip: str) -> bool:
    """验证IP地址格式是否正确"""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def _test_connectivity(ip: str, port: int = 80, timeout: float = 2.0) -> bool:
    """测试到指定IP的连通性"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def get_optimal_stream_ip() -> str:
    """
    获取最优的推流目标IP地址
    综合多种检测方法，返回最可靠的IP地址
    """
    logger.info("开始自动检测WSL主机IP地址...")
    
    # 检测当前运行环境
    system = platform.system().lower()
    
    if system == 'linux':
        # 在WSL环境中运行
        ip = get_wsl_host_ip()
    elif system == 'windows':
        # 在Windows环境中运行
        ip = get_windows_wsl_interface_ip()
        if not ip:
            ip = get_wsl_host_ip()  # 备用方法
    else:
        # 其他系统，使用通用方法
        ip = get_wsl_host_ip()
    
    if ip:
        logger.info(f"✅ 自动检测到最优推流IP: {ip}")
        return ip
    else:
        # 最后的备用方案
        fallback_ip = "172.20.240.1"
        logger.warning(f"⚠️ 无法自动检测IP，使用备用地址: {fallback_ip}")
        return fallback_ip

if __name__ == "__main__":
    # 测试脚本
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 WSL网络IP自动检测测试")
    print("=" * 40)
    
    ip = get_optimal_stream_ip()
    print(f"检测结果: {ip}")
    
    # 测试连通性
    if _test_connectivity(ip, 1234, 1.0):
        print(f"✅ IP {ip} 连通性测试通过")
    else:
        print(f"⚠️ IP {ip} 连通性测试失败（可能端口未开放）")