# -*- coding: utf-8 -*-
"""
SQL 语法修复器

用于自动修复 MySQL SQL 语句中的常见语法错误，特别是 MySQL 保留字冲突问题。
"""

import re
from typing import List, Tuple, Dict


class SQLSyntaxFixer:
    """SQL 语法修复器"""
    
    # MySQL 8.0 保留字列表（完整版）
    # 参考: https://dev.mysql.com/doc/refman/8.0/en/keywords.html
    MYSQL_RESERVED_WORDS = {
        'accessible', 'add', 'all', 'alter', 'analyze', 'and', 'as', 'asc',
        'asensitive', 'before', 'between', 'bigint', 'binary', 'blob', 'both',
        'by', 'call', 'cascade', 'case', 'change', 'char', 'character', 'check',
        'collate', 'column', 'condition', 'constraint', 'continue', 'convert',
        'create', 'cross', 'cube', 'cume_dist', 'current_date', 'current_time',
        'current_timestamp', 'current_user', 'cursor', 'database', 'databases',
        'day_hour', 'day_microsecond', 'day_minute', 'day_second', 'dec',
        'decimal', 'declare', 'default', 'delayed', 'delete', 'dense_rank',
        'desc', 'describe', 'deterministic', 'distinct', 'distinctrow', 'div',
        'double', 'drop', 'dual', 'each', 'else', 'elseif', 'empty', 'enclosed',
        'escaped', 'except', 'exists', 'exit', 'explain', 'false', 'fetch',
        'first_value', 'float', 'float4', 'float8', 'for', 'force', 'foreign',
        'from', 'fulltext', 'function', 'generated', 'get', 'grant', 'group',
        'grouping', 'groups', 'having', 'high_priority', 'hour_microsecond',
        'hour_minute', 'hour_second', 'if', 'ignore', 'in', 'index', 'infile',
        'inner', 'inout', 'insensitive', 'insert', 'int', 'int1', 'int2',
        'int3', 'int4', 'int8', 'integer', 'interval', 'into', 'io_after_gtids',
        'io_before_gtids', 'is', 'iterate', 'join', 'json_table', 'key', 'keys',
        'kill', 'lag', 'last_value', 'lateral', 'lead', 'leading', 'leave',
        'left', 'like', 'limit', 'linear', 'lines', 'load', 'localtime',
        'localtimestamp', 'lock', 'long', 'longblob', 'longtext', 'loop',
        'low_priority', 'master_bind', 'master_ssl_verify_server_cert', 'match',
        'maxvalue', 'mediumblob', 'mediumint', 'mediumtext', 'member', 'middleint',
        'minute_microsecond', 'minute_second', 'mod', 'modifies', 'natural',
        'not', 'no_write_to_binlog', 'nth_value', 'ntile', 'null', 'numeric',
        'of', 'on', 'optimize', 'optimizer_costs', 'option', 'optionally', 'or',
        'order', 'out', 'outer', 'outfile', 'over', 'partition', 'percent_rank',
        'precision', 'primary', 'procedure', 'purge', 'range', 'rank', 'read',
        'reads', 'read_write', 'real', 'recursive', 'references', 'regexp',
        'release', 'rename', 'repeat', 'replace', 'require', 'resignal',
        'restrict', 'return', 'revoke', 'right', 'rlike', 'row', 'rows',
        'row_number', 'schema', 'schemas', 'second_microsecond', 'select',
        'sensitive', 'separator', 'set', 'show', 'signal', 'smallint', 'spatial',
        'specific', 'sql', 'sqlexception', 'sqlstate', 'sqlwarning',
        'sql_big_result', 'sql_calc_found_rows', 'sql_small_result', 'ssl',
        'starting', 'stored', 'straight_join', 'system', 'table', 'terminated',
        'then', 'tinyblob', 'tinyint', 'tinytext', 'to', 'trailing', 'trigger',
        'true', 'undo', 'union', 'unique', 'unlock', 'unsigned', 'update',
        'usage', 'use', 'using', 'utc_date', 'utc_time', 'utc_timestamp',
        'values', 'varbinary', 'varchar', 'varcharacter', 'varying', 'virtual',
        'when', 'where', 'while', 'window', 'with', 'write', 'xor',
        'year_month', 'zerofill',
    }
    
    def __init__(self, enable_report: bool = False):
        """初始化修复器
        
        Args:
            enable_report: 是否启用修复报告
        """
        self.enable_report = enable_report
        self.fixes_applied: List[Dict] = []  # 记录修复历史
        self.current_file: str = ""
        self.current_line: int = 0
    
    def fix_sql_content(self, sql_content: str, file_name: str = "") -> Tuple[str, int]:
        """修复整个 SQL 文件内容
        
        Args:
            sql_content: SQL 文件内容
            file_name: 文件名（用于报告）
        
        Returns:
            (fixed_sql, fix_count): 修复后的 SQL 和修复次数
        """
        self.current_file = file_name
        self.current_line = 0
        
        # 先修复整个文件级别的问题
        sql_content, file_fix_count = self._fix_file_level_issues(sql_content)
        
        lines = sql_content.split('\n')
        fixed_lines = []
        fix_count = file_fix_count
        
        for i, line in enumerate(lines):
            self.current_line = i + 1
            fixed_line, line_fix_count = self._fix_line(line)
            fixed_lines.append(fixed_line)
            fix_count += line_fix_count
        
        return '\n'.join(fixed_lines), fix_count
    
    def _fix_file_level_issues(self, sql_content: str) -> Tuple[str, int]:
        """修复文件级别的 SQL 问题
        
        Args:
            sql_content: SQL 文件内容
        
        Returns:
            (fixed_sql, fix_count): 修复后的 SQL 和修复次数
        """
        fix_count = 0
        
        # 1. 修复 CREATE TABLE 最后一个字段后的多余逗号
        # 模式：字段定义,\n)
        pattern = r',(\s*)\n(\s*)\)'
        
        def replace_trailing_comma(match):
            nonlocal fix_count
            # 只有当逗号后面直接跟着 ) 时才删除
            space_before_newline = match.group(1)
            space_before_paren = match.group(2)
            fix_count += 1
            return f'{space_before_newline}\n{space_before_paren})'
        
        sql_content = re.sub(pattern, replace_trailing_comma, sql_content)
        
        if fix_count > 0 and self.enable_report:
            self._record_fix(
                '移除多余逗号',
                '字段定义后的多余逗号（在 ) 之前）',
                f'已修复 {fix_count} 处'
            )
        
        # 2. 修复 NUMBER(*,n) → DECIMAL(65,n)
        number_pattern = r'\bNUMBER\s*\(\s*\*\s*,\s*(\d+)\s*\)'
        number_count = 0
        
        def replace_number_star(match):
            nonlocal number_count
            scale = match.group(1)
            number_count += 1
            return f'DECIMAL(65,{scale})'
        
        sql_content = re.sub(number_pattern, replace_number_star, sql_content, flags=re.IGNORECASE)
        
        if number_count > 0:
            fix_count += number_count
            if self.enable_report:
                self._record_fix(
                    'NUMBER(*,n) 转 DECIMAL',
                    f'NUMBER(*,n) → DECIMAL(65,n)',
                    f'已修复 {number_count} 处'
                )
        
        # 3. 修复 DOUBLE(n) → DOUBLE
        # MySQL DOUBLE 不支持单一精度参数，应该是 DOUBLE 或 DOUBLE(M,D)
        # 只匹配 DOUBLE(单个数字)，不匹配 DOUBLE(M,D)
        double_single_param_pattern = r'\bDOUBLE\s*\(\s*\d+\s*\)(?!\s*,\s*\d)'
        double_single_count = 0
        
        def replace_double_single_param(match):
            nonlocal double_single_count
            double_single_count += 1
            return 'DOUBLE'
        
        sql_content = re.sub(double_single_param_pattern, replace_double_single_param, sql_content, flags=re.IGNORECASE)
        
        if double_single_count > 0:
            fix_count += double_single_count
            if self.enable_report:
                self._record_fix(
                    'DOUBLE(n) 转 DOUBLE',
                    'DOUBLE(n) → DOUBLE',
                    f'已修复 {double_single_count} 处'
                )
        
        # 4. 修复 NVARCHAR → VARCHAR
        nvarchar_pattern = r'\bNVARCHAR\b'
        nvarchar_count = 0
        
        def replace_nvarchar(match):
            nonlocal nvarchar_count
            nvarchar_count += 1
            return 'VARCHAR'
        
        sql_content = re.sub(nvarchar_pattern, replace_nvarchar, sql_content, flags=re.IGNORECASE)
        
        if nvarchar_count > 0:
            fix_count += nvarchar_count
            if self.enable_report:
                self._record_fix(
                    'NVARCHAR 转 VARCHAR',
                    'NVARCHAR → VARCHAR',
                    f'已修复 {nvarchar_count} 处'
                )
        
        # 5. 修复字符串中的单个反斜杠 → 双反斜杠
        # MySQL 中反斜杠是转义字符，单个 '\' 需要转义为 '\\'
        backslash_count = 0
        
        # 模式：匹配 '\' 后面跟单引号和逗号（在 VALUES 中）
        # raw 字符串 r"'\\'" 中的 \\ 表示一个反斜杠
        backslash_pattern = r"'\\'\s*,"
        matches = re.findall(backslash_pattern, sql_content)
        
        if matches:
            # 替换为 '\\' （两个反斜杠）
            # raw 字符串 r"'\\\\'" 中的 \\\\ 表示两个反斜杠
            sql_content = re.sub(backslash_pattern, r"'\\\\',", sql_content)
            backslash_count = len(matches)
        
        if backslash_count > 0:
            fix_count += backslash_count
            if self.enable_report:
                self._record_fix(
                    '反斜杠转义',
                    r"'\' → '\\\\'",
                    f'已修复 {backslash_count} 处'
                )
        
        # 6. 修复双引号标识符 → 反引号
        # 例如："date" → `date`
        double_quote_pattern = r'"([a-zA-Z_][a-zA-Z0-9_]*)"'
        double_quote_count = 0
        
        def replace_double_quote(match):
            nonlocal double_quote_count
            identifier = match.group(1)
            # 检查是否在字符串字面量中（简单判断：前面是否有单引号）
            # 这里我们只替换看起来像列名的情况
            double_quote_count += 1
            return f'`{identifier}`'
        
        sql_content = re.sub(double_quote_pattern, replace_double_quote, sql_content)
        
        if double_quote_count > 0:
            fix_count += double_quote_count
            if self.enable_report:
                self._record_fix(
                    '双引号转反引号',
                    '"identifier" → `identifier`',
                    f'已修复 {double_quote_count} 处'
                )
        
        # 7. 修复 Oracle 函数 → MySQL 函数
        # sysdate → CURRENT_TIMESTAMP
        oracle_func_replacements = [
            (r'\bsysdate\b', 'CURRENT_TIMESTAMP'),
            (r'\bSYSDATE\b', 'CURRENT_TIMESTAMP'),
        ]
        
        oracle_func_count = 0
        for pattern, replacement in oracle_func_replacements:
            matches = re.findall(pattern, sql_content)
            if matches:
                sql_content = re.sub(pattern, replacement, sql_content)
                oracle_func_count += len(matches)
        
        # 6b. 修复 to_timestamp() → STR_TO_DATE()
        # Oracle: to_timestamp('15-03-2021 00:00:00.000000', 'dd-mm-yyyy hh24:mi:ss.ff')
        # MySQL: STR_TO_DATE('15-03-2021 00:00:00', '%d-%m-%Y %H:%i:%s')
        to_timestamp_pattern = r"to_timestamp\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)"
        
        def replace_to_timestamp(match):
            nonlocal oracle_func_count
            date_str = match.group(1)
            format_str = match.group(2)
            
            # 移除微秒部分（.000000）
            date_str = re.sub(r'\.\d+$', '', date_str)
            
            # 转换格式字符串从 Oracle 到 MySQL
            # Oracle -> MySQL 格式映射
            format_mapping = {
                'dd': '%d',
                'mm': '%m',
                'yyyy': '%Y',
                'hh24': '%H',
                'mi': '%i',
                'ss': '%s',
                'ff': '',  # 微秒，MySQL 用 %f，但我们已移除
            }
            
            mysql_format = format_str.lower()
            for oracle_fmt, mysql_fmt in format_mapping.items():
                mysql_format = mysql_format.replace(oracle_fmt, mysql_fmt)
            
            # 移除 .ff 及其前面的点
            mysql_format = re.sub(r'\.\s*$', '', mysql_format)
            
            oracle_func_count += 1
            return f"STR_TO_DATE('{date_str}', '{mysql_format}')"
        
        sql_content = re.sub(to_timestamp_pattern, replace_to_timestamp, sql_content, flags=re.IGNORECASE)
        
        # 6c. 移除 Oracle 特定的 ALTER TABLE ... ENABLE ALL TRIGGERS
        # 这在 MySQL 中不支持，直接注释掉
        trigger_pattern = r'^\s*alter\s+table\s+\w+\s+enable\s+all\s+triggers\s*;?\s*$'
        trigger_matches = re.findall(trigger_pattern, sql_content, flags=re.IGNORECASE | re.MULTILINE)
        if trigger_matches:
            sql_content = re.sub(trigger_pattern, '-- \\g<0> (Oracle specific, removed)', sql_content, flags=re.IGNORECASE | re.MULTILINE)
            oracle_func_count += len(trigger_matches)
        
        # 6d. 移除 Oracle 特定的 ALTER TABLE ... ENABLE CONSTRAINT
        # MySQL 不支持 ENABLE/DISABLE CONSTRAINT 语法
        constraint_pattern = r'^\s*alter\s+table\s+\w+\s+enable\s+constraint\s+[\w_]+\s*;?\s*$'
        constraint_matches = re.findall(constraint_pattern, sql_content, flags=re.IGNORECASE | re.MULTILINE)
        if constraint_matches:
            sql_content = re.sub(constraint_pattern, '-- \\g<0> (Oracle specific, removed)', sql_content, flags=re.IGNORECASE | re.MULTILINE)
            oracle_func_count += len(constraint_matches)
        
        if oracle_func_count > 0:
            fix_count += oracle_func_count
            if self.enable_report:
                self._record_fix(
                    'Oracle 函数转 MySQL',
                    'sysdate/to_timestamp → CURRENT_TIMESTAMP/STR_TO_DATE',
                    f'已修复 {oracle_func_count} 处'
                )
        
        # 7. 修复 Oracle 字符串连接符 || → CONCAT()
        # 策略：递归替换，每次处理最简单的情况
        # 注意：SQL 字符串中的单引号转义为 ''
        concat_count = 0
        
        if '||' in sql_content:
            max_iterations = 100  # 防止无限循环
            iteration = 0
            
            while '||' in sql_content and iteration < max_iterations:
                iteration += 1
                old_content = sql_content
                
                # 模式1: CONCAT(...) || 'string' -> CONCAT(..., 'string')
                # 使用非贪婪匹配，避免嵌套括号问题
                # (?:[^']|'')* 匹配：非单引号字符或两个连续单引号（转义的单引号）
                pattern1 = r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*'((?:[^']|'')*)'"
                sql_content = re.sub(pattern1, r"CONCAT(\1, '\2')", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式2: 'string' || CONCAT(...) -> CONCAT('string', ...)
                pattern2 = r"'((?:[^']|'')*)'\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
                sql_content = re.sub(pattern2, r"CONCAT('\1', \2)", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式3: 'string1' || 'string2' -> CONCAT('string1', 'string2')
                pattern3 = r"'((?:[^']|'')*)'\s*\|\|\s*'((?:[^']|'')*)'"
                sql_content = re.sub(pattern3, r"CONCAT('\1', '\2')", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式4: FUNC(...) || 'string' -> CONCAT(FUNC(...), 'string')
                # 匹配简单的函数调用（不含嵌套括号）
                pattern4 = r"(\w+\([^()]+\))\s*\|\|\s*'((?:[^']|'')*)'"
                sql_content = re.sub(pattern4, r"CONCAT(\1, '\2')", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式5: 'string' || FUNC(...) -> CONCAT('string', FUNC(...))
                pattern5 = r"'((?:[^']|'')*)'\s*\|\|\s*(\w+\([^()]+\))"
                sql_content = re.sub(pattern5, r"CONCAT('\1', \2)", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式6: CONCAT(...) || CONCAT(...) -> CONCAT(..., ...)
                pattern6 = r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
                sql_content = re.sub(pattern6, r"CONCAT(\1, \2)", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式7: CONCAT(...) || FUNC(...) -> CONCAT(..., FUNC(...))
                pattern7 = r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*(\w+\([^()]+\))"
                sql_content = re.sub(pattern7, r"CONCAT(\1, \2)", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 模式8: FUNC(...) || CONCAT(...) -> CONCAT(FUNC(...), ...)
                pattern8 = r"(\w+\([^()]+\))\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
                sql_content = re.sub(pattern8, r"CONCAT(\1, \2)", sql_content)
                if sql_content != old_content:
                    concat_count += 1
                    continue
                
                # 如果没有任何替换发生，退出循环
                break
        
        if concat_count > 0:
            fix_count += concat_count
            if self.enable_report:
                self._record_fix(
                    'Oracle 字符串连接符转换',
                    'expr1 || expr2 → CONCAT(expr1, expr2)',
                    f'已修复 {concat_count} 处'
                )
        
        # 8. 智能修复 INT 溢出 → BIGINT
        # 扫描 CREATE TABLE 和 INSERT 语句，检测 INT 列是否有超出范围的值
        int_to_bigint_count = 0
        
        # 分析 CREATE TABLE 找到 INT 类型的列
        create_table_pattern = r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\)\s*ENGINE'
        create_matches = re.finditer(create_table_pattern, sql_content, flags=re.IGNORECASE | re.DOTALL)
        
        for create_match in create_matches:
            table_name = create_match.group(1)
            table_def = create_match.group(2)
            
            # 找到所有 INT 类型的列（不包括 BIGINT）
            int_columns = []
            for line in table_def.split('\n'):
                # 匹配列定义：列名 INT
                col_match = re.search(r'^\s*(\w+)\s+INT\b', line.strip(), re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    int_columns.append(col_name)
            
            if not int_columns:
                continue
            
            # 查找这个表的 INSERT 语句，检查是否有超出 INT 范围的值
            insert_pattern = r'INSERT\s+INTO\s+' + table_name + r'\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)'
            insert_matches = re.finditer(insert_pattern, sql_content, flags=re.IGNORECASE)
            
            columns_need_bigint = set()
            INT_MAX = 2147483647
            
            for insert_match in insert_matches:
                columns_str = insert_match.group(1)
                values_str = insert_match.group(2)
                
                # 解析列名列表
                columns = [c.strip().strip('`').strip('"') for c in columns_str.split(',')]
                
                # 解析值列表（需要处理字符串中的逗号）
                # 简单处理：分割并清理
                values = []
                in_string = False
                current_value = ''
                for char in values_str:
                    if char == "'" and (not current_value or current_value[-1] != '\\'):
                        in_string = not in_string
                    if char == ',' and not in_string:
                        values.append(current_value.strip())
                        current_value = ''
                    else:
                        current_value += char
                if current_value:
                    values.append(current_value.strip())
                
                # 检查 INT 列的值是否超出范围
                for i, col in enumerate(columns):
                    if col in int_columns and i < len(values):
                        value = values[i].strip()
                        # 跳过 null 和非数字值
                        if value.lower() != 'null' and value.isdigit():
                            try:
                                int_value = int(value)
                                if int_value > INT_MAX:
                                    columns_need_bigint.add(col)
                            except:
                                pass
            
            # 将需要升级的列从 INT 改为 BIGINT
            for col in columns_need_bigint:
                # 在 CREATE TABLE 定义中替换
                col_pattern = r'\b' + col + r'\s+INT\b'
                old_content = sql_content
                sql_content = re.sub(col_pattern, f'{col} BIGINT', sql_content, flags=re.IGNORECASE)
                if sql_content != old_content:
                    int_to_bigint_count += 1
        
        if int_to_bigint_count > 0:
            fix_count += int_to_bigint_count
            if self.enable_report:
                self._record_fix(
                    'INT 溢出转 BIGINT',
                    'INT → BIGINT (数据值超出范围)',
                    f'已修复 {int_to_bigint_count} 处'
                )
        
        return sql_content, fix_count
    
    def _fix_line(self, line: str) -> Tuple[str, int]:
        """修复单行 SQL
        
        Args:
            line: SQL 行
        
        Returns:
            (fixed_line, fix_count): 修复后的行和修复次数
        """
        # 跳过注释行
        if line.strip().startswith('--'):
            return line, 0
        
        original_line = line
        fix_count = 0
        
        # 检查是否是 CREATE TABLE 或 INSERT INTO 语句，或者是列定义行
        line_upper = line.upper().strip()
        
        # 需要修复的情况：
        # 1. 包含 CREATE TABLE
        # 2. 包含 INSERT INTO
        # 3. 包含列定义（包含数据类型关键字且有字母）
        has_data_type = any(dtype in line_upper for dtype in [
            'VARCHAR', 'INT', 'BIGINT', 'TEXT', 'DATETIME', 'DATE', 
            'DECIMAL', 'FLOAT', 'DOUBLE', 'CHAR', 'TIMESTAMP'
        ])
        
        if 'CREATE TABLE' in line_upper or 'INSERT INTO' in line_upper or \
           (',' in line and any(c.isalpha() for c in line)) or \
           (has_data_type and any(c.isalpha() for c in line)):
            # 先修复大 VARCHAR（防止行大小超限）
            fixed_line, varchar_count = self._fix_large_varchar(line)
            if varchar_count > 0:
                if self.enable_report:
                    self._record_fix(
                        '大 VARCHAR 转 TEXT',
                        original_line.strip(),
                        fixed_line.strip()
                    )
                line = fixed_line
                fix_count += varchar_count
            
            # 再修复特殊字符列名（如 line# → `line#`）
            fixed_line, special_count = self._fix_special_chars_in_column_names(line)
            if special_count > 0:
                if self.enable_report:
                    self._record_fix(
                        '特殊字符列名修复',
                        original_line.strip(),
                        fixed_line.strip()
                    )
                line = fixed_line
                fix_count += special_count
            
            # 再修复保留字
            fixed_line, count = self._fix_reserved_words_in_line(line)
            if count > 0:
                if self.enable_report:
                    self._record_fix(
                        'MySQL 保留字修复',
                        original_line.strip(),
                        fixed_line.strip()
                    )
                line = fixed_line
                fix_count += count
        
        return line, fix_count
    
    def _fix_trailing_comma(self, line: str) -> Tuple[str, int]:
        """修复字段定义后多余的逗号（仅在下一行是 ')' 的情况）
        
        这个方法需要配合整体文件上下文使用，这里只做简单处理：
        如果一行只包含逗号和空格/括号，移除逗号
        
        Args:
            line: SQL 行
        
        Returns:
            (fixed_line, fix_count): 修复后的行和修复次数
        """
        fix_count = 0
        
        # 只处理看起来像 "  ,\n" 或 "字段,\n)\n" 这样的情况
        # 更安全的做法：不在这里修复，而是在 SQL 文件级别修复
        # 这里暂时返回原样
        
        return line, fix_count
    
    def _fix_large_varchar(self, line: str) -> Tuple[str, int]:
        """修复大 VARCHAR 字段（转为 TEXT，防止行大小超限）
        
        MySQL 单行最大 65535 字节，UTF8MB4 下 VARCHAR(n) 最多占 4*n 字节
        将 VARCHAR(1000+) 转为 TEXT 类型
        
        Args:
            line: SQL 行
        
        Returns:
            (fixed_line, fix_count): 修复后的行和修复次数
        """
        fix_count = 0
        
        # 匹配 VARCHAR(n)，其中 n >= 1000
        # 例如：VARCHAR(4000) → TEXT
        #       VARCHAR(2000) → TEXT
        varchar_pattern = r'\bVARCHAR\((\d+)\)'
        
        def replace_large_varchar(match):
            nonlocal fix_count
            size = int(match.group(1))
            # 如果 VARCHAR 长度 >= 1000，转为 TEXT
            if size >= 1000:
                fix_count += 1
                return 'TEXT'
            return match.group(0)
        
        line = re.sub(varchar_pattern, replace_large_varchar, line, flags=re.IGNORECASE)
        
        return line, fix_count
    
    def _fix_special_chars_in_column_names(self, line: str) -> Tuple[str, int]:
        """修复列名中的特殊字符（如 line# → `line#`）
        
        Args:
            line: SQL 行
        
        Returns:
            (fixed_line, fix_count): 修复后的行和修复次数
        """
        fix_count = 0
        
        # 匹配包含特殊字符的列名模式
        # 格式：标识符+特殊字符 空格 数据类型
        # 例如：line# DECIMAL(38,0)
        #      field@ VARCHAR(100)
        special_char_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*[#@$%&])\s+(VARCHAR|INT|BIGINT|TEXT|DATETIME|DATE|DECIMAL|FLOAT|DOUBLE|CHAR|TINYINT|SMALLINT|MEDIUMINT|LONGTEXT|MEDIUMTEXT|TINYTEXT|BLOB|LONGBLOB|MEDIUMBLOB|TINYBLOB|TIMESTAMP|TIME|YEAR|BINARY|VARBINARY|ENUM|SET|JSON|BIT)(?=\s*[\(,\)\s\n]|$)'
        
        def replace_special_char_column(match):
            nonlocal fix_count
            col_name = match.group(1)
            data_type = match.group(2)
            # 检查是否在字符串内
            prefix = line[:match.start()]
            if prefix.count("'") % 2 == 1:  # 在字符串内
                return match.group(0)
            # 检查是否已经有反引号
            if prefix.rstrip().endswith('`'):
                return match.group(0)
            fix_count += 1
            # 保留原始的空格数量
            original_spaces = match.group(0)[len(col_name):len(match.group(0)) - len(data_type)]
            return f'`{col_name}`{original_spaces}{data_type}'
        
        line = re.sub(special_char_pattern, replace_special_char_column, line, flags=re.IGNORECASE)
        
        return line, fix_count
    
    def _fix_reserved_words_in_line(self, line: str) -> Tuple[str, int]:
        """修复行中的 MySQL 保留字
        
        Args:
            line: SQL 行
        
        Returns:
            (fixed_line, fix_count): 修复后的行和修复次数
        """
        fix_count = 0
        
        # 构建保留字模式（不区分大小写）
        reserved_words_pattern = '|'.join(self.MYSQL_RESERVED_WORDS)
        
        # 模式 1: CREATE TABLE 中的列定义
        # 格式: 列名 数据类型 [约束]
        # 例如: describe VARCHAR(4000),
        #       key VARCHAR(50),
        #       describe  VARCHAR(400)  -- 注意：支持多个空格
        # 匹配：标识符 + 一个或多个空格 + 数据类型
        # 后面可以跟：括号、逗号、换行、空格等
        pattern1 = r'\b(' + reserved_words_pattern + r')\s+(VARCHAR|INT|BIGINT|TEXT|DATETIME|DATE|DECIMAL|FLOAT|DOUBLE|CHAR|TINYINT|SMALLINT|MEDIUMINT|LONGTEXT|MEDIUMTEXT|TINYTEXT|BLOB|LONGBLOB|MEDIUMBLOB|TINYBLOB|TIMESTAMP|TIME|YEAR|BINARY|VARBINARY|ENUM|SET|JSON|BIT)(?=\s*[\(,\)\s\n]|$)'
        
        def replace_reserved_word(match):
            nonlocal fix_count
            word = match.group(1)
            data_type = match.group(2)
            # 检查是否在字符串内（简单检查：查找前面是否有未闭合的单引号）
            prefix = line[:match.start()]
            if prefix.count("'") % 2 == 1:  # 在字符串内
                return match.group(0)
            # 检查是否已经有反引号
            if prefix.rstrip().endswith('`'):
                return match.group(0)
            fix_count += 1
            # 保留原始的空格数量
            original_spaces = match.group(0)[len(word):len(match.group(0)) - len(data_type)]
            return f'`{word}`{original_spaces}{data_type}'
        
        line = re.sub(pattern1, replace_reserved_word, line, flags=re.IGNORECASE)
        
        # 模式 2: CREATE TABLE 表名
        # 格式: CREATE TABLE 表名 (
        # 只匹配紧跟在 CREATE TABLE 后的标识符（且不是已知的 SQL 关键字上下文）
        pattern2 = r'\bCREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\s+)(' + reserved_words_pattern + r')\s*\('
        
        def replace_table_name(match):
            nonlocal fix_count
            word = match.group(1)
            fix_count += 1
            return f'CREATE TABLE `{word}` ('
        
        line = re.sub(pattern2, replace_table_name, line, flags=re.IGNORECASE)
        
        # 模式 3: INSERT INTO 表名
        # 格式: INSERT INTO 表名 (列1, 列2, ...)
        # 只匹配紧跟在 INSERT INTO 后的标识符
        pattern3 = r'\bINSERT\s+INTO\s+(' + reserved_words_pattern + r')\s*[\(\s]'
        
        def replace_insert_table(match):
            nonlocal fix_count
            word = match.group(1)
            # 检查这个词是否真的是表名（后面跟 ( 或空格）
            suffix = match.group(0)[match.end(1) - match.start():]
            fix_count += 1
            return f'INSERT INTO `{word}`{suffix}'
        
        line = re.sub(pattern3, replace_insert_table, line, flags=re.IGNORECASE)
        
        # 模式 4: INSERT 语句中的列名（在括号内）
        # 格式: INSERT INTO table (col1, col2, reserved_word, col3)
        # 匹配逗号分隔的标识符
        if 'INSERT' in line.upper():
            # 匹配括号内的保留字列名：, reserved_word, 或 (reserved_word,
            insert_col_pattern = r'([,\(]\s*)(' + reserved_words_pattern + r')(\s*[,\)])'
            
            def replace_insert_column(match):
                nonlocal fix_count
                prefix = match.group(1)
                word = match.group(2)
                suffix = match.group(3)
                # 检查是否在字符串内
                line_prefix = line[:match.start()]
                if line_prefix.count("'") % 2 == 1:  # 在字符串内
                    return match.group(0)
                # 检查是否已经有反引号
                if '`' in prefix or '`' in suffix:
                    return match.group(0)
                fix_count += 1
                return f'{prefix}`{word}`{suffix}'
            
            line = re.sub(insert_col_pattern, replace_insert_column, line, flags=re.IGNORECASE)
        
        return line, fix_count
    
    def _record_fix(self, fix_type: str, before: str, after: str):
        """记录修复信息"""
        self.fixes_applied.append({
            'file': self.current_file,
            'line': self.current_line,
            'type': fix_type,
            'before': before,
            'after': after
        })
    
    def generate_report(self) -> str:
        """生成修复报告
        
        Returns:
            修复报告文本
        """
        if not self.fixes_applied:
            return "未进行任何修复。"
        
        report_lines = [
            "=" * 80,
            "SQL 语法修复报告",
            f"生成时间: {self._get_current_time()}",
            "=" * 80,
            ""
        ]
        
        # 按文件分组
        fixes_by_file: Dict[str, List[Dict]] = {}
        for fix in self.fixes_applied:
            file = fix['file'] or '未知文件'
            if file not in fixes_by_file:
                fixes_by_file[file] = []
            fixes_by_file[file].append(fix)
        
        # 生成每个文件的修复信息
        for file, fixes in fixes_by_file.items():
            report_lines.append(f"文件: {file}")
            report_lines.append("修复内容:")
            
            for i, fix in enumerate(fixes, 1):
                report_lines.append(f"  {i}. [Line {fix['line']}] {fix['type']}")
                report_lines.append(f"     修复前: {fix['before'][:60]}")
                report_lines.append(f"     修复后: {fix['after'][:60]}")
            
            report_lines.append("")
        
        # 统计信息
        report_lines.extend([
            "=" * 80,
            f"总计修复: {len(self.fixes_applied)} 处",
            f"涉及文件: {len(fixes_by_file)} 个",
            "=" * 80
        ])
        
        return '\n'.join(report_lines)
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def get_fix_count(self) -> int:
        """获取修复次数"""
        return len(self.fixes_applied)
    
    def reset(self):
        """重置修复器状态"""
        self.fixes_applied = []
        self.current_file = ""
        self.current_line = 0


def detect_fixable_errors(error_message: str) -> List[str]:
    """检测错误信息中是否包含可自动修复的问题
    
    Args:
        error_message: 错误信息
    
    Returns:
        修复建议列表
    """
    suggestions = []
    error_lower = error_message.lower()
    
    # 检测 MySQL 保留字问题
    fixer = SQLSyntaxFixer()
    for word in fixer.MYSQL_RESERVED_WORDS:
        if word in error_lower:
            suggestions.append(
                f"检测到可能的 MySQL 保留字问题: '{word}'\n"
                f"建议: 使用 --auto-fix 参数自动修复"
            )
            break  # 只提示一次
    
    return suggestions

