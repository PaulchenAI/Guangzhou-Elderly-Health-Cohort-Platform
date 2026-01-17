# -*- coding: utf-8 -*-
"""
外键关系元数据 Schema 定义

定义 API 请求和响应的数据结构。
"""
from typing import Optional, List
from ninja import Schema, Field, FilterSchema


class ForeignKeyMetadataSchemaOut(Schema):
    """外键关系元数据输出 Schema"""
    id: int = Field(..., description="主键ID")
    source_table: str = Field(..., description="源表名（带前缀）")
    source_columns: List[str] = Field(..., description="源字段列表")
    target_table: str = Field(..., description="目标表名（带前缀）")
    target_columns: List[str] = Field(..., description="目标字段列表")
    constraint_name: Optional[str] = Field(None, description="约束名")
    on_delete: Optional[str] = Field(None, description="删除规则")
    source_file: Optional[str] = Field(None, description="来源 JSON 文件名")
    
    class Config:
        from_attributes = True


class ForeignKeyMetadataFilters(FilterSchema):
    """外键关系元数据过滤器"""
    source_table: Optional[str] = Field(None, q="source_table__icontains", description="源表名（模糊查询）")
    target_table: Optional[str] = Field(None, q="target_table__icontains", description="目标表名（模糊查询）")
    constraint_name: Optional[str] = Field(None, q="constraint_name__icontains", description="约束名（模糊查询）")


class ForeignKeyRelationItem(Schema):
    """单个外键关系项"""
    id: int = Field(..., description="外键ID")
    source_table: str = Field(..., description="源表名")
    source_columns: List[str] = Field(..., description="源字段列表")
    target_table: str = Field(..., description="目标表名")
    target_columns: List[str] = Field(..., description="目标字段列表")
    constraint_name: Optional[str] = Field(None, description="约束名")
    on_delete: Optional[str] = Field(None, description="删除规则")
    columns_display: str = Field(..., description="字段映射显示（如 DEPT_ID -> ID）")


class ForeignKeyByTableOut(Schema):
    """按表名查询外键响应"""
    table_name: str = Field(..., description="查询的表名")
    relations: List[ForeignKeyRelationItem] = Field(..., description="外键关系列表")
    count: int = Field(..., description="关系数量")


class ForeignKeyRelationSummary(Schema):
    """关系摘要（简化版）"""
    table: str = Field(..., description="关联的表名")
    columns: str = Field(..., description="字段映射（如 DEPT_ID -> ID）")
    constraint_name: Optional[str] = Field(None, description="约束名")


class ForeignKeyRelationsOut(Schema):
    """表关联关系输出 Schema"""
    table_name: str = Field(..., description="查询的表名")
    outgoing: List[ForeignKeyRelationSummary] = Field(..., description="出向关系（该表引用的其他表）")
    incoming: List[ForeignKeyRelationSummary] = Field(..., description="入向关系（引用该表的其他表）")
    outgoing_count: int = Field(..., description="出向关系数量")
    incoming_count: int = Field(..., description="入向关系数量")


class ForeignKeyStatsOut(Schema):
    """外键统计信息输出 Schema"""
    total_foreignkeys: int = Field(..., description="总外键关系数")
    unique_source_tables: int = Field(..., description="有外键的表数（源表去重）")
    unique_target_tables: int = Field(..., description="被引用的表数（目标表去重）")
