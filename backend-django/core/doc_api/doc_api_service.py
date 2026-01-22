#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Doc API Service - 文档 API 业务逻辑层

提供文档数据读取、缓存和查询功能
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================================================
# 配置
# =============================================================================

# 从环境变量读取配置
DOC_API_URL = os.environ.get('DOC_API_URL', '')
DOC_API_TOKEN = os.environ.get('DOC_API_TOKEN', '')

# 文档文件路径（相对于项目根目录）
DOC_OPENAPI_PATH = 'docs/his/openapi.json'
DOC_REPORT_PATH = 'docs/his/report.json'

# 缓存配置
CACHE_TTL_SECONDS = 300  # 缓存 5 分钟

# =============================================================================
# 缓存实现
# =============================================================================

class DocDataCache:
    """
    文档数据缓存类
    
    使用简单的内存缓存，支持文件修改时间检测自动失效
    """
    
    def __init__(self):
        self._openapi_data: Optional[Dict[str, Any]] = None
        self._report_data: Optional[Dict[str, Any]] = None
        self._openapi_mtime: float = 0
        self._report_mtime: float = 0
        self._openapi_cache_time: float = 0
        self._report_cache_time: float = 0
    
    def _get_file_mtime(self, file_path: Path) -> float:
        """获取文件修改时间"""
        try:
            return file_path.stat().st_mtime
        except (FileNotFoundError, OSError):
            return 0
    
    def _is_cache_valid(self, cache_time: float, file_mtime: float, current_mtime: float) -> bool:
        """检查缓存是否有效"""
        now = time.time()
        # 缓存过期或文件已修改
        if now - cache_time > CACHE_TTL_SECONDS:
            return False
        if current_mtime != file_mtime:
            return False
        return True
    
    def get_openapi_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """获取 OpenAPI 数据（带缓存）"""
        current_mtime = self._get_file_mtime(file_path)
        
        if self._openapi_data and self._is_cache_valid(
            self._openapi_cache_time, self._openapi_mtime, current_mtime
        ):
            logger.debug("使用缓存的 OpenAPI 数据")
            return self._openapi_data
        
        # 重新加载数据
        data = self._load_json_file(file_path)
        if data:
            self._openapi_data = data
            self._openapi_mtime = current_mtime
            self._openapi_cache_time = time.time()
            logger.info(f"已加载 OpenAPI 数据: {file_path}")
        
        return data
    
    def get_report_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """获取报告数据（带缓存）"""
        current_mtime = self._get_file_mtime(file_path)
        
        if self._report_data and self._is_cache_valid(
            self._report_cache_time, self._report_mtime, current_mtime
        ):
            logger.debug("使用缓存的报告数据")
            return self._report_data
        
        # 重新加载数据
        data = self._load_json_file(file_path)
        if data:
            self._report_data = data
            self._report_mtime = current_mtime
            self._report_cache_time = time.time()
            logger.info(f"已加载报告数据: {file_path}")
        
        return data
    
    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """从文件加载 JSON 数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"文件不存在: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {file_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"读取文件失败: {file_path} - {e}")
            return None
    
    def clear(self):
        """清除缓存"""
        self._openapi_data = None
        self._report_data = None
        self._openapi_mtime = 0
        self._report_mtime = 0
        self._openapi_cache_time = 0
        self._report_cache_time = 0
        logger.info("已清除文档数据缓存")


# 全局缓存实例
_cache = DocDataCache()


# =============================================================================
# 文件路径辅助函数
# =============================================================================

def _get_project_root() -> Path:
    """获取项目根目录"""
    # settings.BASE_DIR 通常指向 backend-django 目录
    # 项目根目录在其上一级
    base_dir = Path(settings.BASE_DIR)
    return base_dir.parent


def _get_openapi_path() -> Path:
    """获取 OpenAPI 文件路径"""
    return _get_project_root() / DOC_OPENAPI_PATH


def _get_report_path() -> Path:
    """获取报告文件路径"""
    return _get_project_root() / DOC_REPORT_PATH


# =============================================================================
# 数据获取函数
# =============================================================================

def get_openapi_data() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    获取 OpenAPI 数据
    
    Returns:
        (data, error): 数据和错误信息的元组
    """
    file_path = _get_openapi_path()
    
    if not file_path.exists():
        return None, f"OpenAPI 文件不存在: {file_path}"
    
    data = _cache.get_openapi_data(file_path)
    if data is None:
        return None, f"无法读取 OpenAPI 文件: {file_path}"
    
    return data, None


