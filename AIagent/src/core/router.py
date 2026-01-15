# -*- coding: utf-8 -*-
"""
智能体路由（最小可用版）

根据 state["route"] 或 OrchestratorAgent 的决策进行路由。
"""

from __future__ import annotations

from typing import Any, Dict


def route_decision(state: Dict[str, Any]) -> str:
    """
    返回下一步节点名：
    - need_context -> rag
    - need_memory -> memory
    - need_plan / need_openspec -> planning
    - execute -> claude_code
    - end -> end
    """

    route = state.get("route") or "execute"
    if route == "need_context":
        return "rag"
    if route == "need_memory":
        return "memory"
    if route in ("need_plan", "need_openspec"):
        return "planning"
    if route == "execute":
        return "claude_code"
    return "end"

