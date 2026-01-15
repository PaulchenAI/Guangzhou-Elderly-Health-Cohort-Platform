# -*- coding: utf-8 -*-
"""
OpenSpec 验证脚本（最小可用版）

尝试调用 openspec-cn list/show/validate（如果本机安装了 openspec-cn）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接运行脚本（python scripts/*.py）
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.openspec.client import OpenSpecClient


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 OpenSpec CLI（openspec-cn）可用性")
    parser.add_argument("--change-id", default=None, help="可选：指定 change-id 进行 validate")
    args = parser.parse_args()

    # 该脚本不依赖 Claude Code/LLM，避免被无关校验阻塞
    # openspec-cn 需要在包含 openspec/ 的项目根目录运行
    project_root = Path(__file__).resolve().parent.parent.parent
    client = OpenSpecClient(working_dir=str(project_root))
    try:
        changes = asyncio_run(client.list_changes())
    except Exception as e:
        print(f"OpenSpec CLI 不可用或调用失败: {e}")
        return 1

    print(f"OpenSpec CLI 可用，活动变更数: {len(changes)}")

    if args.change_id:
        res = asyncio_run(client.validate_change(args.change_id, strict=True))
        if not res.success:
            print("validate 失败：")
            print(res.stderr or res.stdout)
            return 1
        print("validate 通过")

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

