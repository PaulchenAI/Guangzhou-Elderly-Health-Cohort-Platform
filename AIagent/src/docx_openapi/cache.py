# -*- coding: utf-8 -*-
"""
DOCX OpenAPI 解析缓存（断点续跑）

用途：
- LLM 解析每个接口表格耗时且可能失败
- 将“单接口解析结果（已通过 Pydantic 校验）”落盘
- 下次运行时优先复用缓存，避免从头开始
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


def _safe_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def compute_text_hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8", errors="ignore")).hexdigest()


@dataclass(frozen=True)
class CacheKey:
    """缓存键：优先 operationId，其次 block_index"""

    block_index: int
    operation_id: str = ""

    def to_filename(self) -> str:
        if self.operation_id:
            return f"op_{_safe_name(self.operation_id)}__b{self.block_index}.json"
        return f"b{self.block_index}.json"


class EndpointCache:
    """单接口缓存读写"""

    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def read(self, key: CacheKey) -> Optional[Dict[str, Any]]:
        path = self.cache_dir / key.to_filename()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def write(self, key: CacheKey, payload: Dict[str, Any]) -> None:
        path = self.cache_dir / key.to_filename()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

