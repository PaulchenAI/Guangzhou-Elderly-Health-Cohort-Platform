# -*- coding: utf-8 -*-
"""
记忆系统测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.memory.base_memory import MemoryItem, MemorySearchResult
from src.memory.conversation import ConversationMemory
from src.memory.long_term import LongTermMemory
from src.memory.vector_store import ChromaVectorStore
from src.memory.manager import MemoryManager
from src.memory.redis_cache import RedisCache
from src.utils.config_models import MemoryConfig, VectorDBConfig


class TestMemoryItem:
    """MemoryItem测试"""
    
    def test_memory_item_creation(self):
        """测试创建MemoryItem"""
        item = MemoryItem(
            id="test_id",
            content="test content",
            metadata={"key": "value"},
            timestamp=datetime.now(),
            importance=0.8
        )
        assert item.id == "test_id"
        assert item.content == "test content"
        assert item.metadata == {"key": "value"}
        assert item.importance == 0.8
    
    def test_memory_item_defaults(self):
        """测试MemoryItem默认值"""
        item = MemoryItem(
            id="test_id",
            content="test content",
            timestamp=datetime.now()
        )
        assert item.metadata == {}
        assert item.importance == 0.5


class TestMemorySearchResult:
    """MemorySearchResult测试"""
    
    def test_memory_search_result(self):
        """测试MemorySearchResult"""
        item = MemoryItem(
            id="test_id",
            content="test content",
            timestamp=datetime.now()
        )
        result = MemorySearchResult(item=item, score=0.9)
        assert result.item == item
        assert result.score == 0.9


class TestConversationMemory:
    """对话记忆测试"""
    
    @pytest.fixture
    def conversation_memory(self):
        """创建ConversationMemory实例"""
        return ConversationMemory(max_size=100)
    
    @pytest.mark.asyncio
    async def test_save_memory(self, conversation_memory):
        """测试保存记忆"""
        memory_id = await conversation_memory.save(
            content="test content",
            metadata={"key": "value"},
            importance=0.8
        )
        assert memory_id is not None
        assert len(memory_id) > 0
    
    @pytest.mark.asyncio
    async def test_get_memory(self, conversation_memory):
        """测试获取记忆"""
        memory_id = await conversation_memory.save(
            content="test content",
            importance=0.8
        )
        memory = await conversation_memory.get(memory_id)
        assert memory is not None
        assert memory.id == memory_id
        assert memory.content == "test content"
        assert memory.importance == 0.8
    
    @pytest.mark.asyncio
    async def test_search_memory(self, conversation_memory):
        """测试搜索记忆"""
        await conversation_memory.save(
            content="Python programming language",
            importance=0.8
        )
        await conversation_memory.save(
            content="Java programming language",
            importance=0.7
        )
        
        results = await conversation_memory.search("Python", top_k=5)
        assert len(results) > 0
        assert results[0].item.content == "Python programming language"
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, conversation_memory):
        """测试删除记忆"""
        memory_id = await conversation_memory.save(
            content="test content"
        )
        result = await conversation_memory.delete(memory_id)
        assert result is True
        
        memory = await conversation_memory.get(memory_id)
        assert memory is None
    
    @pytest.mark.asyncio
    async def test_update_memory(self, conversation_memory):
        """测试更新记忆"""
        memory_id = await conversation_memory.save(
            content="old content",
            importance=0.5
        )
        
        result = await conversation_memory.update(
            memory_id,
            content="new content",
            importance=0.9
        )
        assert result is True
        
        memory = await conversation_memory.get(memory_id)
        assert memory.content == "new content"
        assert memory.importance == 0.9
    
    @pytest.mark.asyncio
    async def test_list_memories(self, conversation_memory):
        """测试列出记忆"""
        # 保存多个记忆
        for i in range(5):
            await conversation_memory.save(
                content=f"content {i}",
                importance=0.5
            )
        
        memories = await conversation_memory.list(limit=10)
        assert len(memories) == 5
    
    @pytest.mark.asyncio
    async def test_clear_memories(self, conversation_memory):
        """测试清空记忆"""
        await conversation_memory.save(content="test content")
        result = await conversation_memory.clear()
        assert result is True
        
        memories = await conversation_memory.list()
        assert len(memories) == 0
    
    def test_set_session(self, conversation_memory):
        """测试设置会话"""
        conversation_memory.set_session("session_123")
        assert conversation_memory.get_session() == "session_123"
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, conversation_memory):
        """测试获取对话历史"""
        for i in range(10):
            await conversation_memory.save(content=f"message {i}")
        
        history = conversation_memory.get_conversation_history(limit=5)
        assert len(history) == 5
    
    @pytest.mark.asyncio
    async def test_get_session_memories(self, conversation_memory):
        """测试获取会话记忆"""
        conversation_memory.set_session("session_123")
        
        await conversation_memory.save(
            content="session content",
            metadata={"session_id": "session_123"}
        )
        
        session_memories = conversation_memory.get_session_memories()
        assert len(session_memories) > 0
    
    @pytest.mark.asyncio
    async def test_max_size_limit(self, conversation_memory):
        """测试最大大小限制"""
        # 保存超过最大大小的记忆
        for i in range(150):  # max_size=100
            await conversation_memory.save(content=f"content {i}")
        
        memories = await conversation_memory.list()
        assert len(memories) <= 100


class TestChromaVectorStore:
    """ChromaDB向量存储测试"""
    
    @pytest.fixture
    def temp_chroma_dir(self, temp_dir):
        """创建临时ChromaDB目录"""
        chroma_dir = temp_dir / "chroma"
        chroma_dir.mkdir()
        return chroma_dir
    
    @pytest.fixture
    def vector_store(self, temp_chroma_dir):
        """创建ChromaVectorStore实例"""
        config = VectorDBConfig(
            type="chromadb",
            persist_dir=str(temp_chroma_dir)
        )
        return ChromaVectorStore(config, collection_name="test_memories")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_save_memory(self, vector_store):
        """测试保存记忆到向量存储"""
        memory_id = await vector_store.save(
            content="test content",
            metadata={"key": "value"},
            importance=0.8
        )
        assert memory_id is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_memory(self, vector_store):
        """测试从向量存储获取记忆"""
        memory_id = await vector_store.save(
            content="test content",
            importance=0.8
        )
        memory = await vector_store.get(memory_id)
        assert memory is not None
        assert memory.content == "test content"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_memory(self, vector_store):
        """测试向量搜索"""
        await vector_store.save(
            content="Python is a programming language",
            importance=0.8
        )
        await vector_store.save(
            content="Java is another programming language",
            importance=0.7
        )
        
        results = await vector_store.search("Python", top_k=5)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_delete_memory(self, vector_store):
        """测试删除记忆"""
        memory_id = await vector_store.save(content="test content")
        result = await vector_store.delete(memory_id)
        assert result is True
        
        memory = await vector_store.get(memory_id)
        assert memory is None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_memory(self, vector_store):
        """测试更新记忆"""
        memory_id = await vector_store.save(
            content="old content",
            importance=0.5
        )
        
        result = await vector_store.update(
            memory_id,
            content="new content",
            importance=0.9
        )
        assert result is True
        
        memory = await vector_store.get(memory_id)
        assert memory.content == "new content"
        assert memory.importance == 0.9
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_list_memories(self, vector_store):
        """测试列出记忆"""
        for i in range(5):
            await vector_store.save(content=f"content {i}")
        
        memories = await vector_store.list(limit=10)
        assert len(memories) == 5
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_clear_memories(self, vector_store):
        """测试清空记忆"""
        await vector_store.save(content="test content")
        result = await vector_store.clear()
        assert result is True
        
        memories = await vector_store.list()
        assert len(memories) == 0


class TestLongTermMemory:
    """长期记忆测试"""
    
    @pytest.fixture
    def temp_chroma_dir(self, temp_dir):
        """创建临时ChromaDB目录"""
        chroma_dir = temp_dir / "chroma"
        chroma_dir.mkdir()
        return chroma_dir
    
    @pytest.fixture
    def long_term_memory(self, temp_chroma_dir):
        """创建LongTermMemory实例"""
        config = VectorDBConfig(
            type="chromadb",
            persist_dir=str(temp_chroma_dir)
        )
        vector_store = ChromaVectorStore(config, collection_name="test_long_term")
        return LongTermMemory(vector_store)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_save_important_memory(self, long_term_memory):
        """测试保存重要记忆"""
        memory_id = await long_term_memory.save_important_memory(
            content="important content",
            metadata={"type": "important"}
        )
        assert memory_id is not None
        
        memory = await long_term_memory.get(memory_id)
        assert memory.importance >= 0.9
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_by_importance(self, long_term_memory):
        """测试按重要性搜索"""
        await long_term_memory.save(
            content="high importance content",
            importance=0.9
        )
        await long_term_memory.save(
            content="low importance content",
            importance=0.3
        )
        
        results = await long_term_memory.search_by_importance(
            "content",
            min_importance=0.7,
            top_k=5
        )
        assert len(results) > 0
        assert all(r.item.importance >= 0.7 for r in results)


class TestMemoryManager:
    """记忆管理器测试"""
    
    @pytest.fixture
    def temp_chroma_dir(self, temp_dir):
        """创建临时ChromaDB目录"""
        chroma_dir = temp_dir / "chroma"
        chroma_dir.mkdir()
        return chroma_dir
    
    @pytest.fixture
    def memory_manager(self, temp_chroma_dir):
        """创建MemoryManager实例"""
        memory_config = MemoryConfig(
            backend="memory",  # 不使用Redis，避免需要Redis服务
            ttl=86400
        )
        vector_db_config = VectorDBConfig(
            type="chromadb",
            persist_dir=str(temp_chroma_dir)
        )
        return MemoryManager(
            memory_config=memory_config,
            vector_db_config=vector_db_config,
            conversation_max_size=100
        )
    
    @pytest.mark.asyncio
    async def test_save_memory_auto(self, memory_manager):
        """测试自动选择存储类型保存记忆"""
        # 高重要性 -> 长期记忆
        memory_ids = await memory_manager.save(
            content="high importance content",
            importance=0.8
        )
        assert "conversation" in memory_ids
        assert "long_term" in memory_ids
    
    @pytest.mark.asyncio
    async def test_save_memory_all(self, memory_manager):
        """测试保存到所有存储"""
        memory_ids = await memory_manager.save(
            content="test content",
            store_type="all"
        )
        assert "conversation" in memory_ids
        assert "long_term" in memory_ids
    
    @pytest.mark.asyncio
    async def test_search_memory(self, memory_manager):
        """测试搜索记忆"""
        await memory_manager.save(
            content="Python programming",
            importance=0.8
        )
        
        results = await memory_manager.search(
            query="Python",
            top_k=5
        )
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_get_memory(self, memory_manager):
        """测试获取记忆"""
        memory_ids = await memory_manager.save(
            content="test content",
            importance=0.8
        )
        
        # 尝试从所有存储获取
        memory = await memory_manager.get(memory_ids.get("conversation"))
        assert memory is not None
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_manager):
        """测试删除记忆"""
        memory_ids = await memory_manager.save(
            content="test content"
        )
        
        result = await memory_manager.delete(
            memory_ids.get("conversation")
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_clear_memory(self, memory_manager):
        """测试清空记忆"""
        await memory_manager.save(content="test content")
        result = await memory_manager.clear()
        assert result is True
    
    def test_set_session(self, memory_manager):
        """测试设置会话"""
        memory_manager.set_session("session_123")
        assert memory_manager.conversation_memory.get_session() == "session_123"
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, memory_manager):
        """测试获取对话历史"""
        for i in range(10):
            await memory_manager.save(content=f"message {i}")
        
        history = memory_manager.get_conversation_history(limit=5)
        assert len(history) == 5
    
    @pytest.mark.asyncio
    async def test_close(self, memory_manager):
        """测试关闭管理器"""
        await memory_manager.close()  # 应该不报错


class TestRedisCache:
    """RedisCache 单元测试（完全 mock Redis 客户端）"""

    @pytest.mark.asyncio
    async def test_save_get_delete(self, mocker):
        cfg = MemoryConfig(backend="redis", redis_url="redis://localhost:6379/1", ttl=10)
        cache = RedisCache(cfg)

        store = {}
        index = set()

        mock_client = mocker.Mock()
        mock_client.ping = mocker.AsyncMock(return_value=True)

        async def setex(key, ttl, value):
            store[key] = value
            return True

        async def get(key):
            return store.get(key)

        async def delete(*keys):
            n = 0
            for k in keys:
                if k in store:
                    del store[k]
                    n += 1
            return n

        async def sadd(key, value):
            index.add(value)
            return 1

        async def srem(key, value):
            index.discard(value)
            return 1

        async def smembers(key):
            return set(index)

        async def ttl(key):
            return cfg.ttl

        mock_client.setex = mocker.AsyncMock(side_effect=setex)
        mock_client.get = mocker.AsyncMock(side_effect=get)
        mock_client.delete = mocker.AsyncMock(side_effect=delete)
        mock_client.sadd = mocker.AsyncMock(side_effect=sadd)
        mock_client.srem = mocker.AsyncMock(side_effect=srem)
        mock_client.smembers = mocker.AsyncMock(side_effect=smembers)
        mock_client.ttl = mocker.AsyncMock(side_effect=ttl)
        mock_client.close = mocker.AsyncMock(return_value=True)

        mocker.patch("src.memory.redis_cache.redis.from_url", new=mocker.AsyncMock(return_value=mock_client))

        mid = await cache.save("hello", metadata={"k": "v"}, importance=0.6)
        assert mid

        item = await cache.get(mid)
        assert item is not None
        assert item.content == "hello"

        ok = await cache.delete(mid)
        assert ok is True

        assert await cache.get(mid) is None
