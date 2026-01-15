# -*- coding: utf-8 -*-
"""
日志追踪装饰器
用于追踪函数调用、Claude Code CLI调用、智能体交互等
"""

import time
import functools
from typing import Callable, Any
from .logger import get_logger


def log_function_call(logger_name: str = "aiagent"):
    """
    函数调用追踪装饰器
    
    Args:
        logger_name: 日志记录器名称
        
    Usage:
        @log_function_call("claude_code")
        async def read_file(path: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            func_name = f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            logger.info(
                f"调用函数: {func_name}",
                function=func_name,
                func_args=str(args)[:200],  # 使用func_args避免与LogRecord.args冲突
                func_kwargs=str(kwargs)[:200],
                action="function_call_start"
            )
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    f"函数执行成功: {func_name}",
                    function=func_name,
                    elapsed_time=elapsed,
                    action="function_call_success"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"函数执行失败: {func_name}",
                    function=func_name,
                    error=str(e),
                    elapsed_time=elapsed,
                    action="function_call_error"
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            func_name = f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            logger.info(
                f"调用函数: {func_name}",
                function=func_name,
                func_args=str(args)[:200],  # 使用func_args避免与LogRecord.args冲突
                func_kwargs=str(kwargs)[:200],
                action="function_call_start"
            )
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    f"函数执行成功: {func_name}",
                    function=func_name,
                    elapsed_time=elapsed,
                    action="function_call_success"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"函数执行失败: {func_name}",
                    function=func_name,
                    error=str(e),
                    elapsed_time=elapsed,
                    action="function_call_error"
                )
                raise
        
        # 判断是否为协程函数
        if hasattr(func, '__code__') and 'async' in str(func.__code__.co_flags):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_claude_code_call(logger_name: str = "claude_code"):
    """
    Claude Code CLI调用追踪装饰器
    
    Args:
        logger_name: 日志记录器名称
        
    Usage:
        @log_claude_code_call()
        async def execute_command(prompt: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            
            # 提取命令信息
            command = kwargs.get('command', '') or (args[0] if args else '')
            
            start_time = time.time()
            logger.info(
                "Claude Code CLI调用开始",
                command=command[:500],  # 限制长度
                action="claude_code_call_start"
            )
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    "Claude Code CLI调用成功",
                    command=command[:500],
                    elapsed_time=elapsed,
                    result_size=len(str(result)),
                    action="claude_code_call_success"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    "Claude Code CLI调用失败",
                    command=command[:500],
                    error=str(e),
                    elapsed_time=elapsed,
                    action="claude_code_call_error"
                )
                raise
        
        return wrapper
    
    return decorator


def log_agent_interaction(agent_name: str, logger_name: str = "agents"):
    """
    智能体交互追踪装饰器
    
    Args:
        agent_name: 智能体名称
        logger_name: 日志记录器名称
        
    Usage:
        @log_agent_interaction("orchestrator")
        async def process_request(request: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            
            # 提取输入信息
            input_data = kwargs.get('input', '') or (args[0] if args else '')
            
            start_time = time.time()
            logger.info(
                f"智能体交互开始: {agent_name}",
                agent=agent_name,
                input=str(input_data)[:500],
                action="agent_interaction_start"
            )
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    f"智能体交互成功: {agent_name}",
                    agent=agent_name,
                    elapsed_time=elapsed,
                    output_size=len(str(result)),
                    action="agent_interaction_success"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"智能体交互失败: {agent_name}",
                    agent=agent_name,
                    error=str(e),
                    elapsed_time=elapsed,
                    action="agent_interaction_error"
                )
                raise
        
        return wrapper
    
    return decorator
