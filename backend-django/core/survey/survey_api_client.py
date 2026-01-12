#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey API Client - 外部问卷调查 API 客户端

负责与外部问卷调查系统 API 通信，包括：
- JWT 认证（Token 获取和自动刷新）
- 问卷类型列表获取
- 问卷 Schema 获取
- 问卷数据搜索
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

# 从环境变量读取配置
SURVEY_API_URL = os.environ.get('SURVEY_API_URL', 'http://106.52.105.202:13000')
SURVEY_API_ADMIN = os.environ.get('SURVEY_API_ADMIN', '')
SURVEY_API_PASSWORD = os.environ.get('SURVEY_API_PASSWORD', '')

# 请求超时时间（秒）
REQUEST_TIMEOUT = 30


class SurveyAPIError(Exception):
    """问卷 API 异常基类"""
    pass


class SurveyAuthError(SurveyAPIError):
    """认证异常"""
    pass


class SurveyRequestError(SurveyAPIError):
    """请求异常"""
    pass


class SurveyAPIClient:
    """
    问卷调查 API 客户端（含 JWT 认证）
    
    功能：
    1. JWT Token 获取和自动刷新
    2. 问卷类型列表获取
    3. 问卷 Schema 获取
    4. 问卷数据搜索
    
    使用示例：
        client = SurveyAPIClient()
        
        # 获取问卷类型列表
        types = client.get_survey_types()
        
        # 获取问卷 Schema
        schema = client.get_survey_schema('fried')
        
        # 搜索问卷数据
        result = client.search_surveys({
            'survey_type': 'fried',
            'page': 1,
            'page_size': 20
        })
    """
    
    def __init__(
        self, 
        base_url: str = None, 
        admin: str = None, 
        password: str = None
    ):
        """
        初始化客户端
        
        Args:
            base_url: API 地址（默认从环境变量读取）
            admin: 管理员账号（默认从环境变量读取）
            password: 管理员密码（默认从环境变量读取）
        """
        self.base_url = (base_url or SURVEY_API_URL).rstrip('/')
        self.admin = admin or SURVEY_API_ADMIN
        self.password = password or SURVEY_API_PASSWORD
        
        # Token 缓存
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # 验证配置
        if not self.base_url:
            raise SurveyAPIError("SURVEY_API_URL 未配置")
    
    def _get_token(self) -> str:
        """
        获取或刷新 JWT Token
        
        Returns:
            有效的 JWT Token
            
        Raises:
            SurveyAuthError: 认证失败
        """
        # 检查缓存的 Token 是否有效（提前 5 分钟刷新）
        if self._token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._token
        
        # 检查认证信息
        if not self.admin or not self.password:
            raise SurveyAuthError("SURVEY_API_ADMIN 或 SURVEY_API_PASSWORD 未配置")
        
        try:
            logger.info(f"正在获取 JWT Token: {self.base_url}/api/auth/login")
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": self.admin,
                    "password": self.password
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 401:
                raise SurveyAuthError("认证失败：用户名或密码错误")
            
            response.raise_for_status()
            data = response.json()
            
            self._token = data.get("access_token")
            if not self._token:
                raise SurveyAuthError("认证响应中缺少 access_token")
            
            # 假设 Token 有效期为 24 小时
            self._token_expires_at = datetime.now() + timedelta(hours=23)
            
            logger.info("JWT Token 获取成功")
            return self._token
            
        except Timeout:
            raise SurveyAuthError(f"认证请求超时（{REQUEST_TIMEOUT}秒）")
        except RequestException as e:
            raise SurveyAuthError(f"认证请求失败: {str(e)}")
    
    def _request(
        self, 
        method: str, 
        path: str, 
        auth_required: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法（GET, POST 等）
            path: API 路径
            auth_required: 是否需要认证
            **kwargs: 传递给 requests 的其他参数
            
        Returns:
            JSON 响应数据
            
        Raises:
            SurveyRequestError: 请求失败
        """
        url = f"{self.base_url}{path}"
        
        # 设置请求头
        headers = kwargs.pop('headers', {})
        if auth_required:
            token = self._get_token()
            headers['Authorization'] = f"Bearer {token}"
        
        # 设置超时
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        
        try:
            logger.debug(f"请求: {method} {url}")
            response = requests.request(
                method, 
                url, 
                headers=headers, 
                **kwargs
            )
            
            # 处理 401 错误（Token 过期）
            if response.status_code == 401 and auth_required:
                logger.warning("Token 可能已过期，尝试刷新")
                self._token = None
                self._token_expires_at = None
                token = self._get_token()
                headers['Authorization'] = f"Bearer {token}"
                response = requests.request(
                    method, 
                    url, 
                    headers=headers, 
                    **kwargs
                )
            
            response.raise_for_status()
            return response.json()
            
        except Timeout:
            raise SurveyRequestError(f"请求超时（{REQUEST_TIMEOUT}秒）: {url}")
        except RequestException as e:
            raise SurveyRequestError(f"请求失败: {url} - {str(e)}")
    
    def get_survey_types(self) -> Dict[str, Any]:
        """
        获取所有问卷类型列表
        
        Returns:
            {
                "total": 10,
                "surveys": [
                    {"type": "fried", "name": "Fried衰弱评估", "description": "..."},
                    ...
                ]
            }
        """
        logger.info("获取问卷类型列表")
        return self._request("GET", "/api/survey-schemas", auth_required=False)
    
    def get_survey_schema(self, survey_type: str) -> Dict[str, Any]:
        """
        获取问卷 Schema
        
        Args:
            survey_type: 问卷类型（如：fried, rockwood, gpm）
            
        Returns:
            问卷 Schema 定义
        """
        logger.info(f"获取问卷 Schema: {survey_type}")
        return self._request(
            "GET", 
            f"/api/survey-schema/{survey_type}", 
            auth_required=False
        )
    
    def search_surveys(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        搜索问卷数据（需要 JWT 认证）
        
        Args:
            params: 搜索参数
                - survey_type: 问卷类型（可选）
                - survey_id: 问卷ID（可选）
                - patient_name: 患者姓名（可选，模糊匹配）
                - start_date: 开始日期（可选，YYYY-MM-DD）
                - end_date: 结束日期（可选，YYYY-MM-DD）
                - page: 页码（默认 1）
                - page_size: 每页数量（默认 20）
                
        Returns:
            {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "items": [...]
            }
        """
        logger.info(f"搜索问卷数据: {params}")
        return self._request(
            "POST", 
            "/api/db/surveys/search", 
            json=params,
            auth_required=True
        )
    
    def test_connection(self) -> bool:
        """
        测试 API 连接
        
        Returns:
            连接是否成功
        """
        try:
            self.get_survey_types()
            return True
        except SurveyAPIError as e:
            logger.error(f"API 连接测试失败: {e}")
            return False
    
    def test_auth(self) -> bool:
        """
        测试认证是否正常
        
        Returns:
            认证是否成功
        """
        try:
            self._get_token()
            return True
        except SurveyAuthError as e:
            logger.error(f"认证测试失败: {e}")
            return False


# 全局客户端实例（懒加载）
_client: Optional[SurveyAPIClient] = None


def get_survey_api_client() -> SurveyAPIClient:
    """
    获取全局 API 客户端实例
    
    Returns:
        SurveyAPIClient 实例
    """
    global _client
    if _client is None:
        _client = SurveyAPIClient()
    return _client

