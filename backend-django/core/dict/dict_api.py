#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dictionary API - 字典数据接口

字典模块用于管理系统字典数据，支持字典的增删改查和批量操作。
集成缓存机制，优化频繁访问的字典数据性能。
"""
from typing import List
import logging

from ninja import Router, Query
from ninja.pagination import paginate

from common.fu_crud import create, retrieve, delete, update, dynamic_query, get_searchable_fields_response
from common.fu_pagination import MyPagination
from common.fu_schema import DynamicQueryResult, SearchableFieldsResult
from common.fu_cache import DictCacheManager, CacheStrategy, CacheManager, CacheKeyPrefix
from core.dict.dict_schema import DictSchemaOut, DictSchemaIn, DictFilters, DictQueryIn, DICT_SEARCHABLE_FIELDS
from core.dict.dict_model import Dict

logger = logging.getLogger(__name__)
router = Router()


@router.post("/dict", response=DictSchemaOut, tags=["字典管理"], summary="创建字典")
def create_dict(request, data: DictSchemaIn):
    """
    创建字典
    
    请求体:
    - name: 字典名称 (必填)
    - code: 字典编码 (必填，唯一)
    - status: 状态 (可选，默认为 True)
    - remark: 备注 (可选)
    """
    query_set = create(request, data, Dict)
    
    # 创建后立即缓存
    if query_set:
        DictCacheManager.set_dict(query_set, dict_id=str(query_set.id), dict_code=query_set.code)
        logger.info(f"字典已创建并缓存: {query_set.code}")
    
    return query_set


@router.delete("/dict/{dict_id}", response=DictSchemaOut, tags=["字典管理"], summary="删除字典")
def delete_dict(request, dict_id: str):
    """
    删除字典
    
    路径参数:
    - dict_id: 字典ID
    
    注意: 删除字典时会级联删除所有关联的字典项，并清除相关缓存
    """
    # 获取字典信息用于缓存清除
    try:
        dict_obj = Dict.objects.get(id=dict_id)
        dict_code = dict_obj.code
    except Dict.DoesNotExist:
        dict_code = None
    
    instance = delete(dict_id, Dict)
    
    # 删除后清除缓存
    if dict_code:
        DictCacheManager.invalidate_dict(dict_id=dict_id, dict_code=dict_code)
        logger.info(f"字典缓存已清除: {dict_code}")
    
    return instance


@router.put("/dict/{dict_id}", response=DictSchemaOut, tags=["字典管理"], summary="更新字典")
def update_dict(request, dict_id: str, data: DictSchemaIn):
    """
    更新字典
    
    路径参数:
    - dict_id: 字典ID
    
    请求体:
    - name: 字典名称 (可选)
    - code: 字典编码 (可选)
    - status: 状态 (可选)
    - remark: 备注 (可选)
    
    注意: 更新后会自动更新缓存
    """
    # 获取旧的字典编码用于缓存清除
    try:
        old_dict = Dict.objects.get(id=dict_id)
        old_code = old_dict.code
    except Dict.DoesNotExist:
        old_code = None
    
    instance = update(request, dict_id, data, Dict)
    
    # 更新后重新缓存
    if instance:
        # 清除旧缓存
        if old_code and old_code != instance.code:
            DictCacheManager.invalidate_dict(dict_id=dict_id, dict_code=old_code)
        
        # 设置新缓存
        DictCacheManager.set_dict(instance, dict_id=str(instance.id), dict_code=instance.code)
        logger.info(f"字典已更新并重新缓存: {instance.code}")
    
    return instance


@router.get("/dict", response=List[DictSchemaOut], tags=["字典管理"], summary="获取字典列表（分页）")
@paginate(MyPagination)
def list_dict(request, filters: DictFilters = Query(...)):
    """
    获取字典列表 (分页)
    
    查询参数:
    - page: 页码 (可选，默认为 1)
    - page_size: 每页数量 (可选，默认为 20)
    - name: 字典名称 (可选，模糊查询)
    - code: 字典编码 (可选，模糊查询)
    - status: 状态 (可选，精确查询)
    """
    query_set = retrieve(request, Dict, filters)
    return query_set


@router.get("/dict/get/all", response=List[DictSchemaOut], tags=["字典管理"], summary="获取所有字典")
def list_all_dict(request):
    """
    获取所有字典 (不分页，有缓存)
    
    返回所有字典，不进行分页处理，用于前端下拉框等场景。
    此接口结果会被缓存 1 小时，以提高性能。
    """
    # 尝试从缓存获取
    cache_key = f"{CacheKeyPrefix.DICT}:all:list"
    cached_result = CacheManager.get(cache_key)
    if cached_result is not None:
        logger.debug("从缓存返回所有字典")
        return cached_result
    
    # 从数据库查询
    query_set = list(retrieve(request, Dict))
    
    # 缓存结果
    CacheManager.set(cache_key, query_set, CacheStrategy.DICT_CACHE)
    logger.debug(f"字典列表已缓存: {len(query_set)} 项")
    
    return query_set


@router.get("/dict/by-name/{name}", response=DictSchemaOut, tags=["字典管理"], summary="按名称查询字典")
def get_dict_by_name(request, name: str):
    """
    按字典名称查询字典（支持模糊匹配）
    
    路径参数:
    - name: 字典名称（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回名称完全匹配的字典
    2. 如果没有完全匹配，返回名称包含关键字的第一个字典
    3. 如果都没有匹配，返回 404 错误
    
    AI 调用建议: 直接传入用户提到的字典名称，无需获取 ID。
    
    示例:
    - /dict/by-name/用户状态 → 精确匹配
    - /dict/by-name/状态 → 模糊匹配到"用户状态"
    """
    from ninja.errors import HttpError
    
    # 优先精确匹配
    dict_obj = Dict.objects.filter(name=name, is_deleted=False).first()
    if dict_obj:
        return dict_obj
    
    # 模糊匹配
    dict_obj = Dict.objects.filter(name__icontains=name, is_deleted=False).first()
    if dict_obj:
        return dict_obj
    
    raise HttpError(404, f"未找到名称匹配 '{name}' 的字典")


@router.get("/dict/by-code/{code}", response=DictSchemaOut, tags=["字典管理"], summary="按编码查询字典")
def get_dict_by_code(request, code: str):
    """
    按字典编码查询字典（支持模糊匹配）
    
    路径参数:
    - code: 字典编码（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回编码完全匹配的字典
    2. 如果没有完全匹配，返回编码包含关键字的第一个字典
    3. 如果都没有匹配，返回 404 错误
    
    AI 调用建议: 直接传入用户提到的字典编码，无需获取 ID。
    """
    from ninja.errors import HttpError
    
    # 优先精确匹配
    dict_obj = Dict.objects.filter(code=code, is_deleted=False).first()
    if dict_obj:
        return dict_obj
    
    # 模糊匹配
    dict_obj = Dict.objects.filter(code__icontains=code, is_deleted=False).first()
    if dict_obj:
        return dict_obj
    
    raise HttpError(404, f"未找到编码匹配 '{code}' 的字典")


# =============================================================================
# 动态查询接口
# =============================================================================

@router.post("/dict/query", response=DynamicQueryResult, tags=["字典管理"], summary="动态查询字典")
def query_dict(request, data: DictQueryIn):
    """
    动态查询字典数据
    
    支持灵活的过滤条件和操作符选择。
    
    支持的操作符: eq, ne, gt, gte, lt, lte, like, in, between
    
    AI 调用建议: 先调用 /dict/searchable-fields 获取可搜索字段列表。
    """
    base_queryset = Dict.objects.filter(is_deleted=False)
    
    items, total = dynamic_query(
        model=Dict,
        filters=data.filters,
        searchable_fields=DICT_SEARCHABLE_FIELDS,
        page=data.page,
        page_size=data.page_size,
        order_by=data.order_by or "-sys_create_datetime",
        base_queryset=base_queryset,
        module="dict",
        user=request.auth
    )
    
    result_items = [DictSchemaOut.from_orm(item) for item in items]
    
    return DynamicQueryResult(
        items=result_items,
        total=total,
        page=data.page,
        page_size=data.page_size
    )


@router.get("/dict/searchable-fields", response=SearchableFieldsResult, tags=["字典管理"], summary="获取字典可搜索字段")
def get_dict_searchable_fields(request):
    """
    获取字典模块的可搜索字段列表
    
    注意: 返回的字段列表会根据当前用户权限进行过滤。
    
    AI 调用建议: 在生成带过滤条件的查询脚本前，先调用此接口获取可用的过滤字段。
    """
    return get_searchable_fields_response(
        module="dict",
        display_name="字典管理",
        searchable_fields=DICT_SEARCHABLE_FIELDS,
        user=request.auth
    )

