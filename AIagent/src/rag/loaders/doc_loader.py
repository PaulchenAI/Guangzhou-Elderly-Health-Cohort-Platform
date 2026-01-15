# -*- coding: utf-8 -*-
"""
文档加载器

支持读取 Markdown / TXT 等文档并输出 LangChain Document。
（最小实现：按文件整体读取，可选分块）
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from ...logging.logger import get_logger

logger = get_logger("rag.doc_loader")


@dataclass(frozen=True)
class DocChunkConfig:
    """文档分块配置"""

    chunk_size: int = 1000
    chunk_overlap: int = 200


class DocLoader:
    """文档加载器（本地文件读取）"""

    def __init__(self, chunk_config: Optional[DocChunkConfig] = None) -> None:
        self.chunk_config = chunk_config or DocChunkConfig()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_config.chunk_size,
            chunk_overlap=self.chunk_config.chunk_overlap,
        )

    def load_files(self, file_paths: Sequence[str], chunk: bool = True) -> List[Document]:
        """读取并（可选）分块一组文档文件。"""

        docs: List[Document] = []
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                logger.warning(f"文档文件不存在或不可读: {file_path}")
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"读取文档失败: {file_path} ({e})")
                continue

            doc_type = path.suffix.lstrip(".").lower() or "text"
            base_meta = {"source": str(path), "type": "doc", "format": doc_type}

            if not chunk:
                docs.append(Document(page_content=content, metadata=base_meta))
                continue

            chunks = self._splitter.split_text(content)
            for i, c in enumerate(chunks):
                docs.append(
                    Document(
                        page_content=c,
                        metadata={**base_meta, "chunk_index": i, "chunk_count": len(chunks)},
                    )
                )

        return docs

    def load_dir(
        self,
        directory: str,
        extensions: Optional[Iterable[str]] = None,
        chunk: bool = True,
    ) -> List[Document]:
        """读取目录下指定扩展名的文档。"""

        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"文档目录不存在或不可读: {directory}")
            return []

        exts = [e.lower().lstrip(".") for e in (extensions or ["md", "txt"])]
        files = [str(p) for p in dir_path.rglob("*") if p.is_file() and p.suffix.lstrip(".").lower() in exts]
        return self.load_files(files, chunk=chunk)

