# -*- coding: utf-8 -*-
"""
Claude Code CLI 封装测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.claude_code.models import (
    ExecutionResult, FileInfo, GrepResult, AnalysisResult
)
from src.claude_code.executor import ClaudeCodeExecutor
from src.claude_code.parser import ClaudeCodeParser
from src.claude_code.client import ClaudeCodeClient
from src.claude_code.session import ClaudeCodeSession
from src.claude_code.tools import create_claude_code_tools
from src.utils.config_models import ClaudeCodeConfig


class TestExecutionResult:
    """ExecutionResult测试"""
    
    def test_execution_result_success(self):
        """测试成功结果"""
        result = ExecutionResult(
            success=True,
            stdout="test output",
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        assert result.success is True
        assert result.error is None
    
    def test_execution_result_error(self):
        """测试错误结果"""
        result = ExecutionResult(
            success=False,
            stdout="",
            stderr="test error",
            return_code=1,
            execution_time=0.5
        )
        assert result.success is False
        assert result.error == "test error"


class TestClaudeCodeParser:
    """Claude Code解析器测试"""
    
    def test_parse_json_success(self):
        """测试JSON解析成功"""
        result = ExecutionResult(
            success=True,
            stdout='{"key": "value"}',
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        
        data = ClaudeCodeParser.parse_json(result)
        assert data is not None
        assert data['key'] == 'value'
    
    def test_parse_json_failure(self):
        """测试JSON解析失败"""
        result = ExecutionResult(
            success=True,
            stdout="not json",
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        
        data = ClaudeCodeParser.parse_json(result)
        assert data is None
    
    def test_parse_error(self):
        """测试错误信息提取"""
        result = ExecutionResult(
            success=False,
            stdout="",
            stderr="error message",
            return_code=1,
            execution_time=0.5
        )
        
        error = ClaudeCodeParser.parse_error(result)
        assert error == "error message"
    
    def test_parse_file_list(self):
        """测试文件列表解析"""
        result = ExecutionResult(
            success=True,
            stdout='{"files": ["file1.py", "file2.py"]}',
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        
        files = ClaudeCodeParser.parse_file_list(result)
        assert len(files) == 2
        assert "file1.py" in files

    def test_parse_grep_results_json(self):
        """测试grep结果JSON解析"""
        result = ExecutionResult(
            success=True,
            stdout='{"results":[{"file":"a.py","line":2,"content":"xx","match":"x"}]}',
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        rs = ClaudeCodeParser.parse_grep_results(result)
        assert len(rs) == 1
        assert rs[0].file_path == "a.py"
        assert rs[0].line_number == 2

    def test_parse_grep_results_fallback(self):
        """测试grep结果fallback解析"""
        result = ExecutionResult(
            success=True,
            stdout="a.py:10:hello",
            stderr="",
            return_code=0,
            execution_time=1.0
        )
        rs = ClaudeCodeParser.parse_grep_results(result)
        assert len(rs) == 1
        assert rs[0].line_number == 10


class TestClaudeCodeExecutor:
    """Claude Code执行器测试"""
    
    def test_executor_init(self, tmp_path, monkeypatch):
        """测试执行器初始化"""
        # 创建模拟的Claude Code CLI
        claude_path = tmp_path / "claude"
        claude_path.touch()
        claude_path.chmod(0o755)
        
        executor = ClaudeCodeExecutor(
            claude_path=str(claude_path),
            working_dir=str(tmp_path),
            timeout=300,
            max_concurrent=2
        )
        
        assert executor.claude_path == claude_path
        assert executor.timeout == 300
        assert executor.max_concurrent == 2
    
    def test_executor_init_file_not_found(self, tmp_path):
        """测试CLI文件不存在"""
        with pytest.raises(FileNotFoundError):
            ClaudeCodeExecutor(
                claude_path=str(tmp_path / "nonexistent"),
                working_dir=str(tmp_path),
                timeout=300,
                max_concurrent=2
            )

    @pytest.mark.asyncio
    async def test_execute_success(self, tmp_path, monkeypatch):
        """测试执行器 execute 成功路径（mock subprocess）"""
        claude_path = tmp_path / "claude"
        claude_path.touch()
        claude_path.chmod(0o755)

        executor = ClaudeCodeExecutor(
            claude_path=str(claude_path),
            working_dir=str(tmp_path),
            timeout=1,
            max_concurrent=1,
        )

        mock_proc = Mock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b'{"ok":true}', b""))

        async def fake_create(*args, **kwargs):
            return mock_proc

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

        result = await executor.execute("ping", command="test")
        assert result.success is True
        assert "ok" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_timeout(self, tmp_path, monkeypatch):
        """测试执行器超时路径"""
        claude_path = tmp_path / "claude"
        claude_path.touch()
        claude_path.chmod(0o755)

        executor = ClaudeCodeExecutor(
            claude_path=str(claude_path),
            working_dir=str(tmp_path),
            timeout=0,  # 触发超时逻辑（wait_for 会被 mock）
            max_concurrent=1,
        )

        mock_proc = Mock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock()
        mock_proc.kill = Mock()
        mock_proc.wait = AsyncMock(return_value=1)

        async def fake_create(*args, **kwargs):
            return mock_proc

        async def fake_wait_for(*args, **kwargs):
            raise asyncio.TimeoutError()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
        monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

        result = await executor.execute("ping", command="test_timeout")
        assert result.success is False
        assert "超时" in result.stderr


class TestClaudeCodeClient:
    """Claude Code客户端测试"""
    
    @pytest.fixture
    def config(self, tmp_path):
        """创建测试配置"""
        claude_path = tmp_path / "claude"
        claude_path.touch()
        claude_path.chmod(0o755)
        
        return ClaudeCodeConfig(
            path=str(claude_path),
            timeout=300,
            max_concurrent=2,
            working_dir=str(tmp_path)
        )
    
    def test_client_init(self, config):
        """测试客户端初始化"""
        client = ClaudeCodeClient(config)
        assert client.config == config
        assert client.executor is not None
        assert client.parser is not None
    
    @pytest.mark.asyncio
    async def test_read_file_not_found(self, config):
        """测试读取不存在的文件"""
        client = ClaudeCodeClient(config)
        
        with pytest.raises(FileNotFoundError):
            await client.read_file("nonexistent.py")

    @pytest.mark.asyncio
    async def test_read_file_success_json(self, config, tmp_path):
        """测试读取文件成功（JSON content）"""
        client = ClaudeCodeClient(config)
        fp = tmp_path / "a.py"
        fp.write_text("print('x')", encoding="utf-8")

        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"content":"hello"}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))

        content = await client.read_file(str(fp))
        assert content == "hello"

    @pytest.mark.asyncio
    async def test_write_file_success_when_file_exists(self, config, tmp_path):
        """测试写入文件成功（通过exists校验）"""
        client = ClaudeCodeClient(config)
        fp = tmp_path / "b.txt"
        fp.write_text("old", encoding="utf-8")  # 预先存在，write_file 成功后会检查 exists

        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"ok":true}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))

        ok = await client.write_file(str(fp), "new")
        assert ok is True

    @pytest.mark.asyncio
    async def test_edit_file_success(self, config, tmp_path):
        """测试编辑文件成功"""
        client = ClaudeCodeClient(config)
        fp = tmp_path / "c.txt"
        fp.write_text("old", encoding="utf-8")

        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"ok":true}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))

        ok = await client.edit_file(str(fp), "old", "new")
        assert ok is True

    @pytest.mark.asyncio
    async def test_search_files_success(self, config):
        """测试 search_files 解析 file_list"""
        client = ClaudeCodeClient(config)
        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"files":["a.py","b.py"]}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))
        files = await client.search_files("*.py", ".")
        assert files == ["a.py", "b.py"]

    @pytest.mark.asyncio
    async def test_grep_success(self, config):
        """测试 grep 解析结果"""
        client = ClaudeCodeClient(config)
        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"results":[{"file":"a.py","line":1,"content":"x","match":"x"}]}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))
        results = await client.grep("x", ".")
        assert len(results) == 1
        assert results[0].file_path == "a.py"

    @pytest.mark.asyncio
    async def test_list_dir_success_json(self, config):
        """测试 list_dir JSON items 解析"""
        client = ClaudeCodeClient(config)
        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"items":[{"path":"a.py","name":"a.py","type":"file","size":1}]}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))
        items = await client.list_dir(".")
        assert len(items) == 1
        assert items[0].is_file is True

    @pytest.mark.asyncio
    async def test_analyze_code_success_json(self, config, tmp_path):
        """测试 analyze_code JSON 解析"""
        client = ClaudeCodeClient(config)
        fp = tmp_path / "d.py"
        fp.write_text("print('x')", encoding="utf-8")

        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"summary":"ok","findings":[],"suggestions":["a"],"complexity_score":1.0}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))
        res = await client.analyze_code(str(fp), "what?")
        assert res.summary == "ok"

    @pytest.mark.asyncio
    async def test_generate_code_success_json(self, config):
        """测试 generate_code JSON code 解析"""
        client = ClaudeCodeClient(config)
        client.executor.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            stdout='{"code":"print(1)"}',
            stderr="",
            return_code=0,
            execution_time=0.01
        ))
        code = await client.generate_code("x")
        assert "print" in code


class TestClaudeCodeTools:
    """LangChain Tools 封装测试"""

    @pytest.mark.asyncio
    async def test_tools_ainvoke(self, tmp_path):
        # 创建一个可用的客户端（executor 会验证 cli 文件存在）
        claude_path = tmp_path / "claude"
        claude_path.touch()
        claude_path.chmod(0o755)
        cfg = ClaudeCodeConfig(path=str(claude_path), timeout=300, max_concurrent=2, working_dir=str(tmp_path))
        client = ClaudeCodeClient(cfg)

        # mock 客户端方法，避免真正执行
        client.read_file = AsyncMock(return_value="hello")
        client.write_file = AsyncMock(return_value=True)
        client.list_dir = AsyncMock(return_value=[])

        tools = create_claude_code_tools(client)
        by_name = {t.name: t for t in tools}

        assert await by_name["read_file"].ainvoke({"path": "a.py"}) == "hello"
        assert await by_name["write_file"].ainvoke({"path": "b.py", "content": "x"}) is True
        assert await by_name["list_dir"].ainvoke({"path": "."}) == []


class TestClaudeCodeSession:
    """Claude Code会话测试"""
    
    @pytest.fixture
    def mock_client(self, tmp_path):
        """创建模拟客户端"""
        mock = Mock(spec=ClaudeCodeClient)
        mock.executor = Mock()
        mock.executor.working_dir = tmp_path
        return mock
    
    def test_session_init(self, mock_client):
        """测试会话初始化"""
        session = ClaudeCodeSession(mock_client, "test_session")
        assert session.session_id == "test_session"
        assert session.client == mock_client
        assert len(session.context) == 0
        assert len(session.history) == 0
    
    def test_session_context(self, mock_client):
        """测试会话上下文"""
        session = ClaudeCodeSession(mock_client)
        
        session.set_context("key1", "value1")
        assert session.get_context("key1") == "value1"
        assert session.get_context("key2", "default") == "default"
        
        session.clear_context()
        assert len(session.context) == 0
    
    def test_session_history(self, mock_client):
        """测试会话历史"""
        session = ClaudeCodeSession(mock_client)
        
        session.add_to_history("action1", "result1")
        session.add_to_history("action2", "result2")
        
        history = session.get_history()
        assert len(history) == 2
        assert history[-1]['action'] == "action2"
        
        session.clear_history()
        assert len(session.history) == 0
    
    def test_change_directory(self, mock_client, tmp_path):
        """测试切换目录"""
        session = ClaudeCodeSession(mock_client)
        session.current_dir = tmp_path
        
        new_dir = tmp_path / "subdir"
        new_dir.mkdir()
        
        assert session.change_directory(str(new_dir)) is True
        assert session.get_current_directory() == new_dir
        
        assert session.change_directory("nonexistent") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
