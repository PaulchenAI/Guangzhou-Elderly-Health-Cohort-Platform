# -*- coding: utf-8 -*-
"""
Claude Code CLI 客户端
提供文件操作、Coding能力和上下文理解接口
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from .executor import ClaudeCodeExecutor
from .parser import ClaudeCodeParser
from .models import (
    ExecutionResult, FileInfo, GrepResult, AnalysisResult,
    RefactorResult, FixResult, ReviewResult, ProjectContext,
    DependencyGraph, CodeChunk
)
from ..utils.config_models import ClaudeCodeConfig
from ..logging.logger import get_logger


class ClaudeCodeClient:
    """Claude Code CLI 客户端封装"""
    
    def __init__(self, config: ClaudeCodeConfig):
        """
        初始化客户端
        
        Args:
            config: Claude Code配置
        """
        self.config = config
        self.executor = ClaudeCodeExecutor(
            claude_path=config.path,
            working_dir=config.working_dir,
            timeout=config.timeout,
            max_concurrent=config.max_concurrent
        )
        self.parser = ClaudeCodeParser()
        self.logger = get_logger("claude_code")
    
    # ===== 本地文件操作 =====
    
    async def read_file(self, path: str) -> str:
        """
        读取文件内容
        
        Args:
            path: 文件路径（相对于working_dir或绝对路径）
            
        Returns:
            文件内容
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 读取失败
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        prompt = f"读取文件: {file_path}\n请返回文件的完整内容。"
        
        result = await self.executor.execute(prompt, command="read_file")
        
        if not result.success:
            error = self.parser.parse_error(result) or "读取文件失败"
            raise ValueError(error)
        
        # 尝试从JSON中提取内容
        data = self.parser.parse_json(result)
        if data and 'content' in data:
            return data['content']
        
        # 如果不是JSON，直接返回stdout
        return result.stdout.strip()
    
    async def write_file(self, path: str, content: str) -> bool:
        """
        写入文件内容
        
        Args:
            path: 文件路径
            content: 文件内容
            
        Returns:
            是否成功
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        prompt = f"""写入文件: {file_path}

内容：
{content}

请创建或覆盖该文件。"""
        
        result = await self.executor.execute(prompt, command="write_file")
        
        if not result.success:
            error = self.parser.parse_error(result) or "写入文件失败"
            self.logger.error(f"写入文件失败: {error}")
            return False
        
        # 验证文件是否已创建
        if file_path.exists():
            return True
        
        return False
    
    async def edit_file(self, path: str, old_str: str, new_str: str) -> bool:
        """
        编辑文件（字符串替换）
        
        Args:
            path: 文件路径
            old_str: 要替换的旧字符串
            new_str: 新字符串
            
        Returns:
            是否成功
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        prompt = f"""编辑文件: {file_path}

将以下内容：
{old_str}

替换为：
{new_str}

请执行替换操作。"""
        
        result = await self.executor.execute(prompt, command="edit_file")
        
        if not result.success:
            error = self.parser.parse_error(result) or "编辑文件失败"
            self.logger.error(f"编辑文件失败: {error}")
            return False
        
        return True
    
    async def search_files(self, pattern: str, path: str = ".") -> List[str]:
        """
        搜索文件（glob模式）
        
        Args:
            pattern: 文件模式（如 "*.py"）
            path: 搜索路径
            
        Returns:
            匹配的文件路径列表
        """
        search_path = Path(path)
        if not search_path.is_absolute():
            search_path = self.executor.working_dir / search_path
        
        prompt = f"""在目录 {search_path} 中搜索文件模式: {pattern}

请返回所有匹配的文件路径。"""
        
        result = await self.executor.execute(prompt, command="search_files")
        
        if not result.success:
            self.logger.warning(f"搜索文件失败: {self.parser.parse_error(result)}")
            return []
        
        files = self.parser.parse_file_list(result)
        return files
    
    async def grep(self, pattern: str, path: str = ".") -> List[GrepResult]:
        """
        搜索文件内容（正则表达式）
        
        Args:
            pattern: 搜索模式（正则表达式）
            path: 搜索路径
            
        Returns:
            GrepResult列表
        """
        search_path = Path(path)
        if not search_path.is_absolute():
            search_path = self.executor.working_dir / search_path
        
        prompt = f"""在目录 {search_path} 中搜索内容模式: {pattern}

请返回所有匹配的行，包括文件路径、行号和内容。"""
        
        result = await self.executor.execute(prompt, command="grep")
        
        if not result.success:
            self.logger.warning(f"Grep搜索失败: {self.parser.parse_error(result)}")
            return []
        
        return self.parser.parse_grep_results(result)
    
    async def list_dir(self, path: str = ".") -> List[FileInfo]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            FileInfo列表
        """
        dir_path = Path(path)
        if not dir_path.is_absolute():
            dir_path = self.executor.working_dir / dir_path
        
        prompt = f"""列出目录内容: {dir_path}

