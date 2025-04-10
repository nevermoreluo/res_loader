from res_loader.config import config
from res_loader.logger import logger
from res_loader.utils.video import VideoProcessor

if __name__ == "__main__":
    logger.info("res_loader")
    video_processor = VideoProcessor(config.get("ffmpeg_path"))
    video_processor.video_to_audio("aaa.mp4")


