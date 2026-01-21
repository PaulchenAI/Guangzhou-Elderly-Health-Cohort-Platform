# -*- coding: utf-8 -*-
"""
日志格式化器
提供JSON和文本两种日志格式
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON格式
        
        Args:
            record: 日志记录
            
        Returns:
            JSON字符串
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段（从extra参数传入）
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """文本格式日志格式化器"""
    
    def __init__(self):
        fmt = "%(asctime)s [%(levelname)8s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        # 将 extra 字段以 JSON 形式附加到文本日志，便于排障
        extras: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ]:
                extras[key] = value
        if extras:
            return f"{base} | extra={json.dumps(extras, ensure_ascii=False)}"
        return base


def create_json_formatter() -> JSONFormatter:
    """创建JSON格式化器"""
    return JSONFormatter()


def create_text_formatter() -> TextFormatter:
    """创建文本格式化器"""
    return TextFormatter()
