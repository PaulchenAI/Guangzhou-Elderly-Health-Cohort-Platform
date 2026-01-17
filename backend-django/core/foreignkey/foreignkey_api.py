# -*- coding: utf-8 -*-
"""
外键关系元数据 API - 提供外键关系的查询接口

支持 AI 通过表名查询表之间的关联关系。

端点列表:
- GET /foreignkey/metadata - 获取外键关系列表（分页）
- GET /foreignkey/metadata/all - 获取所有外键关系
- GET /foreignkey/metadata/{id} - 获取单个外键详情
- GET /foreignkey/by-source/{table_name} - 按源表查询（AI 友好）
- GET /foreignkey/by-target/{table_name} - 按目标表查询（AI 友好）
- GET /foreignkey/relations/{table_name} - 获取表所有关联
- GET /foreignkey/stats - 获取统计信息
"""
import logging
from typing import List, Optional

from django.shortcuts import get_object_or_404
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate

from common.fu_crud import retrieve
from common.fu_pagination import MyPagination
from core.foreignkey.foreignkey_model import ForeignKeyMetadata
from core.foreignkey.foreignkey_schema import (
    ForeignKeyMetadataSchemaOut,
    ForeignKeyMetadataFilters,
    ForeignKeyByTableOut,
    ForeignKeyRelationItem,
    ForeignKeyRelationsOut,
    ForeignKeyRelationSummary,
    ForeignKeyStatsOut,
)

logger = logging.getLogger(__name__)
router = Router()


def _build_columns_display(source_columns: List[str], target_columns: List[str]) -> str:
    """
    构建字段映射显示字符串
    
    Args:
        source_columns: 源字段列表
        target_columns: 目标字段列表
    
    Returns:
        字段映射显示，如 "DEPT_ID -> ID" 或 "PATIENT_ID, VISIT_ID -> ID, VISIT_ID"
    """
    source = ', '.join(source_columns) if source_columns else ''
    target = ', '.join(target_columns) if target_columns else ''
    return f"{source} -> {target}"


def _match_table_name(queryset, field_name: str, table_name: str):
    """
    智能匹配表名（支持精确匹配、后缀匹配、模糊匹配）
    
    查询逻辑:
    1. 优先精确匹配
    2. 尝试后缀匹配（支持不带前缀的表名）
    3. 模糊匹配（包含关键字）
    
    Args:
        queryset: 查询集
        field_name: 字段名（source_table 或 target_table）
        table_name: 要匹配的表名
    
    Returns:
        匹配的查询结果列表
    """
    # 1. 精确匹配
    filter_kwargs = {field_name: table_name}
    results = queryset.filter(**filter_kwargs)
    if results.exists():
        return list(results)
    
    # 2. 后缀匹配（支持不带前缀的表名，如 BS_STAFF 匹配 gzlry_BS_STAFF）
    filter_kwargs = {f"{field_name}__iendswith": table_name}
    results = queryset.filter(**filter_kwargs)
    if results.exists():
        return list(results)
    
    # 3. 模糊匹配
    filter_kwargs = {f"{field_name}__icontains": table_name}
    results = queryset.filter(**filter_kwargs)
    return list(results)


def _to_relation_item(fk: ForeignKeyMetadata) -> ForeignKeyRelationItem:
    """将 ForeignKeyMetadata 转换为 ForeignKeyRelationItem"""
    return ForeignKeyRelationItem(
        id=fk.id,
        source_table=fk.source_table,
        source_columns=fk.source_columns or [],
        target_table=fk.target_table,
        target_columns=fk.target_columns or [],
        constraint_name=fk.constraint_name,
        on_delete=fk.on_delete,
        columns_display=_build_columns_display(fk.source_columns or [], fk.target_columns or [])
    )


# =============================================================================
# 基础查询 API
# =============================================================================

