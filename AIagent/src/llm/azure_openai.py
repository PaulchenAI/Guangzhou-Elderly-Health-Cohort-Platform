# -*- coding: utf-8 -*-
"""
Azure OpenAI LLM客户端实现
"""

from typing import List, AsyncIterator
from langchain_core.messages import BaseMessage
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from .base import BaseLLMClient
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger


class AzureOpenAILLMClient(BaseLLMClient):
    """Azure OpenAI LLM客户端"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化Azure OpenAI客户端
        
        Args:
            config: LLM配置
        """
        super().__init__(config)
        
        if not config.api_key:
            raise ValueError("Azure OpenAI需要设置api_key")
        
        if not config.azure_endpoint:
            raise ValueError("Azure OpenAI需要设置azure_endpoint")
        
        self.api_key = config.api_key
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.azure_endpoint = config.azure_endpoint
        self.azure_api_version = config.azure_api_version or "2024-02-15-preview"
    
    def get_langchain_model(self) -> BaseLanguageModel:
        """
        获取LangChain AzureChatOpenAI模型实例
        
        Returns:
            AzureChatOpenAI实例
        """
        if self._langchain_model is None:
            self._langchain_model = AzureChatOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.azure_api_version,
                azure_deployment=self.model,  # Azure使用deployment名称
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        return self._langchain_model
    
    async def invoke(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> str:
        """
        调用Azure OpenAI
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            LLM响应文本
        """
        model = self.get_langchain_model()
        
        # 合并kwargs参数
        invoke_kwargs = {
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
        }
        invoke_kwargs.update({k: v for k, v in kwargs.items() if k not in invoke_kwargs})
        
        try:
            response = await model.ainvoke(messages, **invoke_kwargs)
            return response.content
        except Exception as e:
            self.logger.error(f"Azure OpenAI调用失败: {e}")
            raise
    
    async def stream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式调用Azure OpenAI
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            LLM响应文本块
        """
        model = self.get_langchain_model()
        
        # 合并kwargs参数
        invoke_kwargs = {
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
        }
        invoke_kwargs.update({k: v for k, v in kwargs.items() if k not in invoke_kwargs})
        
        try:
            async for chunk in model.astream(messages, **invoke_kwargs):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
        except Exception as e:
            self.logger.error(f"Azure OpenAI流式调用失败: {e}")
            raise
