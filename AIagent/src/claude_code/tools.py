# -*- coding: utf-8 -*-
"""
Claude Code CLI LangChain工具集
将Claude Code接口封装为LangChain Tool，供智能体调用
"""

import asyncio
from typing import List, Optional
from langchain_core.tools import tool
from langchain.tools import BaseTool
from .client import ClaudeCodeClient


def create_claude_code_tools(client: ClaudeCodeClient) -> List[BaseTool]:
    """
    创建供LangChain使用的Claude Code工具集
    
    Args:
        client: Claude Code客户端
        
    Returns:
        LangChain Tool列表
    """
    tools = []
    
    # 文件操作工具
    @tool
    async def read_file(path: str) -> str:
        """读取本地文件内容
        
        Args:
            path: 文件路径（相对于工作目录或绝对路径）
            
        Returns:
            文件内容
        """
        return await client.read_file(path)
    
    @tool
    async def write_file(path: str, content: str) -> bool:
        """写入内容到本地文件
        
        Args:
            path: 文件路径
            content: 文件内容
            
        Returns:
            是否成功
        """
        return await client.write_file(path, content)
    
    @tool
    async def edit_file(path: str, old_str: str, new_str: str) -> bool:
        """编辑本地文件（替换内容）
        
        Args:
            path: 文件路径
            old_str: 要替换的旧字符串
            new_str: 新字符串
            
        Returns:
            是否成功
        """
        return await client.edit_file(path, old_str, new_str)
    
    @tool
    async def search_files(pattern: str, path: str = ".") -> List[str]:
        """搜索文件（glob模式）
        
        Args:
            pattern: 文件模式（如 "*.py"）
            path: 搜索路径
            
        Returns:
            匹配的文件路径列表
        """
        return await client.search_files(pattern, path)
    
    @tool
    async def grep(pattern: str, path: str = ".") -> List[dict]:
        """搜索文件内容（正则表达式）
        
        Args:
            pattern: 搜索模式（正则表达式）
            path: 搜索路径
            
        Returns:
            搜索结果列表（包含file_path, line_number, line_content）
        """
        results = await client.grep(pattern, path)
        return [
            {
                'file_path': r.file_path,
                'line_number': r.line_number,
                'line_content': r.line_content,
                'match_text': r.match_text
            }
            for r in results
        ]
    
    @tool
    async def list_dir(path: str = ".") -> List[dict]:
        """列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            文件和目录信息列表
        """
        items = await client.list_dir(path)
        return [
            {
                'path': item.path,
                'name': item.name,
                'is_file': item.is_file,
                'is_dir': item.is_dir,
                'size': item.size
            }
            for item in items
        ]
    
    # Coding能力工具
    @tool
    async def analyze_code(path: str, question: str) -> dict:
        """分析代码并回答问题
        
        Args:
            path: 代码文件路径
            question: 问题
            
        Returns:
            分析结果（包含summary, findings, suggestions）
        """
        result = await client.analyze_code(path, question)
        return {
            'summary': result.summary,
            'findings': result.findings,
            'suggestions': result.suggestions,
            'complexity_score': result.complexity_score
        }
    
    @tool
    async def generate_code(prompt: str, context: Optional[str] = None) -> str:
        """根据需求生成代码
        
        Args:
            prompt: 生成需求描述
            context: 上下文信息（可选）
            
        Returns:
            生成的代码
        """
        return await client.generate_code(prompt, context)
    
    @tool
    async def refactor_code(path: str, instruction: str) -> dict:
        """重构代码
        
        Args:
            path: 代码文件路径
            instruction: 重构指令
            
        Returns:
            重构结果（包含refactored_code, changes, explanation）
        """
        result = await client.refactor_code(path, instruction)
        return {
            'refactored_code': result.refactored_code,
            'changes': result.changes,
            'explanation': result.explanation
        }
    
    @tool
    async def fix_bug(path: str, bug_description: str) -> dict:
        """修复Bug
        
        Args:
            path: 代码文件路径
            bug_description: Bug描述
            
        Returns:
            修复结果（包含fixed_code, fix_explanation, test_suggestions）
        """
        result = await client.fix_bug(path, bug_description)
        return {
            'fixed_code': result.fixed_code,
            'fix_explanation': result.fix_explanation,
            'test_suggestions': result.test_suggestions
        }
    
    @tool
    async def review_code(path: str) -> dict:
        """代码审查
        
        Args:
            path: 代码文件路径
            
        Returns:
            审查结果（包含score, issues, suggestions, strengths, improvements）
        """
        result = await client.review_code(path)
        return {
            'overall_score': result.overall_score,
            'issues': result.issues,
            'suggestions': result.suggestions,
            'strengths': result.strengths,
            'improvements': result.improvements
        }
    
    # 上下文理解工具
    @tool
    async def understand_project(path: str = ".") -> dict:
        """理解项目结构
        
        Args:
            path: 项目路径
            
        Returns:
            项目上下文（包含structure, main_files, dependencies, entry_points, description）
        """
        result = await client.understand_project(path)
        return {
            'structure': result.structure,
            'main_files': result.main_files,
            'dependencies': result.dependencies,
            'entry_points': result.entry_points,
            'description': result.description
        }
    
    @tool
    async def analyze_dependencies(path: str) -> dict:
        """分析依赖关系
        
        Args:
            path: 项目路径
            
        Returns:
            依赖关系图（包含nodes, edges, root_modules）
        """
        result = await client.analyze_dependencies(path)
        return {
            'nodes': result.nodes,
            'edges': result.edges,
            'root_modules': result.root_modules
        }
    
    @tool
    async def semantic_search(query: str, path: str = ".") -> List[dict]:
        """语义搜索代码
        
        Args:
            query: 搜索查询
            path: 搜索路径
            
        Returns:
            代码块列表（包含file_path, code, relevance_score）
        """
        chunks = await client.semantic_search(query, path)
        return [
            {
                'file_path': chunk.file_path,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'code': chunk.code,
                'context': chunk.context,
                'relevance_score': chunk.relevance_score
            }
            for chunk in chunks
        ]
    
    # 添加到工具列表
    tools.extend([
        read_file,
        write_file,
        edit_file,
        search_files,
        grep,
        list_dir,
        analyze_code,
        generate_code,
        refactor_code,
        fix_bug,
        review_code,
        understand_project,
        analyze_dependencies,
        semantic_search
    ])
    
    return tools
