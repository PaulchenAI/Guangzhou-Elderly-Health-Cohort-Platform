# -*- coding: utf-8 -*-
"""
工作流执行器（最小可用版）

提供：
- run：异步执行 LangGraph，返回最终 state
- 基础错误恢复：捕获异常并写入 final_response
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage

from ..logging.logger import get_logger
from .state import AgentState

logger = get_logger("core.executor")


class WorkflowExecutor:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    async def run(self, user_input: str, *, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state: Dict[str, Any] = dict(initial_state or {})
        state.setdefault("messages", [])
        state["messages"].append(HumanMessage(content=user_input))
        state["current_task"] = user_input

        try:
            result = await self.graph.ainvoke(state)
            return dict(result)
        except Exception as e:
            # Logger 封装使用 extra=kwargs，避免传 exc_info 进入 extra 导致 KeyError
            logger.exception(f"工作流执行失败: {e}")
            state["final_response"] = f"工作流执行失败: {e}"
            return state

