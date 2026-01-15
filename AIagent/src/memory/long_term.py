# -*- coding: utf-8 -*-
"""
长期记忆
使用向量存储实现长期记忆的存储和检索
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_memory import BaseMemory, MemoryItem, MemorySearchResult
from .vector_store import ChromaVectorStore
from ..utils.config_models import VectorDBConfig
from ..logging.logger import get_logger

logger = get_logger(__name__)


class LongTermMemory(BaseMemory):
    """长期记忆（使用向量存储）"""
    
    def __init__(self, vector_store: ChromaVectorStore):
        """
        初始化长期记忆
        
        Args:
            vector_store: 向量存储实例
        """
        self.vector_store = vector_store
        logger.info("长期记忆已初始化")
    
    async def save(self, content: str, metadata: Optional[Dict[str, Any]] = None,
                   importance: float = 0.5) -> str:
        """保存记忆到长期存储"""
        return await self.vector_store.save(content, metadata, importance)
    
    async def search(self, query: str, top_k: int = 5,
                    min_score: float = 0.0) -> List[MemorySearchResult]:
        """搜索长期记忆（使用向量相似度搜索）"""
        return await self.vector_store.search(query, top_k, min_score)
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return await self.vector_store.get(memory_id)
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        return await self.vector_store.delete(memory_id)
    
    async def update(self, memory_id: str, content: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    importance: Optional[float] = None) -> bool:
        """更新记忆"""
        return await self.vector_store.update(memory_id, content, metadata, importance)
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """列出记忆"""
        return await self.vector_store.list(limit, offset)
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        return await self.vector_store.clear()
    
    async def save_important_memory(self, content: str, 
                                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        保存重要记忆（高重要性）
        
        Args:
            content: 记忆内容
            metadata: 元数据
            
        Returns:
            记忆ID
        """
        return await self.save(content, metadata, importance=0.9)
    
    async def search_by_importance(self, query: str, min_importance: float = 0.7,
                                  top_k: int = 5) -> List[MemorySearchResult]:
        """
        按重要性搜索记忆
        
        Args:
            query: 查询文本
            min_importance: 最小重要性评分
            top_k: 返回数量
            
        Returns:
            搜索结果列表
        """
        results = await self.search(query, top_k=top_k * 2)  # 获取更多结果用于过滤
        
        # 过滤重要性
        filtered = [
            r for r in results
            if r.item.importance >= min_importance
        ]
        
        return filtered[:top_k]
