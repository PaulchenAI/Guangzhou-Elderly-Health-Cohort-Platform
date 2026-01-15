# -*- coding: utf-8 -*-
"""
检索器（最小可用版）

- 语义检索：基于向量库相似度
- 基础过滤：按 metadata 过滤（source/type/language 等）

混合检索（关键词+语义）先预留接口，后续可引入 BM25 等实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from ..logging.logger import get_logger

logger = get_logger("rag.retriever")


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 5


class RAGRetriever:
    """RAG 检索器"""

    def __init__(self, vectorstore: Chroma, config: Optional[RetrievalConfig] = None) -> None:
        self.vectorstore = vectorstore
        self.config = config or RetrievalConfig()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        语义检索并返回文档。

        Args:
            query: 查询文本
            top_k: 返回数量
            metadata_filter: Chroma where 过滤条件（最小实现：原样透传）
        """

        k = top_k or self.config.top_k
        try:
            if metadata_filter:
                return self.vectorstore.similarity_search(query, k=k, filter=metadata_filter)
            return self.vectorstore.similarity_search(query, k=k)
        except Exception as e:
            logger.warning(f"检索失败: {e}")
            return []

    def hybrid_retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        混合检索（占位实现）：当前直接退化为语义检索。
        """

        return self.retrieve(query=query, top_k=top_k, metadata_filter=metadata_filter)

