# -*- coding: utf-8 -*-
"""
LLM客户端基类接口
定义所有LLM提供商必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator, Any, Dict
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置
        """
        self.config = config
        self.logger = get_logger("llm")
        self._langchain_model: Optional[BaseLanguageModel] = None
    
    @abstractmethod
    async def invoke(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> str:
        """
        调用LLM
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数（temperature, max_tokens等）
            
        Returns:
            LLM响应文本
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式调用LLM
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            LLM响应文本块
        """
        pass
    
    @abstractmethod
    def get_langchain_model(self) -> BaseLanguageModel:
        """
        获取LangChain兼容的模型实例
        
        Returns:
            LangChain模型实例
        """
        pass
    
    def format_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[BaseMessage]] = None
    ) -> List[BaseMessage]:
        """
        格式化消息列表
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            history: 历史消息（可选）
            
        Returns:
            消息列表
        """
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        if history:
            messages.extend(history)
        
        messages.append(HumanMessage(content=prompt))
        
        return messages
    
    async def invoke_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[BaseMessage]] = None,
        **kwargs
    ) -> str:
        """
        便捷方法：使用字符串提示词调用LLM
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            history: 历史消息（可选）
            **kwargs: 其他参数
            
        Returns:
            LLM响应文本
        """
        messages = self.format_messages(prompt, system_prompt, history)
        return await self.invoke(messages, **kwargs)
    
    async def stream_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[BaseMessage]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        便捷方法：使用字符串提示词流式调用LLM
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            history: 历史消息（可选）
            **kwargs: 其他参数
            
        Yields:
            LLM响应文本块
        """
        messages = self.format_messages(prompt, system_prompt, history)
        async for chunk in self.stream(messages, **kwargs):
            yield chunk
    
    def get_config(self) -> LLMConfig:
        """
        获取配置
        
        Returns:
            LLM配置对象
        """
        return self.config
