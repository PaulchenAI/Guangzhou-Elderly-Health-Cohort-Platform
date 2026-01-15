# -*- coding: utf-8 -*-
"""
LangGraph 状态模型（最小可用版）

包含 OpenSpec 相关字段：
- openspec_proposals
- openspec_plan
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    # 消息历史
    messages: List[BaseMessage]
    # 当前任务
    current_task: str
    # RAG 上下文（可序列化）
    context: Any
    # 记忆上下文（可序列化）
    memory: Any
    # 规划结果
    plan: Any
    # OpenSpec 相关
    openspec_proposals: Any
    openspec_plan: Any
    # Claude Code 执行结果
    claude_code_result: Any
    # 最终输出
    final_response: str
    # 编排路由
    route: str
    route_reason: str
    # 用于终止循环（claude_code 节点执行后置 True）
    _executed: bool


def validate_state(state: Dict[str, Any]) -> None:
    """
    最小校验：确保基本字段类型可用。
    """

    if "messages" in state and not isinstance(state["messages"], list):
        raise ValueError("state.messages 必须是 list")
    if "current_task" in state and state["current_task"] is not None and not isinstance(state["current_task"], str):
        raise ValueError("state.current_task 必须是 str")

