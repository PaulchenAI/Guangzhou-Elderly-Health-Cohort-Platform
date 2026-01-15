#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code CLI Stub（仅用于本地/CI 验证与测试）

注意：
- 这是一个最小兼容实现，用于验证 ClaudeCodeExecutor/ClaudeCodeClient 的封装流程。
- 不代表真实 Claude Code CLI 的能力与行为。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


def _read_stdin() -> str:
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def _json(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))


def _extract_path_after(prefix: str, text: str) -> str:
    # 形如：读取文件: /path/to/file
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_between(text: str, start_mark: str, end_mark: str) -> str:
    if start_mark not in text:
        return ""
    s = text.split(start_mark, 1)[1]
    if end_mark in s:
        s = s.split(end_mark, 1)[0]
    return s.strip("\n")


def _list_dir(dir_path: Path) -> List[Dict[str, Any]]:
    items = []
    for p in sorted(dir_path.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_dir():
            items.append({"path": str(p), "name": p.name, "type": "dir"})
        else:
            items.append({"path": str(p), "name": p.name, "type": "file", "size": p.stat().st_size})
    return items


def _glob_files(dir_path: Path, pattern: str) -> List[str]:
    # pattern 可能包含 **，用 rglob 兼容
    pat = pattern.strip() or "*"
    if "**" in pat:
        results = [str(p) for p in dir_path.rglob(pat.replace("**/", "")) if p.is_file()]
    else:
        results = [str(p) for p in dir_path.rglob(pat) if p.is_file()]
    return results


def _grep(dir_path: Path, pattern: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    try:
        rx = re.compile(pattern)
    except Exception:
        rx = re.compile(re.escape(pattern))

    for p in dir_path.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        # 只扫文本（粗略）
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            m = rx.search(line)
            if not m:
                continue
            results.append({"file": str(p), "line": i, "content": line, "match": m.group(0)})
            if len(results) >= 50:
                return results
    return results


def main() -> int:
    prompt = _read_stdin()

    # 文件读取
    if "读取文件:" in prompt:
        fp = Path(_extract_path_after("读取文件", prompt))
        try:
            _json({"content": fp.read_text(encoding="utf-8", errors="ignore")})
        except Exception as e:
            _json({"error": str(e)})
            return 1
        return 0

    # 文件写入
    if "写入文件:" in prompt:
        fp = Path(_extract_path_after("写入文件", prompt))
        content = _extract_between(prompt, "内容：\n", "\n\n请创建或覆盖该文件。")
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
            _json({"ok": True})
        except Exception as e:
            _json({"error": str(e)})
            return 1
        return 0

    # 文件编辑（字符串替换）
    if "编辑文件:" in prompt:
        fp = Path(_extract_path_after("编辑文件", prompt))
        old_str = _extract_between(prompt, "将以下内容：\n", "\n\n替换为：\n")
        new_str = _extract_between(prompt, "替换为：\n", "\n\n请执行替换操作。")
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
            fp.write_text(txt.replace(old_str, new_str), encoding="utf-8")
            _json({"ok": True})
        except Exception as e:
            _json({"error": str(e)})
            return 1
        return 0

    # 搜索文件（glob）
    if "搜索文件模式:" in prompt:
        # 形如：在目录 X 中搜索文件模式: PAT
        m = re.search(r"在目录\s+(.+?)\s+中搜索文件模式:\s*(.+)\s*$", prompt, re.M)
        if not m:
            _json({"files": []})
            return 0
        dir_path = Path(m.group(1).strip())
        pattern = m.group(2).strip()
        _json({"files": _glob_files(dir_path, pattern)})
        return 0

    # grep
    if "搜索内容模式:" in prompt:
        m = re.search(r"在目录\s+(.+?)\s+中搜索内容模式:\s*(.+)\s*$", prompt, re.M)
        if not m:
            _json({"results": []})
            return 0
        dir_path = Path(m.group(1).strip())
        pattern = m.group(2).strip()
        _json({"results": _grep(dir_path, pattern)})
        return 0

    # 列目录
    if "列出目录内容:" in prompt:
        dp = Path(_extract_path_after("列出目录内容", prompt))
        _json({"items": _list_dir(dp)})
        return 0

    # analyze_code
    if "分析代码文件:" in prompt:
        fp = Path(_extract_path_after("分析代码文件", prompt))
        summary = f"已分析：{fp.name}"
        _json({"summary": summary, "findings": [], "suggestions": ["保持代码可读性"], "complexity_score": 1.0})
        return 0

    # generate_code
    if "根据以下需求生成代码" in prompt:
        _json({"code": "def hello():\n    return 'hello'\n"})
        return 0

    # 默认兜底
    _json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

