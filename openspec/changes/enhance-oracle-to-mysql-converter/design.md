# 技术设计：Oracle 到 MySQL 转换工具增强

## 上下文

当前 `tools/oracle_to_mysql.py` 转换工具只处理基本的 DDL 和 DML 语句转换，忽略了重要的元数据（COMMENT）和业务需求（表名前缀）。用户需要在转换后手动运行 `sql-fix-tools` 进行二次修复，流程繁琐且容易出错。

### 现有架构
```
Oracle SQL → oracle_to_mysql.py → MySQL SQL (基础转换) → sql-fix-tools → 最终 SQL
                                        ↓
                                  convertsql/
```

### 技术约束
- Python 3.10+
- 需要处理超大文件（最大 8960 行，如 BS_OLDER.sql）
- 需要保持流式处理特性，避免内存溢出
- 必须向后兼容现有工具和流程

## 目标 / 非目标

### 目标
1. **保留元数据**：将 Oracle COMMENT 信息转换为 MySQL 格式
2. **支持表名前缀**：在 SQL 语句中为表名添加前缀（如 `gzlry_`）
3. **自动化流程**：集成 sql-fix-tools，实现一键转换
4. **向后兼容**：不影响现有使用方式

### 非目标
- 不改变现有的类型映射规则
- 不处理存储过程、函数、触发器等复杂对象（当前已跳过）
- 不修改 sql-fix-tools 的核心逻辑（仅集成调用）

## 决策

### 决策 1：COMMENT 转换策略

**选择方案**：混合方式（列注释内联 + 表注释追加）

```python
# Oracle 原始格式
CREATE TABLE BS_AREA (
  mainid VARCHAR2(50) not null,
  areaname VARCHAR2(50)
);
COMMENT ON TABLE BS_AREA IS '院区表';
COMMENT ON COLUMN BS_AREA.mainid IS '主键ID';
COMMENT ON COLUMN BS_AREA.areaname IS '院区名称';

# MySQL 转换结果
CREATE TABLE BS_AREA (
  mainid VARCHAR(50) NOT NULL COMMENT '主键ID',
  areaname VARCHAR(50) COMMENT '院区名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='院区表';
```

**实现方式**：
1. 第一遍扫描：收集所有 COMMENT 语句到字典
   ```python
   {
       'BS_AREA': '院区表',
       'BS_AREA.mainid': '主键ID',
       'BS_AREA.areaname': '院区名称'
   }
   ```

2. 第二遍处理 CREATE TABLE：在列定义和表选项中注入注释

**考虑的替代方案**：
- **方案A**：使用 ALTER TABLE 追加所有注释
  - 优点：逻辑简单，不修改 CREATE TABLE 解析
  - 缺点：生成额外的 ALTER 语句，影响导入性能；列注释需要多条 ALTER
  - **拒绝原因**：MySQL 8.0+ 才支持 `ALTER TABLE ... MODIFY COLUMN ... COMMENT`，且性能较差

- **方案B**：只保留表注释，忽略列注释
  - 优点：实现简单
  - 缺点：丢失重要的列说明信息
  - **拒绝原因**：列注释对开发者理解字段含义至关重要

### 决策 2：表名前缀实现

**选择方案**：正则表达式识别并替换表名

```python
def add_table_prefix(self, stmt: str, table_prefix: str) -> str:
    """为 SQL 语句中的表名添加前缀"""
    # 1. CREATE TABLE table_name
    stmt = re.sub(
        r'CREATE\s+TABLE\s+(\w+)',
        lambda m: f'CREATE TABLE {table_prefix}{m.group(1)}',
        stmt,
        flags=re.IGNORECASE
    )
    
    # 2. INSERT INTO table_name
    stmt = re.sub(
        r'INSERT\s+INTO\s+(\w+)',
        lambda m: f'INSERT INTO {table_prefix}{m.group(1)}',
        stmt,
        flags=re.IGNORECASE
    )
    
    # 3. DROP TABLE IF EXISTS table_name
    stmt = re.sub(
        r'DROP\s+TABLE\s+IF\s+EXISTS\s+(\w+)',
        lambda m: f'DROP TABLE IF EXISTS {table_prefix}{m.group(1)}',
        stmt,
        flags=re.IGNORECASE
    )
    
    return stmt
```

