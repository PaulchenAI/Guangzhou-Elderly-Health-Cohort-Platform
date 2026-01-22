#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Doc API Schema - 文档 API Pydantic Schema

用于 API 接口的数据校验和序列化
"""
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import Field


# =============================================================================
# 接口列表输出
# =============================================================================

class DocEndpointSchemaOut(Schema):
    """文档接口基本信息输出"""
    operation_id: str = Field(..., description="接口操作 ID")
    name: str = Field(..., description="接口名称")
    method: str = Field(..., description="HTTP 方法（GET/POST/PUT/DELETE 等）")
    path: str = Field(..., description="接口路径")
    summary: Optional[str] = Field(None, description="接口摘要")


class DocEndpointListOut(Schema):
    """文档接口列表输出"""
    total: int = Field(..., description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    items: List[DocEndpointSchemaOut] = Field(default=[], description="接口列表")


# =============================================================================
# 接口详情输出
# =============================================================================

class DocEndpointDetailSchemaOut(Schema):
    """文档接口详情输出"""
    operation_id: str = Field(..., description="接口操作 ID")
    name: str = Field(..., description="接口名称")
    method: str = Field(..., description="HTTP 方法")
    path: str = Field(..., description="接口路径")
    summary: Optional[str] = Field(None, description="接口摘要")
    description: Optional[str] = Field(None, description="接口详细描述")
    parameters: List[Dict[str, Any]] = Field(default=[], description="请求参数列表")
    request_body: Optional[Dict[str, Any]] = Field(None, description="请求体定义")
    responses: Dict[str, Any] = Field(default={}, description="响应定义")
    request_example: Optional[Any] = Field(None, description="请求示例")
    response_example: Optional[Any] = Field(None, description="响应示例")
    # 来自 report.json 的额外信息
    request_fields: Optional[int] = Field(None, description="请求字段数量")
    response_fields: Optional[int] = Field(None, description="响应字段数量")
    location: Optional[Dict[str, Any]] = Field(None, description="文档定位信息")


# =============================================================================
# 搜索输入
# =============================================================================

class DocEndpointSearchIn(Schema):
    """文档接口搜索输入"""
    name: Optional[str] = Field(None, description="接口名称（模糊匹配）")
    path: Optional[str] = Field(None, description="接口路径（模糊匹配）")
    method: Optional[str] = Field(None, description="HTTP 方法（精确匹配，如 POST、GET）")
    operation_id: Optional[str] = Field(None, description="操作 ID（模糊匹配）")
    keyword: Optional[str] = Field(None, description="关键词（在名称、路径、摘要中搜索）")
    page: int = Field(1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(20, ge=1, le=100, description="每页数量（1-100）")


# =============================================================================
# 文档摘要输出
# =============================================================================

class DocSummarySchemaOut(Schema):
    """文档摘要信息输出"""
    title: str = Field(..., description="文档标题")
    version: str = Field(..., description="文档版本")
    endpoint_count: int = Field(..., description="接口总数")
    issue_count: int = Field(0, description="问题数量")
    openapi_error_count: int = Field(0, description="OpenAPI 错误数量")
    # 额外信息
    methods_summary: Optional[Dict[str, int]] = Field(None, description="各 HTTP 方法的接口数量统计")
