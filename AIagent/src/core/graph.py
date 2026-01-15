# -*- coding: utf-8 -*-
"""
LangGraph 工作流定义（最小可用版）

节点：
- orchestrator：决定 route
- rag：检索上下文
- memory：检索记忆
- planning：拆解 + 生成 openspec_plan
- claude_code：占位执行（可注入执行器）

说明：为了避免在测试中调用真实 Claude Code CLI，这里支持注入 claude_node 实现。
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from langgraph.graph import END, StateGraph

from .state import AgentState, validate_state
from .router import route_decision
from ..agents.base_agent import AgentResult
from ..agents.orchestrator import OrchestratorAgent
from ..agents.rag_agent import RAGAgent
from ..agents.memory_agent import MemoryAgent
from ..agents.planning_agent import PlanningAgent


AgentNode = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


def _agent_node(agent) -> AgentNode:
    async def node(state: Dict[str, Any]) -> Dict[str, Any]:
        validate_state(state)
        result: AgentResult = await agent.run(state)
        state.update(result.updates)
        return state

    return node


def build_graph(
    *,
    orchestrator: OrchestratorAgent,
    rag: Optional[RAGAgent] = None,
    memory: Optional[MemoryAgent] = None,
    planning: Optional[PlanningAgent] = None,
    claude_node: Optional[AgentNode] = None,
) -> Any:
    """
    构建并编译 LangGraph。
    """

    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", _agent_node(orchestrator))
    if rag:
        graph.add_node("rag", _agent_node(rag))
    if memory:
        graph.add_node("memory", _agent_node(memory))
    if planning:
        graph.add_node("planning", _agent_node(planning))

    async def default_claude_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # 最小占位：把当前任务原样回填
        state["claude_code_result"] = {"output": state.get("current_task", "")}
        state["final_response"] = state.get("final_response") or state.get("current_task", "")
        # 用于在 orchestrator 中判定终止，避免无限循环
        state["_executed"] = True
        return state

    graph.add_node("claude_code", claude_node or default_claude_node)

    # 入口：先到 orchestrator
    graph.set_entry_point("orchestrator")

    # orchestrator 条件路由
    graph.add_conditional_edges(
        "orchestrator",
        route_decision,
        {
            "rag": "rag" if rag else "claude_code",
            "memory": "memory" if memory else "claude_code",
            "planning": "planning" if planning else "claude_code",
            "claude_code": "claude_code",
            "end": END,
        },
    )

    # 其他节点完成后统一去 claude_code，再回 orchestrator 汇总
    if rag:
        graph.add_edge("rag", "claude_code")
    if memory:
        graph.add_edge("memory", "claude_code")
    if planning:
        graph.add_edge("planning", "claude_code")

    graph.add_edge("claude_code", "orchestrator")

    return graph.compile()

