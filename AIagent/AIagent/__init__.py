# -*- coding: utf-8 -*-
"""
兼容包入口：AIagent

目的：
- 允许在未安装（pip install -e .）的情况下，从项目根直接执行：
  `python -m AIagent.src.docx_openapi ...`

实现：
- 动态将 `<project>/src` 加入 sys.path
- 将 `AIagent.src` 映射到实际的 `src` 包

注意：
- 这只是“运行时兼容层”，真实代码仍在 `src/` 下。
"""

from __future__ import annotations

import importlib
import sys


def _install_src_alias() -> None:
    src_pkg = importlib.import_module("src")
    sys.modules.setdefault(__name__ + ".src", src_pkg)

_install_src_alias()

