#!/usr/bin/env python
# -*- coding: utf-8 -*-
# time: 1/24/2024 10:20 AM
# file: fu_schema.py
# author: 臧成龙
# QQ: 939589097

from typing import Any, List, Optional
from ninja import Schema, FilterSchema, Field


# =============================================================================
# 动态查询相关常量和 Schema
# =============================================================================

# 允许的 SQL 操作符
ALLOWED_OPERATORS = {
    "eq": "等于",
    "ne": "不等于",
    "gt": "大于",
    "gte": "大于等于",
    "lt": "小于",
    "lte": "小于等于",
    "like": "模糊匹配",
    "in": "包含",
    "between": "范围",
}


class FilterCondition(Schema):
    """通用过滤条件"""
    field: str = Field(..., description="字段名")
    operator: str = Field("eq", description="操作符: eq/ne/gt/gte/lt/lte/like/in/between")
    value: Any = Field(..., description="过滤值")


class DynamicQueryIn(Schema):
    """通用动态查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段，如: -create_datetime")


class DynamicQueryResult(Schema):
    """通用动态查询结果"""
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")


class SearchableFieldInfo(Schema):
    """可搜索字段信息"""
    name: str = Field(..., description="字段名")
    display_name: str = Field(..., description="显示名称")
    type: str = Field("string", description="数据类型: string/integer/datetime/boolean")


class SearchableFieldsResult(Schema):
    """可搜索字段查询结果"""
    module: str = Field(..., description="模块名称")
    display_name: str = Field(..., description="模块显示名称")
    searchable_fields: List[SearchableFieldInfo] = Field(..., description="可搜索字段列表")


# =============================================================================
# 原有 Schema
# =============================================================================

class FuFilters(FilterSchema):
    creator_id: str = Field(None, alias="creator_id")
    curr_flag: bool = Field(None, alias="curr_flag")


class UserSchema(Schema):
    id: str = None
    name: str = None


def response_success(data='success'):
    return {"detail": data}
