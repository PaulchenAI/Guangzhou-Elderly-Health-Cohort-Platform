#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dictionary Schema - 字典数据验证模式
"""
from typing import Optional, List, Any
from ninja import ModelSchema, Field, Schema

from common.fu_model import exclude_fields
from common.fu_schema import FuFilters, FilterCondition
from core.dict.dict_model import Dict


# =============================================================================
# 动态查询相关 Schema
# =============================================================================

DICT_SEARCHABLE_FIELDS = [
    {"name": "id", "display_name": "字典ID", "type": "string"},
    {"name": "name", "display_name": "字典名称", "type": "string"},
    {"name": "code", "display_name": "字典编码", "type": "string"},
    {"name": "status", "display_name": "状态", "type": "boolean"},
    {"name": "sys_create_datetime", "display_name": "创建时间", "type": "datetime"},
]


class DictQueryIn(Schema):
    """字典动态查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段")


# =============================================================================
# 原有 Schema
# =============================================================================

class DictFilters(FuFilters):
    name: Optional[str] = Field(None, q="name__contains", alias="name")
    code: Optional[str] = Field(None, q="code__contains", alias="code")
    status: Optional[bool] = Field(None, alias="status")


class DictSchemaIn(ModelSchema):

    class Config:
        model = Dict
        model_exclude = exclude_fields


class DictSchemaOut(ModelSchema):

    class Config:
        model = Dict
        model_fields = "__all__"

