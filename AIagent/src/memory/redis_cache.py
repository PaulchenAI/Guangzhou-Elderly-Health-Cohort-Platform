# -*- coding: utf-8 -*-
"""
Redis缓存
实现中期记忆存储（跨会话，TTL管理）
"""

import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from .base_memory import BaseMemory, MemoryItem, MemorySearchResult
from ..utils.config_models import MemoryConfig
from ..logging.logger import get_logger

logger = get_logger(__name__)


class RedisCache(BaseMemory):
    """Redis缓存实现（中期记忆）"""
    
    def __init__(self, config: MemoryConfig):
        """
        初始化Redis缓存
        
        Args:
            config: 记忆系统配置
        """
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
        self.key_prefix = "memory:"
    
    async def _initialize(self):
        """初始化Redis客户端"""
        if self._initialized:
            return
        
        try:
            self.redis_client = await redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # 测试连接
            await self.redis_client.ping()
            
            self._initialized = True
            logger.info(f"Redis缓存初始化成功: {self.config.redis_url}")
            
        except Exception as e:
            logger.error(f"Redis初始化失败: {e}", exc_info=True)
            raise
    
    def _get_key(self, memory_id: str) -> str:
        """生成Redis键"""
        return f"{self.key_prefix}{memory_id}"
    
    def _get_index_key(self) -> str:
        """获取索引键"""
        return f"{self.key_prefix}index"
    
    async def save(self, content: str, metadata: Optional[Dict[str, Any]] = None,
                   importance: float = 0.5) -> str:
        """保存记忆到Redis"""
        await self._initialize()
        
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # 创建记忆项
        memory_item = MemoryItem(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            timestamp=timestamp,
            importance=importance
        )
        
        try:
            # 序列化记忆项
            memory_data = {
                "id": memory_item.id,
                "content": memory_item.content,
                "metadata": memory_item.metadata,
                "timestamp": memory_item.timestamp.isoformat(),
                "importance": memory_item.importance
            }
            
            # 保存到Redis（带TTL）
            key = self._get_key(memory_id)
            await self.redis_client.setex(
                key,
                self.config.ttl,
                json.dumps(memory_data, ensure_ascii=False)
            )
            
            # 添加到索引
            index_key = self._get_index_key()
            await self.redis_client.sadd(index_key, memory_id)
            
            logger.debug(f"Redis记忆已保存: {memory_id} (TTL: {self.config.ttl}s)")
            return memory_id
            
        except Exception as e:
            logger.error(f"保存Redis记忆失败: {e}", exc_info=True)
            raise
    
    async def search(self, query: str, top_k: int = 5,
                    min_score: float = 0.0) -> List[MemorySearchResult]:
        """搜索记忆（简单的关键词匹配）"""
        await self._initialize()
        
        query_lower = query.lower()
        results = []
        
        try:
            # 获取所有记忆ID
            index_key = self._get_index_key()
            memory_ids = await self.redis_client.smembers(index_key)
            
            # 遍历所有记忆
            for memory_id in memory_ids:
                memory_item = await self.get(memory_id)
                if not memory_item:
                    continue
                
                # 简单的文本匹配评分
                content_lower = memory_item.content.lower()
                if query_lower in content_lower:
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
            
        except Exception as e:
            logger.error(f"搜索Redis记忆失败: {e}", exc_info=True)
            return []
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        await self._initialize()
        
        try:
            key = self._get_key(memory_id)
            data = await self.redis_client.get(key)
            
            if not data:
                return None
            
            # 反序列化
            memory_data = json.loads(data)
            
            # 解析时间戳
            timestamp_str = memory_data.get('timestamp', datetime.now().isoformat())
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except:
                timestamp = datetime.now()
            
            return MemoryItem(
                id=memory_data['id'],
                content=memory_data['content'],
                metadata=memory_data.get('metadata', {}),
                timestamp=timestamp,
                importance=memory_data.get('importance', 0.5)
            )
            
        except Exception as e:
            logger.error(f"获取Redis记忆失败: {e}", exc_info=True)
            return None
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        await self._initialize()
        
        try:
            key = self._get_key(memory_id)
            result = await self.redis_client.delete(key)
            
            # 从索引中删除
            index_key = self._get_index_key()
            await self.redis_client.srem(index_key, memory_id)
            
            logger.debug(f"Redis记忆已删除: {memory_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"删除Redis记忆失败: {e}", exc_info=True)
            return False
    
    async def update(self, memory_id: str, content: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    importance: Optional[float] = None) -> bool:
        """更新记忆"""
        await self._initialize()
        
        try:
            # 获取现有记忆
            existing = await self.get(memory_id)
            if not existing:
                return False
            
            # 更新字段
            if content is not None:
                existing.content = content
            
            if metadata is not None:
                existing.metadata.update(metadata)
            
            if importance is not None:
                existing.importance = importance
            
            existing.timestamp = datetime.now()
            
            # 保存更新后的记忆
            memory_data = {
                "id": existing.id,
                "content": existing.content,
                "metadata": existing.metadata,
                "timestamp": existing.timestamp.isoformat(),
                "importance": existing.importance
            }
            
            key = self._get_key(memory_id)
            # 获取剩余TTL
            ttl = await self.redis_client.ttl(key)
            if ttl > 0:
                await self.redis_client.setex(
                    key,
                    ttl,  # 保持原有TTL
                    json.dumps(memory_data, ensure_ascii=False)
                )
            else:
                # 如果已过期，使用默认TTL
                await self.redis_client.setex(
                    key,
                    self.config.ttl,
                    json.dumps(memory_data, ensure_ascii=False)
                )
            
            logger.debug(f"Redis记忆已更新: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新Redis记忆失败: {e}", exc_info=True)
            return False
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """列出记忆"""
        await self._initialize()
        
        try:
            # 获取所有记忆ID
            index_key = self._get_index_key()
            memory_ids = list(await self.redis_client.smembers(index_key))
            
            # 获取所有记忆
            memories = []
            for memory_id in memory_ids[offset:offset + limit]:
                memory_item = await self.get(memory_id)
                if memory_item:
                    memories.append(memory_item)
            
            # 按时间戳排序
            memories.sort(key=lambda x: x.timestamp, reverse=True)
            
            return memories
            
        except Exception as e:
            logger.error(f"列出Redis记忆失败: {e}", exc_info=True)
            return []
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        await self._initialize()
        
        try:
            # 获取所有记忆ID
            index_key = self._get_index_key()
            memory_ids = await self.redis_client.smembers(index_key)
            
            # 删除所有记忆
            if memory_ids:
                keys = [self._get_key(mid) for mid in memory_ids]
                await self.redis_client.delete(*keys)
            
            # 清空索引
            await self.redis_client.delete(index_key)
            
            logger.info("Redis记忆已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空Redis记忆失败: {e}", exc_info=True)
            return False
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False
            logger.info("Redis连接已关闭")
