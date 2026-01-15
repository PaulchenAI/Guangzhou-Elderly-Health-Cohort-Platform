# -*- coding: utf-8 -*-
"""
编排智能体（最小可用版）

职责：
- 任务意图分析（启发式）
- 路由决策（need_context / need_memory / need_plan / need_openspec / execute）
- 汇总输出（final_response）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base_agent import AgentResult, BaseAgent


@dataclass(frozen=True)
class RouteDecision:
    route: str
    reason: str = ""


class OrchestratorAgent(BaseAgent):
    name = "orchestrator"

    def decide_route(self, task: str) -> RouteDecision:
        t = (task or "").lower()

        # OpenSpec / 规划类优先
        if "openspec" in t or "提案" in t or "proposal" in t or "规范" in t or "规划" in t:
            return RouteDecision(route="need_openspec", reason="检测到提案/规范/规划相关关键词")

        # RAG：检索/上下文/文档/数据库
        if "检索" in t or "rag" in t or "文档" in t or "数据库" in t or "schema" in t:
            return RouteDecision(route="need_context", reason="检测到检索/文档/数据库相关关键词")

        # 记忆：记住/回忆/历史
        if "记住" in t or "回忆" in t or "历史" in t or "memory" in t:
            return RouteDecision(route="need_memory", reason="检测到记忆/历史相关关键词")

        # 默认直接执行
        return RouteDecision(route="execute", reason="默认路径：直接执行")

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        current_task = state.get("current_task") or ""
        # 若已经执行过且已有最终响应，则终止工作流，避免无限循环
        if state.get("_executed") and state.get("final_response"):
            decision = RouteDecision(route="end", reason="已获得最终响应，结束工作流")
        else:
            decision = self.decide_route(current_task)

        # 汇总输出：如果已有 claude_code_result / final_response 则尽量输出
        final_response = state.get("final_response")
        if not final_response:
            # 优先使用 claude_code_result 的文本形态
            ccr = state.get("claude_code_result")
            if isinstance(ccr, str):
                final_response = ccr
            elif isinstance(ccr, dict) and "output" in ccr:
                final_response = str(ccr.get("output"))

        updates: Dict[str, Any] = {
            "route": decision.route,
            "route_reason": decision.reason,
        }
        if final_response:
            updates["final_response"] = final_response

        return AgentResult(updates=updates, output_text=final_response or "")

