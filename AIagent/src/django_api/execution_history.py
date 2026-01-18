# -*- coding: utf-8 -*-
"""
执行记录存储模块

保存所有执行记录（成功和失败），支持：
- 按日期分目录存储
- 元数据 JSON 格式
- 脚本内容保存
- 向量索引（用于 RAG 检索）
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================

class ExecutionStatus(Enum):
    """执行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class ErrorType(Enum):
    """错误类型分类"""
    PARAMETER_ERROR = "parameter_error"      # 参数错误
    API_NOT_FOUND = "api_not_found"          # API 不存在
    AUTH_ERROR = "auth_error"                # 权限不足
    NETWORK_ERROR = "network_error"          # 网络错误
    TIMEOUT_ERROR = "timeout_error"          # 超时错误
    SCRIPT_ERROR = "script_error"            # 脚本执行错误
    UNKNOWN = "unknown"                       # 未知错误


@dataclass
class NormalizedIntent:
    """归一化后的意图"""
    core_intent: str           # 核心意图（去除参数）
    original_intent: str       # 原始意图
    limit: Optional[int] = None       # 数目限制
    page: Optional[int] = None        # 页码
    page_size: Optional[int] = None   # 每页数量
    order_by: Optional[str] = None    # 排序字段
    order_desc: bool = False          # 是否倒序
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "core_intent": self.core_intent,
            "original_intent": self.original_intent,
            "limit": self.limit,
            "page": self.page,
            "page_size": self.page_size,
            "order_by": self.order_by,
            "order_desc": self.order_desc,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedIntent":
        """从字典创建"""
        return cls(**data)


@dataclass
class ExecutionRecord:
    """执行记录"""
    id: str                              # 唯一标识（意图哈希）
    intent: str                          # 用户原始指令
    normalized_intent: str               # 归一化后的核心意图
    intent_params: Dict[str, Any]        # 提取的参数（limit、page 等）
    status: str                          # 执行状态：success/failed/error
    apis_used: List[str]                 # 调用的 API 列表
    script_content: str                  # 生成的脚本内容
    execution_output: str = ""           # 执行输出
    error_message: str = ""              # 错误信息（失败时）
    error_type: str = ""                 # 错误类型分类
    created_at: str = ""                 # 创建时间
    script_path: str = ""                # 脚本文件路径
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionRecord":
        """从字典创建"""
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ==================== 意图归一化 ====================

def normalize_intent(intent: str) -> NormalizedIntent:
    """
    意图归一化：提取核心意图和参数信息
    
    示例：
    - "查询用户列表前10个" → core="查询用户列表", limit=10
    - "查询第2页用户" → core="查询用户", page=2
    - "查询用户列表按创建时间倒序" → core="查询用户列表", order_by="创建时间", order_desc=True
    
    Args:
        intent: 原始用户意图
    
    Returns:
        归一化后的意图对象
    """
    original = intent
    core = intent
    limit, page, page_size, order_by, order_desc = None, None, None, None, False
    
    # 提取数目参数
    patterns_limit = [
        (r'前(\d+)个', 1),
        (r'(\d+)条', 1),
        (r'limit\s*(\d+)', 1),
        (r'top\s*(\d+)', 1),
    ]
    for pattern, group in patterns_limit:
        match = re.search(pattern, core, re.IGNORECASE)
        if match:
            limit = int(match.group(group))
            core = re.sub(pattern, '', core, flags=re.IGNORECASE)
            break  # 只提取第一个匹配
    
    # 提取翻页参数
    patterns_page = [
        (r'第(\d+)页', 1),
        (r'page\s*(\d+)', 1),
    ]
    for pattern, group in patterns_page:
        match = re.search(pattern, core, re.IGNORECASE)
        if match:
            page = int(match.group(group))
            core = re.sub(pattern, '', core, flags=re.IGNORECASE)
            break
    
    # 提取每页数量
    pagesize_match = re.search(r'每页(\d+)条?', core)
    if pagesize_match:
        page_size = int(pagesize_match.group(1))
        core = re.sub(r'每页\d+条?', '', core)
    
    # 提取排序参数
    order_match = re.search(r'按(.+?)(排序|倒序|升序|降序)', core)
    if order_match:
        order_by = order_match.group(1).strip()
        order_desc = '倒序' in order_match.group(0) or '降序' in order_match.group(0)
        core = re.sub(r'按.+?(排序|倒序|升序|降序)', '', core)
    
    # 清理多余空格和标点
    core = re.sub(r'\s+', '', core).strip()
    core = re.sub(r'[，。、]+$', '', core)  # 去除末尾标点
    
    return NormalizedIntent(
        core_intent=core,
        original_intent=original,
        limit=limit,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_desc=order_desc,
    )


