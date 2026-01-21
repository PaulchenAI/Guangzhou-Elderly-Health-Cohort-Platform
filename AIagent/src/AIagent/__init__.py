# -*- coding: utf-8 -*-
"""
兼容包：AIagent

背景：
- 本项目实际代码包根为 `src/`（见 setup.py 的 package_dir={"": "src"}）
- 但部分测试/示例代码使用 `AIagent.src.*` 形式导入

因此这里提供一个轻量别名：
- `import AIagent.src.xxx` 等价于 `import src.xxx`

说明：这是兼容层，不改变真实代码组织结构。
"""

from __future__ import annotations

import importlib
import sys


def _install_src_alias() -> None:
    # 将 AIagent.src 指向实际的 src 包
    src_pkg = importlib.import_module("src")
    sys.modules.setdefault(__name__ + ".src", src_pkg)


_install_src_alias()