请返回目录中的所有文件和子目录，包括类型和大小信息。"""
        
        result = await self.executor.execute(prompt, command="list_dir")
        
        if not result.success:
            self.logger.warning(f"列出目录失败: {self.parser.parse_error(result)}")
            return []
        
        data = self.parser.parse_json(result)
        if data and 'items' in data:
            items = []
            for item in data['items']:
                items.append(FileInfo(
                    path=item.get('path', ''),
                    name=item.get('name', ''),
                    is_file=item.get('type') == 'file',
                    is_dir=item.get('type') == 'dir',
                    size=item.get('size')
                ))
            return items
        
        # 如果不是JSON，尝试解析标准ls格式
        items = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    items.append(FileInfo(
                        path=parts[-1],
                        name=Path(parts[-1]).name,
                        is_file='d' not in parts[0] if parts[0] else True,
                        is_dir='d' in parts[0] if parts[0] else False
                    ))
        
        return items
    
    # ===== Coding能力 =====
    
    async def analyze_code(self, path: str, question: str) -> AnalysisResult:
        """
        分析代码，回答问题
        
        Args:
            path: 代码文件路径
            question: 问题
            
        Returns:
            AnalysisResult分析结果
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        prompt = f"""分析代码文件: {file_path}

问题: {question}

请分析代码并回答上述问题，包括：
1. 代码结构分析
2. 发现的问题
3. 改进建议"""
        
        result = await self.executor.execute(prompt, command="analyze_code")
        
        if not result.success:
            error = self.parser.parse_error(result) or "代码分析失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return AnalysisResult(
                summary=data.get('summary', ''),
                findings=data.get('findings', []),
                suggestions=data.get('suggestions', []),
                complexity_score=data.get('complexity_score')
            )
        
        # 如果不是JSON，从stdout提取
        return AnalysisResult(
            summary=result.stdout[:500],
            findings=[],
            suggestions=[],
            complexity_score=None
        )
    
    async def generate_code(self, prompt: str, context: Optional[str] = None) -> str:
        """
        根据需求生成代码
        
        Args:
            prompt: 生成需求描述
            context: 上下文信息（可选）
            
        Returns:
            生成的代码
        """
        full_prompt = f"""根据以下需求生成代码：

需求：
{prompt}
"""
        
        if context:
            full_prompt += f"\n上下文：\n{context}\n"
        
        full_prompt += "\n请生成完整的代码。"
        
        result = await self.executor.execute(full_prompt, command="generate_code")
        
        if not result.success:
            error = self.parser.parse_error(result) or "代码生成失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data and 'code' in data:
            return data['code']
        
        return result.stdout.strip()
    
    async def refactor_code(self, path: str, instruction: str) -> RefactorResult:
        """
        重构代码
        
        Args:
            path: 代码文件路径
            instruction: 重构指令
            
        Returns:
            RefactorResult重构结果
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        # 先读取原代码
        original_code = await self.read_file(str(file_path))
        
        prompt = f"""重构代码文件: {file_path}

重构指令：
{instruction}

原代码：
{original_code}