@router.get(
    "/foreignkey/metadata",
    response=List[ForeignKeyMetadataSchemaOut],
    tags=["外键关系元数据"],
    summary="获取外键关系列表（分页）"
)
@paginate(MyPagination)
def list_foreignkey_metadata(request, filters: ForeignKeyMetadataFilters = Query(...)):
    """
    获取外键关系元数据列表（分页）
    
    查询参数:
    - page: 页码（默认 1）
    - pageSize: 每页数量（默认 10）
    - source_table: 源表名（模糊查询）
    - target_table: 目标表名（模糊查询）
    - constraint_name: 约束名（模糊查询）
    
    返回:
    - items: 外键关系列表
    - total: 总数
    
    示例:
    - /foreignkey/metadata?source_table=BS_STAFF
    - /foreignkey/metadata?target_table=BS_DEPARTMENT
    """
    queryset = retrieve(request, ForeignKeyMetadata, filters)
    return queryset


@router.get(
    "/foreignkey/metadata/all",
    response=List[ForeignKeyMetadataSchemaOut],
    tags=["外键关系元数据"],
    summary="获取所有外键关系"
)
def list_all_foreignkey_metadata(
    request,
    source_table: Optional[str] = None,
    target_table: Optional[str] = None
):
    """
    获取所有外键关系（不分页）
    
    查询参数:
    - source_table: 源表名过滤（模糊匹配）
    - target_table: 目标表名过滤（模糊匹配）
    
    注意: 数据量较大时建议使用分页接口
    """
    queryset = ForeignKeyMetadata.objects.all()
    
    if source_table:
        queryset = queryset.filter(source_table__icontains=source_table)
    if target_table:
        queryset = queryset.filter(target_table__icontains=target_table)
    
    return list(queryset)


@router.get(
    "/foreignkey/metadata/{fk_id}",
    response=ForeignKeyMetadataSchemaOut,
    tags=["外键关系元数据"],
    summary="获取外键关系详情"
)
def get_foreignkey_metadata(request, fk_id: int):
    """
    获取单个外键关系详情
    
    路径参数:
    - fk_id: 外键关系ID
    
    返回:
    - 外键关系的完整信息
    """
    return get_object_or_404(ForeignKeyMetadata, id=fk_id)


# =============================================================================
# AI 友好的表名查询 API
# =============================================================================

@router.get(
    "/foreignkey/by-source/{table_name}",
    response=ForeignKeyByTableOut,
    tags=["外键关系元数据"],
    summary="按源表名查询外键（出向引用）"
)
def get_foreignkey_by_source(request, table_name: str):
    """
    按源表名查询外键关系（出向引用）
    
    查询该表作为源表的所有外键关系，即该表引用了哪些其他表。
    
    路径参数:
    - table_name: 源表名（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回表名完全匹配的结果
    2. 如果没有完全匹配，尝试后缀匹配（支持不带前缀的表名）
    3. 如果仍无结果，返回包含关键字的结果
    
    AI 调用建议: 直接传入用户提到的表名，支持不带前缀。
    
    示例:
    - /foreignkey/by-source/gzlry_BS_STAFF → 精确匹配
    - /foreignkey/by-source/BS_STAFF → 后缀匹配到 gzlry_BS_STAFF
    - /foreignkey/by-source/STAFF → 模糊匹配到包含 STAFF 的表
    """
    results = _match_table_name(ForeignKeyMetadata.objects.all(), 'source_table', table_name)
    
    # 确定实际匹配的表名
    matched_table = results[0].source_table if results else table_name
    
    relations = [_to_relation_item(fk) for fk in results]
    
    return ForeignKeyByTableOut(
        table_name=matched_table,
        relations=relations,
        count=len(relations)
    )


@router.get(
    "/foreignkey/by-target/{table_name}",
    response=ForeignKeyByTableOut,
    tags=["外键关系元数据"],
    summary="按目标表名查询外键（入向引用）"
)
def get_foreignkey_by_target(request, table_name: str):
    """
    按目标表名查询外键关系（入向引用）
    
    查询该表作为目标表的所有外键关系，即哪些表引用了该表。
    
    路径参数:
    - table_name: 目标表名（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回表名完全匹配的结果
    2. 如果没有完全匹配，尝试后缀匹配（支持不带前缀的表名）
    3. 如果仍无结果，返回包含关键字的结果
    
    AI 调用建议: 直接传入用户提到的表名，支持不带前缀。
    
    示例:
    - /foreignkey/by-target/gzlry_BS_DEPARTMENT → 精确匹配
    - /foreignkey/by-target/BS_DEPARTMENT → 后缀匹配
    - /foreignkey/by-target/DEPARTMENT → 模糊匹配
    """
    results = _match_table_name(ForeignKeyMetadata.objects.all(), 'target_table', table_name)
    
    # 确定实际匹配的表名
    matched_table = results[0].target_table if results else table_name
    
    relations = [_to_relation_item(fk) for fk in results]
    
    return ForeignKeyByTableOut(
        table_name=matched_table,
        relations=relations,
        count=len(relations)
    )


