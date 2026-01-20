#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Query Schema - 表查询数据验证模式
定义所有 API 请求和响应的数据结构
"""
from typing import Optional, List, Dict, Any

from ninja import ModelSchema, Schema, Field

from common.fu_model import exclude_fields
from common.fu_schema import FuFilters
from core.table_query.table_query_model import TableQueryConfig, TableQueryLog


# =============================================================================
# 过滤器 Schema
# =============================================================================

class TableQueryConfigFilters(FuFilters):
    """表查询配置过滤器"""
    table_name: Optional[str] = Field(None, q="table_name__contains", alias="table_name")
    display_name: Optional[str] = Field(None, q="display_name__contains", alias="display_name")
    is_active: Optional[bool] = Field(None, alias="is_active")


class TableQueryLogFilters(FuFilters):
    """表查询日志过滤器"""
    user_id: Optional[str] = Field(None, q="user_id", alias="user_id", description="用户ID（关联 User 模型/表 core_user.id）")
    table_name: Optional[str] = Field(None, q="table_name__contains", alias="table_name")
    operation: Optional[str] = Field(None, alias="operation")


# =============================================================================
# 配置管理 Schema
# =============================================================================

class FieldConfigSchema(Schema):
    """字段配置 Schema"""
    name: str = Field(..., description="字段名")
    display_name: str = Field(..., description="显示名称")
    type: str = Field("string", description="字段类型: string/integer/decimal/date/datetime/boolean")
    searchable: bool = Field(False, description="是否可搜索")
    sortable: bool = Field(False, description="是否可排序")
    visible: bool = Field(True, description="是否可见")
    width: Optional[int] = Field(None, description="列宽度")


class ConfigJsonSchema(Schema):
    """配置 JSON Schema"""
    fields: List[FieldConfigSchema] = Field(default=[], description="字段配置列表")
    default_page_size: int = Field(20, description="默认分页大小")
    max_page_size: int = Field(100, description="最大分页大小")
    default_order_by: str = Field("id DESC", description="默认排序")
    allowed_operations: List[str] = Field(default=["query", "export"], description="允许的操作")


class TableQueryConfigSchemaIn(Schema):
    """创建表查询配置输入"""
    table_name: str = Field(..., description="数据库表名")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="表描述")
    config_json: Dict[str, Any] = Field(default_factory=dict, description="配置内容")
    is_active: bool = Field(True, description="是否激活")
    sort: int = Field(0, description="排序")


class TableQueryConfigSchemaPatch(Schema):
    """更新表查询配置输入"""
    table_name: Optional[str] = Field(None, description="数据库表名")
    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="表描述")
    config_json: Optional[Dict[str, Any]] = Field(None, description="配置内容")
    is_active: Optional[bool] = Field(None, description="是否激活")
    sort: Optional[int] = Field(None, description="排序")


class TableQueryConfigSchemaOut(ModelSchema):
    """表查询配置输出"""
    
    class Config:
        model = TableQueryConfig
        model_fields = "__all__"


# =============================================================================
# 动态查询 Schema
# =============================================================================

class FilterCondition(Schema):
    """过滤条件"""
    field: str = Field(..., description="字段名")
    operator: str = Field("eq", description="操作符: eq/ne/gt/gte/lt/lte/like/in/between")
    value: Any = Field(..., description="值")


class TableQueryIn(Schema):
    """执行表查询输入"""
    config_id: Optional[str] = Field(
        None, 
        description="配置ID（精确匹配，优先级高于 config_name）"
    )
    config_name: Optional[str] = Field(
        None, 
        description="配置名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")
    fields: Optional[List[str]] = Field(None, description="要查询的字段列表")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段，如: name ASC, id DESC")


class TableQueryResult(Schema):
    """表查询结果"""
    items: List[Dict[str, Any]] = Field(default=[], description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")


# =============================================================================
# 数据导出 Schema
# =============================================================================

class ExportParams(Schema):
    """导出参数"""
    config_id: Optional[str] = Field(
        None, 
        description="配置ID（精确匹配，优先级高于 config_name）"
    )
    config_name: Optional[str] = Field(
        None, 
        description="配置名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
    format: str = Field("excel", description="导出格式: excel/csv")
    fields: Optional[List[str]] = Field(None, description="要导出的字段列表")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    max_rows: int = Field(10000, ge=1, le=100000, description="最大导出行数")


# =============================================================================
# 日志查询 Schema
# =============================================================================

class TableQueryLogSchemaOut(ModelSchema):
    """表查询日志输出"""
    
    class Config:
        model = TableQueryLog
        model_fields = "__all__"


# =============================================================================
# 联合查询 Schema
# =============================================================================

class ManualJoin(Schema):
    """手动字段匹配关联"""
    source_field: str = Field(..., description="源字段名（主表的字段）")
    target_table: str = Field(..., description="目标表名")
    target_field: str = Field(..., description="目标字段名")
    match_type: str = Field(
        "exact",
        description="匹配类型: exact(精确) | fuzzy(模糊)"
    )


class JoinQueryIn(Schema):
    """联合查询输入"""
    primary_table: str = Field(
        ..., 
        description="主表名或配置名（支持模糊匹配）"
    )
    max_depth: int = Field(
        2, 
        ge=1, 
        le=5, 
        description="最大关联深度（1-5级，默认2级）"
    )
    include_tables: Optional[List[str]] = Field(
        None, 
        description="指定要包含的关联表（优先级高于 exclude_tables）"
    )
    exclude_tables: Optional[List[str]] = Field(
        None, 
        description="指定要排除的关联表"
    )
    manual_joins: Optional[List[ManualJoin]] = Field(
        None,
        description="手动字段匹配关联列表"
    )
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量（最大100）")
    filters: Optional[List[FilterCondition]] = Field(
        None, 
        description="过滤条件（字段名需使用 表名_字段名 格式）"
    )
    order_by: Optional[str] = Field(
        None, 
        description="排序字段（字段名需使用 表名_字段名 格式，如: 主表_id DESC）"
    )


class JoinTableInfo(Schema):
    """关联表信息"""
    table_name: str = Field(..., description="表名")
    join_depth: int = Field(..., description="关联深度")
    source_table: str = Field(..., description="来源表（通过哪个表关联）")
    source_columns: List[str] = Field(..., description="来源表的外键字段")
    target_columns: List[str] = Field(..., description="目标表的关联字段")
    join_type: str = Field("foreign_key", description="关联类型: foreign_key/manual")
    match_type: Optional[str] = Field(
        None,
        description="手动关联匹配类型: exact/fuzzy"
    )


class JoinInfo(Schema):
    """联合查询关联信息"""
    primary_table: str = Field(..., description="主表名")
    joined_tables: List[str] = Field(default=[], description="关联的表名列表")
    join_depth: int = Field(0, description="实际关联深度")
    total_tables: int = Field(1, description="总表数（包含主表）")
    has_cycle: bool = Field(False, description="是否检测到循环引用")
    join_details: List[JoinTableInfo] = Field(default=[], description="关联详情")


class FieldInfo(Schema):
    """字段元信息"""
    alias: str = Field(..., description="字段别名（表名_字段名）")
    original_table: str = Field(..., description="原始表名")
    original_field: str = Field(..., description="原始字段名")
    field_type: str = Field("string", description="字段类型")
    field_comment: str = Field("", description="字段注释（中文名称）")


class JoinQueryResult(Schema):
    """联合查询结果"""
    items: List[Dict[str, Any]] = Field(default=[], description="数据列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页数量")
    join_info: JoinInfo = Field(..., description="关联信息")
    field_info: List[FieldInfo] = Field(default=[], description="字段元信息列表")


class JoinPreviewOut(Schema):
    """关联关系预览输出"""
    primary_table: str = Field(..., description="主表名")
    join_tree: List[JoinTableInfo] = Field(default=[], description="关联关系树")
    total_related_tables: int = Field(0, description="总关联表数")
    max_depth: int = Field(0, description="最大关联深度")
    has_cycle: bool = Field(False, description="是否存在循环引用")
    all_fields: List[FieldInfo] = Field(default=[], description="所有字段列表（带前缀）")


class JoinExportParams(Schema):
    """联合查询导出参数"""
    primary_table: str = Field(
        ..., 
        description="主表名或配置名（支持模糊匹配）"
    )
    max_depth: int = Field(
        2, 
        ge=1, 
        le=5, 
        description="最大关联深度（1-5级，默认2级）"
    )
    include_tables: Optional[List[str]] = Field(
        None, 
        description="指定要包含的关联表"
    )
    exclude_tables: Optional[List[str]] = Field(
        None, 
        description="指定要排除的关联表"
    )
    format: str = Field("excel", description="导出格式: excel/csv")
    filters: Optional[List[FilterCondition]] = Field(
        None, 
        description="过滤条件"
    )
    max_rows: int = Field(10000, ge=1, le=100000, description="最大导出行数")