请提供重构后的代码和变更说明。"""
        
        result = await self.executor.execute(prompt, command="refactor_code")
        
        if not result.success:
            error = self.parser.parse_error(result) or "代码重构失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return RefactorResult(
                original_code=original_code,
                refactored_code=data.get('refactored_code', ''),
                changes=data.get('changes', []),
                explanation=data.get('explanation', '')
            )
        
        return RefactorResult(
            original_code=original_code,
            refactored_code=result.stdout,
            changes=[],
            explanation="重构完成"
        )
    
    async def fix_bug(self, path: str, bug_description: str) -> FixResult:
        """
        修复Bug
        
        Args:
            path: 代码文件路径
            bug_description: Bug描述
            
        Returns:
            FixResult修复结果
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        # 先读取原代码
        original_code = await self.read_file(str(file_path))
        
        prompt = f"""修复Bug: {file_path}

Bug描述：
{bug_description}

原代码：
{original_code}

请修复Bug并提供修复后的代码和说明。"""
        
        result = await self.executor.execute(prompt, command="fix_bug")
        
        if not result.success:
            error = self.parser.parse_error(result) or "Bug修复失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return FixResult(
                original_code=original_code,
                fixed_code=data.get('fixed_code', ''),
                bug_description=bug_description,
                fix_explanation=data.get('explanation', ''),
                test_suggestions=data.get('test_suggestions', [])
            )
        
        return FixResult(
            original_code=original_code,
            fixed_code=result.stdout,
            bug_description=bug_description,
            fix_explanation="Bug已修复",
            test_suggestions=[]
        )
    
    async def review_code(self, path: str) -> ReviewResult:
        """
        代码审查
        
        Args:
            path: 代码文件路径
            
        Returns:
            ReviewResult审查结果
        """
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.executor.working_dir / file_path
        
        code = await self.read_file(str(file_path))
        
        prompt = f"""审查代码文件: {file_path}

代码：
{code}

请进行代码审查，包括：
1. 代码质量评分
2. 发现的问题
3. 改进建议
4. 优点
5. 需要改进的地方"""
        
        result = await self.executor.execute(prompt, command="review_code")
        
        if not result.success:
            error = self.parser.parse_error(result) or "代码审查失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return ReviewResult(
                overall_score=data.get('score', 0.0),
                issues=data.get('issues', []),
                suggestions=data.get('suggestions', []),
                strengths=data.get('strengths', []),
                improvements=data.get('improvements', [])
            )
        
        return ReviewResult(
            overall_score=0.0,
            issues=[],
            suggestions=[],
            strengths=[],
            improvements=[]
        )
    
    # ===== 上下文理解 =====
    
    async def understand_project(self, path: str = ".") -> ProjectContext:
        """
        理解项目结构
        
        Args:
            path: 项目路径
            
        Returns:
            ProjectContext项目上下文
        """
        project_path = Path(path)
        if not project_path.is_absolute():
            project_path = self.executor.working_dir / project_path
        
        prompt = f"""分析项目结构: {project_path}

请分析项目结构，包括：
1. 项目目录结构
2. 主要文件
3. 依赖关系
4. 入口点
5. 项目描述"""
        
        result = await self.executor.execute(prompt, command="understand_project")
        
        if not result.success:
            error = self.parser.parse_error(result) or "项目分析失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return ProjectContext(
                structure=data.get('structure', {}),
                main_files=data.get('main_files', []),
                dependencies=data.get('dependencies', []),
                entry_points=data.get('entry_points', []),
                description=data.get('description', '')
            )
        
        return ProjectContext(
            structure={},
            main_files=[],
            dependencies=[],
            entry_points=[],
            description=result.stdout[:500]
        )
    
    async def analyze_dependencies(self, path: str) -> DependencyGraph:
        """
        分析依赖关系
        
        Args:
            path: 项目路径
            
        Returns:
            DependencyGraph依赖关系图
        """
        project_path = Path(path)
        if not project_path.is_absolute():
            project_path = self.executor.working_dir / project_path
        
        prompt = f"""分析项目依赖关系: {project_path}

请分析项目的依赖关系，包括：
1. 所有模块/包
2. 模块间的依赖关系
3. 根模块（无依赖的模块）"""
        
        result = await self.executor.execute(prompt, command="analyze_dependencies")
        
        if not result.success:
            error = self.parser.parse_error(result) or "依赖分析失败"
            raise ValueError(error)
        
        data = self.parser.parse_json(result)
        if data:
            return DependencyGraph(
                nodes=data.get('nodes', []),
                edges=data.get('edges', []),
                root_modules=data.get('root_modules', [])
            )
        
        return DependencyGraph(
            nodes=[],
            edges=[],
            root_modules=[]
        )
    
    async def semantic_search(self, query: str, path: str = ".") -> List[CodeChunk]:
        """
        语义搜索代码
        
        Args:
            query: 搜索查询
            path: 搜索路径
            
        Returns:
            CodeChunk列表
        """
        search_path = Path(path)
        if not search_path.is_absolute():
            search_path = self.executor.working_dir / search_path
        
        prompt = f"""在项目中进行语义搜索: {search_path}

查询: {query}

请返回相关的代码片段，包括文件路径、行号、代码内容和相关性评分。"""
        
        result = await self.executor.execute(prompt, command="semantic_search")
        
        if not result.success:
            self.logger.warning(f"语义搜索失败: {self.parser.parse_error(result)}")
            return []
        
        data = self.parser.parse_json(result)
        if data and 'chunks' in data:
            chunks = []
            for item in data['chunks']:
                chunks.append(CodeChunk(
                    file_path=item.get('file', ''),
                    start_line=item.get('start_line', 0),
                    end_line=item.get('end_line', 0),
                    code=item.get('code', ''),
                    context=item.get('context', ''),
                    relevance_score=item.get('score', 0.0)
                ))
            return chunks
        
        return []
