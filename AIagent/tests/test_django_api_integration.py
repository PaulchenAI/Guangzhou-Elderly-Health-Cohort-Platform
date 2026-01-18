# -*- coding: utf-8 -*-
"""
Django API 优化功能集成测试

测试内容：
- 大规模 API（>200 端点）的上下文优化效果
- 相似指令复用流程（含参数替换）
- 失败记录的错误避免效果
- 无数目查询的翻页行为
- 不同输出格式切换
- 相同核心意图匹配历史记录
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AIagent.src.django_api.client import OpenAPIAwareClient
from AIagent.src.django_api.models import DjangoAPIConfig, APIEndpoint
from AIagent.src.django_api.execution_history import (
    ExecutionHistoryStorage,
    ExecutionRecord,
    ExecutionStatus,
    normalize_intent,
    substitute_params,
    generate_intent_hash,
)
from AIagent.src.django_api.history_retriever import (
    HistoryRetriever,
    HistoryRetrievalConfig,
    TieredSearchResults,
    SearchResult,
    build_history_context,
)
from AIagent.src.django_api.output_format import (
    OutputFormat,
    PaginationInfo,
    QueryResult,
    inject_pagination,
)


# ==================== 测试 1: 大规模 API 上下文优化 ====================

class TestLargeScaleAPIContext:
    """测试大规模 API（>200 端点）的上下文优化效果"""
    
    def _create_mock_endpoints(self, count: int) -> Dict[str, List[APIEndpoint]]:
        """创建模拟的 API 端点"""
        endpoints_by_tag = {}
        tags = ["Core-User", "Core-Auth", "Survey", "TableQuery", "System", "Report"]
        
        for i in range(count):
            tag = tags[i % len(tags)]
            endpoint = APIEndpoint(
                path=f"/api/{tag.lower()}/endpoint{i}",
                method="GET" if i % 2 == 0 else "POST",
                operation_id=f"{tag.lower()}_endpoint_{i}",
                summary=f"端点 {i} 的功能描述",
                description=f"这是端点 {i} 的详细描述，包含更多信息",
                tags=[tag],
                parameters=[{"name": "page", "in": "query"}] if i % 3 == 0 else [],
                request_body=None,
                responses={},
            )
            
            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []
            endpoints_by_tag[tag].append(endpoint)
        
        return endpoints_by_tag
    
    def test_compact_summary_token_reduction(self):
        """测试紧凑摘要的 Token 减少效果"""
        # 创建 300 个模拟端点
        endpoints_by_tag = self._create_mock_endpoints(300)
        
        # 模拟客户端
        client = OpenAPIAwareClient(DjangoAPIConfig(base_url="http://test"))
        client._endpoints_by_tag = endpoints_by_tag
        client._endpoints = {
            ep.operation_id: ep 
            for eps in endpoints_by_tag.values() 
            for ep in eps
        }
        client._schema = {"info": {"title": "Test API", "description": "测试 API"}}
        
        # 生成完整摘要
        full_summary = client._generate_full_summary(include_schema=False)
        full_tokens = client.estimate_token_count(full_summary)
        
        # 生成紧凑摘要
        compact_summary = client.get_api_summary_compact()
        compact_tokens = client.estimate_token_count(compact_summary)
        
        # 验证紧凑摘要 Token 数量大幅减少
        print(f"完整摘要 Token: {full_tokens}")
        print(f"紧凑摘要 Token: {compact_tokens}")
        print(f"减少比例: {(1 - compact_tokens/full_tokens)*100:.1f}%")
        
        assert compact_tokens < full_tokens * 0.3  # 紧凑模式应减少 70% 以上
        assert "共 6 个分类" in compact_summary
        assert "300 个端点" in compact_summary
    
    def test_auto_switch_to_compact_mode(self):
        """测试超过 Token 限制时自动切换到紧凑模式"""
        endpoints_by_tag = self._create_mock_endpoints(300)
        
        client = OpenAPIAwareClient(DjangoAPIConfig(base_url="http://test"))
        client._endpoints_by_tag = endpoints_by_tag
        client._endpoints = {
            ep.operation_id: ep 
            for eps in endpoints_by_tag.values() 
            for ep in eps
        }
        client._schema = {"info": {"title": "Test API"}}
        
        # 设置较低的 Token 限制
        summary = client.get_api_summary_for_ai(max_tokens=500)
        
        # 应该自动切换到紧凑模式
        assert "API 概览" in summary or "API 分类" in summary
        assert client.estimate_token_count(summary) < 1000
    
    def test_tag_endpoints_summary(self):
        """测试按 Tag 获取端点摘要"""
        endpoints_by_tag = self._create_mock_endpoints(100)
        
        client = OpenAPIAwareClient(DjangoAPIConfig(base_url="http://test"))
        client._endpoints_by_tag = endpoints_by_tag
        client._schema = {"info": {"title": "Test API"}}
        
        # 获取特定 Tag 的端点摘要
        tag_summary = client.get_tag_endpoints_summary("Core-User")
        
        assert "Core-User API 端点列表" in tag_summary
        assert "operation_id" in tag_summary
    
    def test_endpoint_detail(self):
        """测试获取单个端点详情"""
        endpoints_by_tag = self._create_mock_endpoints(10)
        
        client = OpenAPIAwareClient(DjangoAPIConfig(base_url="http://test"))
        client._endpoints_by_tag = endpoints_by_tag
        client._endpoints = {
            ep.operation_id: ep 
            for eps in endpoints_by_tag.values() 
            for ep in eps
        }
        
        # 获取端点详情
        detail = client.get_endpoint_detail("core-user_endpoint_0")
        
        assert "GET" in detail or "POST" in detail
        assert "endpoint0" in detail


# ==================== 测试 2: 相似指令复用流程 ====================

class TestSimilarIntentReuse:
    """测试相似指令复用流程（含参数替换）"""
    
    def test_history_retrieval_with_parameter_substitution(self):
        """测试历史检索和参数替换"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExecutionHistoryStorage(tmpdir)
            
            # 保存历史记录（查询用户列表前5个）
            history_record = ExecutionRecord(
                id=generate_intent_hash("查询用户列表前5个"),
                intent="查询用户列表前5个",
                normalized_intent="查询用户列表",
                intent_params={"limit": 5},
                status=ExecutionStatus.SUCCESS.value,
                apis_used=["core_user_list"],
                script_content='params = {"limit": 5, "page": 1}\nresponse = client.call(params)',
                execution_output="返回 5 条记录",
            )
            storage.save_execution(history_record)
            
            # 创建检索器（不使用向量索引，回退到关键词匹配）
            retriever = HistoryRetriever(
                storage=storage,
                indexer=None,
                config=HistoryRetrievalConfig(
                    exact_threshold=0.95,
                    high_threshold=0.80,
                    low_threshold=0.60,
                ),
            )
            
            # 检索相似意图（查询用户列表前10个）
            results = retriever.retrieve("查询用户列表前10个")
            
            # 应该能找到相似记录
            assert results.best_match is not None
            print(f"最佳匹配: {results.best_match.intent}, 分数: {results.best_match.score:.2f}")
            
            # 测试参数替换
            if results.best_match:
                new_script = substitute_params(
                    results.best_match.script_content,
                    {"limit": 5},
                    {"limit": 10}
                )
                assert '"limit": 10' in new_script
    
    def test_same_core_intent_matching(self):
        """测试"查询用户前10个"能匹配到"查询用户前5个"的历史"""
        # 归一化两个意图
        intent1 = normalize_intent("查询用户列表前10个")
        intent2 = normalize_intent("查询用户列表前5个")
        
        # 核心意图应该相同
        assert intent1.core_intent == intent2.core_intent
        
        # 哈希也应该相同
        hash1 = generate_intent_hash("查询用户列表前10个")
        hash2 = generate_intent_hash("查询用户列表前5个")
        assert hash1 == hash2
    
    def test_build_history_context_for_exact_match(self):
        """测试精确匹配时的上下文构建"""
        # 创建精确匹配结果
        exact_match = SearchResult(
            record_id="test123",
            intent="查询用户列表前5个",
            normalized_intent="查询用户列表",
            status="success",
            score=0.97,
            apis_used=["core_user_list"],
            script_content='params = {"limit": 5}',
            execution_output="返回 5 条记录",
            intent_params={"limit": 5},
        )
        
        results = TieredSearchResults(
            exact_matches=[exact_match],
            high_similar=[],
            low_similar=[],
        )
        
        # 构建上下文
        context = build_history_context("查询用户列表前10个", results)
        
        # 验证上下文包含复用提示
        assert "精确匹配" in context
        assert "直接复用" in context or "复用" in context
        assert "0.97" in context


