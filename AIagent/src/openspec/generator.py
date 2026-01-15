# -*- coding: utf-8 -*-
"""
OpenSpec 提案生成器（最小可用版）

提供：
- create_proposal：创建变更目录与 proposal.md / tasks.md
- generate_spec_increment：生成 specs/<capability>/spec.md 增量
- generate_tasks：生成 tasks.md
- check_conflicts：扫描 changes/ 目录检查规范增量冲突（最小实现）
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..logging.logger import get_logger

logger = get_logger("openspec.generator")


@dataclass(frozen=True)
class Conflict:
    other_change_id: str
    spec_path: str


class OpenSpecGenerator:
    def __init__(self, openspec_root: str = "openspec") -> None:
        self.openspec_root = Path(openspec_root)
        self.changes_dir = self.openspec_root / "changes"

    def create_proposal(
        self,
        change_id: str,
        description: str,
        why: str,
        changes: Sequence[str],
        impacts: Optional[Sequence[str]] = None,
        overwrite: bool = False,
    ) -> Path:
        """
        创建提案骨架：proposal.md + tasks.md + specs/ 目录。
        """

        change_dir = self.changes_dir / change_id
        if change_dir.exists() and not overwrite:
            raise FileExistsError(f"变更目录已存在: {change_dir}")

        (change_dir / "specs").mkdir(parents=True, exist_ok=True)

        proposal_md = change_dir / "proposal.md"
        tasks_md = change_dir / "tasks.md"

        proposal_md.write_text(
            "\n".join(
                [
                    f"# 变更：{description}",
                    "",
                    "## 为什么",
                    "",
                    why.strip(),
                    "",
                    "## 变更内容",
                    "",
                    *[f"- {c}" for c in changes],
                    "",
                    "## 影响",
                    "",
                    *([f"- {i}" for i in impacts] if impacts else ["- 受影响规范：", "- 受影响代码："]),
                    "",
                ]
            ),
            encoding="utf-8",
        )

        if not tasks_md.exists() or overwrite:
            tasks_md.write_text(
                "\n".join(
                    [
                        f"# 任务清单：{description}",
                        "",
                        "## 1. 实施",
                        "- [ ] 1.1 ...",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

        return change_dir

    def generate_tasks(self, change_id: str, plan: Sequence[str], overwrite: bool = True) -> Path:
        """
        根据执行计划生成 tasks.md（最小实现：单层列表）。
        """

        change_dir = self.changes_dir / change_id
        change_dir.mkdir(parents=True, exist_ok=True)
        tasks_md = change_dir / "tasks.md"

        lines = [f"# 任务清单：{change_id}", "", "## 1. 实施"]
        for i, step in enumerate(plan, start=1):
            lines.append(f"- [ ] 1.{i} {step}")
        lines.append("")

        if tasks_md.exists() and not overwrite:
            return tasks_md

        tasks_md.write_text("\n".join(lines), encoding="utf-8")
        return tasks_md

    def generate_spec_increment(
        self,
        change_id: str,
        capability: str,
        requirement_titles: Sequence[str],
        overwrite: bool = False,
    ) -> Path:
        """
        生成 specs/<capability>/spec.md 增量（最小实现：为每个需求生成一个场景骨架）。
        """

        spec_dir = self.changes_dir / change_id / "specs" / capability
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"

        if spec_path.exists() and not overwrite:
            raise FileExistsError(f"规范增量已存在: {spec_path}")

        lines: List[str] = ["## 新增需求", ""]
        for title in requirement_titles:
            lines.extend(
                [
                    f"### 需求：{title}",
                    "系统必须实现该需求。",
                    "",
                    f"#### 场景：{title}（示例）",
                    "- **当** 满足触发条件",
                    "- **那么** 返回期望结果",
                    "",
                ]
            )

        spec_path.write_text("\n".join(lines), encoding="utf-8")
        return spec_path

    def check_conflicts(self, new_change_id: str, spec_paths: Iterable[str]) -> List[Conflict]:
        """
        检查与现有 changes/* 的增量规范路径冲突（最小实现：同一路径即视为冲突）。
        """

        conflicts: List[Conflict] = []
        normalized = {Path(p).as_posix() for p in spec_paths}

        for change_dir in self.changes_dir.iterdir():
            if not change_dir.is_dir():
                continue
            if change_dir.name == new_change_id:
                continue

            specs_dir = change_dir / "specs"
            if not specs_dir.exists():
                continue

            for p in specs_dir.rglob("*.md"):
                rel = p.relative_to(change_dir).as_posix()
                # 只比较 specs/<capability>/spec.md 路径
                if rel.startswith("specs/") and rel in normalized:
                    conflicts.append(Conflict(other_change_id=change_dir.name, spec_path=rel))

        return conflicts

