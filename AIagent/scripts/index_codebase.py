# -*- coding: utf-8 -*-
"""
代码库/文档索引脚本（最小可用版）

说明：
- 代码加载通过 ClaudeCodeClient（需要 Claude Code CLI 可用）
- 文档加载直接读文件
- 向量化需要 Embeddings（通常需要 EMBEDDING_API_KEY）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接运行脚本（python scripts/*.py）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config_manager import ConfigManager
from src.claude_code.client import ClaudeCodeClient
from src.rag.loaders.code_loader import CodeLoader
from src.rag.loaders.doc_loader import DocLoader
from src.rag.embeddings import create_embeddings
from src.rag.indexer import RAGIndexer


def main() -> int:
    parser = argparse.ArgumentParser(description="索引代码库与文档（RAG）")
    parser.add_argument("--collection", default="aiagent", help="Chroma collection 名称")
    parser.add_argument("--code-glob", default="**/*.py", help="代码文件 glob（默认：**/*.py）")
    parser.add_argument("--code-root", default=".", help="代码搜索根目录（相对 working_dir）")
    parser.add_argument("--docs-dir", default="docs", help="文档目录（默认：docs）")
    parser.add_argument("--docs-ext", default="md,txt", help="文档扩展名（默认：md,txt）")
    args = parser.parse_args()

    cm = ConfigManager()
    # 索引脚本允许在 Claude Code CLI 不可用时仅索引 docs（跳过 code）
    errors = [
        e for e in cm.validate()
        if not str(e).startswith("Claude Code CLI路径不存在")
    ]
    if errors:
        print("配置校验失败：")
        for e in errors:
            print(f"- {e}")
        return 1

    rag_cfg = cm.get_rag_config()
    llm_cfg = cm.get_llm_config()
    vcfg = cm.get_vector_db_config()

    # Embeddings（需要 key）
    try:
        embeddings = create_embeddings(rag_config=rag_cfg, llm_config=llm_cfg)
    except Exception as e:
        print(f"创建 Embeddings 失败（请检查 EMBEDDING_PROVIDER/EMBEDDING_API_KEY）：{e}")
        return 1
    indexer = RAGIndexer(persist_dir=vcfg.persist_dir, collection_name=args.collection, embeddings=embeddings)

    # 文档索引（本地）
    doc_loader = DocLoader()
    exts = [e.strip() for e in args.docs_ext.split(",") if e.strip()]
    docs_dir = Path(args.docs_dir)
    doc_docs = doc_loader.load_dir(str(docs_dir), extensions=exts, chunk=True) if docs_dir.exists() else []
    if doc_docs:
        indexer.add_documents(doc_docs)
        print(f"已索引文档数量: {len(doc_docs)}")
    else:
        print("未发现可索引文档（跳过 docs）")

    # 代码索引（需要 Claude Code CLI）
    code_docs = []
    try:
        claude = ClaudeCodeClient(cm.get_claude_code_config())
        code_loader = CodeLoader(claude)
        # 注意：ClaudeCodeClient.search_files 接受 glob，不一定支持 **；这里保持最小实现
        code_docs = asyncio_run(
            code_loader.load_glob(
                args.code_glob,
                path=args.code_root,
                exclude_patterns=["node_modules", ".git"],
            )
        )
    except Exception as e:
        print(f"代码索引跳过/失败（可能 Claude Code CLI 不可用）：{e}")

    if code_docs:
        indexer.add_documents(code_docs)
        print(f"已索引代码块数量: {len(code_docs)}")

    print("索引完成")
    return 0


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 脚本场景一般不会走到这里；保底
        return asyncio.get_event_loop().run_until_complete(coro)
    return asyncio.run(coro)


if __name__ == "__main__":
    raise SystemExit(main())

