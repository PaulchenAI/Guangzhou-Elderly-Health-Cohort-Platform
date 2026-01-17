# -*- coding: utf-8 -*-
"""
配置管理器
整合环境变量、YAML配置和Pydantic验证，提供统一的配置访问接口
"""

from pathlib import Path
from typing import Optional
from .env_loader import EnvLoader
from .config_loader import ConfigLoader
from .config_models import Settings, ClaudeCodeConfig, LLMConfig, VectorDBConfig, MemoryConfig, LoggingConfig, RAGConfig, DjangoAPIConfigModel


class ConfigManager:
    """配置管理器（单例模式）"""
    
    _instance: Optional['ConfigManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.env_loader = EnvLoader()
        self.config_loader = ConfigLoader(env_loader=self.env_loader)
        self._settings: Optional[Settings] = None
        self._load_settings()
    
    def _load_settings(self):
        """加载设置（从环境变量）"""
        try:
            self._settings = Settings()
        except Exception as e:
            raise ValueError(f"配置加载失败: {e}。请检查.env文件或环境变量。")
    
    @property
    def settings(self) -> Settings:
        """获取设置对象"""
        if self._settings is None:
            self._load_settings()
        return self._settings
    
    def get_claude_code_config(self) -> ClaudeCodeConfig:
        """获取Claude Code配置"""
        return self.settings.get_claude_code_config()
    
    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        return self.settings.get_llm_config()
    
    def get_vector_db_config(self) -> VectorDBConfig:
        """获取向量数据库配置"""
        return self.settings.get_vector_db_config()
    
    def get_memory_config(self) -> MemoryConfig:
        """获取记忆系统配置"""
        return self.settings.get_memory_config()
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        return self.settings.get_logging_config()
    
    def get_rag_config(self) -> RAGConfig:
        """获取RAG配置"""
        return self.settings.get_rag_config()
    
    def get_django_api_config(self) -> DjangoAPIConfigModel:
        """获取Django API配置"""
        return self.settings.get_django_api_config()
    
    def get_agent_config(self, agent_name: str) -> dict:
        """
        获取智能体配置（从YAML）
        
        Args:
            agent_name: 智能体名称
            
        Returns:
            智能体配置字典
        """
        agents_config = self.config_loader.load_with_env_override("agents.yaml")
        agents = agents_config.get("agents", {})
        return agents.get(agent_name, {})
    
    def get_prompt(self, agent_name: str, prompt_key: str) -> str:
        """
        获取Prompts模板（从YAML）
        
        Args:
            agent_name: 智能体名称
            prompt_key: Prompts键名（如system_prompt）
            
        Returns:
            Prompts内容
        """
        prompt_file = f"{agent_name}.yaml"
        prompts = self.config_loader.load_yaml(f"prompts/{prompt_file}")
        return prompts.get(prompt_key, "")
    
    def reload(self):
        """重新加载所有配置"""
        self.env_loader._load_env()
        self.config_loader.reload()
        self._load_settings()
    
    def validate(self) -> list:
        """
        验证所有配置
        
        Returns:
            错误列表，如果为空则表示配置有效
        """
        errors = []
        
        try:
            # 验证Claude Code配置
            claude_config = self.get_claude_code_config()
            if not Path(claude_config.path).exists():
                errors.append(f"Claude Code CLI路径不存在: {claude_config.path}")
        except Exception as e:
            errors.append(f"Claude Code配置验证失败: {e}")
        
        try:
            # 验证LLM配置
            llm_config = self.get_llm_config()
            if llm_config.provider != "local" and not llm_config.api_key:
                errors.append(f"{llm_config.provider} 需要设置 API密钥")
        except Exception as e:
            errors.append(f"LLM配置验证失败: {e}")
        
        return errors


# 全局配置管理器实例（延迟初始化，避免模块导入时立即创建）
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例（延迟初始化）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

# 为了向后兼容，提供config_manager属性访问
def __getattr__(name: str):
    if name == "config_manager":
        return get_config_manager()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
