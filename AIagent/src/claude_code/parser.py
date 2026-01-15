# -*- coding: utf-8 -*-
"""
Claude Code CLI 输出解析器
解析JSON输出和错误信息
"""

import json
from typing import Any, Dict, Optional, List
from .models import ExecutionResult, GrepResult, FileInfo


class ClaudeCodeParser:
    """Claude Code CLI 输出解析器"""
    
    @staticmethod
    def parse_json(result: ExecutionResult) -> Optional[Dict[str, Any]]:
        """
        解析JSON输出
        
        Args:
            result: 执行结果
            
        Returns:
            解析后的JSON字典，如果解析失败返回None
        """
        if not result.success or not result.stdout:
            return None
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            # 尝试提取JSON部分
            stdout = result.stdout.strip()
            # 查找JSON对象
            start = stdout.find('{')
            end = stdout.rfind('}') + 1
            
            if start >= 0 and end > start:
                try:
                    return json.loads(stdout[start:end])
                except json.JSONDecodeError:
                    pass
            
            return None
    
    @staticmethod
    def parse_error(result: ExecutionResult) -> Optional[str]:
        """
        提取错误信息
        
        Args:
            result: 执行结果
            
        Returns:
            错误信息，如果没有错误返回None
        """
        if result.success:
            return None
        
        # 优先从stderr获取错误
        if result.stderr:
            return result.stderr.strip()
        
        # 从stdout尝试提取错误
        if result.stdout:
            # 尝试解析JSON错误
            try:
                data = json.loads(result.stdout)
                if 'error' in data:
                    return data['error']
                if 'message' in data:
                    return data['message']
            except json.JSONDecodeError:
                pass
            
            # 查找常见错误模式
            error_keywords = ['error', 'Error', 'ERROR', 'failed', 'Failed']
            for keyword in error_keywords:
                if keyword in result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if keyword in line:
                            return line.strip()
        
        return f"执行失败，返回码: {result.return_code}"
    
    @staticmethod
    def parse_file_list(result: ExecutionResult) -> List[str]:
        """
        解析文件列表输出
        
        Args:
            result: 执行结果
            
        Returns:
            文件路径列表
        """
        if not result.success:
            return []
        
        data = ClaudeCodeParser.parse_json(result)
        if data and 'files' in data:
            return data['files']
        
        # 如果不是JSON，尝试按行解析
        files = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                files.append(line)
        
        return files
    
    @staticmethod
    def parse_grep_results(result: ExecutionResult) -> List[GrepResult]:
        """
        解析grep搜索结果
        
        Args:
            result: 执行结果
            
        Returns:
            GrepResult列表
        """
        if not result.success:
            return []
        
        data = ClaudeCodeParser.parse_json(result)
        if data and 'results' in data:
            results = []
            for item in data['results']:
                results.append(GrepResult(
                    file_path=item.get('file', ''),
                    line_number=item.get('line', 0),
                    line_content=item.get('content', ''),
                    match_text=item.get('match', '')
                ))
            return results
        
        # 如果不是JSON，尝试解析标准grep格式
        results = []
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    results.append(GrepResult(
                        file_path=parts[0],
                        line_number=int(parts[1]) if parts[1].isdigit() else 0,
                        line_content=parts[2],
                        match_text=parts[2]
                    ))
        
        return results
