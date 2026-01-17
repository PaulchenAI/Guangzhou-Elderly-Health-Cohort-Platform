# -*- coding: utf-8 -*-
"""
API 端点向量索引器

将 OpenAPI 端点向量化，支持语义检索
"""

import logging
from typing import List, Optional, Dict, Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .models import APIEndpoint

logger = logging.getLogger(__name__)


class APIEndpointIndexer:
    """
    API 端点向量索引器
    
    将 API 端点转换为向量，存入向量数据库
    支持语义相似度检索
    """
    
    def __init__(
        self,
        embeddings: Embeddings,
        persist_dir: str = "./data/chroma",
        collection_name: str = "django_api_endpoints",
    ):
        """
        初始化索引器
        
        Args:
            embeddings: 嵌入模型
            persist_dir: 向量数据库持久化目录
            collection_name: 集合名称
        """
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.vectorstore = None
        self._endpoint_map: Dict[str, APIEndpoint] = {}
    
    def build_index(self, endpoints: List[APIEndpoint]) -> int:
        """
        为 API 端点构建向量索引
        
        Args:
            endpoints: API 端点列表
        
        Returns:
            索引的端点数量
        """
        from langchain_community.vectorstores import Chroma
        from pathlib import Path
        
        if not endpoints:
            logger.warning("没有端点需要索引")
            return 0
        
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # 将端点转换为 Document
        documents = []
        for ep in endpoints:
            doc = Document(
                page_content=ep.to_ai_description(),
                metadata={
                    "operation_id": ep.operation_id,
                    "path": ep.path,
                    "method": ep.method,
                    "tags": ",".join(ep.tags),
                    "summary": ep.summary,
                }
            )
            documents.append(doc)
            # 保存映射以便检索后还原
            self._endpoint_map[ep.operation_id] = ep
        
        # 创建向量索引
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=self.persist_dir,
        )
        self.vectorstore.persist()
        
        logger.info(f"已构建 API 端点索引，共 {len(documents)} 个端点")
        return len(documents)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0
    ) -> List[tuple[APIEndpoint, float]]:
        """
        向量相似度检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 相似度阈值（0-1，越大越相似）
        
        Returns:
            (端点, 相似度分数) 列表
        """
        if not self.vectorstore:
            logger.warning("向量索引未初始化")
            return []
        
        # 使用 similarity_search_with_relevance_scores
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query,
            k=top_k,
        )
        
        # 过滤并转换结果
        endpoint_scores = []
        for doc, score in results:
            if score >= score_threshold:
                operation_id = doc.metadata.get("operation_id", "")
                if operation_id in self._endpoint_map:
                    endpoint_scores.append((self._endpoint_map[operation_id], score))
        
        return endpoint_scores
    
    def update_index(self, endpoints: List[APIEndpoint]) -> int:
        """
        增量更新索引
        
        对于已存在的端点进行更新，新端点添加
        
        Args:
            endpoints: 要更新的端点列表
        
        Returns:
            更新的端点数量
        """
        # 简单实现：删除旧的，重新构建
        # 后续可以优化为真正的增量更新
        return self.build_index(endpoints)
    
    def get_endpoint_by_id(self, operation_id: str) -> Optional[APIEndpoint]:
        """根据 operation_id 获取端点"""
        return self._endpoint_map.get(operation_id)
    
    def load_index(self) -> bool:
        """
        加载已存在的索引
        
        Returns:
            是否加载成功
        """
        from langchain_community.vectorstores import Chroma
        from pathlib import Path
        
        index_path = Path(self.persist_dir)
        if not index_path.exists():
            logger.warning(f"索引目录不存在: {self.persist_dir}")
            return False
        
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
            logger.info(f"已加载 API 端点索引: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            return False
