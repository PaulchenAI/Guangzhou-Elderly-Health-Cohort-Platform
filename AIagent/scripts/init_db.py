# -*- coding: utf-8 -*-
"""
向量数据库初始化脚本

最小可用目标：
- 校验配置（ConfigManager.validate）
- 确保 Chroma 持久化目录存在
- 创建/连通一个 Chroma collection（不依赖外部 Embedding API）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb

# 允许直接运行脚本（python scripts/*.py）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config_manager import ConfigManager


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化向量数据库（ChromaDB）")
    parser.add_argument("--collection", default="aiagent", help="集合名称（默认：aiagent）")
    args = parser.parse_args()

    cm = ConfigManager()
    errors = [
        e for e in cm.validate()
        if not str(e).startswith("Claude Code CLI路径不存在")
    ]
    if errors:
        print("配置校验失败：")
        for e in errors:
            print(f"- {e}")
        return 1

    vcfg = cm.get_vector_db_config()
    persist_dir = Path(vcfg.persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_dir))
    client.get_or_create_collection(name=args.collection)

    print(f"ChromaDB 初始化完成：persist_dir={persist_dir} collection={args.collection}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