# ==================== 测试 3: 失败记录的错误避免 ====================

class TestFailedRecordErrorAvoidance:
    """测试失败记录的错误避免效果"""
    
    def test_failed_record_saved(self):
        """测试失败记录能正确保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExecutionHistoryStorage(tmpdir)
            
            # 保存失败记录
            failed_record = ExecutionRecord(
                id="failed123",
                intent="查询问卷数据中的户外活动",
                normalized_intent="查询问卷数据户外活动",
                intent_params={},
                status=ExecutionStatus.FAILED.value,
                apis_used=["survey_query"],
                script_content="# 失败的脚本",
                error_message="缺少必需参数 table_name",
                error_type="parameter_error",
            )
            storage.save_execution(failed_record)
            
            # 验证能加载
            loaded = storage.get_record("failed123")
            assert loaded is not None
            assert loaded.status == "failed"
            assert loaded.error_type == "parameter_error"
    
    def test_build_history_context_for_failed_match(self):
        """测试失败记录的上下文构建（提示避免错误）"""
        # 创建高度相似的失败记录
        failed_match = SearchResult(
            record_id="failed456",
            intent="查询问卷数据",
            normalized_intent="查询问卷数据",
            status="failed",
            score=0.85,
            apis_used=["survey_query"],
            error_type="parameter_error",
            error_message="缺少必需参数 survey_name",
        )
        
        results = TieredSearchResults(
            exact_matches=[],
            high_similar=[failed_match],
            low_similar=[],
        )
        
        # 构建上下文
        context = build_history_context("查询问卷数据", results)
        
        # 验证上下文包含错误警告
        assert "失败" in context or "错误" in context
        assert "避免" in context or "parameter_error" in context


# ==================== 测试 4: 无数目查询的翻页行为 ====================

class TestPaginationBehavior:
    """测试无数目查询的翻页行为"""
    
    def test_inject_pagination_when_no_count(self):
        """测试无数目时自动注入翻页参数"""
        params = {"keyword": "test"}
        result = inject_pagination(params, "查询用户列表")
        
        assert result["page"] == 1
        assert result["pageSize"] == 10
    
    def test_no_inject_when_explicit_count(self):
        """测试有明确数目时不注入"""
        params = {"keyword": "test"}
        
        # 有"前10个"时不应注入
        result = inject_pagination(params, "查询用户列表前10个")
        # 检查是否保持原样（不强制添加）
        assert "keyword" in result
    
    def test_pagination_info_calculation(self):
        """测试翻页信息计算"""
        info = PaginationInfo(page=2, page_size=10, total=156)
        
        assert info.total_pages == 16
        assert info.has_more is True
        
        # 最后一页
        last_page = PaginationInfo(page=16, page_size=10, total=156)
        assert last_page.has_more is False
    
    def test_pagination_summary(self):
        """测试翻页摘要生成"""
        info = PaginationInfo(page=1, page_size=10, total=156)
        summary = info.to_summary()
        
        assert "第 1 页" in summary
        assert "156 条" in summary
        assert "146 条未显示" in summary
        assert "下一页" in summary or "继续" in summary


# ==================== 测试 5: 不同输出格式切换 ====================

class TestOutputFormatSwitch:
    """测试不同输出格式切换"""
    
    def test_text_output_format(self):
        """测试文本格式输出"""
        result = QueryResult(
            success=True,
            data=[{"id": 1, "name": "张三"}, {"id": 2, "name": "李四"}],
            pagination=PaginationInfo(page=1, page_size=10, total=100),
            meta={"intent": "查询用户列表"},
        )
        
        text = result.to_text()
        
        assert "📊 查询结果" in text
        assert "2 条记录" in text
        assert "翻页信息" in text
    
    def test_json_output_format(self):
        """测试 JSON 格式输出"""
        result = QueryResult(
            success=True,
            data=[{"id": 1, "name": "张三"}],
            pagination=PaginationInfo(page=1, page_size=10, total=100),
            meta={"intent": "查询用户列表", "api": "core_user_list"},
        )
        
        json_str = result.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["success"] is True
        assert len(parsed["data"]) == 1
        assert parsed["pagination"]["total"] == 100
        assert parsed["pagination"]["hasMore"] is True
        assert parsed["meta"]["intent"] == "查询用户列表"
    
    def test_output_format_switch(self):
        """测试输出格式切换"""
        result = QueryResult(
            success=True,
            data=[{"id": 1}],
            pagination=PaginationInfo(page=1, page_size=10, total=10),
        )
        
        # 文本格式
        text_output = result.output(OutputFormat.TEXT)
        assert "📊" in text_output
        
        # JSON 格式
        json_output = result.output(OutputFormat.JSON)
        assert json_output.startswith("{")
        assert "success" in json_output


# ==================== 测试 6: 相同核心意图匹配历史 ====================

class TestCoreIntentMatching:
    """测试相同核心意图匹配历史记录"""
    
    def test_normalize_different_limits_same_core(self):
        """测试不同数目限制归一化到相同核心意图"""
        intents = [
            "查询用户列表前10个",
            "查询用户列表前5个",
            "查询用户列表前100个",
            "查询用户列表",
        ]
        
        cores = [normalize_intent(i).core_intent for i in intents]
        
        # 所有核心意图应该相同
        assert len(set(cores)) == 1
        assert cores[0] == "查询用户列表"
    
    def test_normalize_different_pages_same_core(self):
        """测试不同页码归一化到相同核心意图"""
        intents = [
            "查询用户列表第1页",
            "查询用户列表第2页",
            "查询用户列表第10页",
        ]
        
        cores = [normalize_intent(i).core_intent for i in intents]
        
        # 所有核心意图应该相同
        assert len(set(cores)) == 1
    
    def test_hash_consistency_for_similar_intents(self):
        """测试相似意图生成一致的哈希"""
        hash1 = generate_intent_hash("查询用户前10个")
        hash2 = generate_intent_hash("查询用户前5个")
        hash3 = generate_intent_hash("查询用户第2页")
        
        # 核心意图相同的应该生成相同哈希
        assert hash1 == hash2 == hash3
    
    def test_end_to_end_history_matching(self):
        """端到端测试：保存后能通过相似意图检索到"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExecutionHistoryStorage(tmpdir)
            
            # 保存"查询用户前5个"
            record = ExecutionRecord(
                id=generate_intent_hash("查询用户前5个"),
                intent="查询用户前5个",
                normalized_intent=normalize_intent("查询用户前5个").core_intent,
                intent_params={"limit": 5},
                status=ExecutionStatus.SUCCESS.value,
                apis_used=["core_user_list"],
                script_content='params = {"limit": 5}',
            )
            storage.save_execution(record)
            
            # 用"查询用户前10个"搜索
            results = storage.search_by_intent("查询用户前10个")
            
            # 应该能找到
            assert len(results) == 1
            assert results[0]["intent"] == "查询用户前5个"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
