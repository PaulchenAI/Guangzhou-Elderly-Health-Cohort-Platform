# -*- coding: utf-8 -*-
"""
LLM工厂
根据配置创建对应的LLM客户端实例
"""

from typing import Optional
from .base import BaseLLMClient
from .anthropic import AnthropicLLMClient
from .openai import OpenAILLMClient
from .local import LocalLLMClient
from .azure_openai import AzureOpenAILLMClient
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger


class LLMFactory:
    """LLM工厂类"""
    
    _logger = get_logger("llm")
    
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseLLMClient:
        """
        根据LLM_PROVIDER创建对应的LLM客户端
        
        Args:
            config: LLM配置
            
        Returns:
            LLM客户端实例
            
        Raises:
            ValueError: 不支持的提供商
        """
        provider = config.provider.lower()
        
        LLMFactory._logger.info(f"创建LLM客户端: provider={provider}, model={config.model}")
        
        if provider == "anthropic":
            return AnthropicLLMClient(config)
        elif provider == "openai":
            return OpenAILLMClient(config)
        elif provider == "local":
            return LocalLLMClient(config)
        elif provider == "azure_openai":
            return AzureOpenAILLMClient(config)
        else:
            raise ValueError(
                f"不支持的LLM提供商: {provider}。"
                f"支持的提供商: anthropic, openai, local, azure_openai"
            )
    
    @staticmethod
    def create_llm_from_config_manager(config_manager) -> BaseLLMClient:
        """
        从配置管理器创建LLM客户端（便捷方法）
        
        Args:
            config_manager: 配置管理器实例
            
        Returns:
            LLM客户端实例
        """
        llm_config = config_manager.get_llm_config()
        return LLMFactory.create_llm(llm_config)
