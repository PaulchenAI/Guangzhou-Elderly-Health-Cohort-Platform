# -*- coding: utf-8 -*-
"""
输出格式模块

支持多种输出格式：
- 文本格式（默认）：友好的人类可读格式
- JSON 格式：结构化数据，便于程序处理
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ==================== 输出格式 ====================

class OutputFormat(Enum):
    """输出格式枚举"""
    TEXT = "text"
    JSON = "json"


# ==================== 翻页信息 ====================

@dataclass
class PaginationInfo:
    """翻页信息"""
    page: int = 1              # 当前页码
    page_size: int = 10        # 每页数量
    total: int = 0             # 总记录数
    total_pages: int = 0       # 总页数
    has_more: bool = False     # 是否有下一页
    
    def __post_init__(self):
        # 自动计算总页数和是否有下一页
        if self.total > 0 and self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size
            self.has_more = self.page < self.total_pages
    
    @classmethod
    def from_response(
        cls,
        response: Dict[str, Any],
        default_page: int = 1,
        default_page_size: int = 10,
    ) -> "PaginationInfo":
        """
        从 API 响应中提取翻页信息
        
        Args:
            response: API 响应数据
            default_page: 默认页码
            default_page_size: 默认每页数量
        
        Returns:
            翻页信息对象
        """
        # 如果响应是列表，使用列表长度估算
        if isinstance(response, list):
            return cls(
                page=default_page,
                page_size=default_page_size,
                total=len(response),
            )
        
        # 首先检查是否有 pagination 子对象（优先级最高）
        pagination_obj = response.get("pagination") or response.get("paging") or {}
        
        # 合并顶层字段和 pagination 子对象，子对象优先
        def get_field(*keys, default=None):
            """从 pagination 子对象或顶层获取字段"""
            for key in keys:
                if pagination_obj.get(key) is not None:
                    return pagination_obj[key]
                if response.get(key) is not None:
                    return response[key]
            return default
        
        page = get_field("page", "currentPage", default=default_page)
        page_size = get_field("pageSize", "page_size", "size", default=default_page_size)
        total = get_field("total", "totalCount", "count", default=0)
        
        # 如果还是没有 total，尝试从数据列表估算
        if total == 0:
            data_keys = ["list", "data", "items", "users", "records", "results"]
            for key in data_keys:
                data_list = response.get(key)
                if isinstance(data_list, list) and len(data_list) > 0:
                    total = len(data_list)
                    break
        
        return cls(
            page=int(page),
            page_size=int(page_size),
            total=int(total),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "page": self.page,
            "pageSize": self.page_size,
            "total": self.total,
            "totalPages": self.total_pages,
            "hasMore": self.has_more,
        }
    
    def to_summary(self) -> str:
        """
        生成用户友好的翻页摘要
        
        Returns:
            翻页摘要文本
        """
        remaining = max(0, self.total - (self.page * self.page_size))
        
        summary = f"当前返回第 {self.page} 页，共 {self.page_size} 条。"
        summary += f"总计 {self.total} 条记录"
        
        if self.has_more:
            summary += f"，还有 {remaining} 条未显示。"
            summary += "可输入'下一页'或'查询第N页'继续查看。"
        else:
            summary += "，已全部显示。"
        
        return summary


# ==================== 查询结果 ====================

@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: List[Any] = field(default_factory=list)
    pagination: Optional[PaginationInfo] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    
    def __post_init__(self):
        if self.pagination is None:
            self.pagination = PaginationInfo()
        if not self.meta.get("timestamp"):
            self.meta["timestamp"] = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "pagination": self.pagination.to_dict() if self.pagination else None,
            "meta": self.meta,
            "error": self.error if self.error else None,
        }
    
    def to_text(self) -> str:
        """
        转换为文本格式
        
        Returns:
            友好的文本格式输出
        """
        lines = []
        
        if not self.success:
            lines.append(f"❌ 查询失败: {self.error}")
            return "\n".join(lines)
        
        lines.append("📊 查询结果")
        
        # 数据展示
        data_count = len(self.data)
        lines.append(f"├── 数据: [{data_count} 条记录]")
        
        # 显示前几条数据
        for i, item in enumerate(self.data[:3]):
            item_str = json.dumps(item, ensure_ascii=False)
            if len(item_str) > 80:
                item_str = item_str[:80] + "..."
            prefix = "│   ├──" if i < min(3, data_count) - 1 else "│   └──"
            lines.append(f"{prefix} {item_str}")
        
        if data_count > 3:
            lines.append(f"│   └── ... (共 {data_count} 条)")
        
        lines.append("│")
        
        # 翻页信息
        if self.pagination:
            lines.append("└── 📄 翻页信息")
            lines.append(f"    ├── 当前页: {self.pagination.page} / {self.pagination.total_pages}")
            lines.append(f"    ├── 每页数量: {self.pagination.page_size}")
            lines.append(f"    ├── 总记录数: {self.pagination.total}")
            
            if self.pagination.has_more:
                remaining = self.pagination.total - (self.pagination.page * self.pagination.page_size)
                lines.append(f"    └── 💡 还有 {remaining} 条未显示，可输入\"下一页\"继续查看")
            else:
                lines.append("    └── ✓ 已全部显示")
        
        # 元信息
        if self.meta.get("intent"):
            lines.append("")
            lines.append(f"📝 意图: {self.meta.get('intent')}")
        if self.meta.get("api"):
            lines.append(f"🔗 API: {self.meta.get('api')}")
        if self.meta.get("duration"):
            lines.append(f"⏱️ 耗时: {self.meta.get('duration')}")
        
        return "\n".join(lines)
    
    def to_json(self, indent: int = 2) -> str:
        """
        转换为 JSON 格式
        
        Args:
            indent: 缩进空格数
        
        Returns:
            JSON 字符串
        """
        result = self.to_dict()
        # 移除 None 值
        result = {k: v for k, v in result.items() if v is not None}
        return json.dumps(result, ensure_ascii=False, indent=indent)
    
    def output(self, format: OutputFormat = OutputFormat.TEXT) -> str:
        """
        按指定格式输出
        
        Args:
            format: 输出格式
        
        Returns:
            格式化后的输出
        """
        if format == OutputFormat.JSON:
            return self.to_json()
        return self.to_text()


# ==================== 默认翻页配置 ====================

DEFAULT_PAGE = int(os.environ.get("DJANGO_API_DEFAULT_PAGE", "1"))
DEFAULT_PAGE_SIZE = int(os.environ.get("DJANGO_API_DEFAULT_PAGE_SIZE", "10"))
DEFAULT_OUTPUT_FORMAT = os.environ.get("DJANGO_API_OUTPUT_FORMAT", "text")


def get_default_output_format() -> OutputFormat:
    """获取默认输出格式"""
    fmt = DEFAULT_OUTPUT_FORMAT.lower()
    if fmt == "json":
        return OutputFormat.JSON
    return OutputFormat.TEXT


def inject_pagination(
    params: Dict[str, Any],
    intent: str,
    default_page: int = DEFAULT_PAGE,
    default_page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    注入默认翻页参数
    
    当意图没有明确数目时，自动添加翻页参数
    
    Args:
        params: 原始参数字典
        intent: 用户意图
        default_page: 默认页码
        default_page_size: 默认每页数量
    
    Returns:
        注入翻页参数后的字典
    """
    from .execution_history import has_explicit_count
    
    result = params.copy()
    
    if not has_explicit_count(intent):
        result.setdefault("page", default_page)
        result.setdefault("pageSize", default_page_size)
    
    return result
