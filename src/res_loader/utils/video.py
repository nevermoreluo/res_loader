import subprocess
from pathlib import Path
from typing import Optional
import os
from res_loader.logger import logger

class VideoProcessor:
    def __init__(self, ffmpeg_path: str):
        """
        初始化视频处理器
        
        Args:
            ffmpeg_path: ffmpeg可执行文件的路径
        """
        self.ffmpeg_path = ffmpeg_path
    
    def video_to_audio(self, video_path: str, output_path: Optional[str] = None) -> bool:
        """
        将视频转换为音频文件
        
        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径，如果为None则自动生成
            
        Returns:
            输出音频文件路径
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"视频文件不存在: {video_path}")
            return False
            
        if output_path is None:
            output_path = str(video_path.with_suffix('.mp3'))
        
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        # 构建ffmpeg命令
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_path),
            '-vn',  # 不处理视频
            '-acodec', 'libmp3lame',  # 使用MP3编码
            '-ab', '192k',  # 音频比特率
            '-ar', '44100',  # 采样率
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        try:
            # 执行ffmpeg命令
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"视频转换失败: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"视频转换过程中发生错误: {str(e)}")
            return False
