# -*- coding: utf-8 -*-
"""
数据库元数据加载器（最小可用版）

本项目暂未定义具体数据库连接配置，因此这里提供一个可扩展的接口：
- 允许调用方传入 schema 文本/字典
- 输出 LangChain Document 以供索引与检索
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_core.documents import Document

from ...logging.logger import get_logger

logger = get_logger("rag.db_loader")


SchemaInput = Union[str, Dict[str, Any], List[Dict[str, Any]]]


@dataclass(frozen=True)
class DBSchemaDoc:
    """数据库 schema 文档封装"""

    name: str
    schema: SchemaInput
    metadata: Optional[Dict[str, Any]] = None


class DBLoader:
    """数据库元数据加载器"""

    def load(self, items: Sequence[DBSchemaDoc]) -> List[Document]:
        docs: List[Document] = []
        for item in items:
            meta = {"source": item.name, "type": "db_schema", **(item.metadata or {})}
            content = self._normalize_schema(item.schema)
            docs.append(Document(page_content=content, metadata=meta))
        return docs

    def _normalize_schema(self, schema: SchemaInput) -> str:
        if isinstance(schema, str):
            return schema
        try:
            return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception as e:
            logger.warning(f"序列化schema失败，将退回str(): {e}")
            return str(schema)

