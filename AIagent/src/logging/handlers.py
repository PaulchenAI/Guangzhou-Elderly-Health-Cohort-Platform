# -*- coding: utf-8 -*-
"""
日志处理器
提供文件和控制台日志处理器
"""

import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def create_file_handler(
    log_dir: Path,
    logger_name: str,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> RotatingFileHandler:
    """
    创建文件日志处理器（支持日志轮转）
    
    Args:
        log_dir: 日志目录
        logger_name: 日志记录器名称
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 备份文件数量
        
    Returns:
        RotatingFileHandler实例
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"{logger_name}.log"
    
    # 确保文件存在（即使为空）
    if not log_file.exists():
        log_file.touch()
    
    handler = RotatingFileHandler(
        str(log_file),  # 使用字符串路径
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    handler.setLevel(logging.DEBUG)
    return handler


def create_console_handler() -> logging.StreamHandler:
    """
    创建控制台日志处理器
    
    Returns:
        StreamHandler实例
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    return handler
