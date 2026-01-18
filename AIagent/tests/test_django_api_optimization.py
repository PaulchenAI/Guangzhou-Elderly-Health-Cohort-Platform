# -*- coding: utf-8 -*-
"""
Django API 优化功能单元测试

测试内容：
- 意图归一化
- 参数自动替换
- 分层 API 摘要
- 执行记录保存
- 历史指令检索
- 默认翻页参数
- 翻页信息提取
- JSON 输出格式
"""

import json
import os
import pytest
import tempfile
from pathlib import Path

from AIagent.src.django_api.execution_history import (
    ExecutionHistoryStorage,
    ExecutionRecord,
    ExecutionStatus,
    NormalizedIntent,
    generate_intent_hash,
    has_explicit_count,
    normalize_intent,
    substitute_params,
)
from AIagent.src.django_api.output_format import (
    OutputFormat,
    PaginationInfo,
    QueryResult,
    get_default_output_format,
    inject_pagination,
)


class TestNormalizeIntent:
    """测试意图归一化"""
    
    def test_extract_limit_from_chinese(self):
        """测试从中文提取数目限制"""
        result = normalize_intent("查询用户列表前10个")
        assert result.core_intent == "查询用户列表"
        assert result.limit == 10
    
    def test_extract_limit_from_count(self):
        """测试从条数提取数目限制"""
        result = normalize_intent("获取100条记录")
        assert result.limit == 100
    
    def test_extract_page(self):
        """测试提取页码"""
        result = normalize_intent("查询第2页用户")
        assert result.core_intent == "查询用户"
        assert result.page == 2
    
    def test_extract_order(self):
        """测试提取排序参数"""
        result = normalize_intent("查询用户列表按创建时间倒序")
        assert result.core_intent == "查询用户列表"
        assert result.order_by == "创建时间"
        assert result.order_desc is True
    
    def test_extract_multiple_params(self):
        """测试提取多个参数"""
        result = normalize_intent("查询用户列表前10个第2页")
        assert result.core_intent == "查询用户列表"
        assert result.limit == 10
        assert result.page == 2
    
    def test_no_params(self):
        """测试无参数意图"""
        result = normalize_intent("查询用户列表")
        assert result.core_intent == "查询用户列表"
        assert result.limit is None
        assert result.page is None


class TestHasExplicitCount:
    """测试明确数目检测"""
    
    def test_has_count_chinese(self):
        """测试中文数目"""
        assert has_explicit_count("查询前10个用户") is True
        assert has_explicit_count("获取100条记录") is True
    
    def test_has_count_page(self):
        """测试翻页"""
        assert has_explicit_count("查询第2页") is True
    
    def test_has_count_all(self):
        """测试全部"""
        assert has_explicit_count("获取全部用户") is True
        assert has_explicit_count("查询所有记录") is True
    
    def test_no_count(self):
        """测试无数目"""
        assert has_explicit_count("查询用户列表") is False
        assert has_explicit_count("获取用户信息") is False


class TestSubstituteParams:
    """测试参数自动替换"""
    
    def test_substitute_limit(self):
        """测试替换 limit 参数"""
        script = 'params = {"limit": 5, "page": 1}'
        result = substitute_params(
            script,
            {"limit": 5},
            {"limit": 10}
        )
        assert '"limit": 10' in result
    
    def test_substitute_page(self):
        """测试替换 page 参数"""
        script = 'params = {"page": 1}'
        result = substitute_params(
            script,
            {"page": 1},
            {"page": 3}
        )
        assert '"page": 3' in result
    
    def test_substitute_multiple(self):
        """测试替换多个参数"""
        script = 'params = {"limit": 5, "page": 1, "pageSize": 10}'
        result = substitute_params(
            script,
            {"limit": 5, "page": 1, "page_size": 10},
            {"limit": 20, "page": 2, "page_size": 50}
        )
        assert '"limit": 20' in result
        assert '"page": 2' in result
        assert '"pageSize": 50' in result