@router.get(
    "/foreignkey/relations/{table_name}",
    response=ForeignKeyRelationsOut,
    tags=["外键关系元数据"],
    summary="获取表的所有关联关系"
)
def get_table_relations(request, table_name: str):
    """
    获取表的所有外键关联关系（出向 + 入向）
    
    一次请求获取表的所有关联：
    - 出向关系：该表引用的其他表（该表是源表）
    - 入向关系：引用该表的其他表（该表是目标表）
    
    路径参数:
    - table_name: 表名（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回表名完全匹配的结果
    2. 如果没有完全匹配，尝试后缀匹配（支持不带前缀的表名）
    3. 如果仍无结果，返回包含关键字的结果
    
    AI 调用建议: 直接传入用户提到的表名，可一次获取表的全部关联关系。
    
    示例:
    - /foreignkey/relations/BS_DEPARTMENT
    
    返回示例:
    {
        "table_name": "gzlry_BS_DEPARTMENT",
        "outgoing": [{"table": "gzlry_BS_ORGANIZATION", "columns": "ORG_ID -> ID"}],
        "incoming": [{"table": "gzlry_BS_STAFF", "columns": "DEPT_ID -> ID"}],
        "outgoing_count": 1,
        "incoming_count": 5
    }
    """
    # 获取出向关系（该表作为源表）
    outgoing_results = _match_table_name(ForeignKeyMetadata.objects.all(), 'source_table', table_name)
    
    # 获取入向关系（该表作为目标表）
    incoming_results = _match_table_name(ForeignKeyMetadata.objects.all(), 'target_table', table_name)
    
    # 确定实际匹配的表名
    matched_table = table_name
    if outgoing_results:
        matched_table = outgoing_results[0].source_table
    elif incoming_results:
        matched_table = incoming_results[0].target_table
    
    # 构建出向关系摘要
    outgoing = [
        ForeignKeyRelationSummary(
            table=fk.target_table,
            columns=_build_columns_display(fk.source_columns or [], fk.target_columns or []),
            constraint_name=fk.constraint_name
        )
        for fk in outgoing_results
    ]
    
    # 构建入向关系摘要
    incoming = [
        ForeignKeyRelationSummary(
            table=fk.source_table,
            columns=_build_columns_display(fk.source_columns or [], fk.target_columns or []),
            constraint_name=fk.constraint_name
        )
        for fk in incoming_results
    ]
    
    return ForeignKeyRelationsOut(
        table_name=matched_table,
        outgoing=outgoing,
        incoming=incoming,
        outgoing_count=len(outgoing),
        incoming_count=len(incoming)
    )


# =============================================================================
# 统计信息 API
# =============================================================================

@router.get(
    "/foreignkey/stats",
    response=ForeignKeyStatsOut,
    tags=["外键关系元数据"],
    summary="获取外键统计信息"
)
def get_foreignkey_stats(request):
    """
    获取外键关系的统计信息
    
    返回:
    - total_foreignkeys: 总外键关系数
    - unique_source_tables: 有外键的表数（源表去重）
    - unique_target_tables: 被引用的表数（目标表去重）
    
    用途: 了解数据库的外键关系整体情况
    """
    total = ForeignKeyMetadata.objects.count()
    unique_source = ForeignKeyMetadata.objects.values('source_table').distinct().count()
    unique_target = ForeignKeyMetadata.objects.values('target_table').distinct().count()
    
    return ForeignKeyStatsOut(
        total_foreignkeys=total,
        unique_source_tables=unique_source,
        unique_target_tables=unique_target
    )
