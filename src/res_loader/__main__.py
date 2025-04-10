import signal
import sys
import time
import threading
from pathlib import Path
import concurrent.futures
import os

from res_loader.config import config
from res_loader.db import Database, Resource,ResourceStatus,ResourceType
from res_loader.file_watcher import FileWatcher
from res_loader.logger import logger
from res_loader.utils.video import VideoProcessor
from res_loader.utils.audio import AudioProcessor


class ResourcePreProcessor:
    def __init__(self, db: Database):
        self.db = db
        self._audio_processor: AudioProcessor = None
        self._video_processor: VideoProcessor = None

    @property
    def audio_processor(self):
        if self._audio_processor is None:
            whisper_conf = config.get("whisper") or {}
            logger.debug(f"whisper_conf: {whisper_conf}")
            self._audio_processor = AudioProcessor(
                model_size_or_path=whisper_conf.get("model_size_or_path", "base"),
                device=whisper_conf.get("device", "cpu"),
                compute_type=whisper_conf.get("compute_type", "int8")
            )
        return self._audio_processor
    
    @property
    def video_processor(self):
        if self._video_processor is None:
            self._video_processor = VideoProcessor(config.get("ffmpeg_path"))
        return self._video_processor

    def do_process_video(self,resource: Resource, session):
        # 获取音频输出目录
        audio_dir = config.get("tmp_audio_dir", "tmp_audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        # 生成音频文件路径
        audio_filename = f"{Path(resource.path).stem}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)

        if not self.video_processor.video_to_audio(resource.path, audio_path):
            logger.error(f"视频转换为音频失败: {resource.path}")
            resource.status = ResourceStatus.FAILED
            session.commit()
            return
        resource.converted_path = audio_path
        self.do_process_audio(resource, session)

    def do_process_audio(self, resource: Resource, session):
        audio_path = resource.audio_path()
        if not audio_path:
            logger.error(f"音频文件不存在: {resource.path}")
            resource.status = ResourceStatus.FAILED
            session.commit()
            return
        
        # 使用 Whisper 将音频转换为文本
        text = self.audio_processor.audio_to_text(audio_path)
        if text is None:
            logger.error(f"音频转文本失败: {audio_path}")
            resource.status = ResourceStatus.FAILED
            session.commit()
            return
        
        # 保存转换后的文本
        resource.content = text
        resource.status = ResourceStatus.PRE_PROCESSED
        session.commit()
        logger.info(f"音频转文本成功: {audio_path} {text[:100]}...")

    def pre_process_resource(self, resource: Resource, session):
        logger.info(f"处理加载资源: {resource.path}")
        # 获取待处理文件
        file_path = Path(resource.path)
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            resource.status = ResourceStatus.FAILED
            session.commit()
            return
        if not file_path.is_file():
            logger.error(f"路径不是文件: {file_path}")
            resource.status = ResourceStatus.FAILED
            session.commit()
            return
        # 获取文件类型
        resource_type = resource.resource_type
        if resource_type == ResourceType.TEXT \
            or resource_type == ResourceType.MARKDOWN:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                resource.content = content
                resource.status = ResourceStatus.PRE_PROCESSED
                session.commit()
        elif resource_type == ResourceType.AUDIO:
            self.do_process_audio(resource, session)
        elif resource_type == ResourceType.VIDEO:
            self.do_process_video(resource, session)
        elif resource_type == ResourceType.IMAGE \
            or resource_type == ResourceType.PDF \
            or resource_type == ResourceType.WORD \
            or resource_type == ResourceType.PPT \
            or resource_type == ResourceType.EXCEL \
            or resource_type == ResourceType.CSV:
            resource.status = ResourceStatus.PRE_PROCESSED
            session.commit()
        else:
            resource.status = ResourceStatus.FAILED
            resource.error_message = "尚未支持的文件类型"
            session.commit()
            logger.error(f"尚未支持的文件类型: {resource.path}")

    
    def process_media_resources(self, stop_event: threading.Event):
        """处理音视频资源的线程函数"""
        while not stop_event.is_set():
            try:
                session = self.db.Session()
                # 获取待处理的音视频资源
                resources = session.query(Resource).filter(
                    Resource.status == ResourceStatus.PENDING
                ).filter(
                    Resource.resource_type.in_([ResourceType.AUDIO, ResourceType.VIDEO])
                ).limit(10).all()
                
                for resource in resources:
                    if stop_event.is_set():
                        break
                    self.pre_process_resource(resource, session)
                    
                session.close()
            except Exception as e:
                logger.error(f"处理音视频资源时出错: {e}")
                if 'session' in locals():
                    session.close()
            
            # 休眠一段时间再检查新资源
            if not stop_event.is_set():
                stop_event.wait(timeout=3)

    def process_other_resources(self, stop_event: threading.Event, max_workers: int = 4):
        """处理非音视频资源的线程池函数"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while not stop_event.is_set():
                try:
                    session = self.db.Session()
                    # 获取待处理的非音视频资源，排除已失败和已完成的资源
                    resources = session.query(Resource).filter(
                        Resource.status == ResourceStatus.PENDING
                    ).filter(
                        ~Resource.resource_type.in_([ResourceType.AUDIO, ResourceType.VIDEO])
                    ).limit(10).all()
                    
                    if resources:
                        logger.info(f"发现 {len(resources)} 个待处理资源")
                        for resource in resources:
                            logger.info(f"资源信息: id={resource.id}, name={resource.name}, type={resource.resource_type}, path={resource.path}, status={resource.status}")
                    
                    # 提交任务到线程池
                    futures = []
                    for resource in resources:
                        if stop_event.is_set():
                            break
                        futures.append(executor.submit(self.pre_process_resource, resource, session))
                    
                    # 等待所有任务完成
                    concurrent.futures.wait(futures)
                    session.close()
                        
                except Exception as e:
                    logger.error(f"处理其他资源时出错: {e}")
                    if 'session' in locals():
                        session.close()
                
                # 休眠一段时间再检查新资源
                if not stop_event.is_set():
                    stop_event.wait(timeout=3)

    def run(self):
        # 创建停止事件
        stop_event = threading.Event()
        session = self.db.Session()
        # 获取待处理的非音视频资源，排除已失败和已完成的资源
        
        # 获取监视目录配置
        watch_dir = config.get("watch_dir", "watch")
        
        # 创建文件监视器
        watcher = FileWatcher(watch_dir, self.db)
        
        # 设置信号处理
        def signal_handler(sig, frame):
            logger.info("正在停止文件监视器...")
            watcher.stop()
            self.db.close()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        

            # 创建并启动处理线程
        media_thread = threading.Thread(
            target=self.process_media_resources,
            args=(stop_event,),
            name="MediaProcessor"
        )
        other_thread = threading.Thread(
            target=self.process_other_resources,
            args=(stop_event,),
            name="OtherProcessor"
        )
        
        media_thread.daemon = True
        other_thread.daemon = True
        
        media_thread.start()
        other_thread.start()

        try:
            # 开始监视
            watcher.start()
            logger.info("文件监视器已启动，按 Ctrl+C 停止")
            
            # 保持程序运行
            while True:
                time.sleep(3)
        except Exception as e:
            logger.error(f"发生错误: {e}")
        finally:
            stop_event.set()
            media_thread.join()
            logger.info("媒体处理线程已停止")
            other_thread.join()
            logger.info("其他处理线程已停止")
            watcher.stop()
            logger.info("文件监视器已停止")
            self.db.close()
            logger.info("数据库已关闭")
    
        

if __name__ == "__main__":
    # 创建停止事件
    stop_event = threading.Event()

    # 获取数据库配置并初始化数据库
    db_conf = config.get_db_conf()
    if not db_conf:
        logger.error("无法获取数据库配置")
        exit(1)
    
    db = Database(**db_conf)
    ResourcePreProcessor(db).run()