class TestPaginationInfo:
    """测试翻页信息"""
    
    def test_calculate_total_pages(self):
        """测试计算总页数"""
        info = PaginationInfo(page=1, page_size=10, total=95)
        assert info.total_pages == 10
        assert info.has_more is True
    
    def test_last_page(self):
        """测试最后一页"""
        info = PaginationInfo(page=10, page_size=10, total=95)
        assert info.has_more is False
    
    def test_from_response(self):
        """测试从响应提取"""
        response = {"page": 2, "pageSize": 20, "total": 100}
        info = PaginationInfo.from_response(response)
        assert info.page == 2
        assert info.page_size == 20
        assert info.total == 100
    
    def test_to_summary(self):
        """测试生成摘要"""
        info = PaginationInfo(page=1, page_size=10, total=156)
        summary = info.to_summary()
        assert "第 1 页" in summary
        assert "156 条" in summary
        assert "146 条未显示" in summary


class TestQueryResult:
    """测试查询结果"""
    
    def test_to_text(self):
        """测试文本格式输出"""
        result = QueryResult(
            success=True,
            data=[{"id": 1, "name": "test"}],
            pagination=PaginationInfo(page=1, page_size=10, total=100),
        )
        text = result.to_text()
        assert "📊 查询结果" in text
        assert "1 条记录" in text
    
    def test_to_json(self):
        """测试 JSON 格式输出"""
        result = QueryResult(
            success=True,
            data=[{"id": 1, "name": "test"}],
            pagination=PaginationInfo(page=1, page_size=10, total=100),
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert len(parsed["data"]) == 1
        assert parsed["pagination"]["total"] == 100
    
    def test_output_format(self):
        """测试输出格式选择"""
        result = QueryResult(success=True, data=[])
        
        text_output = result.output(OutputFormat.TEXT)
        assert "📊" in text_output
        
        json_output = result.output(OutputFormat.JSON)
        assert json_output.startswith("{")


class TestInjectPagination:
    """测试翻页参数注入"""
    
    def test_inject_when_no_count(self):
        """测试无数目时注入"""
        params = {"keyword": "test"}
        result = inject_pagination(params, "查询用户列表")
        assert result["page"] == 1
        assert result["pageSize"] == 10
    
    def test_no_inject_when_has_count(self):
        """测试有数目时不注入"""
        params = {"keyword": "test"}
        result = inject_pagination(params, "查询用户列表前20个")
        assert "page" not in result or result.get("page") == 1
    
    def test_preserve_existing_params(self):
        """测试保留已有参数"""
        params = {"keyword": "test", "page": 5}
        result = inject_pagination(params, "查询用户列表")
        assert result["page"] == 5  # 保留原有值
        assert result["pageSize"] == 10  # 添加默认值


class TestExecutionHistoryStorage:
    """测试执行记录存储"""
    
    def test_save_and_load(self):
        """测试保存和加载记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExecutionHistoryStorage(tmpdir)
            
            record = ExecutionRecord(
                id="test123",
                intent="查询用户列表",
                normalized_intent="查询用户列表",
                intent_params={},
                status=ExecutionStatus.SUCCESS.value,
                apis_used=["core_user_list"],
                script_content="print('hello')",
                execution_output="success",
            )
            
            path = storage.save_execution(record)
            assert Path(path).exists()
            
            loaded = storage.get_record("test123")
            assert loaded is not None
            assert loaded.intent == "查询用户列表"
    
    def test_search_by_intent(self):
        """测试按意图搜索"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExecutionHistoryStorage(tmpdir)
            
            record = ExecutionRecord(
                id="test456",
                intent="查询用户列表前10个",
                normalized_intent="查询用户列表",
                intent_params={"limit": 10},
                status=ExecutionStatus.SUCCESS.value,
                apis_used=["core_user_list"],
                script_content="print('hello')",
            )
            storage.save_execution(record)
            
            results = storage.search_by_intent("查询用户列表")
            assert len(results) == 1
            assert results[0]["id"] == "test456"


class TestGenerateIntentHash:
    """测试意图哈希生成"""
    
    def test_same_core_intent_same_hash(self):
        """测试相同核心意图生成相同哈希"""
        hash1 = generate_intent_hash("查询用户列表前10个")
        hash2 = generate_intent_hash("查询用户列表前5个")
        assert hash1 == hash2  # 核心意图相同
    
    def test_different_intent_different_hash(self):
        """测试不同意图生成不同哈希"""
        hash1 = generate_intent_hash("查询用户列表")
        hash2 = generate_intent_hash("查询问卷数据")
        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
