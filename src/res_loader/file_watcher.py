import os
import time
from pathlib import Path
from typing import Optional, Set, Dict, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent, FileModifiedEvent
from res_loader.logger import logger
from res_loader.utils.file import FileUtils
from res_loader.db import Database, Resource, ResourceType, ResourceStatus
from res_loader.config import config

class FileWatcher:
    def __init__(self, watch_dir: str, db: Database):
        """
        初始化文件监视器
        
        Args:
            watch_dir: 要监视的目录路径
            db: 数据库实例
        """
        self.watch_dir = Path(watch_dir)
        self.db = db
        self.observer = Observer()
        self.handler = FileChangeHandler(self)
        
        # 确保监视目录存在
        os.makedirs(watch_dir, exist_ok=True)
        
        # 初始化时扫描目录中的文件
        self._scan_directory()
    
    def _scan_directory(self) -> None:
        """扫描目录中的所有文件并添加到数据库"""
        for root, _, files in os.walk(self.watch_dir):
            for file in files:
                if not FileUtils.is_write_completed(Path(root) / file):
                    logger.warning(f"文件未写入完成: {Path(root) / file}, 跳过")
                    continue
                file_path = Path(root) / file
                self._process_file(file_path)
    
    def _process_file(self, file_path: Path) -> None:
        """处理单个文件，添加到数据库或更新状态"""
        try:
            # 获取文件信息
            file_name = file_path.name
            file_type = FileUtils.get_file_type(str(file_path))
            file_md5 = FileUtils.get_file_md5(str(file_path))
            
            if not file_md5:
                logger.error(f"无法获取文件MD5: {file_path}")
                return
            
            # 检查文件是否已在数据库中
            existing_resource = self.db.get_resource_by_md5(file_md5)
            
            if existing_resource:
                # 更新现有记录
                self.db.update_resource(
                    existing_resource.id,
                    path=str(file_path),
                    status=ResourceStatus.PENDING
                )
                logger.info(f"更新文件记录: {file_path}")
            else:
                # 添加新记录
                resource_type = self._get_resource_type(file_type)
                self.db.add_resource(
                    name=file_name,
                    type=resource_type,
                    path=str(file_path),
                    md5=file_md5
                )
                logger.info(f"添加新文件记录: {file_path}")
        except Exception as e:
            logger.error(f"处理文件失败 {file_path}: {e}")
    
    def _get_resource_type(self, file_type: str) -> ResourceType:
        """根据文件扩展名获取资源类型"""
        file_type = file_type.lower()
        type_mapping = {
            'mp4': ResourceType.VIDEO,
            'avi': ResourceType.VIDEO,
            'mkv': ResourceType.VIDEO,
            'mp3': ResourceType.AUDIO,
            'wav': ResourceType.AUDIO,
            'txt': ResourceType.TEXT,
            'log': ResourceType.TEXT,
            'pdf': ResourceType.PDF,
            'md': ResourceType.MARKDOWN,
            'doc': ResourceType.WORD,
            'docx': ResourceType.WORD,
            'ppt': ResourceType.PPT,
            'pptx': ResourceType.PPT,
            'xls': ResourceType.EXCEL,
            'xlsx': ResourceType.EXCEL,
            'csv': ResourceType.CSV
        }
        return type_mapping.get(file_type, ResourceType.UNKNOWN)
    
    def start(self) -> None:
        """开始监视目录"""
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=True)
        self.observer.start()
        logger.info(f"开始监视目录: {self.watch_dir}")
    
    def stop(self) -> None:
        """停止监视目录"""
        self.observer.stop()
        self.observer.join()
        logger.info(f"停止监视目录: {self.watch_dir}")

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, watcher: FileWatcher):
        self.watcher = watcher
    
    def on_created(self, event: FileCreatedEvent) -> None:
        """处理文件创建事件"""
        if not event.is_directory:
            logger.info(f"文件创建事件: {event.src_path}")
            # self.watcher._process_file(Path(event.src_path))
    
    def on_modified(self, event: FileModifiedEvent) -> None:
        """处理文件修改事件"""
        if not event.is_directory and FileUtils.is_write_completed(Path(event.src_path)):
            logger.info(f"文件修改事件: {event.src_path}")
            self.watcher._process_file(Path(event.src_path))
    
    def on_deleted(self, event: FileDeletedEvent) -> None:
        """处理文件删除事件"""
        if not event.is_directory:
            try:
                # 查找并更新数据库中对应的记录
                file_path = Path(event.src_path)
                resources = self.watcher.db.list_resources()
                for resource in resources:
                    if Path(resource.path) == file_path:
                        self.watcher.db.update_resource(
                            resource.id,
                            status=ResourceStatus.DELETED,
                            error_message="文件已被删除"
                        )
                        logger.info(f"更新已删除文件状态: {file_path}")
                        break
            except Exception as e:
                logger.error(f"处理文件删除事件失败 {event.src_path}: {e}") 