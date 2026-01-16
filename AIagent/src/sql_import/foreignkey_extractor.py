# -*- coding: utf-8 -*-
"""
外键提取器核心模块 - 多策略架构
"""

import os
import re
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .foreignkey_schema import ForeignKey, TableForeignKeys


class ForeignKeyExtractor:
    """外键提取器 - 支持多策略提取"""
    
    # 大文件阈值（MB）
    LARGE_FILE_THRESHOLD_MB = 1.0
    
    # 外键关键字（用于片段提取）
    FK_KEYWORDS = [
        r'foreign\s+key',
        r'references\s+\w+',
        r'add\s+constraint.*foreign',
        r'constraint.*references'
    ]
    
    def __init__(self, enable_llm: bool = False, api_key: Optional[str] = None):
        """
        初始化外键提取器
        
        Args:
            enable_llm: 是否启用 LLM 辅助
            api_key: Claude API 密钥
        """
        self.enable_llm = enable_llm
        self.api_key = api_key
        
        # 标准正则表达式模式
        self.standard_pattern = re.compile(
            r'alter\s+table\s+(\w+)\s+'                          # 表名
            r'add\s+constraint\s+(\w+)\s+'                       # 约束名
            r'foreign\s+key\s*\(([^)]+)\)\s*'                    # 源字段
            r'references\s+(\w+)\s*\(([^)]+)\)'                  # 目标表和字段
            r'(\s+on\s+delete\s+(cascade|set\s+null|restrict|no\s+action))?',  # 删除规则
            re.IGNORECASE | re.MULTILINE
        )
    
    def check_file_size(self, file_path: str) -> float:
        """
        检测文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（MB）
        """
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        return file_size_mb
    
    def is_large_file(self, file_path: str) -> bool:
        """判断是否为大文件"""
        return self.check_file_size(file_path) > self.LARGE_FILE_THRESHOLD_MB
    
    def read_small_file(self, file_path: str) -> str:
        """
        读取小文件（<1MB）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def extract_fk_fragments_streaming(self, file_path: str, max_fragments: int = 5) -> List[str]:
        """
        流式提取大文件中的外键片段
        
        Args:
            file_path: 文件路径
            max_fragments: 最多提取的片段数量
            
        Returns:
            外键语句片段列表
        """
        fragments = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines) and len(fragments) < max_fragments:
            line = lines[i]
            
            # 检查是否包含外键关键字
            if any(re.search(kw, line, re.I) for kw in self.FK_KEYWORDS):
                # 提取上下文（前5行 + 当前行 + 后10行）
                start = max(0, i - 5)
                end = min(len(lines), i + 10)
                fragment_lines = lines[start:end]
                
                # 确保语句完整性（查找分号）
                fragment_text = ''.join(fragment_lines)
                if ';' not in fragment_text:
                    # 继续向后查找到分号
                    while end < len(lines) and ';' not in lines[end]:
                        end += 1
                    if end < len(lines):
                        end += 1
                    fragment_lines = lines[start:end]
                
                fragment = ''.join(fragment_lines).strip()
                if fragment:
                    fragments.append(fragment)
                
                i = end  # 跳过已提取的部分
            else:
                i += 1
        
        # 去重
        unique_fragments = list(dict.fromkeys(fragments))
        return unique_fragments[:max_fragments]
    
    def extract_using_standard_regex(self, sql_content: str) -> List[ForeignKey]:
        """
        使用标准正则表达式提取外键（策略1）
        
        Args:
            sql_content: SQL 文件内容
            
        Returns:
            外键列表
        """
        foreign_keys = []
        
        matches = self.standard_pattern.findall(sql_content)
        
        for match in matches:
            table_name = match[0].upper()
            constraint_name = match[1].upper()
            source_cols_str = match[2]
            target_table = match[3].upper()
            target_cols_str = match[4]
            on_delete_clause = match[6] if len(match) > 6 else None
            
            # 解析字段列表
            source_columns = [col.strip().upper() for col in source_cols_str.split(',')]
            target_columns = [col.strip().upper() for col in target_cols_str.split(',')]
            
            # 处理删除规则
            on_delete = None
            if on_delete_clause:
                on_delete_clause = on_delete_clause.lower().replace(' ', '_')
                if on_delete_clause == 'set_null':
                    on_delete = 'set_null'
                elif on_delete_clause == 'cascade':
                    on_delete = 'cascade'
                elif on_delete_clause == 'restrict':
                    on_delete = 'restrict'
                elif on_delete_clause == 'no_action':
                    on_delete = 'no_action'
            
            try:
                fk = ForeignKey(
                    constraint_name=constraint_name,
                    source_table=table_name,
                    source_columns=source_columns,
                    target_table=target_table,
                    target_columns=target_columns,
                    on_delete=on_delete
                )
                foreign_keys.append(fk)
            except Exception as e:
                print(f"警告：解析外键失败 - {constraint_name}: {e}")
                continue
        
        return foreign_keys
    
    def extract_from_file(self, file_path: str) -> TableForeignKeys:
        """
        从单个文件提取外键信息
        
        Args:
            file_path: SQL 文件路径
            
        Returns:
            表外键信息
        """
        file_name = os.path.basename(file_path)
        table_name = os.path.splitext(file_name)[0].upper()
        file_size_mb = self.check_file_size(file_path)
        
        # 判断文件大小并选择读取方式
        if self.is_large_file(file_path):
            # 大文件：使用片段提取
            print(f"大文件检测: {file_name} ({file_size_mb:.2f}MB) - 使用片段提取")
            fragments = self.extract_fk_fragments_streaming(file_path)
            sql_content = '\n\n'.join(fragments)
        else:
            # 小文件：直接读取
            sql_content = self.read_small_file(file_path)
        
        # 使用标准正则表达式提取
        foreign_keys = self.extract_using_standard_regex(sql_content)
        
        # 创建表外键信息对象
        table_fks = TableForeignKeys(
            table_name=table_name,
            source_file=file_name,
            extraction_strategy='standard_regex',
            foreign_keys=foreign_keys,
            file_size_mb=file_size_mb
        )
        
        return table_fks
    
    def save_to_json(self, table_fks: TableForeignKeys, output_dir: str, overwrite: bool = False) -> str:
        """
        保存外键信息到 JSON 文件
        
        Args:
            table_fks: 表外键信息
            output_dir: 输出目录
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            保存的文件路径
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        output_file = os.path.join(output_dir, f"{table_fks.table_name}_foreignkeys.json")
        
        # 检查文件是否存在
        if os.path.exists(output_file) and not overwrite:
            print(f"文件已存在，跳过: {output_file}")
            return output_file
        
        # 保存 JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                table_fks.dict(),
                f,
                ensure_ascii=False,
                indent=4,
                default=str  # 处理 datetime
            )
        
        return output_file