def get_report_data() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    获取报告数据
    
    Returns:
        (data, error): 数据和错误信息的元组
    """
    file_path = _get_report_path()
    
    if not file_path.exists():
        return None, f"报告文件不存在: {file_path}"
    
    data = _cache.get_report_data(file_path)
    if data is None:
        return None, f"无法读取报告文件: {file_path}"
    
    return data, None


# =============================================================================
# 接口列表查询
# =============================================================================

def get_endpoints_list(
    page: int = 1, 
    page_size: int = 20
) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
    """
    获取接口列表
    
    Args:
        page: 页码（从 1 开始）
        page_size: 每页数量
        
    Returns:
        (items, total, error): 接口列表、总数和错误信息
    """
    openapi_data, error = get_openapi_data()
    if error:
        return [], 0, error
    
    # 从 paths 中提取接口信息
    paths = openapi_data.get('paths', {})
    endpoints = []
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            # 跳过非 HTTP 方法的字段
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                continue
            
            endpoint = {
                'operation_id': operation.get('operationId', ''),
                'name': operation.get('summary', operation.get('operationId', '')),
                'method': method.upper(),
                'path': path,
                'summary': operation.get('summary'),
            }
            endpoints.append(endpoint)
    
    # 分页
    total = len(endpoints)
    start = (page - 1) * page_size
    end = start + page_size
    items = endpoints[start:end]
    
    return items, total, None


# =============================================================================
# 接口详情查询
# =============================================================================

def get_endpoint_detail(operation_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    获取接口详情
    
    Args:
        operation_id: 操作 ID
        
    Returns:
        (detail, error): 接口详情和错误信息
    """
    openapi_data, error = get_openapi_data()
    if error:
        return None, error
    
    # 查找匹配的接口
    paths = openapi_data.get('paths', {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                continue
            
            if operation.get('operationId') == operation_id:
                # 构建详情
                detail = {
                    'operation_id': operation_id,
                    'name': operation.get('summary', operation_id),
                    'method': method.upper(),
                    'path': path,
                    'summary': operation.get('summary'),
                    'description': operation.get('description'),
                    'parameters': operation.get('parameters', []),
                    'request_body': operation.get('requestBody'),
                    'responses': operation.get('responses', {}),
                }
                
                # 提取示例
                request_body = operation.get('requestBody', {})
                if request_body:
                    content = request_body.get('content', {})
                    json_content = content.get('application/json', {})
                    detail['request_example'] = json_content.get('example')
                
                # 提取响应示例
                responses = operation.get('responses', {})
                success_response = responses.get('200', responses.get('201', {}))
                if success_response:
                    content = success_response.get('content', {})
                    json_content = content.get('application/json', {})
                    detail['response_example'] = json_content.get('example')
                
                # 尝试从 report.json 获取额外信息
                report_data, _ = get_report_data()
                if report_data:
                    for ep in report_data.get('endpoints', []):
                        if ep.get('operationId') == operation_id:
                            detail['request_fields'] = ep.get('requestFields')
                            detail['response_fields'] = ep.get('responseFields')
                            detail['location'] = ep.get('location')
                            break
                
                return detail, None
    
    return None, f"接口不存在: {operation_id}"


# =============================================================================
# 接口搜索
# =============================================================================

def search_endpoints(
    name: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    operation_id: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
    """
    搜索接口
    
    Args:
        name: 接口名称（模糊匹配）
        path: 接口路径（模糊匹配）
        method: HTTP 方法（精确匹配）
        operation_id: 操作 ID（模糊匹配）
        keyword: 关键词（在名称、路径、摘要中搜索）
        page: 页码
        page_size: 每页数量
        
    Returns:
        (items, total, error): 搜索结果、总数和错误信息
    """
    openapi_data, error = get_openapi_data()
    if error:
        return [], 0, error
    
    # 从 paths 中提取接口信息
    paths = openapi_data.get('paths', {})
    endpoints = []
    
    for ep_path, path_item in paths.items():
        for ep_method, operation in path_item.items():
            if ep_method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                continue
            
            ep_name = operation.get('summary', operation.get('operationId', ''))
            ep_operation_id = operation.get('operationId', '')
            ep_summary = operation.get('summary', '')
            
            # 应用过滤条件
            if name and name.lower() not in ep_name.lower():
                continue
            
            if path and path.lower() not in ep_path.lower():
                continue
            
            if method and method.upper() != ep_method.upper():
                continue
            
            if operation_id and operation_id.lower() not in ep_operation_id.lower():
                continue
            
            if keyword:
                keyword_lower = keyword.lower()
                if not any([
                    keyword_lower in ep_name.lower(),
                    keyword_lower in ep_path.lower(),
                    keyword_lower in ep_summary.lower(),
                    keyword_lower in ep_operation_id.lower(),
                ]):
                    continue
            
            endpoint = {
                'operation_id': ep_operation_id,
                'name': ep_name,
                'method': ep_method.upper(),
                'path': ep_path,
                'summary': ep_summary,
            }
            endpoints.append(endpoint)
    
    # 分页
    total = len(endpoints)
    start = (page - 1) * page_size
    end = start + page_size
    items = endpoints[start:end]
    
    return items, total, None


# =============================================================================
# 文档摘要
# =============================================================================

def get_doc_summary() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    获取文档摘要信息
    
    Returns:
        (summary, error): 摘要信息和错误信息
    """
    # 优先从 report.json 读取
    report_data, _ = get_report_data()
    
    if report_data and 'summary' in report_data:
        summary_data = report_data['summary']
        
        # 统计各方法数量
        openapi_data, _ = get_openapi_data()
        methods_summary = _count_methods(openapi_data) if openapi_data else None
        
        return {
            'title': summary_data.get('title', 'DOCX API'),
            'version': summary_data.get('version', '0.0.0'),
            'endpoint_count': summary_data.get('endpointCount', 0),
            'issue_count': summary_data.get('issueCount', 0),
            'openapi_error_count': summary_data.get('openapiErrorCount', 0),
            'methods_summary': methods_summary,
        }, None
    
    # 降级到 openapi.json
    openapi_data, error = get_openapi_data()
    if error:
        return None, error
    
    info = openapi_data.get('info', {})
    paths = openapi_data.get('paths', {})
    
    # 统计接口数量
    endpoint_count = 0
    for path_item in paths.values():
        for method in path_item:
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                endpoint_count += 1
    
    methods_summary = _count_methods(openapi_data)
    
    return {
        'title': info.get('title', 'Unknown'),
        'version': info.get('version', '0.0.0'),
        'endpoint_count': endpoint_count,
        'issue_count': 0,
        'openapi_error_count': 0,
        'methods_summary': methods_summary,
    }, None


def _count_methods(openapi_data: Dict[str, Any]) -> Dict[str, int]:
    """统计各 HTTP 方法的接口数量"""
    methods_count: Dict[str, int] = {}
    
    paths = openapi_data.get('paths', {})
    for path_item in paths.values():
        for method in path_item:
            method_upper = method.upper()
            if method_upper in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                methods_count[method_upper] = methods_count.get(method_upper, 0) + 1
    
    return methods_count


# =============================================================================
# 缓存管理
# =============================================================================

def clear_cache():
    """清除文档数据缓存"""
    _cache.clear()
