# -*- coding: utf-8 -*-
"""
Django API 客户端单元测试

测试 OpenAPIAwareClient 的核心功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from AIagent.src.django_api.models import APIEndpoint, DjangoAPIConfig
from AIagent.src.django_api.client import OpenAPIAwareClient


# 测试数据
MOCK_OPENAPI_SCHEMA = {
    "info": {
        "title": "Test API",
        "description": "测试 API",
        "version": "1.0.0"
    },
    "paths": {
        "/api/core/user": {
            "get": {
                "operationId": "list_users",
                "summary": "获取用户列表",
                "tags": ["Core-User"],
                "parameters": [
                    {"name": "page", "in": "query", "description": "页码"},
                    {"name": "page_size", "in": "query", "description": "每页数量"}
                ]
            },
            "post": {
                "operationId": "create_user",
                "summary": "创建用户",
                "tags": ["Core-User"],
                "requestBody": {"required": True}
            }
        },
        "/api/core/user/{user_id}": {
            "get": {
                "operationId": "get_user",
                "summary": "获取用户详情",
                "tags": ["Core-User"],
                "parameters": [
                    {"name": "user_id", "in": "path", "required": True}
                ]
            }
        },
        "/api/core/login": {
            "post": {
                "operationId": "login",
                "summary": "用户登录",
                "tags": ["Core-Auth"],
                "requestBody": {"required": True}
            }
        }
    }
}


class TestAPIEndpoint:
    """APIEndpoint 数据类测试"""
    
    def test_to_ai_description(self):
        """测试 AI 描述生成"""
        endpoint = APIEndpoint(
            path="/api/core/user",
            method="GET",
            operation_id="list_users",
            summary="获取用户列表",
            tags=["Core-User"],
            parameters=[
                {"name": "page", "in": "query", "description": "页码"},
                {"name": "page_size", "in": "query", "description": "每页数量", "required": True}
            ]
        )
        
        desc = endpoint.to_ai_description()
        
        assert "【GET】/api/core/user" in desc
        assert "获取用户列表" in desc
        assert "Core-User" in desc
        assert "page" in desc
        assert "page_size*" in desc  # required 标记
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        endpoint = APIEndpoint(
            path="/api/test",
            method="POST",
            operation_id="test_op",
            summary="测试操作",
            tags=["Test"]
        )
        
        data = endpoint.to_dict()
        restored = APIEndpoint.from_dict(data)
        
        assert restored.path == endpoint.path
        assert restored.method == endpoint.method
        assert restored.operation_id == endpoint.operation_id


class TestOpenAPIAwareClient:
    """OpenAPIAwareClient 测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return DjangoAPIConfig(
            base_url="http://localhost:8000",
            username="admin",
            password="admin123",
            timeout=10
        )
    
    @pytest.fixture
    def client(self, config):
        """测试客户端"""
        return OpenAPIAwareClient(config)
    
    def test_parse_schema(self, client):
        """测试 Schema 解析"""
        client._schema = MOCK_OPENAPI_SCHEMA
        client._parse_schema()
        
        # 检查端点数量
        assert len(client._endpoints) == 4
        
        # 检查特定端点
        assert "list_users" in client._endpoints
        assert "create_user" in client._endpoints
        assert "login" in client._endpoints
        
        # 检查 tag 索引
        assert "Core-User" in client._endpoints_by_tag
        assert len(client._endpoints_by_tag["Core-User"]) == 3
    
    def test_get_api_summary_for_ai(self, client):
        """测试 AI 摘要生成"""
        client._schema = MOCK_OPENAPI_SCHEMA
        client._parse_schema()
        
        summary = client.get_api_summary_for_ai()
        
        assert "Test API" in summary
        assert "Core-User" in summary
        assert "list_users" in summary
    
    def test_get_endpoints_by_keyword(self, client):
        """测试关键词搜索"""
        client._schema = MOCK_OPENAPI_SCHEMA
        client._parse_schema()
        
        # 搜索 "user"
        results = client.get_endpoints_by_keyword("user")
        assert len(results) >= 3
        
        # 搜索 "login"
        results = client.get_endpoints_by_keyword("login")
        assert len(results) == 1
        assert results[0].operation_id == "login"
    
    def test_find_endpoint(self, client):
        """测试意图匹配"""
        client._schema = MOCK_OPENAPI_SCHEMA
        client._parse_schema()
        
        # 测试登录意图
        endpoint = client.find_endpoint("用户登录")
        assert endpoint is not None
        assert endpoint.operation_id == "login"
        
        # 测试用户列表意图
        endpoint = client.find_endpoint("获取用户列表")
        assert endpoint is not None
        assert "user" in endpoint.operation_id.lower()


class TestOpenAPIAwareClientAsync:
    """OpenAPIAwareClient 异步测试"""
    
    @pytest.fixture
    def config(self):
        return DjangoAPIConfig(
            base_url="http://localhost:8000",
            username="admin",
            password="admin123"
        )
    
    @pytest.mark.asyncio
    async def test_load_openapi_schema(self, config):
        """测试加载 OpenAPI Schema"""
        client = OpenAPIAwareClient(config)
        
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_OPENAPI_SCHEMA
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client._client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            schema = await client.load_openapi_schema()
            
            assert schema == MOCK_OPENAPI_SCHEMA
            assert len(client._endpoints) == 4
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_login(self, config):
        """测试登录"""
        client = OpenAPIAwareClient(config)
        
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accessToken": "test_access_token",
            "refreshToken": "test_refresh_token"
        }
        
        with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await client.login()
            
            assert result is True
            assert client.access_token == "test_access_token"
            assert client.refresh_token == "test_refresh_token"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_call_api(self, config):
        """测试 API 调用"""
        client = OpenAPIAwareClient(config)
        client._schema = MOCK_OPENAPI_SCHEMA
        client._parse_schema()
        client.access_token = "test_token"
        
        endpoint = client._endpoints["list_users"]
        
        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [], "total": 0}
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(client._client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await client.call_api(
                endpoint,
                query_params={"page": 1, "page_size": 10}
            )
            
            assert "items" in result
            mock_get.assert_called_once()
        
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
