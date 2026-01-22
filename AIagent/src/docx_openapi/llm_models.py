# -*- coding: utf-8 -*-
"""
LLM 结构化输出模型（Pydantic）

用于：
- 强约束 LLM 输出格式
- 在输出不符合要求时生成可读错误信息，用于重试提示
"""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class LLMField(BaseModel):
    """字段定义（入参/出参）"""

    name: str = Field(..., description="字段/参数名")
    raw_type: str = Field(default="", description="文档中的类型原文（如 String/int/Date）")
    required: bool = Field(default=False, description="是否必填/非空")
    description: str = Field(default="", description="字段说明")


class LLMEndpoint(BaseModel):
    """单个接口的结构化结果"""

    operation_id: str = Field(default="", description="接口编号/operationId（如 PER_BASE_0001），尽量从文档提取；缺失可留空")
    name: str = Field(..., description="接口名称（中文）")
    method: str = Field(..., description="HTTP 方法（GET/POST/PUT/DELETE/PATCH）")
    path: str = Field(..., description="请求路径（以 / 开头；如为完整 URL 也可原样保留）")
    description: str = Field(default="", description="接口说明/功能说明（可选）")

    request_fields: List[LLMField] = Field(default_factory=list, description="输入参数/入参字段列表")
    response_fields: List[LLMField] = Field(default_factory=list, description="输出参数/出参字段列表")

    request_example: Optional[Any] = Field(default=None, description="请求示例（尽量解析为 JSON；无法解析可返回字符串）")
    response_example: Optional[Any] = Field(default=None, description="响应示例（尽量解析为 JSON；无法解析可返回字符串）")

