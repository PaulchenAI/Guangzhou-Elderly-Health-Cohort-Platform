# -*- coding: utf-8 -*-
"""
本地模型LLM客户端实现（支持Ollama等）
"""

from typing import List, AsyncIterator
from langchain_core.messages import BaseMessage
from langchain_community.chat_models import ChatOllama
from langchain_core.language_models import BaseLanguageModel
from .base import BaseLLMClient
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger


class LocalLLMClient(BaseLLMClient):
    """本地模型LLM客户端（Ollama等）"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化本地模型客户端
        
        Args:
            config: LLM配置
        """
        super().__init__(config)
        
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.base_url = config.base_url or "http://localhost:11434"  # Ollama默认端点
    
    def get_langchain_model(self) -> BaseLanguageModel:
        """
        获取LangChain ChatOllama模型实例
        
        Returns:
            ChatOllama实例
        """
        if self._langchain_model is None:
            self._langchain_model = ChatOllama(
                base_url=self.base_url,
                model=self.model,
                temperature=self.temperature,
                num_predict=self.max_tokens  # Ollama使用num_predict而不是max_tokens
            )
        return self._langchain_model
    
    async def invoke(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> str:
        """
        调用本地模型
        
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
        }
        invoke_kwargs.update({k: v for k, v in kwargs.items() if k not in invoke_kwargs})
        
        try:
            # Ollama的invoke是同步的，需要包装
            response = await model.ainvoke(messages, **invoke_kwargs)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            self.logger.error(f"本地模型调用失败: {e}")
            raise
    
    async def stream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式调用本地模型
        
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
        }
        invoke_kwargs.update({k: v for k, v in kwargs.items() if k not in invoke_kwargs})
        
        try:
            async for chunk in model.astream(messages, **invoke_kwargs):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                elif isinstance(chunk, str):
                    yield chunk
        except Exception as e:
            self.logger.error(f"本地模型流式调用失败: {e}")
            raise
