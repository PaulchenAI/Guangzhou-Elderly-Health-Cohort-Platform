# -*- coding: utf-8 -*-
"""
Anthropic Claude LLM客户端实现
"""

from typing import List, AsyncIterator, Any
from langchain_core.messages import BaseMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from .base import BaseLLMClient
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic Claude LLM客户端"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化Anthropic客户端
        
        Args:
            config: LLM配置
        """
        super().__init__(config)
        
        if not config.api_key:
            raise ValueError("Anthropic需要设置api_key")
        
        self.api_key = config.api_key
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    def get_langchain_model(self) -> BaseLanguageModel:
        """
        获取LangChain ChatAnthropic模型实例
        
        Returns:
            ChatAnthropic实例
        """
        if self._langchain_model is None:
            self._langchain_model = ChatAnthropic(
                api_key=self.api_key,
                model=self.model,
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
        调用Anthropic Claude
        
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
            self.logger.error(f"Anthropic调用失败: {e}")
            raise
    
    async def stream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式调用Anthropic Claude
        
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
            self.logger.error(f"Anthropic流式调用失败: {e}")
            raise
