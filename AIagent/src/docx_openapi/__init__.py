# -*- coding: utf-8 -*-
"""
DOCX API 文档解析与 OpenAPI 导出模块

目标：
- 输入：Word `.docx` 接口规范文档
- 输出：OpenAPI 3.x JSON（覆盖接口信息 + 入参/出参 + 示例）

说明：
- 本模块优先采用“确定性解析”，不依赖外部服务。
- LLM 辅助解析作为可选能力（后续按需开启），默认不启用。
"""

from .models import (
    DocLocation,
    ParseIssue,
    DocumentSpec,
    EndpointSpec,
    FieldSpec,
    ExampleSpec,
)
from .pipeline import export_openapi_from_docx

__all__ = [
    "DocLocation",
    "ParseIssue",
    "DocumentSpec",
    "EndpointSpec",
    "FieldSpec",
    "ExampleSpec",
    "export_openapi_from_docx",
]

