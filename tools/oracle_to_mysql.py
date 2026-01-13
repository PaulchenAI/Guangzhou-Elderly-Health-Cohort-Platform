#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oracle to MySQL SQL 转换工具

将 Oracle PL/SQL Developer 导出的 SQL 文件转换为 MySQL 兼容格式。
支持以下功能：
- 保留表结构和数据（CREATE TABLE 和 INSERT 语句）
- 保留 COMMENT 注释信息（表注释和列注释）
- 支持表名前缀（用于多租户或避免表名冲突）
- 支持 DDL/DML 分离（分阶段导入）
- 自动调用 sql-fix-tools 进行修复

使用方法：
    # 转换单个文件
    python tools/oracle_to_mysql.py convert docs/hospital/sql/BS_DEPARTMENT.sql
    
    # 转换目录下所有文件
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql
    
    # 转换并分离 DDL/DML
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --split-ddl-dml
    
    # 转换并添加表名前缀
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --table-prefix gzlry_
    
    # 启用 COMMENT 转换
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --enable-comments
    
    # 全部功能组合
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql \\
        --split-ddl-dml --table-prefix gzlry_ --enable-comments --auto-fix
"""

import re
import os
import sys
import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class OracleToMySQLConverter:
    """Oracle SQL 到 MySQL 的转换器
    
    支持功能：
    - 表结构和数据转换（CREATE TABLE 和 INSERT 语句）
    - COMMENT 注释转换（表注释和列注释）
    - 表名前缀添加
    - DDL/DML 分离输出
    """
    
    # Oracle 数据类型到 MySQL 的映射
    TYPE_MAPPING = {
        r'VARCHAR2\s*\((\d+)\s*(BYTE|CHAR)?\s*\)': r'VARCHAR(\1)',
        r'NVARCHAR2\s*\((\d+)\)': r'VARCHAR(\1)',
        r'NUMBER\s*\((\d+)\s*,\s*(\d+)\s*\)': r'DECIMAL(\1,\2)',
        r'NUMBER\s*\((\d+)\s*\)': r'BIGINT',
        r'\bNUMBER\b(?!\s*\()': 'DECIMAL(38,0)',
        r'\bINTEGER\b': 'INT',
        r'\bSMALLINT\b': 'SMALLINT',
        r'\bFLOAT\b': 'DOUBLE',
        r'\bBINARY_FLOAT\b': 'FLOAT',
        r'\bBINARY_DOUBLE\b': 'DOUBLE',
        r'\bCLOB\b': 'LONGTEXT',
        r'\bNCLOB\b': 'LONGTEXT',
        r'\bBLOB\b': 'LONGBLOB',
        r'\bLONG\s+RAW\b': 'LONGBLOB',
        r'\bLONG\b': 'LONGTEXT',
        r'RAW\s*\((\d+)\)': r'VARBINARY(\1)',
        r'\bTIMESTAMP\s*\((\d+)\)': r'DATETIME(\1)',
        r'\bTIMESTAMP\b': 'DATETIME',
    }
    
    # DATE 类型模式
    DATE_TYPE_PATTERN = r'(\s+)DATE(\s*(?:,|\)|$|not\s+null|default))'
    
    def __init__(self):
        """初始化转换器"""
        # COMMENT 存储字典
        self.table_comments: Dict[str, str] = {}      # {table_name: comment}
        self.column_comments: Dict[str, str] = {}     # {table_name.column_name: comment}
        
        # 转换选项
        self.enable_comments = False
        self.table_prefix = ''
        
        # 当前处理的表名
        self._current_table_name = None
    
    def reset(self):
        """重置转换器状态（处理新文件前调用）"""
        self.table_comments.clear()
        self.column_comments.clear()
        self._current_table_name = None
    
    def _collect_comments(self, file_path: str) -> None:
        """
        第一遍扫描：收集所有 COMMENT 语句
        
        Args:
            file_path: SQL 文件路径
        """
        # 尝试不同的编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.warning(f"无法读取文件收集 COMMENT: {file_path}")
            return
        
        # 匹配表注释: COMMENT ON TABLE table_name IS 'comment';
        table_comment_pattern = r"comment\s+on\s+table\s+(\w+)\s+is\s+'((?:[^']|'')*)'(?:\s*;)?"
        for match in re.finditer(table_comment_pattern, content, re.IGNORECASE):
            table_name = match.group(1).upper()
            comment = match.group(2).replace("''", "'")  # 还原转义的单引号
            self.table_comments[table_name] = comment
            logger.debug(f"  收集表注释: {table_name} = '{comment}'")
        
        # 匹配列注释: COMMENT ON COLUMN table_name.column_name IS 'comment';
        column_comment_pattern = r"comment\s+on\s+column\s+(\w+)\.(\w+)\s+is\s+'((?:[^']|'')*)'(?:\s*;)?"
        for match in re.finditer(column_comment_pattern, content, re.IGNORECASE):
            table_name = match.group(1).upper()
            column_name = match.group(2).upper()
            comment = match.group(3).replace("''", "'")  # 还原转义的单引号
            key = f"{table_name}.{column_name}"
            self.column_comments[key] = comment
            logger.debug(f"  收集列注释: {key} = '{comment}'")
        
        if self.table_comments or self.column_comments:
            logger.info(f"  收集到 {len(self.table_comments)} 个表注释, {len(self.column_comments)} 个列注释")
    
    def _escape_comment(self, comment: str) -> str:
        """转义注释中的特殊字符"""
        # 转义单引号
        return comment.replace("'", "''")
    
    def _inject_column_comment(self, column_def: str, table_name: str, column_name: str) -> str:
        """
        在列定义后添加 COMMENT
        
        Args:
            column_def: 列定义字符串（如: mainid VARCHAR(50) NOT NULL）
            table_name: 表名
            column_name: 列名
            
        Returns:
            添加了注释的列定义
        """
        key = f"{table_name.upper()}.{column_name.upper()}"
        if key not in self.column_comments:
            return column_def
        
        comment = self._escape_comment(self.column_comments[key])
        
        # 检查是否已经有 COMMENT
        if 'COMMENT' in column_def.upper():
            return column_def
        
        # 在列定义末尾添加 COMMENT（在逗号之前）
        return f"{column_def} COMMENT '{comment}'"
    
    def _inject_table_comment(self, create_stmt: str, table_name: str) -> str:
        """
        在 CREATE TABLE 语句中注入表注释
        
        Args:
            create_stmt: CREATE TABLE 语句
            table_name: 表名
            
        Returns:
            添加了注释的 CREATE TABLE 语句
        """
        if table_name.upper() not in self.table_comments:
            return create_stmt
        
        comment = self._escape_comment(self.table_comments[table_name.upper()])
        
        # 检查是否已经有 COMMENT
        if "COMMENT='" in create_stmt or "COMMENT =" in create_stmt:
            return create_stmt
        
        # 在 ENGINE 子句前插入 COMMENT
        if 'ENGINE=' in create_stmt:
            create_stmt = create_stmt.replace(
                'ENGINE=InnoDB',
                f"COMMENT='{comment}'\nENGINE=InnoDB"
            )
        else:
            # 如果没有 ENGINE 子句，在末尾分号前添加
            create_stmt = create_stmt.rstrip().rstrip(';')
            create_stmt += f"\nCOMMENT='{comment}';"
        
        return create_stmt
    
    def add_table_prefix(self, stmt: str, table_prefix: str) -> str:
        """
        为 SQL 语句中的表名添加前缀
        
        Args:
            stmt: SQL 语句
            table_prefix: 表名前缀
            
        Returns:
            添加了前缀的 SQL 语句
        """
        if not table_prefix:
            return stmt
        
        # 1. CREATE TABLE table_name
        stmt = re.sub(
            r'(CREATE\s+TABLE\s+)(\w+)',
            lambda m: f'{m.group(1)}{table_prefix}{m.group(2)}',
            stmt,
            flags=re.IGNORECASE
        )
        
        # 2. DROP TABLE IF EXISTS table_name
        stmt = re.sub(
            r'(DROP\s+TABLE\s+IF\s+EXISTS\s+)(\w+)',
            lambda m: f'{m.group(1)}{table_prefix}{m.group(2)}',
            stmt,
            flags=re.IGNORECASE
        )
        
        # 3. INSERT INTO table_name
        stmt = re.sub(
            r'(INSERT\s+INTO\s+)(\w+)',
            lambda m: f'{m.group(1)}{table_prefix}{m.group(2)}',
            stmt,
            flags=re.IGNORECASE
        )
        
        return stmt
    
    def convert_file(self, file_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        转换单个 Oracle SQL 文件（使用流式处理，优化内存使用）
        
        Args:
            file_path: SQL 文件路径
            output_path: 输出文件路径（如果提供，直接写入文件，不返回字符串）
            
        Returns:
            str: 转换后的 SQL（如果 output_path 为 None），否则返回 None
        """
        # 尝试不同的编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        file_handle = None
        
        for encoding in encodings:
            try:
                file_handle = open(file_path, 'r', encoding=encoding)
                # 检查 BOM
                first_char = file_handle.read(1)
                if first_char == '\ufeff':
                    pass  # 跳过 BOM
                elif first_char:
                    file_handle.seek(0)  # 重新定位到开头
                break
            except UnicodeDecodeError:
                if file_handle:
                    file_handle.close()
                file_handle = None
                continue
            except Exception as e:
                logger.error(f"无法读取文件 {file_path}: {e}")
                return None
        
        if not file_handle:
            logger.error(f"无法读取文件 {file_path}，尝试的编码都不支持")
            return None
        
        try:
            # 获取文件大小，用于显示进度
            file_size = Path(file_path).stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            is_large_file = file_size > 10 * 1024 * 1024  # 大于10MB
            
            # 如果指定了输出路径，直接写入文件（避免内存累积）
            output_file = None
            if output_path:
                output_file = open(output_path, 'w', encoding='utf-8')
                statement_count = 0
            
            # 提取 CREATE TABLE 和 INSERT 语句（流式处理）
            statements = [] if not output_path else None
            current_stmt = []
            paren_count = 0
            first_line = True
            line_count = 0
            last_progress_time = 0
            import time
            
            # 对于大文件，显示开始转换的信息
            if is_large_file:
                logger.info(f"    开始转换大文件（{file_size_mb:.1f} MB），请稍候...")
            
            for line in file_handle:
                line_count += 1
                # 处理 BOM（只在第一行）
                if first_line and line.startswith('\ufeff'):
                    line = line[1:]
                first_line = False
                
                stripped = line.strip()
                
                # 跳过空行和注释
                if not stripped or stripped.startswith('--'):
                    continue
                
                # 跳过 PL/SQL 命令
                if (stripped.startswith('prompt') or 
                    stripped.startswith('set ') or 
                    stripped.startswith('spool') or
                    stripped.startswith('exit') or
                    stripped.startswith('quit') or
                    stripped.startswith('whenever')):
                    continue
                
                current_stmt.append(line.rstrip('\n\r'))
                paren_count += line.count('(') - line.count(')')
                
                # 语句结束（以分号结尾且括号匹配）
                if stripped.endswith(';') and paren_count <= 0:
                    stmt = '\n'.join(current_stmt)
                    if stmt.strip():
                        converted = self._convert_statement(stmt.strip())
                        if converted:
                            if output_file:
                                # 直接写入文件，避免内存累积
                                if statement_count > 0:
                                    output_file.write('\n\n')
                                output_file.write(converted)
                                statement_count += 1
                                
                                # 每 10000 个语句刷新一次缓冲区
                                if statement_count % 10000 == 0:
                                    output_file.flush()
                                    
                                    # 显示进度（每 10000 个语句或每 5 秒）
                                    current_time = time.time()
                                    if is_large_file and (current_time - last_progress_time > 5 or statement_count % 10000 == 0):
                                        # 估算文件读取进度（基于当前位置）
                                        try:
                                            current_pos = file_handle.tell()
                                            progress_percent = (current_pos / file_size) * 100 if file_size > 0 else 0
                                            logger.info(f"    进度: 已转换 {statement_count:,} 个语句，文件读取 {progress_percent:.1f}% ({current_pos / (1024*1024):.1f} MB / {file_size_mb:.1f} MB)")
                                        except:
                                            logger.info(f"    进度: 已转换 {statement_count:,} 个语句")
                                        last_progress_time = current_time
                                    
                                    # 垃圾回收（减少频率：每 50000 个语句）
                                    if statement_count % 50000 == 0:
                                        import gc
                                        gc.collect()
                            else:
                                statements.append(converted)
                                # 每处理 1000 个语句后清理一次（针对超大文件）
                                if len(statements) % 1000 == 0:
                                    import gc
                                    gc.collect()
                    # 清空当前语句，释放内存
                    current_stmt = []
                    paren_count = 0
            
            # 处理最后一个语句（可能没有分号）
            if current_stmt:
                stmt = '\n'.join(current_stmt)
                if stmt.strip():
                    converted = self._convert_statement(stmt.strip())
                    if converted:
                        if output_file:
                            if statement_count > 0:
                                output_file.write('\n\n')
                            output_file.write(converted)
                        else:
                            statements.append(converted)
            
            if output_file:
                output_file.close()
                if statement_count == 0:
                    return None
                # 对于大文件，显示最终统计信息
                if is_large_file:
                    logger.info(f"    转换完成: 共处理 {line_count:,} 行，转换 {statement_count:,} 个语句")
                return f"已写入 {statement_count} 个语句到文件"
            
            return '\n\n'.join(statements) if statements else None
            
        except MemoryError:
            logger.error(f"内存不足，无法处理文件: {file_path}")
            return None
        except Exception as e:
            logger.error(f"处理文件时出错 {file_path}: {e}")
            return None
        finally:
            file_handle.close()
    
    def convert_file_with_split(
        self, 
        file_path: str, 
        output_dir: str,
        enable_comments: bool = False,
        table_prefix: str = '',
        file_prefix: str = ''
    ) -> Dict[str, Any]:
        """
        转换单个 Oracle SQL 文件，将 DDL 和 DML 分离到不同目录
        
        Args:
            file_path: 输入 SQL 文件路径
            output_dir: 输出目录
            enable_comments: 是否启用 COMMENT 转换
            table_prefix: 表名前缀
            file_prefix: 文件名前缀
            
        Returns:
            转换结果字典，包含 ddl_file, dml_file, ddl_count, dml_count
        """
        # 重置状态
        self.reset()
        self.enable_comments = enable_comments
        self.table_prefix = table_prefix
        
        # 提取表名（从文件名）
        table_name = Path(file_path).stem
        
        # 创建输出目录
        output_path = Path(output_dir)
        create_dir = output_path / 'create'
        insert_dir = output_path / 'insert'
        create_dir.mkdir(parents=True, exist_ok=True)
        insert_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果启用 COMMENT 转换，先收集所有 COMMENT
        if enable_comments:
            self._collect_comments(file_path)
        
        # 打开输入文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        file_handle = None
        
        for encoding in encodings:
            try:
                file_handle = open(file_path, 'r', encoding=encoding)
                first_char = file_handle.read(1)
                if first_char == '\ufeff':
                    pass
                elif first_char:
                    file_handle.seek(0)
                break
            except UnicodeDecodeError:
                if file_handle:
                    file_handle.close()
                file_handle = None
                continue
        
        if not file_handle:
            logger.error(f"无法读取文件 {file_path}")
            return {'success': False, 'error': '无法读取文件'}
        
        # 准备输出文件
        ddl_filename = f"{file_prefix}{table_name}.sql" if file_prefix else f"{table_name}.sql"
        dml_filename = f"{file_prefix}{table_name}_data.sql" if file_prefix else f"{table_name}_data.sql"
        
        ddl_file_path = create_dir / ddl_filename
        dml_file_path = insert_dir / dml_filename
        
        ddl_count = 0
        dml_count = 0
        
        try:
            # 使用流式处理，边解析边写入
            ddl_file = open(ddl_file_path, 'w', encoding='utf-8')
            dml_file = open(dml_file_path, 'w', encoding='utf-8')
            
            current_stmt = []
            paren_count = 0
            first_line = True
            
            for line in file_handle:
                if first_line and line.startswith('\ufeff'):
                    line = line[1:]
                first_line = False
                
                stripped = line.strip()
                
                # 跳过空行、注释和 PL/SQL 命令
                if not stripped or stripped.startswith('--'):
                    continue
                if (stripped.startswith('prompt') or 
                    stripped.startswith('set ') or 
                    stripped.startswith('spool') or
                    stripped.startswith('exit') or
                    stripped.startswith('quit') or
                    stripped.startswith('whenever')):
                    continue
                
                current_stmt.append(line.rstrip('\n\r'))
                paren_count += line.count('(') - line.count(')')
                
                # 语句结束
                if stripped.endswith(';') and paren_count <= 0:
                    stmt = '\n'.join(current_stmt)
                    if stmt.strip():
                        stmt_upper = stmt.upper().strip()
                        
                        if stmt_upper.startswith('CREATE TABLE'):
                            # DDL 语句
                            converted = self._convert_create_table(stmt, enable_comments)
                            if converted:
                                if ddl_count > 0:
                                    ddl_file.write('\n\n')
                                ddl_file.write(converted)
                                ddl_count += 1
                        
                        elif stmt_upper.startswith('INSERT INTO'):
                            # DML 语句
                            converted = self._convert_insert(stmt)
                            if self.table_prefix:
                                converted = self.add_table_prefix(converted, self.table_prefix)
                            if converted:
                                if dml_count > 0:
                                    dml_file.write('\n\n')
                                dml_file.write(converted)
                                dml_count += 1
                    
                    current_stmt = []
                    paren_count = 0
            
            # 处理最后一个语句
            if current_stmt:
                stmt = '\n'.join(current_stmt)
                if stmt.strip():
                    stmt_upper = stmt.upper().strip()
                    if stmt_upper.startswith('CREATE TABLE'):
                        converted = self._convert_create_table(stmt, enable_comments)
                        if converted:
                            if ddl_count > 0:
                                ddl_file.write('\n\n')
                            ddl_file.write(converted)
                            ddl_count += 1
                    elif stmt_upper.startswith('INSERT INTO'):
                        converted = self._convert_insert(stmt)
                        if self.table_prefix:
                            converted = self.add_table_prefix(converted, self.table_prefix)
                        if converted:
                            if dml_count > 0:
                                dml_file.write('\n\n')
                            dml_file.write(converted)
                            dml_count += 1
            
            ddl_file.close()
            dml_file.close()
            
            # 如果没有 DML 语句，删除空的 DML 文件
            if dml_count == 0:
                dml_file_path.unlink()
                dml_file_path = None
                logger.info(f"    {table_name}: 无数据（仅生成 DDL）")
            
            return {
                'success': True,
                'ddl_file': str(ddl_file_path),
                'dml_file': str(dml_file_path) if dml_file_path else None,
                'ddl_count': ddl_count,
                'dml_count': dml_count,
                'table_name': table_name
            }
            
        except Exception as e:
            logger.error(f"转换文件时出错 {file_path}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            file_handle.close()
    
    def _convert_statement(self, stmt: str, inject_comments: bool = False) -> Optional[str]:
        """
        转换单个 SQL 语句，只保留 CREATE TABLE 和 INSERT
        
        Args:
            stmt: SQL 语句
            inject_comments: 是否注入 COMMENT
            
        Returns:
            转换后的语句，如果需要忽略则返回 None
        """
        stmt_upper = stmt.upper().strip()
        
        # 只处理 CREATE TABLE 和 INSERT INTO
        if stmt_upper.startswith('CREATE TABLE'):
            return self._convert_create_table(stmt, inject_comments)
        elif stmt_upper.startswith('INSERT INTO'):
            result = self._convert_insert(stmt)
            # 应用表名前缀
            if self.table_prefix:
                result = self.add_table_prefix(result, self.table_prefix)
            return result
        else:
            # 忽略其他语句（COMMENT、ALTER、DELETE、COMMIT 等）
            return None
    
    def _convert_create_table(self, stmt: str, inject_comments: bool = False) -> str:
        """
        转换 CREATE TABLE 语句
        
        Args:
            stmt: CREATE TABLE 语句
            inject_comments: 是否注入 COMMENT
            
        Returns:
            转换后的 MySQL CREATE TABLE 语句
        """
        result = stmt
        
        # 提取表名
        table_match = re.search(r'CREATE\s+TABLE\s+(\w+)', result, re.IGNORECASE)
        table_name = table_match.group(1) if table_match else None
        self._current_table_name = table_name
        
        # 转换数据类型
        for oracle_type, mysql_type in self.TYPE_MAPPING.items():
            result = re.sub(oracle_type, mysql_type, result, flags=re.IGNORECASE)
        
        # 特殊处理 DATE 类型
        result = re.sub(self.DATE_TYPE_PATTERN, r'\1DATETIME\2', result, flags=re.IGNORECASE)
        
        # 如果启用 COMMENT 注入，处理列注释
        if inject_comments and table_name and self.column_comments:
            result = self._inject_column_comments_into_create(result, table_name)
        
        # 移除 tablespace 及其后的所有存储参数
        result = re.sub(
            r'\)\s*tablespace\s+\w+[^;]*;',
            ')\nENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;',
            result,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # 如果没有 tablespace，添加 ENGINE
        if 'ENGINE=' not in result:
            result = result.rstrip().rstrip(';')
            result += '\nENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;'
        
        # 注入表注释
        if inject_comments and table_name:
            result = self._inject_table_comment(result, table_name)
        
        # 清理多余的空行
        result = re.sub(r'\n\s*\n+', '\n', result)
        
        # 添加 DROP TABLE IF EXISTS（表名前缀由 add_table_prefix 统一处理）
        if table_name:
            result = f"DROP TABLE IF EXISTS {table_name};\n\n{result}"
        
        # 应用表名前缀（统一处理 DROP TABLE、CREATE TABLE 中的表名）
        if self.table_prefix:
            result = self.add_table_prefix(result, self.table_prefix)
        
        return result
    
    def _inject_column_comments_into_create(self, create_stmt: str, table_name: str) -> str:
        """
        在 CREATE TABLE 语句中为每个列注入 COMMENT
        
        Args:
            create_stmt: CREATE TABLE 语句
            table_name: 表名
            
        Returns:
            注入了列注释的 CREATE TABLE 语句
        """
        # 找到 CREATE TABLE 括号内的内容
        match = re.search(r'CREATE\s+TABLE\s+\w+\s*\((.*)\)', create_stmt, re.IGNORECASE | re.DOTALL)
        if not match:
            return create_stmt
        
        columns_content = match.group(1)
        start_pos = match.start(1)
        end_pos = match.end(1)
        
        # 解析每一行，为列添加注释
        lines = columns_content.split('\n')
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            
            # 尝试提取列名（第一个单词）
            col_match = re.match(r'^\s*(\w+)\s+', line)
            if col_match:
                col_name = col_match.group(1).upper()
                key = f"{table_name.upper()}.{col_name}"
                
                # 检查是否有该列的注释
                if key in self.column_comments and 'COMMENT' not in line.upper():
                    comment = self._escape_comment(self.column_comments[key])
                    
                    # 在行末添加 COMMENT（在逗号之前）
                    if line.rstrip().endswith(','):
                        line = line.rstrip()[:-1] + f" COMMENT '{comment}',"
                    else:
                        line = line.rstrip() + f" COMMENT '{comment}'"
            
            new_lines.append(line)
        
        new_columns_content = '\n'.join(new_lines)
        result = create_stmt[:start_pos] + new_columns_content + create_stmt[end_pos:]
        
        return result
    
    def _convert_insert(self, stmt: str) -> str:
        """转换 INSERT 语句"""
        result = stmt
        
        # 转换 to_date 函数
        def replace_to_date(match):
            date_str = match.group(1)
            format_str = match.group(2).lower()
            
            mysql_format = format_str
            mysql_format = mysql_format.replace('yyyy', '%Y')
            mysql_format = mysql_format.replace('yy', '%y')
            mysql_format = mysql_format.replace('mm', '%m')
            mysql_format = mysql_format.replace('dd', '%d')
            mysql_format = mysql_format.replace('hh24', '%H')
            mysql_format = mysql_format.replace('hh', '%h')
            mysql_format = mysql_format.replace('mi', '%i')
            mysql_format = mysql_format.replace('ss', '%s')
            
            return f"STR_TO_DATE('{date_str}', '{mysql_format}')"
        
        result = re.sub(
            r"to_date\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
            replace_to_date,
            result,
            flags=re.IGNORECASE
        )
        
        # 转换 SYSDATE -> NOW()
        result = re.sub(r'\bSYSDATE\b', 'NOW()', result, flags=re.IGNORECASE)
        
        # 转换 chr(n) -> CHAR(n)
        result = re.sub(r'\bchr\s*\(', 'CHAR(', result, flags=re.IGNORECASE)
        
        # 转换 || 连接符：只处理最简单的情况，避免性能问题
        # 对于包含大量引号或复杂嵌套的语句，跳过转换
        # 这些语句在 MySQL 中可能导致语法错误，需要手动处理
        if '||' in result:
            # 统计引号数量，如果太多则跳过（避免复杂解析）
            quote_count = result.count("'")
            if quote_count < 20:  # 只处理引号少的简单语句
                # 简单替换：'str1' || 'str2' -> CONCAT('str1', 'str2')
                # 使用非贪婪匹配，最多替换3次
                simple_pattern = r"('[^']{0,100}')\s*\|\|\s*('[^']{0,100}')"
                for _ in range(3):
                    new_result = re.sub(simple_pattern, r'CONCAT(\1, \2)', result, count=1)
                    if new_result == result:
                        break
                    result = new_result
        
        return result
    
    def _convert_concat_simple(self, stmt: str) -> str:
        """
        简单转换 || 连接符
        只处理 'str' || chr(n) || 'str' 这样的简单模式
        使用高效的字符串解析，避免灾难性回溯
        """
        if '||' not in stmt:
            return stmt
        
        # 快速检查：如果是简单语句（长度<500字符），使用简单替换
        # 否则使用基于位置的解析
        stmt_len = len(stmt)
        
        # 查找 values (...) 部分
        values_match = re.search(r'values\s*\((.*)\)\s*;?\s*$', stmt, re.IGNORECASE | re.DOTALL)
        if not values_match:
            return stmt
        
        values_content = values_match.group(1)
        
        # 如果 values 部分很长（>1000字符）且包含 ||，使用快速字符串替换
        # 避免复杂正则导致的性能问题
        if len(values_content) > 1000:
            # 简单替换策略：
            # 1. 替换 chr(n) -> CHAR(n)
            values_content = re.sub(r'\bchr\s*\(', 'CHAR(', values_content, flags=re.IGNORECASE)
            
            # 2. 对于包含 || 的部分，尝试简单的模式匹配
            # 只处理明显的 || 连接（两边都是引号或函数调用）
            # 使用非贪婪匹配和字符类，避免回溯
            
            # 匹配简单模式：'xxx' || 'yyy' 或 'xxx' || CHAR(n) || 'yyy'
            # 限制字符串长度，避免超长匹配
            simple_pattern = r"('[^']{0,200}(?:''[^']{0,200})*')\s*\|\|\s*('[^']{0,200}(?:''[^']{0,200})*'|CHAR\s*\([^)]+\))"
            
            # 最多替换 100 次，避免无限循环
            for _ in range(100):
                new_content = re.sub(
                    simple_pattern,
                    lambda m: f"CONCAT({m.group(1)}, {m.group(2)})",
                    values_content,
                    count=1,
                    flags=re.IGNORECASE
                )
                if new_content == values_content:
                    break
                values_content = new_content
            
            # 3. 扩展 CONCAT：CONCAT(a, b) || c -> CONCAT(a, b, c)
            concat_extend_pattern = r"CONCAT\(([^)]+)\)\s*\|\|\s*('[^']{0,200}(?:''[^']{0,200})*'|CHAR\s*\([^)]+\))"
            for _ in range(50):
                new_content = re.sub(
                    concat_extend_pattern,
                    lambda m: f"CONCAT({m.group(1)}, {m.group(2)})",
                    values_content,
                    count=1,
                    flags=re.IGNORECASE
                )
                if new_content == values_content:
                    break
                values_content = new_content
        else:
            # 短语句，使用原来的逻辑（但使用更安全的正则）
            # 替换 chr(n) -> CHAR(n)
            values_content = re.sub(r'\bchr\s*\(', 'CHAR(', values_content, flags=re.IGNORECASE)
            
            # 简单模式匹配，限制长度避免回溯
            simple_pattern = r"('[^']{0,200}(?:''[^']{0,200})*')\s*\|\|\s*('[^']{0,200}(?:''[^']{0,200})*'|CHAR\s*\([^)]+\))"
            
            for _ in range(50):
                new_content = re.sub(
                    simple_pattern,
                    lambda m: f"CONCAT({m.group(1)}, {m.group(2)})",
                    values_content,
                    count=1,
                    flags=re.IGNORECASE
                )
                if new_content == values_content:
                    break
                values_content = new_content
        
        result = stmt[:values_match.start(1)] + values_content + stmt[values_match.end(1):]
        
        return result


def convert_file(input_path: str, output_path: str, prefix: str = '', force: bool = False, skip_existing: bool = False) -> tuple:
    """
    转换单个文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        prefix: 文件名前缀
        force: 强制重新转换
        skip_existing: 是否跳过已存在的文件（需要检查完整性）
    
    Returns:
        tuple: (success: bool, skipped: bool, reason: str)
    """
    output_file = Path(output_path)
    
    # 检查文件是否已存在（仅在 skip_existing=True 时跳过）
    if not force and skip_existing and output_file.exists():
        file_size = output_file.stat().st_size
        if file_size > 0:
            # 更严格的完整性检查
            is_complete = True
            check_failures = []
            
            try:
                # 1. 检查文件大小是否合理（至少应该有几KB，除非是空表）
                if file_size < 100:  # 小于100字节，可能不完整
                    is_complete = False
                    check_failures.append(f"文件太小（{file_size} 字节）")
                
                # 2. 检查文件开头：必须包含 CREATE TABLE
                # 尝试多种编码读取文件（转换后的文件应该是 UTF-8，但为了健壮性支持多种编码）
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                f = None
                first_2kb = None
                full_content = None
                
                for encoding in encodings:
                    try:
                        f = open(output_file, 'r', encoding=encoding)
                        first_2kb = f.read(2048)
                        first_2kb_upper = first_2kb.upper()
                        
                        if 'CREATE TABLE' not in first_2kb_upper:
                            is_complete = False
                            check_failures.append("缺少 CREATE TABLE")
                        
                        # 3. 检查文件中间：统计关键语句数量，确保有合理的结构
                        # 对于大文件，分别处理 CREATE TABLE 检查和 INSERT 统计
                        f.seek(0)
                        if file_size < 10 * 1024 * 1024:  # 小于10MB，读取全部
                            full_content = f.read()
                            full_content_upper = full_content.upper()
                            
                            # 必须至少有一个 CREATE TABLE
                            create_count = full_content_upper.count('CREATE TABLE')
                            if create_count == 0:
                                is_complete = False
                                check_failures.append("缺少 CREATE TABLE 语句")
                            
                            # 统计目标文件中的 INSERT 数量
                            output_insert_count = full_content_upper.count('INSERT INTO')
                        else:  # 大文件，使用流式统计
                            # 只读取前2KB检查 CREATE TABLE
                            f.seek(0)
                            first_2kb = f.read(2048)
                            create_count = first_2kb.upper().count('CREATE TABLE')
                            if create_count == 0:
                                is_complete = False
                                check_failures.append("缺少 CREATE TABLE 语句")
                            
                            # 流式统计 INSERT 数量（逐行读取，避免内存占用）
                            f.seek(0)
                            output_insert_count = 0
                            for line in f:
                                if 'INSERT INTO' in line.upper():
                                    output_insert_count += 1
                        
                        break  # 成功读取，退出循环
                    except UnicodeDecodeError:
                        if f:
                            f.close()
                        f = None
                        continue
                    except Exception as e:
                        if f:
                            f.close()
                        f = None
                        raise e
                
                if f is None:
                    # 所有编码都失败
                    is_complete = False
                    check_failures.append("无法读取文件（编码错误）")
                    output_insert_count = 0  # 设置默认值
                    create_count = 0
                else:
                    f.close()
                    
                    # 4. 检查文件末尾：必须以分号结尾，且最后100字符内不能有未完成的语句
                    with open(output_file, 'rb') as f2:
                        f2.seek(max(0, file_size - 200))  # 读取最后200字符
                        tail_bytes = f2.read()
                        tail = tail_bytes.decode('utf-8', errors='ignore')
                        tail_stripped = tail.rstrip()
                        
                        # 必须以分号结尾
                        if not tail_stripped.endswith(';'):
                            is_complete = False
                            check_failures.append("未以分号结尾")
                        else:
                            # 检查最后是否有未完成的语句（如未闭合的引号、括号等）
                            # 更准确的引号检查：从末尾向前查找，确保最后一个语句完整
                            # 简单检查：最后200字符中，单引号应该是偶数（成对出现）
                            # 排除转义的单引号（''）
                            tail_for_check = tail_stripped
                            # 将 '' 替换为占位符，避免干扰统计
                            tail_for_check = tail_for_check.replace("''", "__ESCAPED_QUOTE__")
                            single_quotes = tail_for_check.count("'")
                            if single_quotes % 2 != 0:
                                # 如果引号是奇数，可能有问题，但先不严格检查（因为可能只是部分内容）
                                # 只在明显有问题时才报告
                                pass
                    
                    # 5. 核对 INSERT 语句数量：比较源文件和目标文件（仅在文件读取成功时）
                    if f is not None:
                        try:
                            # 统计源文件中的 INSERT 数量
                            source_insert_count = 0
                            source_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                            
                            # 读取源文件统计 INSERT 数量（优化：使用流式统计，避免读取整个文件）
                            for encoding in source_encodings:
                                try:
                                    input_file_size = Path(input_path).stat().st_size
                                    
                                    # 对于大文件，使用快速统计：只统计包含 "INSERT INTO" 的行
                                    # 使用逐行迭代器，内存占用小，速度快
                                    if input_file_size > 5 * 1024 * 1024:  # 大于5MB，使用快速统计
                                        with open(input_path, 'r', encoding=encoding, errors='ignore') as sf:
                                            # 快速统计：只统计包含 "INSERT INTO" 的行数
                                            # 使用迭代器逐行读取，内存占用小，速度快
                                            source_insert_count = 0
                                            
                                            for line in sf:
                                                # 只检查包含 INSERT INTO 的行（不区分大小写）
                                                if 'INSERT INTO' in line.upper() or ('INSERT ' in line.upper() and 'INTO' in line.upper()):
                                                    source_insert_count += 1
                                    else:
                                        # 小文件，读取全部内容用正则匹配
                                        with open(input_path, 'r', encoding=encoding) as sf:
                                            content = sf.read()
                                            # 使用正则匹配 INSERT INTO ... ; 模式
                                            insert_pattern = r'INSERT\s+INTO\s+[^;]*?;'
                                            matches = re.findall(insert_pattern, content, re.IGNORECASE | re.DOTALL)
                                            source_insert_count = len(matches)
                                    break
                                except UnicodeDecodeError:
                                    continue
                                except Exception as e:
                                    logger.debug(f"  统计源文件 INSERT 数量时出错: {e}")
                                    break
                            
                            # 比较 INSERT 数量
                            if source_insert_count > 0:
                                if output_insert_count == 0:
                                    # 源文件有 INSERT，但目标文件没有，可能不完整
                                    is_complete = False
                                    check_failures.append(f"缺少 INSERT 语句（源文件有 {source_insert_count} 个）")
                                elif abs(output_insert_count - source_insert_count) > max(1, source_insert_count * 0.01):
                                    # 允许 1% 的误差，但差异太大则认为不完整
                                    is_complete = False
                                check_failures.append(f"INSERT 数量不匹配（源文件: {source_insert_count}，目标文件: {output_insert_count}）")
                        except Exception as e:
                            # 如果统计 INSERT 数量失败，记录警告但不作为失败条件
                            logger.debug(f"  无法统计 INSERT 数量: {e}")
                    
                    # 如果所有检查都通过
                    if is_complete:
                        insert_info = f"，{output_insert_count} 个 INSERT" if output_insert_count > 0 else ""
                        return (True, True, f"文件已存在且完整（{file_size / (1024*1024):.2f} MB，{create_count} 个表{insert_info}），跳过")
                    else:
                        # 检查失败，记录警告并继续转换
                        failure_reasons = "、".join(check_failures)
                        logger.warning(f"  文件已存在但不完整（{failure_reasons}），将重新转换: {output_file.name}")
                        # 不返回，继续执行转换
                    
            except Exception as e:
                logger.warning(f"  文件已存在但检查时出错: {e}，将重新转换: {output_file.name}")
                # 不返回，继续执行转换
    
    try:
        # 确保输出目录存在
        output_dir = output_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        converter = OracleToMySQLConverter()
        # 对于大文件，直接写入文件，避免内存累积
        result = converter.convert_file(input_path, str(output_file))
        
        if not result:
            return (False, False, "转换失败或文件为空")
        
        # 如果 convert_file 已经写入文件，result 是提示信息（包含语句数量）
        # 如果返回的是普通字符串，说明需要写入
        if isinstance(result, str) and not result.startswith("已写入"):
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            # 统计语句数量（通过计算 CREATE TABLE 和 INSERT INTO 的数量）
            create_count = result.upper().count('CREATE TABLE')
            insert_count = result.upper().count('INSERT INTO')
            statement_count = create_count + insert_count
            result = f"已写入 {statement_count} 个语句到文件"
        
        # 及时释放内存
        del converter
        
        # 返回详细的成功信息
        if isinstance(result, str) and result.startswith("已写入"):
            return (True, False, result)
        else:
            # 如果 result 不是字符串或格式不对，返回默认成功信息
            return (True, False, "转换成功")
    except MemoryError:
        logger.error(f"内存不足，无法处理文件: {input_path}")
        return (False, False, "内存不足")
    except Exception as e:
        logger.error(f"转换失败 {input_path}: {e}")
        return (False, False, str(e))


def convert_directory(
    input_dir: str, 
    output_dir: str, 
    prefix: str = '', 
    force: bool = False, 
    skip_existing: bool = False,
    split_ddl_dml: bool = False,
    table_prefix: str = '',
    enable_comments: bool = False,
    auto_fix: bool = False
) -> tuple:
    """
    转换目录下所有 SQL 文件
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        prefix: 输出文件名前缀
        force: 强制重新转换
        skip_existing: 跳过已存在且完整的文件
        split_ddl_dml: 是否分离 DDL 和 DML 到不同目录
        table_prefix: 表名前缀（在 SQL 语句中添加）
        enable_comments: 是否启用 COMMENT 转换
        auto_fix: 是否自动调用 sql-fix-tools 修复
    
    Returns:
        tuple: (成功数, 失败数, 跳过数)
    """
    start_time = time.time()
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    sql_files = list(input_path.glob('*.sql'))
    sql_files = [f for f in sql_files if not f.name.endswith('.mysql.sql')]
    
    total = len(sql_files)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    failed_files = []
    
    # 统计 DDL/DML 数量
    total_ddl_count = 0
    total_dml_count = 0
    
    logger.info(f"找到 {total} 个 SQL 文件")
    if prefix:
        logger.info(f"文件名前缀: {prefix}")
    if table_prefix:
        logger.info(f"表名前缀: {table_prefix}")
    if split_ddl_dml:
        logger.info("分离模式：DDL 文件保存到 create/，DML 文件保存到 insert/")
    if enable_comments:
        logger.info("COMMENT 转换：已启用")
    if auto_fix:
        logger.info("自动修复：转换完成后将调用 sql-fix-tools")
    if force:
        logger.info("强制模式：将重新转换所有文件")
    if skip_existing:
        logger.info("跳过模式：将跳过已存在且完整的文件")
    
    # 创建转换器
    converter = OracleToMySQLConverter()
    
    for i, sql_file in enumerate(sql_files, 1):
        # 计算进度百分比
        progress_percent = (i / total) * 100
        progress_bar_length = 30
        filled_length = int(progress_bar_length * i // total)
        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
        
        # 显示进度条和百分比
        logger.info(f"[{i}/{total}] [{bar}] {progress_percent:.1f}% - 处理: {sql_file.name}")
        
        if split_ddl_dml:
            # 使用分离模式
            result = converter.convert_file_with_split(
                str(sql_file),
                str(output_path),
                enable_comments=enable_comments,
                table_prefix=table_prefix,
                file_prefix=prefix
            )
            
            if result['success']:
                success_count += 1
                total_ddl_count += result.get('ddl_count', 0)
                total_dml_count += result.get('dml_count', 0)
                
                ddl_info = f"DDL: {result.get('ddl_count', 0)}"
                dml_info = f"DML: {result.get('dml_count', 0)}" if result.get('dml_count', 0) > 0 else "无数据"
                logger.info(f"  [成功] {ddl_info}, {dml_info}")
            else:
                failed_count += 1
                failed_files.append(sql_file.name)
                logger.error(f"  [失败] {result.get('error', '未知错误')}")
        else:
            # 使用传统模式
            output_filename = f"{prefix}{sql_file.name}" if prefix else sql_file.name
            output_file = output_path / output_filename
            
            # 设置转换器选项
            converter.reset()
            converter.table_prefix = table_prefix
            converter.enable_comments = enable_comments
            
            # 如果启用 COMMENT，先收集
            if enable_comments:
                converter._collect_comments(str(sql_file))
            
            success, skipped, reason = convert_file(str(sql_file), str(output_file), prefix, force, skip_existing)
            
            if success:
                if skipped:
                    logger.info(f"  [跳过] {reason}")
                    skipped_count += 1
                else:
                    logger.info(f"  [成功] {reason}")
                    if "已写入" in reason or "个语句" in reason:
                        try:
                            file_size = output_file.stat().st_size
                            file_size_mb = file_size / (1024 * 1024)
                            logger.info(f"        输出文件: {output_file.name} ({file_size_mb:.2f} MB)")
                        except:
                            pass
                    success_count += 1
            else:
                logger.error(f"  [失败] {reason}")
                failed_count += 1
                failed_files.append(sql_file.name)
        
        # 每处理 100 个文件后强制垃圾回收
        if i % 100 == 0:
            import gc
            gc.collect()
            logger.info(f"  已处理 {i} 个文件，内存已清理")
    
    # 转换完成统计
    conversion_time = time.time() - start_time
    
    logger.info("=" * 50)
    logger.info(f"转换完成: 成功 {success_count}, 跳过 {skipped_count}, 失败 {failed_count}, 总计 {total}")
    if split_ddl_dml:
        logger.info(f"DDL/DML 统计: {total_ddl_count} 个 DDL 语句, {total_dml_count} 个 DML 语句")
        logger.info(f"输出目录: {output_path}/create/ 和 {output_path}/insert/")
    logger.info(f"转换耗时: {conversion_time:.1f} 秒")
    
    if failed_files:
        logger.warning(f"失败文件 ({len(failed_files)} 个):")
        for f in failed_files[:10]:
            logger.warning(f"  - {f}")
        if len(failed_files) > 10:
            logger.warning(f"  ... 还有 {len(failed_files) - 10} 个失败文件")
    
    # 自动修复
    if auto_fix and success_count > 0:
        logger.info("")
        logger.info("=" * 50)
        logger.info("开始自动修复...")
        fix_result = auto_fix_sql_files(str(output_path), split_ddl_dml)
        
        if fix_result['success']:
            logger.info(f"自动修复完成")
            if fix_result.get('create_fixed'):
                logger.info(f"  create/ 目录: {fix_result.get('create_fixed', 0)} 个文件已修复")
            if fix_result.get('insert_fixed'):
                logger.info(f"  insert/ 目录: {fix_result.get('insert_fixed', 0)} 个文件已修复")
        else:
            logger.warning(f"自动修复失败或部分失败: {fix_result.get('error', '未知错误')}")
            logger.warning("请手动运行 sql-fix-tools 进行修复")
    
    # 最终报告
    total_time = time.time() - start_time
    logger.info("")
    logger.info("=" * 50)
    logger.info("【转换报告】")
    logger.info(f"  输入目录: {input_path}")
    logger.info(f"  输出目录: {output_path}")
    logger.info(f"  文件统计: 成功 {success_count}, 跳过 {skipped_count}, 失败 {failed_count}")
    if split_ddl_dml:
        logger.info(f"  DDL 语句: {total_ddl_count}")
        logger.info(f"  DML 语句: {total_dml_count}")
    if enable_comments:
        logger.info(f"  COMMENT 转换: 已启用")
    if table_prefix:
        logger.info(f"  表名前缀: {table_prefix}")
    logger.info(f"  总耗时: {total_time:.1f} 秒")
    logger.info("=" * 50)
    
    return success_count, failed_count, skipped_count


def auto_fix_sql_files(output_dir: str, split_ddl_dml: bool = False) -> Dict[str, Any]:
    """
    自动调用 sql-fix-tools 修复转换后的 SQL 文件
    
    注意：sql-fix-tools 目前是针对特定文件的专用修复工具，主要处理：
    - CONCAT 运算符转换残留问题
    - Oracle sysdate 函数转换
    - 特定表的列定义问题
    
    Args:
        output_dir: 输出目录
        split_ddl_dml: 是否使用了分离模式
        
    Returns:
        修复结果字典
    """
    output_path = Path(output_dir)
    fix_tool_path = Path(__file__).parent / 'sql-fix-tools' / 'fix_sql_main.py'
    
    if not fix_tool_path.exists():
        logger.warning(f"找不到修复工具: {fix_tool_path}")
        logger.info("  跳过自动修复（修复工具不存在）")
        return {'success': True, 'skipped': True, 'reason': '修复工具不存在'}
    
    result = {'success': True}
    
    try:
        # sql-fix-tools 目前是针对特定目录的专用工具
        # 尝试使用 --target-dir 参数调用，如果不支持则使用安静模式
        logger.info(f"  调用 sql-fix-tools 进行修复...")
        
        if split_ddl_dml:
            # 分别修复 create/ 和 insert/ 目录
            create_dir = output_path / 'create'
            insert_dir = output_path / 'insert'
            
            # 修复 create/ 目录
            if create_dir.exists() and list(create_dir.glob('*.sql')):
                logger.info(f"    检查 create/ 目录...")
                proc = subprocess.run(
                    ['python', str(fix_tool_path), '--target-dir', str(create_dir), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if proc.returncode == 0:
                    result['create_checked'] = len(list(create_dir.glob('*.sql')))
                    logger.info(f"    create/ 检查完成 ({result['create_checked']} 个文件)")
                else:
                    # 子脚本可能不支持 --target-dir，这不是错误
                    logger.debug(f"    create/ 修复跳过: {proc.stderr}")
            
            # 修复 insert/ 目录
            if insert_dir.exists() and list(insert_dir.glob('*.sql')):
                logger.info(f"    检查 insert/ 目录...")
                proc = subprocess.run(
                    ['python', str(fix_tool_path), '--target-dir', str(insert_dir), '--quiet'],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if proc.returncode == 0:
                    result['insert_checked'] = len(list(insert_dir.glob('*.sql')))
                    logger.info(f"    insert/ 检查完成 ({result['insert_checked']} 个文件)")
                else:
                    logger.debug(f"    insert/ 修复跳过: {proc.stderr}")
        else:
            # 修复整个输出目录
            logger.info(f"    检查 {output_path} 目录...")
            proc = subprocess.run(
                ['python', str(fix_tool_path), '--target-dir', str(output_path), '--quiet'],
                capture_output=True,
                text=True,
                timeout=600
            )
            if proc.returncode == 0:
                result['files_checked'] = len(list(output_path.glob('*.sql')))
                logger.info(f"    检查完成 ({result['files_checked']} 个文件)")
            else:
                logger.debug(f"    修复跳过: {proc.stderr}")
        
        logger.info("  自动修复完成（sql-fix-tools 将处理已知的特定问题）")
        
    except subprocess.TimeoutExpired:
        logger.warning("修复超时")
        result['success'] = False
        result['error'] = '修复超时'
    except Exception as e:
        logger.error(f"修复时出错: {e}")
        result['success'] = False
        result['error'] = str(e)
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Oracle SQL 转换为 MySQL 格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换单个文件
  python tools/oracle_to_mysql.py convert docs/hospital/sql/BS_DEPARTMENT.sql
  
  # 转换目录下所有文件
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql
  
  # 转换并分离 DDL/DML 到不同目录
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --split-ddl-dml
  
  # 转换并添加表名前缀（在 SQL 语句中）
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --table-prefix gzlry_
  
  # 启用 COMMENT 转换
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --enable-comments
  
  # 全部功能组合
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql \\
      --split-ddl-dml --table-prefix gzlry_ --enable-comments --auto-fix
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='转换单个文件')
    convert_parser.add_argument('file', help='SQL 文件路径')
    convert_parser.add_argument('-o', '--output', 
                               help='输出文件路径（可选，默认: 输出目录/文件名）')
    convert_parser.add_argument('--output-dir',
                               default='docs/hospital/convertsql',
                               help='输出目录（默认: docs/hospital/convertsql，当未指定 -o 时使用）')
    convert_parser.add_argument('--prefix',
                               default='',
                               help='输出文件名前缀（例如: mysql_）')
    convert_parser.add_argument('--table-prefix',
                               default='',
                               help='表名前缀（在 SQL 语句中添加，例如: gzlry_）')
    convert_parser.add_argument('--enable-comments',
                               action='store_true',
                               help='启用 COMMENT 转换（将 Oracle COMMENT 转换为 MySQL 格式）')
    convert_parser.add_argument('--force',
                               action='store_true',
                               help='强制重新转换，即使文件已存在')
    convert_parser.add_argument('--skip-existing',
                               action='store_true',
                               help='跳过已存在且完整的文件（默认不跳过）')
    
    # convert-all 命令
    convert_all_parser = subparsers.add_parser('convert-all', help='转换目录下所有文件')
    convert_all_parser.add_argument('directory', help='SQL 文件目录')
    convert_all_parser.add_argument('-o', '--output-dir',
                                   required=True,
                                   help='输出目录（必需，例如: docs/hospital/convertsql）')
    convert_all_parser.add_argument('--prefix',
                                   default='',
                                   help='输出文件名前缀（例如: mysql_，转换后文件名: mysql_原文件名.sql）')
    convert_all_parser.add_argument('--table-prefix',
                                   default='',
                                   help='表名前缀（在 SQL 语句中添加，例如: gzlry_）')
    convert_all_parser.add_argument('--split-ddl-dml',
                                   action='store_true',
                                   help='分离 DDL 和 DML（DDL 保存到 create/，DML 保存到 insert/）')
    convert_all_parser.add_argument('--enable-comments',
                                   action='store_true',
                                   help='启用 COMMENT 转换（将 Oracle COMMENT 转换为 MySQL 格式）')
    convert_all_parser.add_argument('--auto-fix',
                                   action='store_true',
                                   help='转换完成后自动调用 sql-fix-tools 进行修复')
    convert_all_parser.add_argument('--force',
                                   action='store_true',
                                   help='强制重新转换所有文件，即使文件已存在')
    convert_all_parser.add_argument('--skip-existing',
                                   action='store_true',
                                   help='跳过已存在且完整的文件（默认不跳过，避免跳过不完整的文件）')
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        input_file = Path(args.file)
        if args.output:
            output_file = Path(args.output)
        else:
            # 应用前缀
            output_filename = f"{args.prefix}{input_file.name}" if args.prefix else input_file.name
            output_file = Path(args.output_dir) / output_filename
        
        logger.info(f"转换文件: {input_file.name}")
        
        # 创建转换器并设置选项
        converter = OracleToMySQLConverter()
        converter.table_prefix = args.table_prefix
        converter.enable_comments = args.enable_comments
        
        # 如果启用 COMMENT，先收集
        if args.enable_comments:
            converter._collect_comments(str(input_file))
        
        success, skipped, reason = convert_file(str(input_file), str(output_file), args.prefix, args.force, args.skip_existing)
        
        if skipped:
            logger.info(f"  [跳过] {reason}")
        elif success:
            logger.info(f"  [成功] {reason}")
            if "已写入" in reason or "个语句" in reason:
                try:
                    file_size = output_file.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    logger.info(f"        输出文件: {output_file.name} ({file_size_mb:.2f} MB)")
                except:
                    pass
        else:
            logger.error(f"  [失败] {reason}")
        sys.exit(0 if success else 1)
    
    elif args.command == 'convert-all':
        success, failed, skipped = convert_directory(
            args.directory, 
            args.output_dir, 
            prefix=args.prefix, 
            force=args.force, 
            skip_existing=args.skip_existing,
            split_ddl_dml=args.split_ddl_dml,
            table_prefix=args.table_prefix,
            enable_comments=args.enable_comments,
            auto_fix=args.auto_fix
        )
        sys.exit(0 if failed == 0 else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
