# -*- coding: utf-8 -*-
"""
OpenAPI-Aware Django API 客户端

自动从 OpenAPI schema 学习 API 结构，支持：
- 自动加载和解析 OpenAPI Schema
- 生成 AI 可理解的 API 摘要
- API 端点搜索和意图匹配
- Bearer Token 认证
- 通用 API 调用
"""

import logging
from typing import Optional, Dict, Any, List

import httpx

from .models import APIEndpoint, DjangoAPIConfig

logger = logging.getLogger(__name__)


class OpenAPIAwareClient:
    """
    OpenAPI 感知的 Django API 客户端
    自动从 OpenAPI schema 学习 API 结构
    """
    
    def __init__(self, config: DjangoAPIConfig):
        """
        初始化客户端
        
        Args:
            config: Django API 配置
        """
        self.config = config
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout
        )
        # API 端点索引
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._endpoints_by_tag: Dict[str, List[APIEndpoint]] = {}
        self._schema: Optional[Dict] = None
    
    # ==================== OpenAPI Schema 处理 ====================
    
    async def load_openapi_schema(self) -> Dict:
        """
        加载 OpenAPI Schema
        
        Returns:
            OpenAPI Schema 字典
        """
        logger.info(f"加载 OpenAPI Schema: {self.config.base_url}/api/openapi.json")
        
        response = await self._client.get("/api/openapi.json")
        response.raise_for_status()
        
        self._schema = response.json()
        self._parse_schema()
        
        logger.info(f"OpenAPI Schema 加载完成，共 {len(self._endpoints)} 个端点")
        return self._schema
    
    def _parse_schema(self):
        """解析 OpenAPI Schema 构建端点索引"""
        if not self._schema:
            return
        
        # 设置 schema components，供 APIEndpoint 解析 $ref
        components = self._schema.get("components", {}).get("schemas", {})
        APIEndpoint.set_schema_components(components)
        
        paths = self._schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue
                
                endpoint = APIEndpoint(
                    path=path,
                    method=method.upper(),
                    operation_id=operation.get("operationId", ""),
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    tags=operation.get("tags", []),
                    parameters=operation.get("parameters", []),
                    request_body=operation.get("requestBody"),
                    responses=operation.get("responses", {})
                )
                
                # 按 operation_id 索引
                if endpoint.operation_id:
                    self._endpoints[endpoint.operation_id] = endpoint
                
                # 按 tag 分类索引
                for tag in endpoint.tags:
                    if tag not in self._endpoints_by_tag:
                        self._endpoints_by_tag[tag] = []
                    self._endpoints_by_tag[tag].append(endpoint)
    
    def get_all_endpoints(self) -> List[APIEndpoint]:
        """获取所有 API 端点"""
        return list(self._endpoints.values())
    
    def get_endpoint_count(self) -> int:
        """获取端点数量"""
        return len(self._endpoints)
    
    def get_api_summary_for_ai(self, include_schema: bool = True) -> str:
        """
        生成 AI 可理解的 API 摘要
        用于 LLM 理解可用的 API 能力
        
        Args:
            include_schema: 是否包含详细的请求/响应 Schema
        
        Returns:
            API 摘要文本
        """
        if not self._schema:
            return "API Schema 尚未加载，请先调用 load_openapi_schema()"
        
        info = self._schema.get("info", {})
        lines = []
        
        # 标题和描述
        lines.append(f"# {info.get('title', 'Django API')}")
        if info.get("description"):
            lines.append(f"\n{info.get('description')}")
        lines.append(f"\n## 可用 API\n")
        
        # 按 tag 分类列出，包含完整的 API 描述
        for tag, endpoints in self._endpoints_by_tag.items():
            lines.append(f"### {tag}\n")
            for ep in endpoints:
                # 使用增强的 AI 描述，包含请求/响应结构
                lines.append(ep.to_ai_description(include_schema=include_schema))
                lines.append("")  # 空行分隔
        
        return "\n".join(lines)
    
    def get_endpoints_by_keyword(self, keyword: str) -> List[APIEndpoint]:
        """
        根据关键词搜索相关 API
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的端点列表
        """
        keyword = keyword.lower()
        results = []
        
        for ep in self._endpoints.values():
            # 搜索 operation_id、summary、description、path、tags
            if (keyword in ep.operation_id.lower() or
                keyword in ep.summary.lower() or
                keyword in ep.description.lower() or
                keyword in ep.path.lower() or
                any(keyword in tag.lower() for tag in ep.tags)):
                results.append(ep)
        
        return results
    
    def find_endpoint(self, intent: str) -> Optional[APIEndpoint]:
        """
        根据意图找到最匹配的 API 端点
        
        匹配策略（按优先级）：
        1. 基于 description 的语义匹配（利用 OpenAPI 中文描述）
        2. 基于 summary 的关键词匹配
        3. 基于 path/operation_id 的关键词匹配
        4. 根据动作词推断 HTTP 方法偏好
        
        复杂场景建议使用 HierarchicalRetriever（支持 RAG 向量检索）
        
        Args:
            intent: 用户意图描述
        
        Returns:
            最匹配的端点，或 None
        """
        intent_lower = intent.lower()
        
        # 动作词分类（用于推断 HTTP 方法偏好）
        get_actions = ["获取", "查看", "列表", "列出", "显示", "list", "get", "show", "所有"]
        query_actions = ["查询", "搜索", "筛选", "过滤", "query", "search", "filter"]
        create_actions = ["创建", "新增", "添加", "create", "add", "新建"]
        update_actions = ["更新", "修改", "编辑", "update", "edit", "变更"]
        delete_actions = ["删除", "移除", "remove", "delete", "清除"]
        export_actions = ["导出", "下载", "export", "download"]
        
        # 检测意图动作类型
        is_get = any(action in intent_lower for action in get_actions)
        is_query = any(action in intent_lower for action in query_actions)
        is_create = any(action in intent_lower for action in create_actions)
        is_update = any(action in intent_lower for action in update_actions)
        is_delete = any(action in intent_lower for action in delete_actions)
        is_export = any(action in intent_lower for action in export_actions)
        
        # ========== 策略 1：基于 description 的语义匹配 ==========
        # 利用 OpenAPI 中已有的中文 description 进行匹配
        scored_endpoints = []
        
        # 提取关键词短语
        import re
        all_actions = get_actions + query_actions + create_actions + update_actions + delete_actions + export_actions
        
        # 同义词扩展（解决 OpenAPI 描述不够全面的问题）
        # 注意：只扩展业务同义词，不扩展技术术语
        synonyms = {
            "记录": ["数据", "records"],  # 记录=数据
            "数据": ["记录", "data"],
            "列表": ["清单", "list"],
            "详情": ["详细", "detail"],
            "问卷": ["表单", "survey"],  # 不包含 schema（技术术语）
            "用户": ["人员", "user"],
            "角色": ["role"],
            "部门": ["dept"],
            "菜单": ["menu"],
            "权限": ["permission"],
            "配置": ["config", "设置"],
            "模板": ["template"],
        }
        
        # 已知的业务词汇（用于分词）
        business_terms = list(synonyms.keys()) + [
            "表单", "模板", "配置", "登录", "登出", "密码", "token",
            "schema", "survey", "导入", "导出", "同步", "日志", "监控",
            "数据库", "redis", "服务器", "文件", "字典", "岗位"
        ]
        
        # 用动作词分割
        action_pattern = '|'.join(re.escape(a) for a in all_actions)
        keywords = re.sub(action_pattern, ' ', intent_lower)
        keywords = re.sub(r'[的是在和与]', ' ', keywords)  # 去除常见虚词
        
        # 提取关键词：先尝试识别已知业务词汇
        keyword_list = []
        remaining = keywords.strip()
        
        # 贪婪匹配已知业务词汇
        for term in sorted(business_terms, key=len, reverse=True):
            if term in remaining:
                keyword_list.append(term)
                remaining = remaining.replace(term, ' ')
        
        # 添加剩余的长词（>=2字符）
        for w in remaining.split():
            w = w.strip()
            if len(w) >= 2 and w not in keyword_list:
                keyword_list.append(w)
        
        # 原始关键词（权重高）
        original_keywords = set(keyword_list)
        
        # 扩展关键词（添加同义词，权重较低）
        expanded_keywords = set()
        for kw in keyword_list:
            if kw in synonyms:
                for syn in synonyms[kw]:
                    if syn not in original_keywords:
                        expanded_keywords.add(syn)
        
        # 合并：原始关键词 + 扩展同义词
        all_keywords = list(original_keywords) + list(expanded_keywords)
        
        for ep in self._endpoints.values():
            score = 0
            
            # ===== 分层匹配：summary > tags > description > path =====
            
            summary_lower = ep.summary.lower()
            tags_lower = ' '.join(ep.tags).lower()
            desc_lower = ep.description.lower()
            path_lower = f"{ep.path} {ep.operation_id}".lower()
            
            # 原始关键词匹配（权重高）
            for kw in original_keywords:
                if kw in summary_lower:
                    score += len(kw) * 60  # summary 中匹配
                if kw in tags_lower:
                    score += len(kw) * 50  # tags 中匹配
                if kw in desc_lower:
                    score += len(kw) * 35  # description 中匹配
                if kw in path_lower:
                    score += len(kw) * 20  # path 中匹配
            
            # 扩展同义词匹配（权重低）
            for kw in expanded_keywords:
                if kw in summary_lower:
                    score += len(kw) * 30
                if kw in tags_lower:
                    score += len(kw) * 25
                if kw in desc_lower:
                    score += len(kw) * 15
                if kw in path_lower:
                    score += len(kw) * 8
            
            # ===== 惩罚机制 =====
            
            # 惩罚有必需路径参数的端点（用户没有提供具体ID时）
            has_required_path_param = any(
                p.get('required') and p.get('in') == 'path' 
                for p in ep.parameters
            )
            if has_required_path_param:
                score -= 30  # 需要路径参数但用户没提供，降低优先级
            
            # 惩罚路径很长的端点（越具体的路径通常需要更多上下文）
            path_depth = ep.path.count('/')
            if path_depth > 4:
                score -= (path_depth - 4) * 10
            
            # ========== 策略 2：根据动作词调整分数 ==========
            # 动作词与 HTTP 方法匹配时加分
            if is_get and ep.method == "GET":
                score += 25
            elif is_query and ep.method == "POST" and "query" in ep.operation_id.lower():
                score += 25
            elif is_create and ep.method == "POST" and "create" in ep.operation_id.lower():
                score += 25
            elif is_update and ep.method in ("PUT", "PATCH"):
                score += 25
            elif is_delete and ep.method == "DELETE":
                score += 25
            elif is_export and "export" in ep.operation_id.lower():
                score += 30
            
            # 动作词与 HTTP 方法不匹配时减分
            if is_get and not is_query and ep.method == "POST":
                score -= 10
            if is_query and ep.method == "GET" and "list" in ep.operation_id.lower():
                score -= 5  # 查询时，list 端点优先级稍低
            
            if score > 0:
                scored_endpoints.append((score, ep))
        
        # 按分数排序，返回最高分
        if scored_endpoints:
            scored_endpoints.sort(key=lambda x: -x[0])
            return scored_endpoints[0][1]
        
        # ========== 策略 3：回退到简单关键词搜索 ==========
        results = self.get_endpoints_by_keyword(intent)
        if results:
            # 根据动作偏好过滤
            if is_get and not is_query:
                get_endpoints = [ep for ep in results if ep.method == "GET"]
                if get_endpoints:
                    return get_endpoints[0]
            elif is_query or is_create:
                post_endpoints = [ep for ep in results if ep.method == "POST"]
                if post_endpoints:
                    return post_endpoints[0]
            elif is_delete:
                delete_endpoints = [ep for ep in results if ep.method == "DELETE"]
                if delete_endpoints:
                    return delete_endpoints[0]
            return results[0]
        
        return None
    
    # ==================== 认证 ====================
    
    async def login(self) -> bool:
        """
        登录获取 Token
        
        Returns:
            是否登录成功
        """
        if not self.config.username or not self.config.password:
            logger.warning("未配置用户名或密码，跳过登录")
            return False
        
        logger.info(f"登录 Django API: {self.config.username}")
        
        try:
            response = await self._client.post("/api/core/login", json={
                "username": self.config.username,
                "password": self.config.password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
                logger.info("登录成功")
                return True
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """
        刷新 Access Token
        
        Returns:
            是否刷新成功
        """
        if not self.refresh_token:
            logger.warning("无 refresh_token，无法刷新")
            return False
        
        try:
            response = await self._client.post(
                "/api/core/refresh_token",
                headers={"Authorization": f"Bearer {self.refresh_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
                logger.info("Token 刷新成功")
                return True
            else:
                logger.error(f"Token 刷新失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Token 刷新异常: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头（含认证）"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    # ==================== 通用 API 调用 ====================
    
    async def call_api(
        self,
        endpoint: APIEndpoint,
        path_params: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        通用 API 调用方法
        根据 OpenAPI schema 自动处理参数
        
        Args:
            endpoint: API 端点
            path_params: 路径参数
            query_params: 查询参数
            body: 请求体
        
        Returns:
            API 响应数据
        """
        # 构建实际路径（替换路径参数）
        path = endpoint.path
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))
        
        # 根据方法调用
        method = endpoint.method.lower()
        kwargs = {
            "headers": self._get_headers(),
            "params": query_params
        }
        
        if method in ["post", "put", "patch"] and body:
            kwargs["json"] = body
        
        logger.debug(f"调用 API: {method.upper()} {path}")
        
        response = await getattr(self._client, method)(path, **kwargs)
        
        # 处理 401 错误，尝试刷新 token
        if response.status_code == 401 and self.refresh_token:
            if await self.refresh_access_token():
                kwargs["headers"] = self._get_headers()
                response = await getattr(self._client, method)(path, **kwargs)
        
        response.raise_for_status()
        return response.json()
    
    async def call_api_by_path(
        self,
        method: str,
        path: str,
        path_params: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        直接按路径调用 API（不需要先找 endpoint）
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
            path: API 路径，如 /api/core/survey/schemas
            path_params: 路径参数（用于替换路径中的 {param}）
            query_params: 查询参数
            body: 请求体
        
        Returns:
            API 响应数据
        
        Example:
            # GET 请求
            response = await client.call_api_by_path("GET", "/api/core/survey/schemas", query_params={"page": 1})
            
            # POST 请求
            response = await client.call_api_by_path("POST", "/api/core/survey/query", body={"schema_id": "xxx"})
        """
        # 替换路径参数
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))
        
        method = method.lower()
        kwargs = {
            "headers": self._get_headers(),
            "params": query_params
        }
        
        if method in ["post", "put", "patch"] and body:
            kwargs["json"] = body
        
        logger.debug(f"调用 API: {method.upper()} {path}")
        
        response = await getattr(self._client, method)(path, **kwargs)
        
        # 处理 401 错误，尝试刷新 token
        if response.status_code == 401 and self.refresh_token:
            if await self.refresh_access_token():
                kwargs["headers"] = self._get_headers()
                response = await getattr(self._client, method)(path, **kwargs)
        
        response.raise_for_status()
        return response.json()
    
    async def call_by_intent(
        self,
        intent: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据意图自动调用 API
        
        Args:
            intent: 用户意图描述
            params: 参数字典
        
        Returns:
            API 响应数据
        
        Raises:
            ValueError: 未找到匹配的 API
        """
        endpoint = self.find_endpoint(intent)
        if not endpoint:
            raise ValueError(f"未找到匹配意图的 API: {intent}")
        
        # 分离路径参数、查询参数和请求体
        path_params = {}
        query_params = {}
        body = {}
        
        if params:
            for p in endpoint.parameters:
                name = p.get("name", "")
                if name in params:
                    if p.get("in") == "path":
                        path_params[name] = params[name]
                    else:
                        query_params[name] = params[name]
            
            # 剩余参数作为请求体
            if endpoint.request_body:
                body = {k: v for k, v in params.items() 
                       if k not in path_params and k not in query_params}
        
        return await self.call_api(
            endpoint,
            path_params=path_params or None,
            query_params=query_params or None,
            body=body or None
        )
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
