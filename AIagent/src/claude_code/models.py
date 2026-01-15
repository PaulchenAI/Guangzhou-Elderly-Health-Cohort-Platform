# -*- coding: utf-8 -*-
"""
Claude Code CLI 数据模型
定义返回结果的数据结构
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ExecutionResult:
    """命令执行结果"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    
    @property
    def error(self) -> Optional[str]:
        """获取错误信息"""
        if not self.success and self.stderr:
            return self.stderr
        return None


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    is_file: bool
    is_dir: bool
    size: Optional[int] = None


@dataclass
class GrepResult:
    """Grep搜索结果"""
    file_path: str
    line_number: int
    line_content: str
    match_text: str


@dataclass
class AnalysisResult:
    """代码分析结果"""
    summary: str
    findings: List[Dict[str, Any]]
    suggestions: List[str]
    complexity_score: Optional[float] = None


@dataclass
class RefactorResult:
    """代码重构结果"""
    original_code: str
    refactored_code: str
    changes: List[Dict[str, Any]]
    explanation: str


@dataclass
class FixResult:
    """Bug修复结果"""
    original_code: str
    fixed_code: str
    bug_description: str
    fix_explanation: str
    test_suggestions: List[str]


@dataclass
class ReviewResult:
    """代码审查结果"""
    overall_score: float
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    strengths: List[str]
    improvements: List[str]


@dataclass
class ProjectContext:
    """项目上下文"""
    structure: Dict[str, Any]
    main_files: List[str]
    dependencies: List[str]
    entry_points: List[str]
    description: str


@dataclass
class DependencyGraph:
    """依赖关系图"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    root_modules: List[str]


@dataclass
class CodeChunk:
    """代码块"""
    file_path: str
    start_line: int
    end_line: int
    code: str
    context: str
    relevance_score: float
