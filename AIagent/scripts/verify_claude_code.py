# -*- coding: utf-8 -*-
"""
Claude Code CLI 验证脚本（最小可用版）
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
from src.utils.config_models import ClaudeCodeConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 Claude Code CLI 配置与可用性")
    parser.add_argument("--run", action="store_true", help="执行一组基础能力验证（需要 CLI 可用）")
    parser.add_argument("--use-stub", action="store_true", help="使用仓库内置 claude_stub.py 作为 CLI（用于本地/CI）")
    args = parser.parse_args()

    cm = ConfigManager()
    errors = cm.validate()
    if errors:
        print("配置校验失败：")
        for e in errors:
            print(f"- {e}")
        return 1

    cfg = cm.get_claude_code_config()
    if args.use_stub:
        stub = project_root / "scripts" / "claude_stub.py"
        cfg = ClaudeCodeConfig(
            path=str(stub),
            timeout=cfg.timeout,
            max_concurrent=cfg.max_concurrent,
            working_dir=cfg.working_dir,
        )

    p = Path(cfg.path)
    if not p.exists():
        print(f"Claude Code CLI 路径不存在: {cfg.path}")
        return 1

    print(f"CLI 路径存在: {p}")
    print(f"working_dir: {cfg.working_dir}")
    print(f"timeout: {cfg.timeout}s  max_concurrent: {cfg.max_concurrent}")

    if args.run:
        client = ClaudeCodeClient(cfg)
        try:
            # 1) list_dir
            items = asyncio_run(client.list_dir("."))
        except Exception as e:
            print(f"实际调用失败: {e}")
            return 1
        print(f"实际调用成功，list_dir 返回 {len(items)} 项")

        # 2) write/read/edit/grep/search_files
        try:
            test_file = Path(cfg.working_dir) / "aiagent_verify.txt"
            ok = asyncio_run(client.write_file(str(test_file), "hello"))
            if not ok:
                raise RuntimeError("write_file 返回 False")

            content = asyncio_run(client.read_file(str(test_file)))
            if "hello" not in content:
                raise RuntimeError("read_file 内容不符合预期")

            ok = asyncio_run(client.edit_file(str(test_file), "hello", "world"))
            if not ok:
                raise RuntimeError("edit_file 返回 False")

            files = asyncio_run(client.search_files("*.txt", path=str(Path(cfg.working_dir))))
            _ = files  # 只验证不报错

            results = asyncio_run(client.grep("world", path=str(Path(cfg.working_dir))))
            _ = results

            print("文件操作验证通过（write/read/edit/search/grep）")
        except Exception as e:
            print(f"文件操作验证失败: {e}")
            return 1

        # 3) Coding 能力（最小验证：analyze_code / generate_code）
        try:
            py_file = Path(cfg.working_dir) / "aiagent_verify.py"
            py_file.write_text("print('x')\n", encoding="utf-8")
            analysis = asyncio_run(client.analyze_code(str(py_file), "这段代码做什么？"))
            if not analysis.summary:
                raise RuntimeError("analyze_code summary 为空")

            code = asyncio_run(client.generate_code("生成一个 hello 函数"))
            if not code:
                raise RuntimeError("generate_code 返回为空")

            print("Coding 能力验证通过（analyze/generate）")
        except Exception as e:
            print(f"Coding 能力验证失败: {e}")
            return 1

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

