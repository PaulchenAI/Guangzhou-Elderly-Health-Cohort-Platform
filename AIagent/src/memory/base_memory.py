# -*- coding: utf-8 -*-
"""
记忆系统基类
定义记忆系统的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class MemoryItem(BaseModel):
    """记忆项"""
    id: str
    content: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    importance: float = 0.5  # 重要性评分（0-1）
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemorySearchResult(BaseModel):
    """记忆搜索结果"""
    item: MemoryItem
    score: float  # 相关性评分（0-1）


class BaseMemory(ABC):
    """记忆系统基类"""
    
    @abstractmethod
    async def save(self, content: str, metadata: Optional[Dict[str, Any]] = None, 
                   importance: float = 0.5) -> str:
        """
        保存记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
            importance: 重要性评分（0-1）
            
        Returns:
            记忆ID
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5, 
                    min_score: float = 0.0) -> List[MemorySearchResult]:
        """
        搜索记忆
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_score: 最小相关性评分
            
        Returns:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """
        获取记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆项，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, content: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    importance: Optional[float] = None) -> bool:
        """
        更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容（可选）
            metadata: 新元数据（可选）
            importance: 新重要性评分（可选）
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """
        列出记忆
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            记忆项列表
        """
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """
        清空所有记忆
        
        Returns:
            是否清空成功
        """
        pass
