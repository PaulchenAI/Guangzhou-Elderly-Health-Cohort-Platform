# -*- coding: utf-8 -*-
"""
Claude Code CLI 会话管理
管理会话上下文和工作目录
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from .client import ClaudeCodeClient
from ..logging.logger import get_logger


class ClaudeCodeSession:
    """Claude Code CLI 会话管理器"""
    
    def __init__(self, client: ClaudeCodeClient, session_id: Optional[str] = None):
        """
        初始化会话
        
        Args:
            client: Claude Code客户端
            session_id: 会话ID（可选）
        """
        self.client = client
        self.session_id = session_id or f"session_{id(self)}"
        self.context: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.current_dir: Path = client.executor.working_dir
        self.logger = get_logger("claude_code")
    
    def set_context(self, key: str, value: Any):
        """
        设置会话上下文
        
        Args:
            key: 上下文键
            value: 上下文值
        """
        self.context[key] = value
        self.logger.debug(f"设置上下文: {key}")
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        获取会话上下文
        
        Args:
            key: 上下文键
            default: 默认值
            
        Returns:
            上下文值
        """
        return self.context.get(key, default)
    
    def clear_context(self):
        """清除所有上下文"""
        self.context.clear()
        self.logger.debug("清除上下文")
    
    def change_directory(self, path: str) -> bool:
        """
        切换工作目录
        
        Args:
            path: 目标目录路径
            
        Returns:
            是否成功
        """
        new_dir = Path(path)
        if not new_dir.is_absolute():
            new_dir = self.current_dir / new_dir
        
        if not new_dir.exists() or not new_dir.is_dir():
            self.logger.warning(f"目录不存在或不是目录: {new_dir}")
            return False
        
        self.current_dir = new_dir
        self.logger.debug(f"切换工作目录: {new_dir}")
        return True
    
    def get_current_directory(self) -> Path:
        """
        获取当前工作目录
        
        Returns:
            当前工作目录路径
        """
        return self.current_dir
    
    def add_to_history(self, action: str, result: Any):
        """
        添加到历史记录
        
        Args:
            action: 操作名称
            result: 操作结果
        """
        self.history.append({
            'action': action,
            'result': str(result)[:500],  # 限制长度
            'timestamp': self._get_timestamp()
        })
        
        # 限制历史记录长度
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            limit: 返回的记录数限制
            
        Returns:
            历史记录列表
        """
        return self.history[-limit:]
    
    def clear_history(self):
        """清除历史记录"""
        self.history.clear()
        self.logger.debug("清除历史记录")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        获取会话摘要
        
        Returns:
            会话摘要字典
        """
        return {
            'session_id': self.session_id,
            'current_dir': str(self.current_dir),
            'context_keys': list(self.context.keys()),
            'history_count': len(self.history)
        }
    
    @staticmethod
    def _get_timestamp() -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
