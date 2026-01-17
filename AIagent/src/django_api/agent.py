# -*- coding: utf-8 -*-
"""
Django API 智能体

集成 LLM 进行意图理解和 API 调用决策
支持分层检索（关键词 + RAG + LLM）
"""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.embeddings import Embeddings

from ..agents.base_agent import BaseAgent, AgentResult
from ..llm.base import BaseLLMClient
from .client import OpenAPIAwareClient
from .indexer import APIEndpointIndexer
from .models import APIEndpoint, DjangoAPIConfig
from .retriever import HierarchicalRetriever

logger = logging.getLogger(__name__)


class DjangoAPIAgent(BaseAgent):
    """
    Django API 智能体
    
    使用 LLM 理解用户意图并调用正确的 API
    支持分层检索处理大规模 API
    """
    
    name: str = "django_api"
    
    def __init__(
        self,
        config: DjangoAPIConfig,
        llm_client: Optional[BaseLLMClient] = None,
        embeddings: Optional[Embeddings] = None,
        **kwargs
    ):
        """
        初始化智能体
        
        Args:
            config: Django API 配置
            llm_client: LLM 客户端（可选，用于意图理解）
            embeddings: 嵌入模型（可选，用于 RAG）
        """
        super().__init__(**kwargs)
        self.config = config
        self.llm_client = llm_client
        self.embeddings = embeddings
        
        # 客户端和检索器（延迟初始化）
        self.api_client: Optional[OpenAPIAwareClient] = None
        self.indexer: Optional[APIEndpointIndexer] = None
        self.retriever: Optional[HierarchicalRetriever] = None
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        初始化智能体
        
        加载 OpenAPI Schema、构建索引、登录
        
        Returns:
            是否初始化成功
        """
        try:
            # 创建 API 客户端
            self.api_client = OpenAPIAwareClient(self.config)
            
            # 加载 OpenAPI Schema
            await self.api_client.load_openapi_schema()
            
            # 登录（如果配置了用户名密码）
            if self.config.username and self.config.password:
                await self.api_client.login()
            
            # 构建向量索引（如果启用 RAG 且有嵌入模型）
            if self.config.enable_rag and self.embeddings:
                self.indexer = APIEndpointIndexer(
                    embeddings=self.embeddings,
                    collection_name="django_api_endpoints",
                )
                endpoints = self.api_client.get_all_endpoints()
                self.indexer.build_index(endpoints)
            
            # 创建分层检索器
            self.retriever = HierarchicalRetriever(
                endpoints=self.api_client._endpoints,
                indexer=self.indexer,
                keyword_filter_threshold=self.config.keyword_filter_threshold,
                top_k=self.config.top_k,
                similarity_threshold=self.config.similarity_threshold,
            )
            
            self._initialized = True
            self.logger.info(f"Django API 智能体初始化完成，共 {self.api_client.get_endpoint_count()} 个端点")
            return True
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False
    
    def get_system_prompt(self, relevant_apis: Optional[List[APIEndpoint]] = None) -> str:
        """
        生成系统提示词
        
        Args:
            relevant_apis: 相关的 API 列表（可选，用于减少 context）
        
        Returns:
            系统提示词
        """
        if not self.api_client:
            return "Django API 客户端未初始化"
        
        lines = [
            "你是一个 Django 后台 API 助手。你可以帮助用户查询和操作数据。",
            "",
        ]
        
        if relevant_apis:
            # 只包含检索到的 API
            lines.append("## 可用的相关 API")
            lines.append("")
            for ep in relevant_apis:
                lines.append(f"### {ep.operation_id}")
                lines.append(ep.to_ai_description())
                lines.append("")
        else:
            # 包含所有 API 摘要
            lines.append(self.api_client.get_api_summary_for_ai())
        
        lines.extend([
            "",
            "当用户提出请求时，你需要：",
            "1. 理解用户意图",
            "2. 选择合适的 API",
            "3. 构造正确的参数",
            "",
            "请用 JSON 格式返回你的决策：",
            "```json",
            "{",
            '    "intent": "用户意图描述",',
            '    "api": "operation_id",',
            '    "params": {},',
            '    "explanation": "选择原因"',
            "}",
            "```",
        ])
        
        return "\n".join(lines)
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            query: 用户查询
        
        Returns:
            查询结果
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.api_client:
            return {"error": "API 客户端未初始化"}
        
        try:
            # 第一步：检索相关 API
            relevant_apis = []
            if self.retriever:
                relevant_apis = self.retriever.retrieve(query)
                self.logger.debug(f"检索到 {len(relevant_apis)} 个相关 API")
            
            # 第二步：使用 LLM 理解意图并选择 API（如果有 LLM）
            if self.llm_client and relevant_apis:
                decision = await self._llm_select_api(query, relevant_apis)
                if decision:
                    # 执行 API 调用
                    result = await self._execute_api_call(decision)
                    return {
                        "success": True,
                        "decision": decision,
                        "result": result,
                    }
            
            # 回退：使用简单的意图匹配
            endpoint = self.api_client.find_endpoint(query)
            if endpoint:
                result = await self.api_client.call_api(endpoint)
                return {
                    "success": True,
                    "endpoint": endpoint.operation_id,
                    "result": result,
                }
            
            return {
                "success": False,
                "error": "未找到匹配的 API",
                "available_apis": [ep.operation_id for ep in relevant_apis] if relevant_apis else [],
            }
            
        except Exception as e:
            self.logger.error(f"处理查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _llm_select_api(
        self,
        query: str,
        candidates: List[APIEndpoint],
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 选择最匹配的 API
        
        Args:
            query: 用户查询
            candidates: 候选 API 列表
        
        Returns:
            LLM 的决策结果，或 None
        """
        if not self.llm_client:
            return None
        
        # 构建提示词
        system_prompt = self.get_system_prompt(candidates)
        user_prompt = f"用户请求：{query}"
        
        try:
            # 调用 LLM
            response = await self.llm_client.invoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            
            # 解析 JSON 响应
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 提取 JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(1))
                return decision
            
            # 尝试直接解析
            try:
                decision = json.loads(response_text)
                return decision
            except json.JSONDecodeError:
                pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"LLM 选择 API 失败: {e}")
            return None
    
    async def _execute_api_call(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 API 调用
        
        Args:
            decision: LLM 的决策结果
        
        Returns:
            API 调用结果
        """
        api_name = decision.get("api", "")
        params = decision.get("params", {})
        
        if not api_name:
            return {"error": "未指定 API"}
        
        # 查找端点
        endpoint = self.api_client._endpoints.get(api_name)
        if not endpoint:
            return {"error": f"未找到 API: {api_name}"}
        
        # 分离参数
        path_params = {}
        query_params = {}
        body = {}
        
        for p in endpoint.parameters:
            name = p.get("name", "")
            if name in params:
                if p.get("in") == "path":
                    path_params[name] = params[name]
                else:
                    query_params[name] = params[name]
        
        if endpoint.request_body:
            body = {k: v for k, v in params.items() 
                   if k not in path_params and k not in query_params}
        
        # 调用 API
        return await self.api_client.call_api(
            endpoint,
            path_params=path_params or None,
            query_params=query_params or None,
            body=body or None,
        )
    
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """
        执行智能体逻辑（BaseAgent 接口）
        
        Args:
            state: 当前状态
        
        Returns:
            智能体结果
        """
        query = state.get("query", "") or state.get("user_input", "")
        
        if not query:
            return AgentResult(
                output_text="请提供查询内容",
                updates={"error": "未提供查询内容"}
            )
        
        result = await self.process_query(query)
        
        return AgentResult(
            output_text=json.dumps(result, ensure_ascii=False, indent=2),
            updates={"api_result": result}
        )
    
    async def close(self):
        """关闭智能体"""
        if self.api_client:
            await self.api_client.close()
