# -*- coding: utf-8 -*-
"""
向量存储封装
支持ChromaDB等向量数据库
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from .base_memory import BaseMemory, MemoryItem, MemorySearchResult
from ..utils.config_models import VectorDBConfig
from ..logging.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore(BaseMemory):
    """ChromaDB向量存储实现"""
    
    def __init__(self, config: VectorDBConfig, collection_name: str = "memories"):
        """
        初始化ChromaDB向量存储
        
        Args:
            config: 向量数据库配置
            collection_name: 集合名称
        """
        self.config = config
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialized = False
    
    async def _initialize(self):
        """初始化ChromaDB客户端和集合"""
        if self._initialized:
            return
        
        try:
            # 创建ChromaDB客户端
            if self.config.type == "chromadb":
                self.client = chromadb.PersistentClient(
                    path=self.config.persist_dir,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            else:
                raise ValueError(f"不支持的向量数据库类型: {self.config.type}")
            
            # 获取或创建集合
            # 使用默认的嵌入函数（如果未指定）
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_fn,
                metadata={"description": "记忆系统向量存储"}
            )
            
            self._initialized = True
            logger.info(f"ChromaDB向量存储初始化成功: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {e}", exc_info=True)
            raise
    
    async def save(self, content: str, metadata: Optional[Dict[str, Any]] = None,
                   importance: float = 0.5) -> str:
        """保存记忆到向量存储"""
        await self._initialize()
        
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # 准备元数据
        item_metadata = {
            "timestamp": timestamp.isoformat(),
            "importance": str(importance),
            **(metadata or {})
        }
        
        try:
            # 添加到向量存储
            self.collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[item_metadata]
            )
            
            logger.debug(f"记忆已保存: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"保存记忆失败: {e}", exc_info=True)
            raise
    
    async def search(self, query: str, top_k: int = 5,
                    min_score: float = 0.0) -> List[MemorySearchResult]:
        """搜索记忆"""
        await self._initialize()
        
        try:
            # 执行向量搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # 解析结果
            search_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i, memory_id in enumerate(results['ids'][0]):
                    # 获取距离（ChromaDB返回的是距离，需要转换为相似度分数）
                    distance = results['distances'][0][i] if results.get('distances') else 0.0
                    # 将距离转换为相似度分数（距离越小，相似度越高）
                    score = max(0.0, 1.0 - distance)
                    
                    if score >= min_score:
                        # 获取文档和元数据
                        doc = results['documents'][0][i] if results.get('documents') else ""
                        meta = results['metadatas'][0][i] if results.get('metadatas') else {}
                        
                        # 解析元数据
                        timestamp_str = meta.get('timestamp', datetime.now().isoformat())
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except:
                            timestamp = datetime.now()
                        
                        importance = float(meta.get('importance', '0.5'))
                        
                        # 创建记忆项
                        memory_item = MemoryItem(
                            id=memory_id,
                            content=doc,
                            metadata={k: v for k, v in meta.items() 
                                     if k not in ['timestamp', 'importance']},
                            timestamp=timestamp,
                            importance=importance
                        )
                        
                        search_results.append(
                            MemorySearchResult(item=memory_item, score=score)
                        )
            
            # 按分数排序
            search_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.debug(f"搜索到 {len(search_results)} 条记忆")
            return search_results
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}", exc_info=True)
            return []
    
    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        await self._initialize()
        
        try:
            results = self.collection.get(ids=[memory_id])
            
            if not results['ids'] or len(results['ids']) == 0:
                return None
            
            # 解析结果
            doc = results['documents'][0] if results.get('documents') else ""
            meta = results['metadatas'][0] if results.get('metadatas') else {}
            
            # 解析元数据
            timestamp_str = meta.get('timestamp', datetime.now().isoformat())
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except:
                timestamp = datetime.now()
            
            importance = float(meta.get('importance', '0.5'))
            
            return MemoryItem(
                id=memory_id,
                content=doc,
                metadata={k: v for k, v in meta.items() 
                         if k not in ['timestamp', 'importance']},
                timestamp=timestamp,
                importance=importance
            )
            
        except Exception as e:
            logger.error(f"获取记忆失败: {e}", exc_info=True)
            return None
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        await self._initialize()
        
        try:
            self.collection.delete(ids=[memory_id])
            logger.debug(f"记忆已删除: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除记忆失败: {e}", exc_info=True)
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
            
            # 合并元数据
            new_metadata = existing.metadata.copy()
            if metadata:
                new_metadata.update(metadata)
            
            # 更新重要性
            new_importance = importance if importance is not None else existing.importance
            
            # 更新内容
            new_content = content if content is not None else existing.content
            
            # 更新元数据中的时间戳和重要性
            item_metadata = {
                "timestamp": datetime.now().isoformat(),
                "importance": str(new_importance),
                **new_metadata
            }
            
            # 更新向量存储
            self.collection.update(
                ids=[memory_id],
                documents=[new_content] if content else None,
                metadatas=[item_metadata]
            )
            
            logger.debug(f"记忆已更新: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新记忆失败: {e}", exc_info=True)
            return False
    
    async def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """列出记忆"""
        await self._initialize()
        
        try:
            # 获取所有记忆（ChromaDB不支持分页，需要手动处理）
            results = self.collection.get()
            
            memories = []
            if results['ids']:
                for i, memory_id in enumerate(results['ids']):
                    if i < offset:
                        continue
                    if len(memories) >= limit:
                        break
                    
                    doc = results['documents'][i] if results.get('documents') else ""
                    meta = results['metadatas'][i] if results.get('metadatas') else {}
                    
                    # 解析元数据
                    timestamp_str = meta.get('timestamp', datetime.now().isoformat())
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except:
                        timestamp = datetime.now()
                    
                    importance = float(meta.get('importance', '0.5'))
                    
                    memories.append(
                        MemoryItem(
                            id=memory_id,
                            content=doc,
                            metadata={k: v for k, v in meta.items() 
                                     if k not in ['timestamp', 'importance']},
                            timestamp=timestamp,
                            importance=importance
                        )
                    )
            
            return memories
            
        except Exception as e:
            logger.error(f"列出记忆失败: {e}", exc_info=True)
            return []
    
    async def clear(self) -> bool:
        """清空所有记忆"""
        await self._initialize()
        
        try:
            # 删除集合并重新创建
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_functions.DefaultEmbeddingFunction(),
                metadata={"description": "记忆系统向量存储"}
            )
            
            logger.info(f"已清空集合: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"清空记忆失败: {e}", exc_info=True)
            return False