**考虑的替代方案**：
- **方案A**：使用 SQL 解析器（如 sqlparse）
  - 优点：更准确，支持复杂语法
  - 缺点：引入重依赖，解析性能开销大，可能与现有流式处理冲突
  - **拒绝原因**：过度设计，正则表达式足以覆盖当前场景

- **方案B**：要求用户在导入时使用数据库重命名
  - 优点：无需修改转换工具
  - 缺点：导入后无法回溯，且需要逐个表手动重命名
  - **拒绝原因**：不符合自动化目标

### 决策 3：自动修复集成方式

**选择方案**：子进程调用 + 结果合并

```python
def auto_fix_sql_files(self, output_dir: Path) -> Dict[str, Any]:
    """自动调用 sql-fix-tools 修复转换后的文件"""
    import subprocess
    
    fix_tool_path = Path(__file__).parent / 'sql-fix-tools' / 'fix_sql_main.py'
    
    # 调用修复工具
    result = subprocess.run(
        ['python', str(fix_tool_path), '--target-dir', str(output_dir)],
        capture_output=True,
        text=True
    )
    
    return {
        'success': result.returncode == 0,
        'stdout': result.stdout,
        'stderr': result.stderr
    }
```

**工作流**：
```
1. oracle_to_mysql.py 转换 → convertsql/
2. 如果 --auto-fix：
   2.1 调用 sql-fix-tools/fix_sql_main.py
   2.2 原地修复 convertsql/ 中的文件
   2.3 生成合并报告
```

**考虑的替代方案**：
- **方案A**：将 sql-fix-tools 逻辑直接合并到 oracle_to_mysql.py
  - 优点：避免子进程调用
  - 缺点：违反单一职责原则，代码耦合度高，难以维护
  - **拒绝原因**：sql-fix-tools 是独立工具，应保持模块化

- **方案B**：使用 Python import 导入修复模块
  - 优点：避免子进程开销
  - 缺点：需要重构 sql-fix-tools 以支持编程调用
  - **权衡**：先使用子进程方案（简单快速），未来可重构为模块调用

## 实现细节

### COMMENT 收集与注入流程

```python
class OracleToMySQLConverter:
    def __init__(self):
        self.table_comments = {}   # {table_name: comment}
        self.column_comments = {}  # {table_name.column_name: comment}
    
    def convert_file(self, file_path, output_path, table_prefix='', auto_fix=False):
        # 第一遍：收集 COMMENT
        self._collect_comments(file_path)
        
        # 第二遍：转换语句（注入 COMMENT）
        statements = []
        for stmt in self._parse_statements(file_path):
            if stmt.startswith('CREATE TABLE'):
                stmt = self._inject_comments(stmt, table_prefix)
            if table_prefix:
                stmt = self.add_table_prefix(stmt, table_prefix)
            statements.append(stmt)
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write('\n\n'.join(statements))
        
        # 自动修复
        if auto_fix:
            self.auto_fix_sql_files(output_path.parent)
    
    def _collect_comments(self, file_path):
        """第一遍扫描：收集所有 COMMENT 语句"""
        with open(file_path) as f:
            for line in f:
                # COMMENT ON TABLE table_name IS 'comment';
                match = re.match(r"comment\s+on\s+table\s+(\w+)\s+is\s+'([^']+)'", line, re.I)
                if match:
                    self.table_comments[match.group(1)] = match.group(2)
                
                # COMMENT ON COLUMN table_name.column_name IS 'comment';
                match = re.match(r"comment\s+on\s+column\s+(\w+)\.(\w+)\s+is\s+'([^']+)'", line, re.I)
                if match:
                    key = f"{match.group(1)}.{match.group(2)}"
                    self.column_comments[key] = match.group(3)
    
    def _inject_comments(self, create_stmt, table_prefix):
        """在 CREATE TABLE 语句中注入注释"""
        # 提取表名
        table_match = re.search(r'CREATE\s+TABLE\s+(\w+)', create_stmt, re.I)
        if not table_match:
            return create_stmt
        
        table_name = table_match.group(1)
        prefixed_table = f"{table_prefix}{table_name}" if table_prefix else table_name
        
        # 注入列注释
        for col_key, comment in self.column_comments.items():
            if col_key.startswith(f"{table_name}."):
                col_name = col_key.split('.')[1]
                # 在列定义后添加 COMMENT
                pattern = rf"({col_name}\s+\w+(?:\([^)]+\))?(?:\s+(?:not\s+)?null)?)"
                replacement = rf"\1 COMMENT '{comment}'"
                create_stmt = re.sub(pattern, replacement, create_stmt, flags=re.I)
        
        # 注入表注释
        if table_name in self.table_comments:
            table_comment = self.table_comments[table_name]
            # 在 ENGINE 子句前插入 COMMENT
            create_stmt = create_stmt.replace(
                'ENGINE=InnoDB',
                f"COMMENT='{table_comment}' ENGINE=InnoDB"
            )
        
        return create_stmt
```

