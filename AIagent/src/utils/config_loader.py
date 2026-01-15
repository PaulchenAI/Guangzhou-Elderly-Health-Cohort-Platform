# -*- coding: utf-8 -*-
"""
YAML配置加载器
支持从YAML文件加载配置，并与环境变量合并（优先级：环境变量 > YAML）
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from .env_loader import EnvLoader


class ConfigLoader:
    """YAML配置加载器"""
    
    def __init__(self, config_dir: Optional[Path] = None, env_loader: Optional[EnvLoader] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置目录路径，默认为项目根目录下的config/
            env_loader: 环境变量加载器实例
        """
        if config_dir is None:
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"
        
        self.config_dir = Path(config_dir)
        self.env_loader = env_loader or EnvLoader()
        self._cache: Dict[str, Any] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            filename: YAML文件名（相对于config_dir）
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 如果文件不存在
            yaml.YAMLError: 如果YAML格式错误
        """
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        return config
    
    def load_with_env_override(self, filename: str, env_prefix: str = "") -> Dict[str, Any]:
        """
        加载YAML配置，并用环境变量覆盖
        
        环境变量命名规则：
        - 如果env_prefix为空，直接使用配置键名
        - 如果env_prefix不为空，使用 {env_prefix}_{key} 格式
        - 支持嵌套配置，使用下划线分隔，如：AGENT_TEMPERATURE
        
        Args:
            filename: YAML文件名
            env_prefix: 环境变量前缀
            
        Returns:
            合并后的配置字典
        """
        config = self.load_yaml(filename)
        return self._merge_env_overrides(config, env_prefix)
    
    def _merge_env_overrides(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        递归合并环境变量覆盖到配置中
        
        Args:
            config: 配置字典
            prefix: 环境变量前缀
            
        Returns:
            合并后的配置字典
        """
        result = config.copy()
        
        for key, value in config.items():
            env_key = f"{prefix}_{key}".upper() if prefix else key.upper()
            
            # 检查环境变量
            env_value = self.env_loader.get(env_key)
            if env_value is not None:
                # 尝试转换类型
                if isinstance(value, bool):
                    result[key] = self.env_loader.get_bool(env_key, value)
                elif isinstance(value, int):
                    result[key] = self.env_loader.get_int(env_key, value)
                elif isinstance(value, float):
                    result[key] = self.env_loader.get_float(env_key, value)
                else:
                    result[key] = env_value
            
            # 递归处理嵌套字典
            elif isinstance(value, dict):
                result[key] = self._merge_env_overrides(value, env_key)
        
        return result
    
    def get(self, filename: str, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套键）
        
        Args:
            filename: YAML文件名
            key: 配置键（支持 "section.key" 格式）
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load_yaml(filename)
        
        # 支持点号分隔的嵌套键
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def reload(self):
        """清除缓存，强制重新加载配置"""
        self._cache.clear()
