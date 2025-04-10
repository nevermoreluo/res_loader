from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from datetime import datetime
import enum
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
from res_loader.logger import logger
from res_loader.config import config

# 定义资源类型枚举
class ResourceType(enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    PDF = "pdf"
    MARKDOWN = "markdown"
    WORD = "word"
    PPT = "ppt"
    EXCEL = "excel"
    CSV = "csv"
    UNKNOWN = "unknown"

# 定义资源状态枚举
class ResourceStatus(enum.Enum):
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 处理完成
    FAILED = "failed"       # 处理失败
    DELETED = "deleted"     # 已删除
    UPLOADED = "uploaded"   # 已上传

Base = declarative_base()

class Resource(Base):
    """资源表"""
    __tablename__ = 'resources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(ResourceType), default=ResourceType.UNKNOWN, nullable=False)
    path = Column(String(512), default="", nullable=False)
    md5 = Column(String(32), default="", nullable=False)
    content = Column(Text, default="")
    converted_path = Column(String(512))
    status = Column(Enum(ResourceStatus), default=ResourceStatus.PENDING, nullable=False)
    error_message = Column(Text)  # 存储处理失败时的错误信息
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def audio_path(self) -> Optional[str]:
        if self.type == ResourceType.AUDIO:
            return self.path
        if self.type == ResourceType.VIDEO:
            return self.converted_path
        return None


class Database:
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """
        初始化数据库连接
        
        Args:
            db_type: 数据库类型，支持 "sqlite" 或 "mysql"
            **kwargs: 数据库连接参数
                - sqlite: db_path (数据库文件路径)
                - mysql: host, port, user, password, database
        """
        self.db_type = db_type.lower()
        self.engine = self._create_engine(**kwargs)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # 创建表
        Base.metadata.create_all(self.engine)
    
    def _create_engine(self, **kwargs) -> Any:
        """创建数据库引擎"""
        if self.db_type == "sqlite":
            db_path = kwargs.get('db_path', 'data/res_loader.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return create_engine(
                f'sqlite:///{db_path}',
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
        elif self.db_type == "mysql":
            return create_engine(
                f"mysql+pymysql://{kwargs['user']}:{kwargs['password']}@{kwargs['host']}:{kwargs['port']}/{kwargs['database']}",
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def add_resource(self, name: str, type: ResourceType, path: str, md5: str, 
                    converted_path: Optional[str] = None, metadata: Optional[Dict] = None) -> Resource:
        """添加资源记录"""
        session = self.Session()
        try:
            resource = Resource(
                name=name,
                type=type,
                path=path,
                md5=md5,
                converted_path=converted_path,
                status=ResourceStatus.PENDING,
                metadata=str(metadata) if metadata else None
            )
            session.add(resource)
            session.commit()
            return resource
        except Exception as e:
            session.rollback()
            logger.error(f"添加资源记录失败: {e}")
            raise
        finally:
            session.close()
    
    def get_resource(self, resource_id: int) -> Optional[Resource]:
        """获取资源记录"""
        session = self.Session()
        try:
            return session.query(Resource).filter_by(id=resource_id).first()
        finally:
            session.close()
    
    def get_resource_by_md5(self, md5: str) -> Optional[Resource]:
        """通过MD5获取资源记录"""
        session = self.Session()
        try:
            return session.query(Resource).filter_by(md5=md5).first()
        finally:
            session.close()
    
    def update_resource(self, resource_id: int, **kwargs) -> Optional[Resource]:
        """更新资源记录"""
        session = self.Session()
        try:
            resource = session.query(Resource).filter_by(id=resource_id).first()
            if resource:
                for key, value in kwargs.items():
                    if hasattr(resource, key):
                        setattr(resource, key, value)
                session.commit()
                return resource
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"更新资源记录失败: {e}")
            raise
        finally:
            session.close()
    
    def delete_resource(self, resource_id: int) -> bool:
        """删除资源记录"""
        session = self.Session()
        try:
            resource = session.query(Resource).filter_by(id=resource_id).first()
            if resource:
                session.delete(resource)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"删除资源记录失败: {e}")
            raise
        finally:
            session.close()
    
    def list_resources(self, type: Optional[ResourceType] = None, 
                      status: Optional[ResourceStatus] = None,
                      limit: int = 100, offset: int = 0) -> List[Resource]:
        """列出资源记录"""
        session = self.Session()
        try:
            query = session.query(Resource)
            if type:
                query = query.filter_by(type=type)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(Resource.created_at.desc()).offset(offset).limit(limit).all()
        finally:
            session.close()
    
    def get_pending_resources(self, type: Optional[ResourceType] = None, limit: int = 100) -> List[Resource]:
        """获取待处理的资源"""
        return self.list_resources(type=type, status=ResourceStatus.PENDING, limit=limit)
    
    def get_failed_resources(self, type: Optional[ResourceType] = None, limit: int = 100) -> List[Resource]:
        """获取处理失败的资源"""
        return self.list_resources(type=type, status=ResourceStatus.FAILED, limit=limit)
    
    def close(self):
        """关闭数据库连接"""
        self.Session.remove()
        self.engine.dispose() 