def has_explicit_count(intent: str) -> bool:
    """
    检测意图是否包含明确数目
    
    Args:
        intent: 用户意图
    
    Returns:
        是否包含明确数目
    """
    patterns = [
        r'前\d+个',        # 前10个
        r'第\d+页',        # 第2页
        r'\d+条',          # 100条
        r'全部',           # 全部
        r'所有',           # 所有
        r'top\s*\d+',      # top 10
        r'limit\s*\d+',    # limit 100
    ]
    return any(re.search(p, intent, re.IGNORECASE) for p in patterns)


def generate_intent_hash(intent: str) -> str:
    """
    生成意图的哈希值（用于文件名）
    使用归一化后的核心意图生成
    
    Args:
        intent: 原始意图
    
    Returns:
        8 位哈希值
    """
    normalized = normalize_intent(intent)
    return hashlib.md5(normalized.core_intent.encode()).hexdigest()[:8]


# ==================== 参数替换 ====================

def substitute_params(
    script_content: str,
    old_params: Dict[str, Any],
    new_params: Dict[str, Any]
) -> str:
    """
    替换脚本中的参数值
    
    Args:
        script_content: 原始脚本内容
        old_params: 旧参数（来自历史记录）
        new_params: 新参数（来自当前意图）
    
    Returns:
        替换后的脚本内容
    """
    result = script_content
    
    # 替换 limit 参数
    if new_params.get("limit") and old_params.get("limit"):
        old_limit = old_params["limit"]
        new_limit = new_params["limit"]
        # 替换各种形式的 limit
        result = re.sub(
            rf'\blimit\s*[=:]\s*{old_limit}\b',
            f'limit={new_limit}',
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            rf'"limit"\s*:\s*{old_limit}\b',
            f'"limit": {new_limit}',
            result
        )
        result = re.sub(
            rf"'limit'\s*:\s*{old_limit}\b",
            f"'limit': {new_limit}",
            result
        )
    
    # 替换 page 参数
    if new_params.get("page") and old_params.get("page"):
        old_page = old_params["page"]
        new_page = new_params["page"]
        result = re.sub(
            rf'\bpage\s*[=:]\s*{old_page}\b',
            f'page={new_page}',
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            rf'"page"\s*:\s*{old_page}\b',
            f'"page": {new_page}',
            result
        )
    
    # 替换 pageSize 参数
    if new_params.get("page_size") and old_params.get("page_size"):
        old_size = old_params["page_size"]
        new_size = new_params["page_size"]
        result = re.sub(
            rf'\bpageSize\s*[=:]\s*{old_size}\b',
            f'pageSize={new_size}',
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            rf'"pageSize"\s*:\s*{old_size}\b',
            f'"pageSize": {new_size}',
            result
        )
    
    return result


# ==================== 存储管理 ====================

