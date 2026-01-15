# -*- coding: utf-8 -*-
"""
智能体基类

目标：提供最小统一接口、依赖注入点和日志能力。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..logging.logger import get_logger


@dataclass
class AgentResult:
    """统一的智能体输出（最小实现）"""

    updates: Dict[str, Any] = field(default_factory=dict)
    output_text: str = ""


class BaseAgent:
    """智能体基类"""

    name: str = "base"

    def __init__(self, *, tools: Optional[Dict[str, Any]] = None) -> None:
        self.tools = tools or {}
        self.logger = get_logger(f"agent.{self.name}")

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """
        执行智能体逻辑。

        子类应覆盖此方法，并返回 AgentResult（包含对 state 的增量更新）。
        """

        raise NotImplementedError

