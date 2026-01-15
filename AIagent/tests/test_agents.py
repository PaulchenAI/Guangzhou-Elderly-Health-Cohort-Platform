# -*- coding: utf-8 -*-
"""
智能体单元测试（最小可用版）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from langchain_core.documents import Document
from langchain_community.embeddings import FakeEmbeddings

from src.agents.orchestrator import OrchestratorAgent
from src.agents.rag_agent import RAGAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.planning_agent import PlanningAgent
from src.memory.manager import MemoryManager
from src.utils.config_models import MemoryConfig, VectorDBConfig
from src.rag.indexer import RAGIndexer
from src.rag.retriever import RAGRetriever
from src.openspec.manager import OpenSpecManager


class TestOrchestratorAgent:
    @pytest.mark.asyncio
    async def test_route_decision(self):
        a = OrchestratorAgent()
        s = {"current_task": "请帮我创建提案并规划执行"}
        r = await a.run(s)
        assert r.updates["route"] == "need_openspec"


class TestRAGAgent:
    @pytest.mark.asyncio
    async def test_rag_agent_adds_context(self, temp_dir):
        embeddings = FakeEmbeddings(size=8)
        indexer = RAGIndexer(str(temp_dir / "chroma"), "t", embeddings)
        indexer.add_documents([Document(page_content="hello python", metadata={"source": "x"})])
        retriever = RAGRetriever(indexer.vectorstore)

        agent = RAGAgent(retriever)
        out = await agent.run({"current_task": "python"})
        assert "context" in out.updates
        assert len(out.updates["context"]) > 0


class TestMemoryAgent:
    @pytest.mark.asyncio
    async def test_memory_agent_adds_memory(self, temp_dir):
        mm = MemoryManager(
            memory_config=MemoryConfig(backend="memory", ttl=10),
            vector_db_config=VectorDBConfig(type="chromadb", persist_dir=str(temp_dir / "chroma")),
            conversation_max_size=10,
        )
        await mm.save("用户喜欢Python", importance=0.8)

        agent = MemoryAgent(mm)
        out = await agent.run({"current_task": "Python"})
        assert "memory" in out.updates
        assert "hits" in out.updates["memory"]


class TestPlanningAgent:
    @pytest.mark.asyncio
    async def test_planning_agent_creates_plan(self, temp_dir):
        mgr = OpenSpecManager(openspec_root=str(temp_dir / "openspec"))
        agent = PlanningAgent(mgr)
        out = await agent.run({"current_task": "用户认证、权限管理"})
        assert "openspec_proposals" in out.updates
        assert "openspec_plan" in out.updates

