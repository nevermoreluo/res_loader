from pathlib import Path
from typing import Optional, List
from faster_whisper import WhisperModel
from res_loader.logger import logger

class AudioProcessor:
    def __init__(self, model_size_or_path: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """
        初始化音频处理器
        
        Args:
            model_size_or_path: 模型大小，可选 "tiny", "base", "small", "medium", "large",或者指定路径
            device: 运行设备，可选 "cpu" 或 "cuda"
            compute_type: 计算类型，可选 "int8", "float16", "float32"
        """
        try:
            self.model = WhisperModel(
                model_size_or_path,
                device=device,
                compute_type=compute_type,
                download_root="models"  # 模型下载目录
            )
            logger.info(f"加载 Whisper 模型成功: {model_size_or_path}")
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise
    
    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """将秒数格式化为 HH:MM:SS.mmm 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
    
    def audio_to_text(self, audio_path: str, language: Optional[str] = "zh") -> Optional[str]:
        """
        将音频文件转换为文本
        
        Args:
            audio_path: 音频文件路径
            language: 音频语言代码（如 "zh", "en"），如果为None则自动检测
            
        Returns:
            str: 转换后的文本，如果转换失败则返回None
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                logger.error(f"音频文件不存在: {audio_path}")
                return None
                
            # 执行语音识别
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                beam_size=5,
                vad_filter=True,  # 启用语音活动检测
                vad_parameters=dict(min_silence_duration_ms=500)  # 设置静音检测参数
            )
            
            # 合并所有片段，带时间戳
            text_parts = []
            for segment in segments:
                start_time = self.format_timestamp(segment.start)
                end_time = self.format_timestamp(segment.end)
                text_parts.append(f"[{start_time} -> {end_time}] {segment.text}")
            text = "\n".join(text_parts)
            
            logger.info(f"音频转文本成功: {audio_path}")
            return text.strip()
            
        except Exception as e:
            logger.error(f"音频转文本失败 {audio_path}: {e}", exc_info=True)
            return None
    
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言代码列表
        """
        return self.model.get_supported_languages() 