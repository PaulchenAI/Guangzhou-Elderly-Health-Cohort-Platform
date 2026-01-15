# -*- coding: utf-8 -*-
"""
RAG 智能体（最小可用版）

职责：
- 通过 RAGRetriever 检索相关文档
- 将结果写入 state["context"]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from .base_agent import AgentResult, BaseAgent
from ..rag.retriever import RAGRetriever


class RAGAgent(BaseAgent):
    name = "rag"

    def __init__(self, retriever: RAGRetriever, *, tools: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(tools=tools)
        self.retriever = retriever

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        task = state.get("current_task") or ""
        docs: List[Document] = self.retriever.retrieve(task, top_k=state.get("rag_top_k"))

        # 为了易序列化，context 保存为轻量结构
        context = [
            {"content": d.page_content, "metadata": dict(d.metadata)} for d in docs
        ]

        return AgentResult(
            updates={"context": context},
            output_text=f"RAG检索到 {len(context)} 条上下文",
        )

