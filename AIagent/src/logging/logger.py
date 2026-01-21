# -*- coding: utf-8 -*-
"""
核心日志记录器
提供统一的日志接口，支持文件和控制台输出
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from .handlers import create_file_handler, create_console_handler
from .formatters import create_json_formatter, create_text_formatter


class Logger:
    """日志记录器"""
    
    _loggers: dict = {}
    
    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        log_format: str = "json",
        enable_console: bool = True,
        enable_file: bool = True
    ):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别
            log_dir: 日志目录
            log_format: 日志格式（json/text）
            enable_console: 是否启用控制台输出
            enable_file: 是否启用文件输出
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        # 避免重复输出：不向 root logger 传播
        self.logger.propagate = False
        
        # 避免重复添加handler（但允许在测试时重新配置）
        # 如果logger已经有handlers且不是测试模式，则跳过
        if self.logger.handlers and not hasattr(self, '_allow_reinit'):
            return
        
        # 创建formatter
        if log_format == "json":
            formatter = create_json_formatter()
        else:
            formatter = create_text_formatter()
        
        # 添加控制台handler
        if enable_console:
            console_handler = create_console_handler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件handler
        if enable_file and log_dir:
            file_handler = create_file_handler(log_dir, name)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)  # 文件handler使用DEBUG级别以记录所有日志
            self.logger.addHandler(file_handler)
    
    def _split_reserved_kwargs(self, kwargs: dict) -> tuple[dict, dict]:
        """
        将 logging 关键参数从 extra 中剥离，避免覆盖 LogRecord 保留字段。
        """
        reserved = {}
        for key in ("exc_info", "stack_info", "stacklevel"):
            if key in kwargs:
                reserved[key] = kwargs.pop(key)
        return reserved, kwargs

    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.debug(message, extra=extra, **reserved)
    
    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.info(message, extra=extra, **reserved)
    
    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.warning(message, extra=extra, **reserved)
    
    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.error(message, extra=extra, **reserved)
    
    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.critical(message, extra=extra, **reserved)
    
    def exception(self, message: str, **kwargs):
        """记录异常信息"""
        reserved, extra = self._split_reserved_kwargs(kwargs)
        self.logger.exception(message, extra=extra, **reserved)
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        log_format: str = "json",
        enable_console: bool = True,
        enable_file: bool = True
    ) -> 'Logger':
        """
        获取或创建日志记录器（单例模式）
        
        Args:
            name: 日志记录器名称
            level: 日志级别
            log_dir: 日志目录
            log_format: 日志格式
            enable_console: 是否启用控制台
            enable_file: 是否启用文件
            
        Returns:
            Logger实例
        """
        key = f"{name}_{level}_{log_format}"
        if key not in cls._loggers:
            cls._loggers[key] = cls(
                name=name,
                level=level,
                log_dir=log_dir,
                log_format=log_format,
                enable_console=enable_console,
                enable_file=enable_file
            )
        return cls._loggers[key]


def get_logger(name: str = "aiagent", **kwargs) -> Logger:
    """
    获取日志记录器（便捷函数）
    
    Args:
        name: 日志记录器名称
        **kwargs: 其他参数（level, log_dir, log_format等）
        
    Returns:
        Logger实例
    """
    return Logger.get_logger(name=name, **kwargs)