### 内存优化考虑

对于大文件（如 BS_OLDER.sql，8960 行），需要注意：

1. **COMMENT 收集**：内存占用 O(n)，其中 n 是 COMMENT 语句数量
   - 估算：假设 100 个字段，每个注释 50 字节 = 5KB（可忽略）

2. **流式处理**：保持现有的流式写入逻辑
   ```python
   # 不要一次性加载所有语句到内存
   with open(output_path, 'w') as out:
       for stmt in self._parse_statements(file_path):
           converted = self._convert_statement(stmt)
           out.write(converted + '\n\n')
   ```

3. **双遍扫描开销**：第一遍收集 COMMENT，第二遍转换
   - 对于 10MB 文件，读取两次仅增加约 0.5 秒

## 风险 / 权衡

### 风险 1：正则表达式的准确性

**风险**：复杂的 SQL 语句可能导致正则匹配失败或误匹配
- 例如：列名包含关键字、多行注释、特殊字符

**缓解措施**：
- 限制匹配范围，使用更精确的模式（如 `\w+` 只匹配标识符）
- 添加单元测试覆盖边界情况
- 记录处理失败的情况到日志，便于排查

### 风险 2：表名前缀与外键约束

**风险**：如果添加表名前缀，外键约束中的引用表名不会自动更新
- 例如：`FOREIGN KEY (dept_id) REFERENCES DEPT(id)` 中的 `DEPT` 需要变为 `gzlry_DEPT`

**当前决策**：
- **不处理外键约束**：因为当前工具已经移除所有 ALTER TABLE（包括外键）
- 如果未来需要保留外键：在 `add_table_prefix` 中添加外键引用的处理

**文档说明**：
- 在 README 中明确说明：使用 `--table-prefix` 时，外键约束已被移除

### 风险 3：子进程调用的错误处理

**风险**：sql-fix-tools 执行失败可能导致部分文件未修复

**缓解措施**：
- 检查子进程返回码
- 打印修复工具的 stdout 和 stderr
- 如果修复失败，给出明确提示，但不阻止转换结果的保存

## 迁移计划

### 阶段 1：实现核心功能（无破坏性变更）
1. 添加 COMMENT 转换逻辑（默认禁用）
2. 添加 `--table-prefix` 参数
3. 添加 `--auto-fix` 参数
4. 更新 README 文档

### 阶段 2：测试与验证
1. 使用现有的 Oracle SQL 文件测试（BS_AREA.sql, BS_OLDER.sql 等）
2. 验证 COMMENT 正确注入
3. 验证表名前缀功能
4. 验证自动修复集成

### 阶段 3：文档更新
1. 更新 `tools/oracle_to_mysql.py` 的 docstring
2. 更新 sql-fix-tools README，说明自动化集成
3. 添加使用示例到项目文档

### 回滚策略
- 如果出现问题，用户可以不使用新参数，回退到原有行为
- 新功能都是可选的，默认禁用

## 待决问题

1. **COMMENT 中的特殊字符转义**：
   - 问题：如果 Oracle COMMENT 包含单引号 `'`，如何处理？
   - 建议：转义为 `''`（MySQL 标准）

2. **表名前缀的命名约定**：
   - 问题：是否限制前缀格式（如只允许字母、数字、下划线）？
   - 建议：不强制限制，由用户保证合法性

3. **sql-fix-tools 的接口标准化**：
   - 问题：当前 sql-fix-tools 没有统一的编程接口
   - 建议：后续重构为可导入的 Python 模块，提供 `fix_sql_files(dir)` 接口

4. **是否需要支持反向操作（移除前缀）**：
   - 问题：用户是否需要将 `gzlry_BS_AREA` 还原为 `BS_AREA`
   - 建议：暂不支持，作为未来增强功能
