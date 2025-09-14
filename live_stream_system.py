"""
通用实时直播流系统
支持UDP、RTMP、文件输出等多种模式
适用于WSL和Linux环境
"""

import asyncio
import threading
import queue
import subprocess
import json
import time
import os
import logging
import socket
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StreamConfig:
    """流配置"""
    deepseek_base_url: str = "https://api.deepseek.com"
    gpt_sovits_path: str = "../GPT-SoVITS"
    
    # 输出模式配置
    output_mode: str = "udp"  # udp, file, rtmp, http_flv
    
    # UDP配置
    udp_host: str = "localhost"
    udp_port: int = 1234
    
    # RTMP配置
    rtmp_url: str = "rtmp://localhost:1935/live/stream"
    
    # HTTP配置
    http_port: int = 8080
    http_host: str = "0.0.0.0"
    
    # 文件输出配置
    output_dir: str = "/tmp/stream"
    
    # 通用配置
    buffer_size: int = 10
    max_workers: int = 4
    video_resolution: str = "1920x1080"
    video_fps: int = 30

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, base_url: str):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_long_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """生成长篇文案"""
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            return f"关于{prompt}的内容生成失败，请稍后重试。"

class GPTSoVITSClient:
    """GPT-SoVITS客户端"""
    
    def __init__(self, sovits_path: str):
        self.sovits_path = sovits_path
        self.api_url = "http://127.0.0.1:9880"
    
    def generate_audio(self, text: str, output_path: str) -> bool:
        """生成音频"""
        try:
            # 使用正确的参考音频文件路径
            ref_audio_path = "/mnt/e/CYC/projects/live-selling/assets/250911/reference.FLAC"
            
            # 检查参考音频文件是否存在
            if not os.path.exists(ref_audio_path):
                logger.error(f"参考音频文件不存在: {ref_audio_path}")
                return False
            
            # 按照GPT-SoVITS API v2的正确格式发送请求
            response = requests.post(
                f"{self.api_url}/tts",
                json={
                    "text": text,
                    "text_lang": "zh",
                    "ref_audio_path": ref_audio_path,
                    "aux_ref_audio_paths": [],
                    "prompt_lang": "zh",
                    "prompt_text": "宝宝，先让我们点击右下角小黄车里头，您点击任意一个链接点进去以后",
                    "top_k": 5,
                    "top_p": 1,
                    "temperature": 1,
                    "text_split_method": "cut5",
                    "batch_size": 1,
                    "batch_threshold": 0.75,
                    "split_bucket": True,
                    "speed_factor": 1.0,
                    "fragment_interval": 0.3,
                    "seed": -1,
                    "media_type": "wav",
                    "streaming_mode": False,
                    "parallel_infer": True,
                    "repetition_penalty": 1.35,
                    "sample_steps": 32,
                    "super_sampling": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"TTS音频生成成功: {output_path}")
                return True
            else:
                logger.error(f"TTS生成失败: {response.status_code}, 响应: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"TTS调用失败: {e}")
            return False

class VideoGenerator:
    """视频生成器"""
    
    def __init__(self, config: StreamConfig):
        self.config = config
    
    def create_video_from_audio(self, audio_path: str, text: str, output_path: str) -> bool:
        """使用训练好的数字人模型从音频创建视频"""
        try:
            logger.info(f"开始生成数字人视频，音频文件: {audio_path}")
            
            # 步骤1: 使用HuBERT提取音频特征
            hubert_output_path = audio_path.replace('.wav', '_hu.npy')
            logger.info("步骤1: 提取HuBERT特征...")
            
            hubert_cmd = [
                "python", "data_utils/hubert.py", 
                "--wav", audio_path
            ]
            
            result = subprocess.run(hubert_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"HuBERT特征提取失败: {result.stderr}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            if not os.path.exists(hubert_output_path):
                logger.error(f"HuBERT特征文件未生成: {hubert_output_path}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            logger.info(f"HuBERT特征提取成功: {hubert_output_path}")
            
            # 步骤2: 使用训练好的模型生成视频
            logger.info("步骤2: 生成数字人视频...")
            
            # 检查必要的文件和目录
            dataset_dir = "input/mxbc_0913/"
            checkpoint_path = "checkpoint/195.pth"
            
            if not os.path.exists(dataset_dir):
                logger.error(f"数据集目录不存在: {dataset_dir}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            if not os.path.exists(checkpoint_path):
                logger.error(f"模型检查点不存在: {checkpoint_path}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            inference_cmd = [
                "python", "inference.py",
                "--asr", "hubert",
                "--dataset", dataset_dir,
                "--audio_feat", hubert_output_path,
                "--checkpoint", checkpoint_path,
                "--save_path", output_path
            ]
            
            result = subprocess.run(inference_cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                logger.error(f"视频推理失败: {result.stderr}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            if not os.path.exists(output_path):
                logger.error(f"视频文件未生成: {output_path}")
                return self._create_fallback_video(audio_path, text, output_path)
            
            # 清理中间文件，只保留最终的mp4
            try:
                if os.path.exists(hubert_output_path):
                    os.remove(hubert_output_path)
                    logger.info(f"已清理HuBERT特征文件: {hubert_output_path}")
            except Exception as e:
                logger.warning(f"清理中间文件失败: {e}")
            
            logger.info(f"数字人视频生成成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"数字人视频生成失败: {e}")
            return self._create_fallback_video(audio_path, text, output_path)
    
    def _create_fallback_video(self, audio_path: str, text: str, output_path: str) -> bool:
        """创建简单的回退视频"""
        try:
            logger.info("回退到简单视频生成...")
            
            # 获取音频时长
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path
            ]
            
            try:
                duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                duration = float(duration_result.stdout.strip())
            except:
                duration = 5.0
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={duration}",
                "-i", audio_path,
                "-c:v", "libopenh264",
                "-c:a", "libmp3lame",
                "-shortest",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"回退视频生成成功: {output_path}")
                return True
            else:
                logger.error(f"回退视频生成失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"回退视频生成异常: {e}")
            return False
    
    def _create_simple_video(self, audio_path: str, text: str, output_path: str, duration: float) -> bool:
        """创建简单视频的备用方法"""
        try:
            logger.info("尝试使用简化的视频生成方法...")
            
            # 最简单的方法：只添加黑色背景
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s={self.config.video_resolution}:d={duration}",
                "-i", audio_path,
                "-c:v", "mpeg4",
                "-c:a", "libmp3lame",
                "-shortest",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"简化视频生成成功: {output_path}")
                return True
            else:
                logger.error(f"简化视频生成也失败: {result.stderr}")
                # 最后尝试：直接复制音频为视频
                return self._audio_to_video_fallback(audio_path, output_path)
                
        except Exception as e:
            logger.error(f"简化视频生成异常: {e}")
            return False
    
    def _audio_to_video_fallback(self, audio_path: str, output_path: str) -> bool:
        """音频转视频的最后备用方案"""
        try:
            logger.info("使用最后备用方案：音频转视频...")
            
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-f", "lavfi",
                "-i", "color=c=black:s=640x480",
                "-c:v", "mpeg4",
                "-c:a", "copy",
                "-shortest",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"备用方案成功: {output_path}")
                return True
            else:
                logger.error(f"所有视频生成方法都失败了: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"备用方案异常: {e}")
            return False

class StreamBuffer:
    """流缓冲区"""
    
    def __init__(self, max_size: int = 10):
        self.text_queue = queue.Queue(maxsize=max_size)
        self.video_queue = queue.Queue(maxsize=max_size)
    
    def add_text(self, text: str):
        """添加文本到缓冲区"""
        try:
            self.text_queue.put(text, timeout=1)
        except queue.Full:
            logger.warning("文本缓冲区已满")
    
    def get_text(self) -> Optional[str]:
        """从缓冲区获取文本"""
        try:
            return self.text_queue.get(timeout=1)
        except queue.Empty:
            return None
    
    def add_video(self, video_path: str):
        """添加视频到缓冲区"""
        try:
            self.video_queue.put(video_path, timeout=1)
        except queue.Full:
            logger.warning("视频缓冲区已满")
    
    def get_video(self) -> Optional[str]:
        """从缓冲区获取视频"""
        try:
            return self.video_queue.get(timeout=1)
        except queue.Empty:
            return None

class LiveStreamSystem:
    """通用实时直播流系统"""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self.is_running = False
        self.ffmpeg_process = None
        
        # 初始化组件
        self.deepseek_client = DeepSeekClient(config.deepseek_base_url)
        self.gpt_sovits_client = GPTSoVITSClient(config.gpt_sovits_path)
        self.video_generator = VideoGenerator(config)
        self.stream_buffer = StreamBuffer(config.buffer_size)
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        
        # 创建临时目录
        os.makedirs("temp", exist_ok=True)
    
    def _split_text_to_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        import re
        sentences = re.split(r'[。！？.!?]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def _content_generation_loop(self, topic: str):
        """内容生成循环"""
        while self.is_running:
            try:
                # 生成新内容
                prompt = f"请围绕'{topic}'这个主题，生成一段有趣的直播内容，大约200字左右。"
                content = await self.deepseek_client.generate_long_content(prompt)
                
                # 分割为句子并添加到缓冲区
                sentences = self._split_text_to_sentences(content)
                for sentence in sentences:
                    if sentence:
                        self.stream_buffer.add_text(sentence)
                
                # 等待一段时间再生成新内容
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"内容生成失败: {e}")
                await asyncio.sleep(5)
    
    def _audio_video_generation_loop(self):
        """音视频生成循环"""
        counter = 0
        while self.is_running:
            text = self.stream_buffer.get_text()
            if not text:
                time.sleep(0.1)
                continue
            
            try:
                # 生成音频
                audio_path = f"temp/audio_{counter:06d}.wav"
                if self.gpt_sovits_client.generate_audio(text, audio_path):
                    # 生成视频
                    video_path = f"temp/video_{counter:06d}.mp4"
                    if self.video_generator.create_video_from_audio(audio_path, text, video_path):
                        self.stream_buffer.add_video(video_path)
                        counter += 1
                    
                    # 保留音频文件用于检查
                    logger.info(f"📁 保留音频文件: {audio_path}")
                    # if os.path.exists(audio_path):
                    #     os.remove(audio_path)
                
            except Exception as e:
                logger.error(f"音视频生成失败: {e}")
    
    def start_stream_output(self):
        """启动流输出"""
        if self.config.output_mode == "udp":
            self._start_udp_stream()
        elif self.config.output_mode == "rtmp":
            self._start_rtmp_stream()
        elif self.config.output_mode == "file":
            self._start_file_output()
        elif self.config.output_mode == "http_flv":
            self._start_http_flv_stream()
        else:
            logger.error(f"不支持的输出模式: {self.config.output_mode}")
    
    def _start_udp_stream(self):
        """启动UDP流"""
        try:
            logger.info(f"启动UDP流: {self.config.udp_host}:{self.config.udp_port}")
            logger.info("💡 在VLC中打开: udp://localhost:1234")
            
            # 使用简单的UDP推流方式
            self._udp_stream_loop()
            
        except Exception as e:
            logger.error(f"UDP流启动失败: {e}")
    
    def _start_rtmp_stream(self):
        """启动RTMP推流"""
        try:
            logger.info(f"启动RTMP推流: {self.config.rtmp_url}")
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "ultrafast",
                "-f", "flv",
                self.config.rtmp_url
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info("RTMP推流已启动")
            self._stream_video_loop()
            
        except Exception as e:
            logger.error(f"RTMP推流启动失败: {e}")
    
    def _start_file_output(self):
        """启动文件输出模式"""
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            logger.info(f"启动文件输出模式: {self.config.output_dir}")
            
            self._file_output_loop()
            
        except Exception as e:
            logger.error(f"文件输出启动失败: {e}")
    
    def _start_http_flv_stream(self):
        """启动HTTP-FLV流"""
        try:
            logger.info(f"启动HTTP-FLV流: http://{self.config.http_host}:{self.config.http_port}")
            
            # 启动HTTP服务器
            self._start_http_server()
            
            # 创建HLS目录
            os.makedirs("temp/hls", exist_ok=True)
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "ultrafast",
                "-f", "hls",
                "-hls_time", "2",
                "-hls_list_size", "5",
                "-hls_flags", "delete_segments",
                "temp/hls/stream.m3u8"
            ]
            
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info("HTTP-FLV流已启动")
            self._stream_video_loop()
            
        except Exception as e:
            logger.error(f"HTTP-FLV流启动失败: {e}")
    
    def _udp_stream_loop(self):
        """UDP流循环 - 逐个推送视频"""
        while self.is_running:
            video_path = self.stream_buffer.get_video()
            if video_path and os.path.exists(video_path):
                try:
                    logger.info(f"📡 推送视频到UDP: {video_path}")
                    
                    # 直接推送单个视频文件
                    cmd = [
                        "ffmpeg", "-y",
                        "-re",  # 实时播放
                        "-i", video_path,
                        "-c:v", "libopenh264",
                        "-c:a", "libmp3lame",
                        "-f", "mpegts",
                        "-pix_fmt", "yuv420p",
                        f"udp://{self.config.udp_host}:{self.config.udp_port}?pkt_size=1316"
                    ]
                    
                    # 启动FFmpeg进程
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # 等待进程完成
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0:
                        logger.info(f"✅ 视频推送完成: {video_path}")
                    else:
                        logger.error(f"❌ 视频推送失败: {stderr.decode()}")
                    
                    # 保留视频文件用于检查
                    logger.info(f"📁 保留视频文件: {video_path}")
                    # if os.path.exists(video_path):
                    #     os.remove(video_path)
                        
                except Exception as e:
                    logger.error(f"UDP推送异常: {e}")
            else:
                time.sleep(0.1)
    
    def _stream_video_loop(self):
        """通用视频流推送循环"""
        while self.is_running:
            video_path = self.stream_buffer.get_video()
            if video_path and os.path.exists(video_path):
                try:
                    # 写入文件路径到FFmpeg stdin
                    self.ffmpeg_process.stdin.write(f"file '{video_path}'\n")
                    self.ffmpeg_process.stdin.flush()
                    
                    # 等待视频播放完成后删除
                    time.sleep(5)  # 根据视频长度调整
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        
                except Exception as e:
                    logger.error(f"推送视频失败: {e}")
                    break
            else:
                time.sleep(0.1)
    
    def _file_output_loop(self):
        """文件输出循环"""
        file_counter = 0
        while self.is_running:
            video_path = self.stream_buffer.get_video()
            if video_path and os.path.exists(video_path):
                try:
                    # 复制到输出目录
                    output_file = os.path.join(self.config.output_dir, f"stream_{file_counter:06d}.mp4")
                    import shutil
                    shutil.copy2(video_path, output_file)
                    
                    logger.info(f"输出文件: {output_file}")
                    file_counter += 1
                    
                    # 删除临时文件
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        
                except Exception as e:
                    logger.error(f"文件输出失败: {e}")
            else:
                time.sleep(0.1)
    
    def _start_http_server(self):
        """启动HTTP服务器"""
        def run_server():
            try:
                from http.server import HTTPServer, SimpleHTTPRequestHandler
                import os
                
                class CORSRequestHandler(SimpleHTTPRequestHandler):
                    def end_headers(self):
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        super().end_headers()
                    
                    def translate_path(self, path):
                        # 服务temp/hls目录
                        if path.startswith('/stream/'):
                            return os.path.join('temp/hls', path[8:])
                        return super().translate_path(path)
                
                server = HTTPServer((self.config.http_host, self.config.http_port), CORSRequestHandler)
                logger.info(f"HTTP服务器启动在 http://{self.config.http_host}:{self.config.http_port}")
                server.serve_forever()
                
            except Exception as e:
                logger.error(f"HTTP服务器启动失败: {e}")
        
        http_thread = threading.Thread(target=run_server)
        http_thread.daemon = True
        http_thread.start()
    
    async def start_streaming(self, initial_topic: str):
        """启动流媒体系统"""
        self.is_running = True
        
        # 启动流输出线程
        output_thread = threading.Thread(target=self.start_stream_output)
        output_thread.daemon = True
        output_thread.start()
        
        # 启动音视频生成线程
        av_thread = threading.Thread(target=self._audio_video_generation_loop)
        av_thread.daemon = True
        av_thread.start()
        
        # 启动内容生成循环
        try:
            await self._content_generation_loop(initial_topic)
        except Exception as e:
            logger.error(f"内容生成循环异常: {e}")
        finally:
            self.stop_streaming()
    
    def stop_streaming(self):
        """停止流媒体系统"""
        self.is_running = False
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process = None
        
        # 清理临时文件
        if os.path.exists("temp"):
            import shutil
            shutil.rmtree("temp")

# 测试代码
async def main():
    config = StreamConfig(
        output_mode="udp",
        udp_host="localhost",
        udp_port=1234
    )
    
    system = LiveStreamSystem(config)
    
    try:
        await system.start_streaming("今天聊聊人工智能的发展趋势")
    except KeyboardInterrupt:
        print("用户停止直播")
    finally:
        system.stop_streaming()

if __name__ == "__main__":
    asyncio.run(main())