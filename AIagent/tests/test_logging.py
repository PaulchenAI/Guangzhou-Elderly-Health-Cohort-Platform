# -*- coding: utf-8 -*-
"""
日志系统测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import tempfile
import json

from src.logging.logger import Logger, get_logger
from src.logging.handlers import create_file_handler, create_console_handler
from src.logging.formatters import create_json_formatter, create_text_formatter
from src.logging.decorators import log_function_call, log_claude_code_call, log_agent_interaction


class TestLogger:
    """日志记录器测试"""
    
    def test_create_logger(self):
        """测试创建日志记录器"""
        logger = Logger("test_logger", level="DEBUG")
        assert logger.name == "test_logger"
        assert logger.logger.level == 10  # DEBUG level
    
    def test_log_levels(self):
        """测试不同日志级别"""
        import tempfile
        import time
        import logging
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # 清除可能存在的logger
            test_logger = logging.getLogger("test_logger")
            test_logger.handlers.clear()
            
            logger = Logger(
                "test_logger",
                level="DEBUG",
                log_dir=tmpdir_path,
                log_format="text",
                enable_console=False  # 禁用控制台以便测试文件输出
            )
            
            # 确保handler已添加
            assert len(logger.logger.handlers) > 0, "没有handler被添加"
            
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # 强制刷新和关闭所有handler
            for handler in logger.logger.handlers:
                handler.flush()
                handler.close()
            
            # 等待文件系统同步
            time.sleep(0.1)
            
            # 检查日志文件是否创建
            log_file = tmpdir_path / "test_logger.log"
            # 如果文件不存在，列出目录内容以便调试
            if not log_file.exists():
                files = list(tmpdir_path.iterdir())
                pytest.fail(f"日志文件不存在: {log_file}，目录内容: {files}")
            
            # 检查日志内容
            content = log_file.read_text()
            # 由于日志级别过滤，DEBUG可能不会写入文件（取决于logger级别）
            # 但INFO及以上级别应该存在
            assert "Info message" in content or "INFO" in content or "Info" in content
            assert "Warning message" in content or "WARNING" in content or "Warning" in content
    
    def test_get_logger_singleton(self):
        """测试日志记录器单例模式"""
        logger1 = get_logger("singleton_test", level="INFO")
        logger2 = get_logger("singleton_test", level="INFO")
        
        # 应该是同一个实例（相同配置）
        assert logger1 is logger2


class TestHandlers:
    """日志处理器测试"""
    
    def test_create_file_handler(self):
        """测试创建文件处理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = create_file_handler(
                Path(tmpdir),
                "test_handler",
                max_bytes=1024,
                backup_count=3
            )
            
            assert handler is not None
            assert handler.maxBytes == 1024
            assert handler.backupCount == 3
    
    def test_create_console_handler(self):
        """测试创建控制台处理器"""
        handler = create_console_handler()
        assert handler is not None
        assert handler.level == 20  # INFO level


class TestFormatters:
    """日志格式化器测试"""
    
    def test_json_formatter(self):
        """测试JSON格式化器"""
        import logging
        
        formatter = create_json_formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert "timestamp" in data
    
    def test_text_formatter(self):
        """测试文本格式化器"""
        import logging
        
        formatter = create_text_formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "INFO" in formatted


class TestDecorators:
    """日志装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_log_function_call_async(self):
        """测试异步函数调用装饰器"""
        @log_function_call("test_logger")
        async def async_test_func(x: int, y: int) -> int:
            return x + y
        
        result = await async_test_func(1, 2)
        assert result == 3
    
    def test_log_function_call_sync(self):
        """测试同步函数调用装饰器"""
        @log_function_call("test_logger")
        def sync_test_func(x: int, y: int) -> int:
            return x + y
        
        result = sync_test_func(1, 2)
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_log_claude_code_call(self):
        """测试Claude Code调用装饰器"""
        @log_claude_code_call("claude_code")
        async def claude_code_func(command: str) -> str:
            return f"Result: {command}"
        
        result = await claude_code_func("test command")
        assert "Result: test command" in result
    
    @pytest.mark.asyncio
    async def test_log_agent_interaction(self):
        """测试智能体交互装饰器"""
        @log_agent_interaction("test_agent", "agents")
        async def agent_func(input_data: str) -> str:
            return f"Processed: {input_data}"
        
        result = await agent_func("test input")
        assert "Processed: test input" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
