# -*- coding: utf-8 -*-
"""
OpenSpec 管理器（最小可用版）

提供：
- break_down_task：将复杂任务拆解为多个提案（启发式）
- create_proposal_plan：根据依赖关系生成执行顺序（最小实现）
- track_progress：统计 tasks.md 完成进度
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .generator import OpenSpecGenerator
from .parser import OpenSpecParser
from ..logging.logger import get_logger

logger = get_logger("openspec.manager")


def _slugify(text: str) -> str:
    # 最小 slug：中文保留，英文/数字/短横线，其他替换为短横线
    s = text.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "change"


@dataclass
class ProposalStub:
    change_id: str
    description: str
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ProposalPlan:
    ordered: List[ProposalStub]
    parallel_groups: List[List[ProposalStub]]


class OpenSpecManager:
    def __init__(self, openspec_root: str = "openspec") -> None:
        self.openspec_root = Path(openspec_root)
        self.generator = OpenSpecGenerator(openspec_root=openspec_root)
        self.parser = OpenSpecParser()

    def break_down_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> List[ProposalStub]:
        """
        启发式拆解：
        - 按中文顿号/逗号/“和”/and 分割
        - 每个子任务生成一个 ProposalStub
        """

        _ = context or {}
        parts = re.split(r"[、,，;；]\s*|和|and", task_description)
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            parts = [task_description.strip()]

        stubs: List[ProposalStub] = []
        for p in parts:
            # 生成可读 change-id：add- + slug
            cid = f"add-{_slugify(p)[:40]}"
            stubs.append(ProposalStub(change_id=cid, description=p))
        return stubs

    def create_proposal_plan(self, proposals: Sequence[ProposalStub]) -> ProposalPlan:
        """
        最小实现：
        - 若存在 depends_on 则做拓扑排序
        - 否则按输入顺序
        - 同级无依赖的放入 parallel_groups（粗略）
        """

        by_id = {p.change_id: p for p in proposals}
        indeg: Dict[str, int] = {p.change_id: 0 for p in proposals}
        graph: Dict[str, List[str]] = {p.change_id: [] for p in proposals}

        for p in proposals:
            for dep in p.depends_on:
                if dep in by_id:
                    graph[dep].append(p.change_id)
                    indeg[p.change_id] += 1

        queue = [by_id[i] for i, d in indeg.items() if d == 0]
        ordered: List[ProposalStub] = []
        parallel_groups: List[List[ProposalStub]] = []

        while queue:
            # 当前轮可并行
            current = list(queue)
            parallel_groups.append(current)
            queue = []
            for node in current:
                ordered.append(node)
                for nxt in graph.get(node.change_id, []):
                    indeg[nxt] -= 1
                    if indeg[nxt] == 0:
                        queue.append(by_id[nxt])

        # 若存在环，退化：追加剩余
        if len(ordered) != len(proposals):
            remaining = [p for p in proposals if p.change_id not in {o.change_id for o in ordered}]
            ordered.extend(remaining)
            if remaining:
                parallel_groups.append(remaining)

        return ProposalPlan(ordered=ordered, parallel_groups=parallel_groups)

    def track_progress(self, change_id: str) -> Dict[str, Any]:
        """
        跟踪某个变更的 tasks.md 进度（不依赖 openspec-cn）。
        """

        tasks_path = self.openspec_root / "changes" / change_id / "tasks.md"
        if not tasks_path.exists():
            return {"change_id": change_id, "total": 0, "done": 0, "percent": 0.0, "missing": True}

        parsed = self.parser.parse_tasks(str(tasks_path))
        total = len(parsed)
        done = len([t for t in parsed if t.checked])
        percent = (done / total) * 100.0 if total else 0.0
        pending = [t.text for t in parsed if not t.checked]

        return {
            "change_id": change_id,
            "total": total,
            "done": done,
            "percent": percent,
            "pending": pending[:20],
            "missing": False,
        }

