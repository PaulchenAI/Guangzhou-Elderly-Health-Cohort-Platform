# -*- coding: utf-8 -*-
"""
最小集成测试：LangGraph 工作流跑通
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
from src.core.graph import build_graph
from src.core.executor import WorkflowExecutor
from src.memory.manager import MemoryManager
from src.utils.config_models import MemoryConfig, VectorDBConfig
from src.rag.indexer import RAGIndexer
from src.rag.retriever import RAGRetriever
from src.openspec.manager import OpenSpecManager


@pytest.mark.asyncio
async def test_workflow_end_to_end(temp_dir):
    # 构造 RAG
    embeddings = FakeEmbeddings(size=8)
    indexer = RAGIndexer(str(temp_dir / "chroma"), "it", embeddings)
    indexer.add_documents([Document(page_content="项目使用 Django", metadata={"source": "doc1"})])
    retriever = RAGRetriever(indexer.vectorstore)

    # 构造 Memory
    mm = MemoryManager(
        memory_config=MemoryConfig(backend="memory", ttl=10),
        vector_db_config=VectorDBConfig(type="chromadb", persist_dir=str(temp_dir / "chroma2")),
        conversation_max_size=10,
    )
    await mm.save("用户偏好：Python", importance=0.8)

    # 构造 OpenSpec
    osm = OpenSpecManager(openspec_root=str(temp_dir / "openspec"))

    # Agents
    orchestrator = OrchestratorAgent()
    rag = RAGAgent(retriever)
    memory = MemoryAgent(mm)
    planning = PlanningAgent(osm)

    graph = build_graph(orchestrator=orchestrator, rag=rag, memory=memory, planning=planning)
    executor = WorkflowExecutor(graph)

    # 触发 RAG 路由
    out1 = await executor.run("请检索项目文档")
    assert "final_response" in out1

    # 触发 OpenSpec 路由
    out2 = await executor.run("请创建提案并规划任务")
    assert "openspec_plan" in out2

