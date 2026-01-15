# -*- coding: utf-8 -*-
"""
OpenSpec 文件解析器（最小可用版）

目标：
- 能解析 proposal.md / tasks.md / design.md / spec.md
- 能解析变更目录结构（用于校验与进度跟踪）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logging.logger import get_logger

logger = get_logger("openspec.parser")


@dataclass(frozen=True)
class ParsedTask:
    text: str
    checked: bool
    indent: int


class OpenSpecParser:
    """解析 OpenSpec 变更文件结构"""

    def read_text(self, path: str) -> str:
        p = Path(path)
        return p.read_text(encoding="utf-8", errors="ignore")

    def parse_proposal(self, proposal_path: str) -> Dict[str, Any]:
        """
        解析 proposal.md（最小实现：按标题分段提取文本）。
        """

        text = self.read_text(proposal_path)
        return {
            "title": self._first_heading(text),
            "why": self._section(text, "为什么"),
            "changes": self._section(text, "变更内容"),
            "impact": self._section(text, "影响"),
            "raw": text,
        }

    def parse_design(self, design_path: str) -> Dict[str, Any]:
        text = self.read_text(design_path)
        return {"title": self._first_heading(text), "raw": text}

    def parse_spec(self, spec_path: str) -> Dict[str, Any]:
        text = self.read_text(spec_path)
        return {"title": self._first_heading(text), "raw": text}

    def parse_tasks(self, tasks_path: str) -> List[ParsedTask]:
        """
        解析 tasks.md 中的勾选项。
        """

        text = self.read_text(tasks_path)
        tasks: List[ParsedTask] = []
        for line in text.splitlines():
            m = re.match(r"^(\s*)-\s+\[(x| )\]\s+(.*)$", line)
            if not m:
                continue
            indent = len(m.group(1) or "")
            checked = m.group(2) == "x"
            tasks.append(ParsedTask(text=m.group(3).strip(), checked=checked, indent=indent))
        return tasks

    def parse_change_structure(self, change_dir: str) -> Dict[str, Any]:
        """
        解析变更目录结构（文件存在性 + specs 列表）。
        """

        base = Path(change_dir)
        proposal = base / "proposal.md"
        tasks = base / "tasks.md"
        design = base / "design.md"
        specs_dir = base / "specs"

        spec_files: List[str] = []
        if specs_dir.exists():
            spec_files = [str(p) for p in specs_dir.rglob("*.md") if p.is_file()]

        return {
            "change_dir": str(base),
            "proposal_exists": proposal.exists(),
            "tasks_exists": tasks.exists(),
            "design_exists": design.exists(),
            "spec_files": spec_files,
        }

    def _first_heading(self, text: str) -> str:
        for line in text.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def _section(self, text: str, header: str) -> str:
        """
        提取二级标题段落：## <header>
        """

        pattern = rf"^##\s+{re.escape(header)}\s*$"
        lines = text.splitlines()
        start: Optional[int] = None
        end: Optional[int] = None

        for i, line in enumerate(lines):
            if re.match(pattern, line):
                start = i + 1
                continue
            if start is not None and line.startswith("## "):
                end = i
                break

        if start is None:
            return ""
        if end is None:
            end = len(lines)
        return "\n".join(lines[start:end]).strip()

