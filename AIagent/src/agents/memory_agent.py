# -*- coding: utf-8 -*-
"""
记忆智能体（最小可用版）

职责：
- 根据当前任务从 MemoryManager 搜索相关记忆
- 将结果写入 state["memory"]
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base_agent import AgentResult, BaseAgent
from ..memory.manager import MemoryManager


class MemoryAgent(BaseAgent):
    name = "memory"

    def __init__(self, memory_manager: MemoryManager, *, tools: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tools=tools)
        self.memory_manager = memory_manager

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        task = state.get("current_task") or ""
        top_k = int(state.get("memory_top_k") or 5)

        results = await self.memory_manager.search(task, top_k=top_k)
        memories = [
            {
                "id": r.item.id,
                "content": r.item.content,
                "metadata": dict(r.item.metadata),
                "importance": r.item.importance,
                "score": r.score,
            }
            for r in results
        ]

        return AgentResult(
            updates={"memory": {"hits": memories}},
            output_text=f"记忆检索到 {len(memories)} 条结果",
        )

