# -*- coding: utf-8 -*-
"""
RAG 模块测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from langchain_core.documents import Document
from langchain_community.embeddings import FakeEmbeddings

from src.rag.loaders.doc_loader import DocLoader
from src.rag.loaders.db_loader import DBLoader, DBSchemaDoc
from src.rag.loaders.code_loader import CodeLoader
from src.rag.indexer import RAGIndexer
from src.rag.retriever import RAGRetriever
from src.rag.embeddings import create_embeddings
from src.utils.config_models import RAGConfig, LLMConfig


class TestDocLoader:
    def test_load_files_chunked(self, temp_dir):
        p = temp_dir / "a.md"
        p.write_text("hello world\n" * 300, encoding="utf-8")

        loader = DocLoader()
        docs = loader.load_files([str(p)], chunk=True)

        assert len(docs) > 1
        assert docs[0].metadata["type"] == "doc"
        assert docs[0].metadata["source"] == str(p)


class TestDBLoader:
    def test_load_schema_docs(self):
        loader = DBLoader()
        docs = loader.load(
            [
                DBSchemaDoc(
                    name="test_db",
                    schema={"tables": [{"name": "users", "columns": ["id", "name"]}]},
                    metadata={"env": "test"},
                )
            ]
        )

        assert len(docs) == 1
        assert docs[0].metadata["type"] == "db_schema"
        assert docs[0].metadata["source"] == "test_db"
        assert "users" in docs[0].page_content


class TestCodeLoader:
    @pytest.mark.asyncio
    async def test_load_files_with_mocked_claude_client(self, mocker):
        mock_client = mocker.Mock()
        mock_client.read_file = mocker.AsyncMock(return_value="print('hello')\n" * 200)

        loader = CodeLoader(mock_client)  # type: ignore[arg-type]
        docs = await loader.load_files(["/tmp/test.py"])

        assert len(docs) > 1
        assert docs[0].metadata["type"] == "code"
        assert docs[0].metadata["language"] == "py"


class TestEmbeddingsFactory:
    def test_create_embeddings_requires_api_key_for_openai(self):
        rag = RAGConfig(
            chunk_size=1000,
            chunk_overlap=200,
            top_k=5,
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            embedding_api_key=None,
        )
        with pytest.raises(ValueError):
            create_embeddings(rag_config=rag, llm_config=None)


class TestIndexerAndRetriever:
    @pytest.mark.integration
    def test_index_and_retrieve(self, temp_dir):
        embeddings = FakeEmbeddings(size=8)
        persist_dir = str(temp_dir / "chroma")

        indexer = RAGIndexer(
            persist_dir=persist_dir,
            collection_name="test_rag",
            embeddings=embeddings,
        )

        docs = [
            Document(page_content="Python is great for scripting", metadata={"source": "doc1", "type": "doc"}),
            Document(page_content="Java is popular in enterprise", metadata={"source": "doc2", "type": "doc"}),
        ]
        indexer.add_documents(docs)

        retriever = RAGRetriever(indexer.vectorstore)
        results = retriever.retrieve("Python", top_k=2)

        assert len(results) > 0
        assert any("Python" in d.page_content for d in results)

