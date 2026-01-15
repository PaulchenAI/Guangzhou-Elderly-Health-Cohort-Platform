# -*- coding: utf-8 -*-
"""
文档索引器（最小可用版）

基于 LangChain 的 Chroma 向量库封装：
- 支持增量 add_documents
- 支持按 source 删除并重建（用于“更新”场景的最小实现）
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import Chroma

from ..logging.logger import get_logger

logger = get_logger("rag.indexer")

def _sanitize_collection_name(name: str) -> str:
    """
    Chroma collection name 规则（常见约束）：
    - 长度 3-512
    - 字符集 [a-zA-Z0-9._-]
    - 必须以字母/数字开头与结尾
    """
    import re

    n = (name or "").strip()
    if not n:
        n = "collection"

    # 替换非法字符为 '-'
    n = re.sub(r"[^a-zA-Z0-9._-]+", "-", n)
    # 去掉首尾非字母数字
    n = re.sub(r"^[^a-zA-Z0-9]+", "", n)
    n = re.sub(r"[^a-zA-Z0-9]+$", "", n)

    if not n:
        n = "collection"

    # 长度不足补齐
    if len(n) < 3:
        n = (n + "-idx")[:3] if len(n) == 1 else (n + "idx")[:3]

    # 长度上限
    if len(n) > 512:
        n = n[:512]
        # 再确保结尾是字母数字
        n = re.sub(r"[^a-zA-Z0-9]+$", "", n) or "collection"

    return n


def _doc_id(doc: Document) -> str:
    """
    生成稳定的文档ID，便于增量更新/去重。
    """

    source = str(doc.metadata.get("source", ""))
    chunk_index = str(doc.metadata.get("chunk_index", ""))
    key = f"{source}::{chunk_index}::{doc.page_content[:200]}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


class RAGIndexer:
    """RAG 索引器"""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embeddings: Embeddings,
    ) -> None:
        self.persist_dir = str(persist_dir)
        self.collection_name = _sanitize_collection_name(collection_name)
        self.embeddings = embeddings
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir,
        )

    def add_documents(self, docs: Sequence[Document]) -> int:
        """增量加入文档到索引。"""

        if not docs:
            return 0

        ids = [_doc_id(d) for d in docs]
        self.vectorstore.add_documents(list(docs), ids=ids)
        self.vectorstore.persist()
        logger.debug(f"已索引文档数量: {len(docs)} (collection={self.collection_name})")
        return len(docs)

    def delete_by_sources(self, sources: Iterable[str]) -> int:
        """
        按 source 删除（最小实现：通过 where 过滤删除）。
        返回删除数量（若底层不返回数量，则返回 0）。
        """

        src_list = list(sources)
        if not src_list:
            return 0

        # Chroma 的 delete 支持 where；这里按 source 精确匹配
        deleted_total = 0
        for src in src_list:
            try:
                self.vectorstore._collection.delete(where={"source": src})
            except Exception as e:
                logger.warning(f"按source删除失败: {src} ({e})")
            else:
                # Chroma API 不一定返回数量；保持最小实现
                deleted_total += 0

        self.vectorstore.persist()
        return deleted_total

    def rebuild_sources(self, docs: Sequence[Document]) -> int:
        """
        重建指定 docs 的 source：先删后加（最小实现的“更新”）。
        """

        sources = {str(d.metadata.get("source", "")) for d in docs if d.metadata.get("source")}
        self.delete_by_sources(sources)
        return self.add_documents(docs)

