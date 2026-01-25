#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Doc API - 文档 API 接口

提供后台 API 接口，支持查询从 Word 文档解析生成的 OpenAPI JSON 文档信息，
包括接口列表、接口详情、接口搜索等功能。
"""
import logging
from typing import Optional

from ninja import Query, Router
from ninja.errors import HttpError

from core.doc_api.doc_api_schema import (
    DocEndpointDetailSchemaOut,
    DocEndpointListOut,
    DocEndpointSchemaOut,
    DocEndpointSearchIn,
    DocSummarySchemaOut,
)
from core.doc_api.doc_api_service import (
    get_doc_summary,
    get_endpoint_detail,
    get_endpoints_list,
    search_endpoints,
)

logger = logging.getLogger(__name__)
router = Router()


# =============================================================================
# 接口列表查询
# =============================================================================

@router.get(
    "/doc-api/endpoints",
    response=DocEndpointListOut,
    summary="获取文档接口列表（分页）"
)
def list_endpoints(
    request,
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（1-100）")
):
    """
    获取文档接口列表（分页）
    
    从 OpenAPI JSON 文档中读取接口信息并返回分页列表。
    只返回允许访问的接口，根据访问控制配置进行过滤。
    
    查询参数:
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20，最大 100）
    
    返回:
    - total: 允许访问的接口总数
    - page: 当前页码
    - page_size: 每页数量
    - items: 允许访问的接口列表
    
    AI 调用建议: 用于获取所有可用的文档接口，支持分页浏览。
    """
    items, total, error = get_endpoints_list(page=page, page_size=page_size)
    
    if error:
        logger.error(f"获取接口列表失败: {error}")
        raise HttpError(404, error)
    
    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': items,
    }


# =============================================================================
# 接口详情查询
# =============================================================================

@router.get(
    "/doc-api/endpoints/{operation_id}",
    response=DocEndpointDetailSchemaOut,
    summary="获取文档接口详情"
)
def get_endpoint(request, operation_id: str):
    """
    获取文档接口详情
    
    根据 operation_id 获取指定接口的完整信息，包括请求参数、响应定义和示例数据。
    只允许查询允许访问的接口，不允许访问的接口返回 403 错误。
    
    路径参数:
    - operation_id: 接口操作 ID（如 PER_BASE_0001）
    
    返回:
    - 接口基本信息（operation_id、name、method、path、summary、description）
    - 请求参数信息（parameters、request_body）
    - 响应信息（responses）
    - 示例数据（request_example、response_example）
    - 额外信息（request_fields、response_fields、location）
    
    错误响应:
    - 403: 接口不允许访问
    - 404: 接口不存在
    
    AI 调用建议: 用于获取特定接口的详细定义，包括请求和响应格式。
    """
    detail, error, is_forbidden = get_endpoint_detail(operation_id)
    
    if error:
        if is_forbidden:
            logger.warning(f"接口访问被拒绝: {error}")
            raise HttpError(403, error)
        else:
            logger.warning(f"获取接口详情失败: {error}")
            raise HttpError(404, error)
    
    return detail


# =============================================================================
# 接口搜索
# =============================================================================

@router.post(
    "/doc-api/endpoints/search",
    response=DocEndpointListOut,
    summary="搜索文档接口"
)
def search_endpoint(request, search_in: DocEndpointSearchIn):
    """
    搜索文档接口
    
    支持多条件组合搜索文档接口，所有条件为 AND 关系。
    只在允许访问的接口中进行搜索，根据访问控制配置进行过滤。
    
    请求体参数:
    - name: 接口名称（模糊匹配）
    - path: 接口路径（模糊匹配）
    - method: HTTP 方法（精确匹配，如 POST、GET）
    - operation_id: 操作 ID（模糊匹配）
    - keyword: 关键词（在名称、路径、摘要中搜索）
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20，最大 100）
    
    返回:
    - total: 匹配且允许访问的接口总数
    - page: 当前页码
    - page_size: 每页数量
    - items: 匹配且允许访问的接口列表
    
    AI 调用建议: 用于按条件搜索接口，支持按名称、路径、方法等条件过滤。
    """
    items, total, error = search_endpoints(
        name=search_in.name,
        path=search_in.path,
        method=search_in.method,
        operation_id=search_in.operation_id,
        keyword=search_in.keyword,
        page=search_in.page,
        page_size=search_in.page_size,
    )
    
    if error:
        logger.error(f"搜索接口失败: {error}")
        raise HttpError(404, error)
    
    return {
        'total': total,
        'page': search_in.page,
        'page_size': search_in.page_size,
        'items': items,
    }


# =============================================================================
# 文档摘要查询
# =============================================================================

@router.get(
    "/doc-api/summary",
    response=DocSummarySchemaOut,
    summary="获取文档摘要信息"
)
def get_summary(request):
    """
    获取文档摘要信息
    
    返回文档的整体统计信息，包括标题、版本、接口数量等。
    优先从 report.json 读取摘要，如果不存在则从 openapi.json 提取基本信息。
    
    返回:
    - title: 文档标题
    - version: 文档版本
    - endpoint_count: 接口总数
    - issue_count: 问题数量
    - openapi_error_count: OpenAPI 错误数量
    - methods_summary: 各 HTTP 方法的接口数量统计
    
    AI 调用建议: 用于获取文档整体概况，了解有多少接口可用。
    """
    summary, error = get_doc_summary()
    
    if error:
        logger.error(f"获取文档摘要失败: {error}")
        raise HttpError(404, error)
    
    return summary
