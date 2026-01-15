# -*- coding: utf-8 -*-
"""
环境变量加载器
支持从系统环境变量、.env文件和YAML配置加载，按优先级合并
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class EnvLoader:
    """环境变量加载器"""
    
    def __init__(self, env_file: Optional[str] = None, project_root: Optional[str] = None):
        """
        初始化环境变量加载器
        
        Args:
            env_file: .env文件路径，默认为项目根目录下的.env
            project_root: 项目根目录，用于查找.env文件
        """
        if project_root is None:
            # 默认使用AIagent目录作为项目根目录
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        
        if env_file is None:
            # 先尝试AIagent目录下的.env
            env_file = self.project_root / ".env"
            # 如果不存在，尝试父目录（项目根目录）的.env
            if not env_file.exists():
                parent_env = self.project_root.parent / ".env"
                if parent_env.exists():
                    env_file = parent_env
        else:
            env_file = Path(env_file)
        
        self.env_file = env_file
        self._load_env()
    
    def _load_env(self):
        """加载.env文件"""
        if self.env_file.exists():
            load_dotenv(self.env_file, override=False)  # 不覆盖系统环境变量
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取环境变量（优先级：系统环境变量 > .env文件）
        
        Args:
            key: 环境变量键名
            default: 默认值
            
        Returns:
            环境变量值，如果不存在返回default
        """
        # 系统环境变量优先级最高
        value = os.getenv(key)
        if value is not None:
            return value
        
        # 如果.env已加载，dotenv会自动设置到os.environ
        return os.getenv(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型环境变量"""
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数类型环境变量"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数类型环境变量"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def require(self, key: str) -> str:
        """
        获取必需的环境变量，如果不存在则抛出异常
        
        Args:
            key: 环境变量键名
            
        Returns:
            环境变量值
            
        Raises:
            ValueError: 如果环境变量不存在
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"必需的环境变量 {key} 未设置。请检查.env文件或系统环境变量。")
        return value
    
    def get_all(self, prefix: str = "") -> dict:
        """
        获取所有以指定前缀开头的环境变量
        
        Args:
            prefix: 前缀，空字符串表示获取所有
            
        Returns:
            环境变量字典
        """
        result = {}
        for key, value in os.environ.items():
            if not prefix or key.startswith(prefix):
                result[key] = value
        return result
