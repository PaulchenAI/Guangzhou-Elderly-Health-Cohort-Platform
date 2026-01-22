# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI 中间模型

保持解析与生成解耦：
- extractor 负责把 docx 变成“段落/表格块”的顺序流
- parser 把块流解析为 EndpointSpec/FieldSpec/ExampleSpec
- openapi_builder 负责把中间模型映射为 OpenAPI 3.x JSON
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DocLocation:
    """文档定位信息（尽量可读，便于排错）。"""

    block_index: int
    block_type: str  # "paragraph" | "table"
    detail: str = ""  # 例如：paragraph 前缀、table 行列等（弱约束）


class IssueLevel(str, Enum):
    """解析问题等级"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ParseIssue:
    """解析问题（用于 report 输出）"""

    level: IssueLevel
    message: str
    location: Optional[DocLocation] = None
    endpoint_hint: str = ""  # 尽量指向某个接口（例如 operationId / 接口名称）


@dataclass
class ExampleSpec:
    """示例（请求/响应）"""

    kind: str  # "request" | "response"
    content_type: str = "application/json"
    value: Any = None  # JSON 可解析时为 dict/list，否则为 str
    raw: str = ""  # 原始文本（用于排错/回放）


@dataclass
class FieldSpec:
    """字段/参数定义（入参或出参的单个字段）"""

    name: str
    raw_type: str = ""
    required: bool = False
    description: str = ""
    # OpenAPI 推导字段（生成阶段填充也可）
    inferred_schema: Dict[str, Any] = field(default_factory=dict)
    # 推导参数位置：path/query/body/response（用于 mapping）
    location: str = ""  # "path" | "query" | "body" | "response"


@dataclass
class EndpointSpec:
    """接口定义"""

    name: str
    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # 参数与结构
    request_fields: List[FieldSpec] = field(default_factory=list)
    response_fields: List[FieldSpec] = field(default_factory=list)

    # 示例
    request_examples: List[ExampleSpec] = field(default_factory=list)
    response_examples: List[ExampleSpec] = field(default_factory=list)

    # 解析定位线索
    source_location: Optional[DocLocation] = None


@dataclass
class DocumentSpec:
    """文档级元信息 + 接口集合"""

    title: str = "DOCX API"
    version: str = "0.0.0"
    servers: List[Dict[str, str]] = field(default_factory=list)
    endpoints: List[EndpointSpec] = field(default_factory=list)
    issues: List[ParseIssue] = field(default_factory=list)

