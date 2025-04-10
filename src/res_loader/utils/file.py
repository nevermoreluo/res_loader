import hashlib
from pathlib import Path
from typing import Optional
import os
from res_loader.logger import logger
import time

class FileUtils:
    @staticmethod
    def get_file_md5(file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """
        计算文件的MD5值
        
        Args:
            file_path: 文件路径
            chunk_size: 每次读取的块大小，默认8KB
            
        Returns:
            文件的MD5值，如果文件不存在或读取失败则返回None
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None
                
            if not file_path.is_file():
                logger.error(f"路径不是文件: {file_path}")
                return None
                
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    md5_hash.update(chunk)
                    
            return md5_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件MD5失败: {e}")
            return None
    
    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """
        获取文件大小（字节）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节），如果文件不存在则返回None
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"获取文件大小失败: {e}")
            return None
    
    @staticmethod
    def ensure_dir(directory: str) -> bool:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            是否成功
        """
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False 
    
    @staticmethod
    def get_file_type(file_path: str) -> Optional[str]:
        """
        获取文件类型
        """
        return file_path.split(".")[-1]

    @staticmethod
    def get_file_name(file_path: str) -> Optional[str]:
        """
        获取文件名
        """
        return os.path.basename(file_path)
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        判断文件是否存在
        """
        return os.path.exists(file_path)
    
    @staticmethod
    def is_write_completed(file_path: str, check_interval: float = 0.1, max_checks: int = 2) -> bool:
        """
        检查文件是否写入完成
        
        Args:
            file_path: 文件路径
            check_interval: 检查间隔（秒）
            max_checks: 最大检查次数
            
        Returns:
            bool: 文件是否写入完成
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False
                
            # 获取初始文件大小
            initial_size = file_path.stat().st_size
            
            # 检查文件大小是否稳定
            for _ in range(max_checks):
                time.sleep(check_interval)
                current_size = file_path.stat().st_size
                
                # 如果文件大小没有变化，且文件可读，则认为写入完成
                if current_size == initial_size:
                    try:
                        # 尝试打开文件进行读取
                        with open(file_path, 'rb') as f:
                            f.read(1)  # 尝试读取一个字节
                        return True
                    except IOError:
                        continue
                
                initial_size = current_size
                
            return False
            
        except Exception as e:
            logger.error(f"检查文件写入状态失败 {file_path}: {e}")
            return False
    
    
    


