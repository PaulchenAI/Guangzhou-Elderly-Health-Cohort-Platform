# -*- coding: utf-8 -*-
"""
Claude Code CLI 命令执行器
负责异步执行Claude Code CLI命令，控制并发和超时
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any
from .models import ExecutionResult
from ..logging.decorators import log_claude_code_call
from ..logging.logger import get_logger


class ClaudeCodeExecutor:
    """Claude Code CLI 命令执行器"""
    
    def __init__(
        self,
        claude_path: str,
        working_dir: str,
        timeout: int = 300,
        max_concurrent: int = 2
    ):
        """
        初始化执行器
        
        Args:
            claude_path: Claude Code CLI路径
            working_dir: 工作目录
            timeout: 执行超时时间（秒）
            max_concurrent: 最大并发数
        """
        self.claude_path = Path(claude_path)
        self.working_dir = Path(working_dir)
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = get_logger("claude_code")
        
        # 验证CLI路径
        if not self.claude_path.exists():
            raise FileNotFoundError(f"Claude Code CLI不存在: {self.claude_path}")
        
        # 确保工作目录存在
        self.working_dir.mkdir(parents=True, exist_ok=True)
    
    @log_claude_code_call("claude_code")
    async def execute(
        self,
        prompt: str,
        command: Optional[str] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        执行Claude Code命令
        
        Args:
            prompt: 要执行的提示词/命令
            command: 可选的具体命令（用于日志）
            **kwargs: 其他参数
            
        Returns:
            ExecutionResult执行结果
        """
        async with self.semaphore:  # 并发控制
            start_time = time.time()
            
            try:
                # 构建命令
                cmd = [
                    str(self.claude_path),
                    '--print',  # 非交互模式
                    '--output-format', 'json',
                ]
                
                # 添加额外参数
                if 'args' in kwargs:
                    cmd.extend(kwargs['args'])
                
                self.logger.debug(
                    f"执行Claude Code命令",
                    command=command or prompt[:100],
                    working_dir=str(self.working_dir)
                )
                
                # 创建子进程
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.working_dir)
                )
                
                # 执行并等待结果（带超时）
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(input=prompt.encode('utf-8')),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    # 超时，终止进程
                    process.kill()
                    await process.wait()
                    elapsed = time.time() - start_time
                    
                    self.logger.error(
                        f"Claude Code执行超时",
                        timeout=self.timeout,
                        elapsed_time=elapsed
                    )
                    
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=f"执行超时（{self.timeout}秒）",
                        return_code=-1,
                        execution_time=elapsed
                    )
                
                elapsed = time.time() - start_time
                
                # 解码输出
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                
                success = process.returncode == 0
                
                if success:
                    self.logger.debug(
                        f"Claude Code执行成功",
                        return_code=process.returncode,
                        elapsed_time=elapsed,
                        stdout_length=len(stdout)
                    )
                else:
                    self.logger.warning(
                        f"Claude Code执行失败",
                        return_code=process.returncode,
                        stderr=stderr[:500]
                    )
                
                return ExecutionResult(
                    success=success,
                    stdout=stdout,
                    stderr=stderr,
                    return_code=process.returncode,
                    execution_time=elapsed
                )
                
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.exception(
                    f"Claude Code执行异常",
                    error=str(e),
                    elapsed_time=elapsed
                )
                
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"执行异常: {str(e)}",
                    return_code=-1,
                    execution_time=elapsed
                )
