"""
RAG 模块

包含：
- loaders：代码/文档/数据库元数据加载
- embeddings：嵌入模型封装
- indexer：向量索引构建与增量更新
- retriever：检索器
"""

from .embeddings import create_embeddings
from .indexer import RAGIndexer
from .retriever import RAGRetriever, RetrievalConfig

__all__ = [
    "create_embeddings",
    "RAGIndexer",
    "RAGRetriever",
    "RetrievalConfig",
]

