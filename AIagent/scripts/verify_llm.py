# -*- coding: utf-8 -*-
"""
LLM 验证脚本（最小可用版）

默认仅校验配置；加 --run 才会实际发起一次调用（可能产生费用）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

# 允许直接运行脚本（python scripts/*.py）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config_manager import ConfigManager
from src.llm.factory import LLMFactory


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 LLM 配置与可用性")
    parser.add_argument("--run", action="store_true", help="实际调用一次 LLM（可能产生费用）")
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

    llm_cfg = cm.get_llm_config()
    print(f"provider={llm_cfg.provider} model={llm_cfg.model} max_tokens={llm_cfg.max_tokens} temperature={llm_cfg.temperature}")

    if args.run:
        llm = LLMFactory.create_llm(llm_cfg)
        try:
            resp = asyncio_run(llm.invoke([HumanMessage(content="ping")]))
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return 1
        print("LLM 调用成功，响应：")
        print(resp)

    return 0


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.get_event_loop().run_until_complete(coro)
    return asyncio.run(coro)


if __name__ == "__main__":
    raise SystemExit(main())

