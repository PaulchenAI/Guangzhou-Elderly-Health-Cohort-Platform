# -*- coding: utf-8 -*-
"""
规划智能体（最小可用版，集成 OpenSpecManager）

职责：
- 将复杂任务拆解为提案 stubs
- 生成执行计划（顺序 + 可并行组）
- 将 openspec_proposals / openspec_plan 写入 state
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base_agent import AgentResult, BaseAgent
from ..openspec.manager import OpenSpecManager


class PlanningAgent(BaseAgent):
    name = "planning"

    def __init__(self, openspec_manager: OpenSpecManager, *, tools: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tools=tools)
        self.openspec_manager = openspec_manager

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        task = state.get("current_task") or ""
        stubs = self.openspec_manager.break_down_task(task_description=task, context=state.get("context"))
        plan = self.openspec_manager.create_proposal_plan(stubs)

        proposals = [
            {"change_id": s.change_id, "description": s.description, "depends_on": list(s.depends_on)}
            for s in stubs
        ]
        plan_dict = {
            "ordered": [p.change_id for p in plan.ordered],
            "parallel_groups": [[p.change_id for p in grp] for grp in plan.parallel_groups],
        }

        return AgentResult(
            updates={"openspec_proposals": proposals, "openspec_plan": plan_dict},
            output_text=f"规划生成 {len(proposals)} 个提案",
        )