class ExecutionHistoryStorage:
    """执行记录存储管理器"""
    
    def __init__(self, base_dir: str = "data/execution_history"):
        """
        初始化存储管理器
        
        Args:
            base_dir: 存储根目录
        """
        self.base_dir = Path(base_dir)
        self.index_file = self.base_dir / "index" / "history.json"
        self._index: List[Dict[str, Any]] = []
        self._load_index()
    
    def _load_index(self):
        """加载索引文件"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
                logger.info(f"加载了 {len(self._index)} 条历史记录索引")
            except Exception as e:
                logger.warning(f"加载索引失败: {e}")
                self._index = []
        else:
            self._index = []
    
    def _save_index(self):
        """保存索引文件"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
    
    def _get_date_dir(self, dt: Optional[datetime] = None) -> Path:
        """获取日期目录路径"""
        if dt is None:
            dt = datetime.now()
        return self.base_dir / dt.strftime("%Y") / dt.strftime("%m") / dt.strftime("%d")
    
    def save_execution(self, record: ExecutionRecord) -> str:
        """
        保存执行记录
        
        Args:
            record: 执行记录
        
        Returns:
            保存的文件路径
        """
        # 确定保存目录
        date_dir = self._get_date_dir()
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        status_suffix = record.status
        # 清理意图用于文件名（去除特殊字符）
        clean_intent = re.sub(r'[\\/:*?"<>|]', '', record.normalized_intent)[:30]
        base_name = f"{record.id}_{clean_intent}_{status_suffix}"
        
        # 保存脚本文件
        script_path = date_dir / f"{base_name}.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(record.script_content)
        
        # 更新记录的脚本路径（相对路径）
        record.script_path = str(script_path.relative_to(self.base_dir))
        
        # 保存元数据文件
        meta_path = date_dir / f"{base_name}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(record.to_json())
        
        # 更新索引
        index_entry = {
            "id": record.id,
            "intent": record.intent,
            "normalized_intent": record.normalized_intent,
            "status": record.status,
            "apis_used": record.apis_used,
            "created_at": record.created_at,
            "script_path": record.script_path,
            "meta_path": str(meta_path.relative_to(self.base_dir)),
        }
        if record.error_type:
            index_entry["error_type"] = record.error_type
        
        self._index.append(index_entry)
        self._save_index()
        
        logger.info(f"保存执行记录: {base_name}")
        return str(script_path)
    
    def get_record(self, record_id: str) -> Optional[ExecutionRecord]:
        """
        获取指定 ID 的执行记录
        
        Args:
            record_id: 记录 ID
        
        Returns:
            执行记录，或 None
        """
        for entry in self._index:
            if entry["id"] == record_id:
                meta_path = self.base_dir / entry["meta_path"]
                if meta_path.exists():
                    with open(meta_path, "r", encoding="utf-8") as f:
                        return ExecutionRecord.from_dict(json.load(f))
        return None
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """获取所有记录的索引信息"""
        return self._index.copy()
    
    def search_by_intent(self, intent: str) -> List[Dict[str, Any]]:
        """
        按意图搜索记录（简单关键词匹配）
        
        Args:
            intent: 搜索的意图
        
        Returns:
            匹配的记录索引列表
        """
        normalized = normalize_intent(intent)
        results = []
        
        for entry in self._index:
            # 匹配归一化后的核心意图
            if normalized.core_intent in entry.get("normalized_intent", ""):
                results.append(entry)
        
        return results
    
    def get_success_records(self) -> List[Dict[str, Any]]:
        """获取所有成功的记录"""
        return [e for e in self._index if e.get("status") == "success"]
    
    def get_failed_records(self) -> List[Dict[str, Any]]:
        """获取所有失败的记录"""
        return [e for e in self._index if e.get("status") in ("failed", "error")]
    
    def cleanup_old_records(self, retention_days: int = 30):
        """
        清理过期记录
        
        Args:
            retention_days: 保留天数
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff.isoformat()
        
        # 过滤保留的记录
        new_index = []
        removed_count = 0
        
        for entry in self._index:
            if entry.get("created_at", "") >= cutoff_str:
                new_index.append(entry)
            else:
                # 删除文件
                script_path = self.base_dir / entry.get("script_path", "")
                meta_path = self.base_dir / entry.get("meta_path", "")
                if script_path.exists():
                    script_path.unlink()
                if meta_path.exists():
                    meta_path.unlink()
                removed_count += 1
        
        self._index = new_index
        self._save_index()
        
        logger.info(f"清理了 {removed_count} 条过期记录")
