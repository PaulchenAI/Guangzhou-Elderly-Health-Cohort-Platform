# -*- coding: utf-8 -*-
"""
代码加载器

通过 Claude Code CLI（ClaudeCodeClient）读取代码文件，并进行分块处理，
输出 LangChain Document 以便后续向量化与检索。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from ...claude_code.client import ClaudeCodeClient
from ...logging.logger import get_logger

logger = get_logger("rag.code_loader")


@dataclass(frozen=True)
class CodeChunkConfig:
    """代码分块配置"""

    chunk_size: int = 1000
    chunk_overlap: int = 200


class CodeLoader:
    """代码加载器（通过 ClaudeCodeClient 读取）"""

    def __init__(
        self,
        claude_client: ClaudeCodeClient,
        chunk_config: Optional[CodeChunkConfig] = None,
    ) -> None:
        self.claude_client = claude_client
        self.chunk_config = chunk_config or CodeChunkConfig()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_config.chunk_size,
            chunk_overlap=self.chunk_config.chunk_overlap,
        )

    async def load_files(self, file_paths: Sequence[str]) -> List[Document]:
        """读取并分块一组代码文件。"""

        documents: List[Document] = []
        for file_path in file_paths:
            try:
                content = await self.claude_client.read_file(file_path)
            except Exception as e:
                logger.warning(f"读取代码文件失败: {file_path} ({e})")
                continue

            language = Path(file_path).suffix.lstrip(".").lower() or "text"
            base_meta = {
                "source": str(file_path),
                "type": "code",
                "language": language,
            }

            chunks = self._splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={**base_meta, "chunk_index": i, "chunk_count": len(chunks)},
                    )
                )

        return documents

    async def load_glob(
        self,
        pattern: str,
        path: str = ".",
        exclude_patterns: Optional[Iterable[str]] = None,
    ) -> List[Document]:
        """
        使用 Claude Code CLI 的 glob 能力列出文件，再读取并分块。

        Args:
            pattern: glob 模式（如 "*.py"）
            path: 搜索路径（相对于 ClaudeCodeClient 的 working_dir 或绝对路径）
            exclude_patterns: 需要排除的后缀/子串（最小实现：按“包含”过滤）
        """

        files = await self.claude_client.search_files(pattern=pattern, path=path)
        if not files:
            return []

        excludes = list(exclude_patterns or [])
        if excludes:
            files = [f for f in files if not any(ex in f for ex in excludes)]

        return await self.load_files(files)

