#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oracle to MySQL SQL 转换工具

将 Oracle PL/SQL Developer 导出的 SQL 文件转换为 MySQL 兼容格式。
只保留表结构和数据（CREATE TABLE 和 INSERT 语句）。

使用方法：
    # 转换单个文件
    python tools/oracle_to_mysql.py convert docs/hospital/sql/BS_DEPARTMENT.sql
    
    # 转换目录下所有文件
    python tools/oracle_to_mysql.py convert-all docs/hospital/sql/
"""

import re
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class OracleToMySQLConverter:
    """Oracle SQL 到 MySQL 的转换器（只保留表结构和数据）"""
    
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
    
    def _convert_statement(self, stmt: str) -> Optional[str]:
        """转换单个 SQL 语句，只保留 CREATE TABLE 和 INSERT"""
        stmt_upper = stmt.upper().strip()
        
        # 只处理 CREATE TABLE 和 INSERT INTO
        if stmt_upper.startswith('CREATE TABLE'):
            return self._convert_create_table(stmt)
        elif stmt_upper.startswith('INSERT INTO'):
            return self._convert_insert(stmt)
        else:
            # 忽略其他语句（COMMENT、ALTER、DELETE、COMMIT 等）
            return None
    
    def _convert_create_table(self, stmt: str) -> str:
        """转换 CREATE TABLE 语句"""
        result = stmt
        
        # 提取表名
        table_match = re.search(r'CREATE\s+TABLE\s+(\w+)', result, re.IGNORECASE)
        table_name = table_match.group(1) if table_match else None
        
        # 转换数据类型
        for oracle_type, mysql_type in self.TYPE_MAPPING.items():
            result = re.sub(oracle_type, mysql_type, result, flags=re.IGNORECASE)
        
        # 特殊处理 DATE 类型
        result = re.sub(self.DATE_TYPE_PATTERN, r'\1DATETIME\2', result, flags=re.IGNORECASE)
        
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
        
        # 清理多余的空行
        result = re.sub(r'\n\s*\n+', '\n', result)
        
        # 添加 DROP TABLE IF EXISTS
        if table_name:
            result = f"DROP TABLE IF EXISTS {table_name};\n\n{result}"
        
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


def convert_directory(input_dir: str, output_dir: str, prefix: str = '', force: bool = False, skip_existing: bool = False) -> tuple:
    """
    转换目录下所有 SQL 文件
    
    Returns:
        tuple: (成功数, 失败数, 跳过数)
    """
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
    
    logger.info(f"找到 {total} 个 SQL 文件")
    if prefix:
        logger.info(f"文件名前缀: {prefix}")
    if force:
        logger.info("强制模式：将重新转换所有文件")
    if skip_existing:
        logger.info("跳过模式：将跳过已存在且完整的文件")
    
    for i, sql_file in enumerate(sql_files, 1):
        # 计算进度百分比
        progress_percent = (i / total) * 100
        progress_bar_length = 30
        filled_length = int(progress_bar_length * i // total)
        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
        
        # 显示进度条和百分比
        logger.info(f"[{i}/{total}] [{bar}] {progress_percent:.1f}% - 处理: {sql_file.name}")
        
        # 应用前缀
        output_filename = f"{prefix}{sql_file.name}" if prefix else sql_file.name
        output_file = output_path / output_filename
        
        success, skipped, reason = convert_file(str(sql_file), str(output_file), prefix, force, skip_existing)
        
        if success:
            if skipped:
                logger.info(f"  [跳过] {reason}")
                skipped_count += 1
            else:
                # 输出详细的成功信息
                logger.info(f"  [成功] {reason}")
                # 如果包含语句数量信息，额外显示文件大小
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
        
        # 每处理 100 个文件后强制垃圾回收，释放内存
        if i % 100 == 0:
            import gc
            gc.collect()
            logger.info(f"  已处理 {i} 个文件，内存已清理")
    
    logger.info("=" * 50)
    logger.info(f"转换完成: 成功 {success_count}, 跳过 {skipped_count}, 失败 {failed_count}, 总计 {total}")
    if failed_files:
        logger.warning(f"失败文件 ({len(failed_files)} 个):")
        for f in failed_files[:10]:  # 只显示前 10 个
            logger.warning(f"  - {f}")
        if len(failed_files) > 10:
            logger.warning(f"  ... 还有 {len(failed_files) - 10} 个失败文件")
    
    return success_count, failed_count, skipped_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Oracle SQL 转换为 MySQL 格式（只保留表结构和数据）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换单个文件
  python tools/oracle_to_mysql.py convert docs/hospital/sql/BS_DEPARTMENT.sql
  
  # 转换目录下所有文件（必须指定输出目录）
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql
  
  # 转换目录下所有文件，并添加文件名前缀
  python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql --prefix mysql_
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
        success, skipped, reason = convert_file(str(input_file), str(output_file), args.prefix, args.force, args.skip_existing)
        
        if skipped:
            logger.info(f"  [跳过] {reason}")
        elif success:
            logger.info(f"  [成功] {reason}")
            # 如果包含语句数量信息，额外显示文件大小
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
        success, failed, skipped = convert_directory(args.directory, args.output_dir, args.prefix, args.force, args.skip_existing)
        sys.exit(0 if failed == 0 else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
