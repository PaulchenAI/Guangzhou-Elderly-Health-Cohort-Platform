# -*- coding: utf-8 -*-
"""
记忆管理器
整合短期、中期和长期记忆系统
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_memory import BaseMemory, MemoryItem, MemorySearchResult
from .conversation import ConversationMemory
from .long_term import LongTermMemory
from .redis_cache import RedisCache
from .vector_store import ChromaVectorStore
from ..utils.config_models import MemoryConfig, VectorDBConfig
from ..logging.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """记忆管理器（整合所有记忆系统）"""
    
    def __init__(
        self,
        memory_config: MemoryConfig,
        vector_db_config: VectorDBConfig,
        conversation_max_size: int = 1000
    ):
        """
        初始化记忆管理器
        
        Args:
            memory_config: 记忆系统配置
            vector_db_config: 向量数据库配置
            conversation_max_size: 对话记忆最大数量
        """
        self.memory_config = memory_config
        self.vector_db_config = vector_db_config
        
        # 初始化短期记忆（对话记忆）
        self.conversation_memory = ConversationMemory(max_size=conversation_max_size)
        
        # 初始化长期记忆（向量存储）
        vector_store = ChromaVectorStore(vector_db_config, collection_name="long_term_memories")
        self.long_term_memory = LongTermMemory(vector_store)
        
        # 初始化中期记忆（Redis缓存，可选）
        self.redis_cache: Optional[RedisCache] = None
        if memory_config.backend == "redis":
            try:
                self.redis_cache = RedisCache(memory_config)
            except Exception as e:
                logger.warning(f"Redis缓存初始化失败，将跳过中期记忆: {e}")
        
        logger.info("记忆管理器初始化完成")
    
    def set_session(self, session_id: str):
        """设置当前会话ID"""
        self.conversation_memory.set_session(session_id)
        logger.debug(f"会话已设置: {session_id}")
    
    async def save(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        store_type: str = "auto"
    ) -> Dict[str, str]:
        """
        保存记忆（自动选择存储类型）
        
        Args:
            content: 记忆内容
            metadata: 元数据
            importance: 重要性评分（0-1）
            store_type: 存储类型
                - "auto": 根据重要性自动选择
                - "conversation": 仅保存到对话记忆
                - "redis": 仅保存到Redis缓存
                - "long_term": 仅保存到长期记忆
                - "all": 保存到所有存储
        
        Returns:
            各存储的记忆ID字典
        """
        memory_ids = {}
        
        # 自动选择存储类型
        if store_type == "auto":
            # 重要性高的保存到长期记忆
            if importance >= 0.7:
                store_type = "long_term"
            # 重要性中等的保存到Redis
            elif importance >= 0.4 and self.redis_cache:
                store_type = "redis"
            # 其他保存到对话记忆
            else:
                store_type = "conversation"
        
        # 保存到对话记忆（总是保存，用于当前会话）
        conv_id = await self.conversation_memory.save(content, metadata, importance)
        memory_ids["conversation"] = conv_id
        
        # 根据类型保存到其他存储
        if store_type == "all":
            if self.redis_cache:
                redis_id = await self.redis_cache.save(content, metadata, importance)
                memory_ids["redis"] = redis_id
            
            long_term_id = await self.long_term_memory.save(content, metadata, importance)
            memory_ids["long_term"] = long_term_id
            
        elif store_type == "redis" and self.redis_cache:
            redis_id = await self.redis_cache.save(content, metadata, importance)
            memory_ids["redis"] = redis_id
            
        elif store_type == "long_term":
            long_term_id = await self.long_term_memory.save(content, metadata, importance)
            memory_ids["long_term"] = long_term_id
        
        logger.debug(f"记忆已保存: {memory_ids}")
        return memory_ids
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        search_types: Optional[List[str]] = None
    ) -> List[MemorySearchResult]:
        """
        搜索记忆（从所有存储中搜索）
        
        Args:
            query: 查询文本
            top_k: 每个存储返回的结果数量
            min_score: 最小相关性评分
            search_types: 搜索的存储类型列表
                - None: 搜索所有存储
                - ["conversation"]: 仅搜索对话记忆
                - ["redis"]: 仅搜索Redis缓存
                - ["long_term"]: 仅搜索长期记忆
        
        Returns:
            合并后的搜索结果（按相关性排序）
        """
        all_results = []
        
        if search_types is None:
            search_types = ["conversation", "redis", "long_term"]
        
        # 搜索对话记忆
        if "conversation" in search_types:
            conv_results = await self.conversation_memory.search(query, top_k, min_score)
            all_results.extend(conv_results)
        
        # 搜索Redis缓存
        if "redis" in search_types and self.redis_cache:
            redis_results = await self.redis_cache.search(query, top_k, min_score)
            all_results.extend(redis_results)
        
        # 搜索长期记忆
        if "long_term" in search_types:
            long_term_results = await self.long_term_memory.search(query, top_k, min_score)
            all_results.extend(long_term_results)
        
        # 去重（按ID）并排序
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.item.id not in seen_ids:
                seen_ids.add(result.item.id)
                unique_results.append(result)
        
        # 按分数排序
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        # 返回Top K
        return unique_results[:top_k]
    
    async def get(self, memory_id: str, store_type: Optional[str] = None) -> Optional[MemoryItem]:
        """
        获取记忆
        
        Args:
            memory_id: 记忆ID
            store_type: 存储类型（如果为None则尝试所有存储）
        
        Returns:
            记忆项
        """
        if store_type == "conversation":
            return await self.conversation_memory.get(memory_id)
        elif store_type == "redis" and self.redis_cache:
            return await self.redis_cache.get(memory_id)
        elif store_type == "long_term":
            return await self.long_term_memory.get(memory_id)
        else:
            # 尝试所有存储
            for store in [self.conversation_memory, self.long_term_memory]:
                if store:
                    result = await store.get(memory_id)
                    if result:
                        return result
            
            if self.redis_cache:
                result = await self.redis_cache.get(memory_id)
                if result:
                    return result
        
        return None
    
    async def delete(self, memory_id: str, store_type: Optional[str] = None) -> bool:
        """删除记忆"""
        if store_type:
            stores = {
                "conversation": self.conversation_memory,
                "redis": self.redis_cache,
                "long_term": self.long_term_memory
            }
            store = stores.get(store_type)
            if store:
                return await store.delete(memory_id)
        else:
            # 尝试从所有存储中删除
            results = []
            for store in [self.conversation_memory, self.long_term_memory]:
                if store:
                    results.append(await store.delete(memory_id))
            
            if self.redis_cache:
                results.append(await self.redis_cache.delete(memory_id))
            
            return any(results)
        
        return False
    
    async def clear(self, store_type: Optional[str] = None) -> bool:
        """清空记忆"""
        if store_type:
            stores = {
                "conversation": self.conversation_memory,
                "redis": self.redis_cache,
                "long_term": self.long_term_memory
            }
            store = stores.get(store_type)
            if store:
                return await store.clear()
        else:
            # 清空所有存储
            results = []
            results.append(await self.conversation_memory.clear())
            results.append(await self.long_term_memory.clear())
            
            if self.redis_cache:
                results.append(await self.redis_cache.clear())
            
            return all(results)
        
        return False
    
    def get_conversation_history(self, limit: int = 50) -> List[MemoryItem]:
        """获取对话历史"""
        return self.conversation_memory.get_conversation_history(limit)
    
    async def close(self):
        """关闭所有连接"""
        if self.redis_cache:
            await self.redis_cache.close()
        logger.info("记忆管理器已关闭")
