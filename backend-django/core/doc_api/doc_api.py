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
    DocDefaultParamsOut,
    DocEndpointDetailSchemaOut,
    DocEndpointListOut,
    DocEndpointSchemaOut,
    DocEndpointSearchIn,
    DocEndpointWithAccessListOut,
    DocInvokeLogListOut,
    DocInvokeRequestIn,
    DocInvokeResponseOut,
    DocSummarySchemaOut,
)
from core.doc_api.doc_api_service import (
    get_default_params,
    get_doc_summary,
    get_endpoint_detail,
    get_endpoints_list,
    get_endpoints_list_with_access,
    get_invoke_logs,
    invoke_his_endpoint,
    is_endpoint_accessible,
    search_endpoints,
    search_endpoints_with_access,
)

logger = logging.getLogger(__name__)
router = Router()


# =============================================================================
# 接口列表查询
# =============================================================================

@router.get(
    "/doc-api/endpoints",
    auth=None,
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
# 接口搜索
# =============================================================================

@router.post(
    "/doc-api/endpoints/search",
    auth=None,
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
# 接口详情查询
# =============================================================================

@router.get(
    "/doc-api/endpoints/{operation_id}",
    auth=None,
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
# 文档摘要查询
# =============================================================================

@router.get(
    "/doc-api/summary",
    auth=None,
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


# =============================================================================
# 带访问状态的接口列表查询
# =============================================================================

@router.get(
    "/doc-api/endpoints-with-access",
    auth=None,
    response=DocEndpointWithAccessListOut,
    summary="获取带访问状态的接口列表（分页）"
)
def list_endpoints_with_access(
    request,
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（1-100）"),
    include_inaccessible: bool = Query(True, description="是否包含不可访问的接口")
):
    """
    获取带访问状态的文档接口列表（分页）
    
    返回所有接口及其访问状态，方便前端展示哪些接口可以调用。
    
    查询参数:
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20，最大 100）
    - include_inaccessible: 是否包含不可访问的接口（默认 true）
    
    返回:
    - total: 接口总数
    - page: 当前页码
    - page_size: 每页数量
    - items: 带访问状态的接口列表
    """
    items, total, error = get_endpoints_list_with_access(
        page=page,
        page_size=page_size,
        include_inaccessible=include_inaccessible
    )
    
    if error:
        logger.error(f"获取接口列表失败: {error}")
        raise HttpError(404, error)
    
    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': items,
    }


@router.post(
    "/doc-api/endpoints-with-access/search",
    auth=None,
    response=DocEndpointWithAccessListOut,
    summary="搜索带访问状态的接口"
)
def search_endpoints_with_access_api(request, search_in: DocEndpointSearchIn):
    """
    搜索带访问状态的文档接口
    
    支持多条件组合搜索，返回带访问状态的结果。
    """
    items, total, error = search_endpoints_with_access(
        name=search_in.name,
        path=search_in.path,
        method=search_in.method,
        operation_id=search_in.operation_id,
        keyword=search_in.keyword,
        page=search_in.page,
        page_size=search_in.page_size,
        include_inaccessible=True
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
# HIS 接口调用
# =============================================================================

@router.post(
    "/doc-api/invoke/{operation_id}",
    auth=None,
    response=DocInvokeResponseOut,
    summary="调用 HIS 接口"
)
def invoke_endpoint(request, operation_id: str, invoke_in: DocInvokeRequestIn):
    """
    代理调用 HIS 接口
    
    将请求转发到真实的 HIS API 并返回结果。
    只允许调用已授权的接口（在 access_control.json 中配置为 true）。
    
    路径参数:
    - operation_id: 接口操作 ID
    
    请求体:
    - params: 请求参数（字典格式）
    
    返回:
    - success: 是否调用成功
    - status_code: HTTP 状态码
    - duration_ms: 调用耗时（毫秒）
    - data: 响应数据
    - error: 错误信息（如有）
    - log_id: 调用日志 ID
    
    错误响应:
    - 403: 接口不允许调用
    - 500: 调用失败
    """
    # 获取用户 ID（如果有认证）
    user_id = ""
    if hasattr(request, 'auth') and request.auth:
        user_id = str(getattr(request.auth, 'id', ''))
    
    result, error = invoke_his_endpoint(
        operation_id=operation_id,
        params=invoke_in.params,
        user_id=user_id
    )
    
    if error:
        logger.error(f"调用接口失败: {error}")
        raise HttpError(403 if "不允许" in error else 500, error)
    
    return result


# =============================================================================
# 默认参数获取
# =============================================================================

@router.get(
    "/doc-api/endpoints/{operation_id}/default-params",
    auth=None,
    response=DocDefaultParamsOut,
    summary="获取接口默认测试参数"
)
def get_endpoint_default_params(request, operation_id: str):
    """
    获取接口的默认测试参数
    
    优先从接口定义的 request_example 获取，如果不存在则根据 request_body schema 生成模板。
    
    路径参数:
    - operation_id: 接口操作 ID
    
    返回:
    - params: 默认测试参数
    """
    params, error = get_default_params(operation_id)
    
    if error:
        logger.warning(f"获取默认参数失败: {error}")
        raise HttpError(404, error)
    
    return {'params': params}


# =============================================================================
# 调用历史查询
# =============================================================================

@router.get(
    "/doc-api/invoke-logs",
    auth=None,
    response=DocInvokeLogListOut,
    summary="查询调用历史"
)
def list_invoke_logs(
    request,
    operation_id: Optional[str] = Query(None, description="接口操作 ID（可选，用于筛选）"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（1-100）")
):
    """
    查询 HIS 接口调用历史记录
    
    查询参数:
    - operation_id: 接口操作 ID（可选，用于筛选特定接口的调用记录）
    - page: 页码（默认 1）
    - page_size: 每页数量（默认 20，最大 100）
    
    返回:
    - total: 总记录数
    - page: 当前页码
    - page_size: 每页数量
    - items: 调用历史列表
    """
    items, total, error = get_invoke_logs(
        operation_id=operation_id,
        page=page,
        page_size=page_size
    )
    
    if error:
        logger.error(f"查询调用历史失败: {error}")
        raise HttpError(500, error)
    
    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': items,
    }
