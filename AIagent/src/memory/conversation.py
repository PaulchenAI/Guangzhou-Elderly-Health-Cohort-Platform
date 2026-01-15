# -*- coding: utf-8 -*-
"""
对话记忆
实现短期记忆（内存）和会话管理
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque
import uuid

from .base_memory import BaseMemory, MemoryItem, MemorySearchResult
from ..logging.logger import get_logger

logger = get_logger(__name__)


class ConversationMemory(BaseMemory):
    """对话记忆（短期记忆，存储在内存中）"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化对话记忆
        
        Args:
            max_size: 最大记忆数量
        """
        self.max_size = max_size
        self._memories: Dict[str, MemoryItem] = {}
        self._session_id: Optional[str] = None
        self._conversation_history: deque = deque(maxlen=max_size)
    
    def set_session(self, session_id: str):
        """设置当前会话ID"""
        self._session_id = session_id
        logger.debug(f"会话已设置: {session_id}")
    
    def get_session(self) -> Optional[str]:
        """获取当前会话ID"""
        return self._session_id
    
    async def save(self, content: str, metadata: Optional[Dict[str, Any]] = None,
                   importance: float = 0.5) -> str:
        """保存记忆到内存"""
        memory_id = str(uuid.uuid4())
        
        # 添加会话ID到元数据
        item_metadata = metadata or {}
        if self._session_id:
            item_metadata['session_id'] = self._session_id
        
        memory_item = MemoryItem(
            id=memory_id,
            content=content,
            metadata=item_metadata,
            timestamp=datetime.now(),
            importance=importance
        )
        
        # 存储记忆
        self._memories[memory_id] = memory_item
        self._conversation_history.append(memory_item)
        
        # 如果超过最大大小，删除最旧的记忆
        if len(self._memories) > self.max_size:
            # 删除最旧的记忆（按时间戳）
            sorted_memories = sorted(
                self._memories.items(),
                key=lambda x: x[1].timestamp
            )
            oldest_id = sorted_memories[0][0]
            del self._memories[oldest_id]
        
        logger.debug(f"对话记忆已保存: {memory_id}")
        return memory_id
    
    async def search(self, query: str, top_k: int = 5,
                    min_score: float = 0.0) -> List[MemorySearchResult]:
        """搜索记忆（简单的关键词匹配）"""
        query_lower = query.lower()
        results = []
        
        for memory_item in self._memories.values():
            # 简单的文本匹配评分
            content_lower = memory_item.content.lower()
            if query_lower in content_lower:
                # 计算简单的匹配分数
                score = len(query_lower) / max(len(content_lower), 1)
                score = min(1.0, score)
                
                if score >= min_score:
                    results.append(
                        MemorySearchResult(item=memory_item, score=score)
                    )
        
        # 按分数和时间戳排序
        results.sort(key=lambda x: (x.score, x.item.timestamp), reverse=True)
        
        # 返回Top K
        return results[:top_k]
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return self._memories.get(memory_id)
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self._memories:
            del self._memories[memory_id]
            logger.debug(f"对话记忆已删除: {memory_id}")
            return True
        return False
    
    async def update(self, memory_id: str, content: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    importance: Optional[float] = None) -> bool:
        """更新记忆"""
        if memory_id not in self._memories:
            return False
        
        memory_item = self._memories[memory_id]
        
        if content is not None:
            memory_item.content = content
        
        if metadata is not None:
            memory_item.metadata.update(metadata)
        
        if importance is not None:
            memory_item.importance = importance
        
        memory_item.timestamp = datetime.now()
        
        logger.debug(f"对话记忆已更新: {memory_id}")
        return True
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """列出记忆（按时间倒序）"""
        sorted_memories = sorted(
            self._memories.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return sorted_memories[offset:offset + limit]
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        self._memories.clear()
        self._conversation_history.clear()
        logger.info("对话记忆已清空")
        return True
    
    def get_conversation_history(self, limit: int = 50) -> List[MemoryItem]:
        """
        获取对话历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            对话历史列表（按时间顺序）
        """
        return list(self._conversation_history)[-limit:]
    
    def get_session_memories(self, session_id: Optional[str] = None) -> List[MemoryItem]:
        """
        获取指定会话的记忆
        
        Args:
            session_id: 会话ID，如果为None则使用当前会话
            
        Returns:
            会话记忆列表
        """
        target_session = session_id or self._session_id
        if not target_session:
            return []
        
        return [
            item for item in self._memories.values()
            if item.metadata.get('session_id') == target_session
        ]
