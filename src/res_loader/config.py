from pathlib import Path
from typing import Optional, Dict, Any
import json
import os
from res_loader.logger import logger


class Config:
    def __init__(self, config_path:str = "config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.default_config = {
            "ffmpeg_path": "bin/ffmpeg.exe",
            "temp_dir": "temp",
            "output_dir": "output",
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

config = Config()
