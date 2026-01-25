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
# 接口访问控制配置
# =============================================================================

# 接口访问控制配置文件路径（相对于项目根目录）
HIS_API_ACCESS_CONFIG_PATH = 'docs/his/access_control.json'


def _load_default_config_from_file() -> Dict[str, bool]:
    """
    从配置文件加载默认的接口访问控制配置
    
    配置文件路径: docs/his/access_control.json
    
    Returns:
        配置字典，如果文件不存在或解析失败则返回空字典
    """
    try:
        # 获取项目根目录
        base_dir = Path(settings.BASE_DIR)
        project_root = base_dir.parent
        config_path = project_root / HIS_API_ACCESS_CONFIG_PATH
        
        if not config_path.exists():
            logger.warning(f"接口访问控制配置文件不存在: {config_path}")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 支持两种格式：
        # 1. 直接是 {"operation_id": true/false, ...} 格式
        # 2. {"endpoints": {"operation_id": true/false, ...}} 格式
        if isinstance(config_data, dict):
            if 'endpoints' in config_data:
                endpoints = config_data.get('endpoints', {})
            else:
                endpoints = config_data
            
            if isinstance(endpoints, dict):
                logger.info(f"已从配置文件加载接口访问控制配置: {config_path}, {len(endpoints)} 个接口")
                return endpoints
        
        logger.warning(f"接口访问控制配置文件格式错误: {config_path}")
        return {}
        
    except json.JSONDecodeError as e:
        logger.error(f"接口访问控制配置文件 JSON 解析失败: {e}")
        return {}
    except Exception as e:
        logger.error(f"读取接口访问控制配置文件失败: {e}")
        return {}


def _load_access_control_config() -> Dict[str, bool]:
    """
    加载接口访问控制配置
    
    优先级（从高到低）：
    1. 环境变量 HIS_API_ACCESS_CONTROL（JSON 字符串格式）
    2. 配置文件 docs/his/access_control.json
    
    Returns:
        合并后的访问控制配置字典
    """
    # 从配置文件加载默认配置
    file_config = _load_default_config_from_file()
    
    # 从环境变量读取配置
    env_config_str = os.environ.get('HIS_API_ACCESS_CONTROL', '{}')
    env_config: Dict[str, bool] = {}
    
    try:
        env_config = json.loads(env_config_str)
        if not isinstance(env_config, dict):
            logger.warning(f"HIS_API_ACCESS_CONTROL 配置格式错误，忽略环境变量配置")
            env_config = {}
    except json.JSONDecodeError as e:
        logger.warning(f"HIS_API_ACCESS_CONTROL JSON 解析失败: {e}，忽略环境变量配置")
        env_config = {}
    
    # 合并配置文件和环境变量配置（环境变量配置优先）
    return {**file_config, **env_config}


# 全局访问控制配置（启动时加载一次）
_access_control_config: Optional[Dict[str, bool]] = None


def _get_access_control_config() -> Dict[str, bool]:
    """获取访问控制配置（带缓存）"""
    global _access_control_config
    if _access_control_config is None:
        _access_control_config = _load_access_control_config()
    return _access_control_config


def is_endpoint_accessible(operation_id: str) -> bool:
    """
    检查指定接口是否允许访问
    
    Args:
        operation_id: 接口操作 ID
        
    Returns:
        True 表示允许访问，False 表示不允许访问
    """
    config = _get_access_control_config()
    return config.get(operation_id, False)


def reload_access_control_config():
    """
    重新加载访问控制配置
    
    当环境变量更新后，可以调用此函数刷新配置
    """
    global _access_control_config
    _access_control_config = _load_access_control_config()
    logger.info("已重新加载接口访问控制配置")


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
    
    只返回允许访问的接口，根据访问控制配置进行过滤。
    
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
            
            ep_operation_id = operation.get('operationId', '')
            
            # 检查接口访问权限
            if not is_endpoint_accessible(ep_operation_id):
                continue
            
            endpoint = {
                'operation_id': ep_operation_id,
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

def get_endpoint_detail(operation_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], bool]:
    """
    获取接口详情
    
    只允许查询允许访问的接口，不允许访问的接口返回 403 错误标识。
    
    Args:
        operation_id: 操作 ID
        
    Returns:
        (detail, error, is_forbidden): 接口详情、错误信息和是否为权限拒绝
    """
    # 先检查接口访问权限
    if not is_endpoint_accessible(operation_id):
        return None, f"接口 {operation_id} 不允许访问", True
    
    openapi_data, error = get_openapi_data()
    if error:
        return None, error, False
    
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
                
                return detail, None, False
    
    return None, f"接口不存在: {operation_id}", False


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
    
    只在允许访问的接口中进行搜索，根据访问控制配置进行过滤。
    
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
            
            # 检查接口访问权限
            if not is_endpoint_accessible(ep_operation_id):
                continue
            
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
