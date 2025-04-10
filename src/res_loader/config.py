from pathlib import Path
from typing import Optional, Dict, Any
import json
import os
from res_loader.logger import logger


class Config:
    def __init__(self, config_path:str = "config.json"):
        self.config_path: str = config_path
        self.config: Dict[str, Any] = {}
        self.default_config: dict = {
            "ffmpeg_path": "bin/ffmpeg.exe",
            "temp_dir": "temp",
            "output_dir": "output",
            "tmp_audio_dir": "tmp_audio",
            "watch_dir": "test_data/",
            "whisper": {
                "model_size_or_path": "base",  # 可选: tiny, base, small, medium, large, 或者模型路径models/faster-whisper-large-v3-turbo-ct2
                "device": "cpu",       # 可选: cpu, cuda
                "compute_type": "int8" # 可选: int8, float16, float32
            },
            "log": {
                "dir": "logs",
                "level": "INFO",
                "console": True,
                "max_days": 30
            },
            "database": {
                "type": "sqlite",  # 支持 sqlite 或 mysql
                "sqlite": {
                    "db_path": "data/res_loader.db"
                },
                "mysql": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "",
                    "database": "res_loader"
                }
            }
        }
        
        if config_path and os.path.exists(config_path):
            self.load_config()
        else:
            self.config = self.default_config.copy()
    
    def load_config(self) -> None:
        """从配置文件加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f) or {}
                # 合并默认配置和加载的配置
                self.config = {**self.default_config, **loaded_config}
            logger.debug(f"加载配置文件成功: {self.config_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = self.default_config.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，如果不存在则返回默认值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        self.config[key] = value
    
    def save(self) -> None:
        """保存配置到文件"""
        if not self.config_path:
            logger.error("配置文件路径未设置")
            return
            
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}") 

    def get_db_conf(self) -> dict:
        """获取数据库配置
        
        Returns:
            dict: 数据库配置字典，包含数据库类型和对应的连接参数
        """
        db_conf: dict = self.get("database", {})
        db_type: str = db_conf.get("type") or "sqlite"
        
        if db_type not in ["sqlite", "mysql"]:
            logger.error(f"不支持的数据库类型: {db_type}, 回退到sqlite")
            db_type = "sqlite"
            
        return {
            "type": db_type,
            **db_conf.get(db_type, {})
        }

config = Config()
