import logging
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
from typing import Optional
import sys

class Logger:
    def __init__(
        self,
        name: str = "res_loader",
        log_dir: str = "logs",
        level: int = logging.INFO,
        console: bool = True,
        max_days: int = 30
    ):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            log_dir: 日志文件目录
            level: 日志级别
            console: 是否输出到控制台
            max_days: 日志文件保留天数
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 如果已经配置过处理器，则不再重复配置
        if self.logger.handlers:
            return
            
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 文件处理器 - 按天轮转
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=max_days,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """输出调试日志"""
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """输出信息日志"""
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """输出警告日志"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """输出错误日志"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """输出严重错误日志"""
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """输出异常日志"""
        self.logger.exception(msg, *args, **kwargs)


logger = Logger(
    name="res_loader",
    log_dir="logs",
    level=logging.INFO,
    console=True,
    max_days=30
)




