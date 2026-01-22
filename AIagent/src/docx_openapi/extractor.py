# -*- coding: utf-8 -*-
"""
DOCX 抽取器（不依赖 python-docx）

实现策略：
- 通过 zipfile 读取 `word/document.xml`
- 用 xml.etree.ElementTree 解析段落（w:p）与表格（w:tbl）
- 输出按文档顺序的 block 流（paragraph/table），供 parser 做状态机解析

注意：
- 这里只提取“文本与表格结构”，不做语义解析。
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .models import DocLocation


_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(frozen=True)
class ParagraphBlock:
    """段落块"""

    text: str
    location: DocLocation


@dataclass(frozen=True)
class TableBlock:
    """表格块（二维文本）"""

    rows: List[List[str]]
    location: DocLocation


DocBlock = ParagraphBlock | TableBlock


def _cell_text(tc: ET.Element) -> str:
    parts: List[str] = []
    for t in tc.findall(".//w:t", _NS):
        if t.text:
            parts.append(t.text)
    return "".join(parts).strip()


def _paragraph_text(p: ET.Element) -> str:
    parts: List[str] = []
    for t in p.findall(".//w:t", _NS):
        if t.text:
            parts.append(t.text)
    return "".join(parts).strip()


def extract_blocks_from_docx(docx_path: str, *, max_blocks: int = 200000) -> List[DocBlock]:
    """
    从 docx 提取段落与表格块（按顺序）。

    Args:
        docx_path: `.docx` 文件路径
        max_blocks: 最大块数量保护（避免极端文档导致内存爆炸）
    """
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml")

    root = ET.fromstring(xml)

    blocks: List[DocBlock] = []
    body = root.find("w:body", _NS)
    if body is None:
        return blocks

    # 只遍历 body 的直接子节点以保持顺序（w:p / w:tbl）
    for idx, child in enumerate(list(body)):
        if idx >= max_blocks:
            break
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = _paragraph_text(child)
            if text:
                blocks.append(
                    ParagraphBlock(
                        text=text,
                        location=DocLocation(
                            block_index=len(blocks),
                            block_type="paragraph",
                            detail=text[:60],
                        ),
                    )
                )
        elif tag == "tbl":
            rows: List[List[str]] = []
            for tr in child.findall(".//w:tr", _NS):
                row: List[str] = []
                for tc in tr.findall(".//w:tc", _NS):
                    row.append(_cell_text(tc))
                if any(c.strip() for c in row):
                    rows.append(row)
            if rows:
                blocks.append(
                    TableBlock(
                        rows=rows,
                        location=DocLocation(
                            block_index=len(blocks),
                            block_type="table",
                            detail=f"rows={len(rows)} cols~={max(len(r) for r in rows)}",
                        ),
                    )
                )

    return blocks


def iter_block_text(blocks: Iterable[DocBlock]) -> Iterable[str]:
    """用于调试：遍历输出块的可读文本。"""
    for b in blocks:
        if isinstance(b, ParagraphBlock):
            yield b.text
        else:
            # 表格做简单拼接
            for r in b.rows:
                yield " | ".join([c for c in r if c])

