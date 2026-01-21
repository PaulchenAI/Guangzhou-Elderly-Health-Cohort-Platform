# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI 命令行入口

使用方法：
    python -m src.docx_openapi export <docx> -o openapi.json --report report.json
"""

from .cli import main

if __name__ == "__main__":
    main()

