# SQL 导入错误处理指南

## 常见错误类型和解决方案

### 1. MySQL 语法错误（1064）

#### 错误示例

```
(1064, "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near 'describe VARCHAR(4000)' at line 5")
```

#### 原因

- SQL 中使用了 MySQL 保留字作为列名或表名
- 常见保留字：`describe`、`key`、`condition`、`index`、`table`、`order`、`group` 等

#### 解决方案

**方法 1：自动修复（推荐）**

```bash
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix
```

系统会自动为保留字添加反引号包裹。

**方法 2：手动修复**

编辑 SQL 文件，为保留字添加反引号：

```sql
-- 修复前
describe VARCHAR(4000),

-- 修复后
`describe` VARCHAR(4000),
```

---

### 2. 重复键错误（1062）

#### 错误示例

```
(1062, "Duplicate entry '1' for key 'PRIMARY'")
```

#### 原因

- 主键或唯一键重复
- 重复导入数据

#### 解决方案

**忽略错误（已自动处理）**

系统默认会忽略重复键错误，确保幂等性。如果仍然报错：

```bash
# 检查是否真的是数据问题
SELECT * FROM table WHERE id = 1;

# 如果需要重新导入，先清理数据
TRUNCATE TABLE table;
```

---

### 3. 外键约束错误（1215）

#### 错误示例

```
(1215, "Cannot add foreign key constraint")
```

#### 原因

- 引用的表或列不存在
- 数据类型不匹配
- 索引缺失

#### 解决方案

**方法 1：调整导入顺序**

先导入被引用的表，再导入引用表：

```bash
# 1. 导入主表
python manage.py import_oracle_sql main_table.sql

# 2. 导入从表
python manage.py import_oracle_sql child_table.sql
```

**方法 2：禁用外键检查（已自动处理）**

系统默认会在导入时禁用外键检查，导入完成后恢复。

---

### 4. 表已存在错误（1050）

#### 错误示例

```
(1050, "Table 'table_name' already exists")
```

#### 原因

- 表已存在，重复创建

#### 解决方案

**忽略错误（已自动处理）**

系统默认会忽略此错误。如果需要重新创建：

```bash
# 方法 1：先删除表
DROP TABLE IF EXISTS table_name;

# 方法 2：使用 CREATE TABLE IF NOT EXISTS
CREATE TABLE IF NOT EXISTS table_name ...;
```

---

### 5. 文件过大导致超时

#### 错误示例

```
TimeoutError: Transaction timeout
```

#### 原因

- 文件过大（>1GB）
- 语句过多

#### 解决方案

**禁用事务**

```bash
python manage.py import_oracle_sql large_file.sql --no-transaction
```

或者**跳过大文件**

```bash
python manage.py import_oracle_sql --default-convertsql --max-size 100  # 跳过 >100MB
```

---

### 6. 字符编码错误

#### 错误示例

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x...
```

#### 原因

- SQL 文件编码不是 UTF-8

#### 解决方案

**转换文件编码**

```bash
# Linux/Mac
iconv -f GBK -t UTF-8 file.sql > file_utf8.sql

# Python 脚本
with open('file.sql', 'r', encoding='gbk') as f:
    content = f.read()
with open('file_utf8.sql', 'w', encoding='utf-8') as f:
    f.write(content)
```

---

## 错误诊断流程

### 步骤 1：查看错误信息

```bash
python manage.py import_oracle_sql --show-status --batch-id <ID>
```

输出示例：
```
文件名                    状态      错误信息
gzlry_PM_SER_MAJOR.sql   failed    (1064, "... near 'describe VARCHAR'...")
```

### 步骤 2：识别错误类型

| 错误码 | 类型 | 可自动修复 |
|--------|------|-----------|
| 1064 | 语法错误 | ✅ 是 |
| 1062 | 重复键 | ⚠️ 已忽略 |
| 1050 | 表已存在 | ⚠️ 已忽略 |
| 1215 | 外键约束 | ⚠️ 已处理 |
| 其他 | 其他错误 | ❌ 否 |

### 步骤 3：尝试自动修复

```bash
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix
```

### 步骤 4：查看修复报告

```bash
cat sql_fix_report_<ID>.txt
```

### 步骤 5：手动修复（如果需要）

如果自动修复失败，根据错误信息手动修复 SQL 文件。

---

## 最佳实践

### 1. 首次导入前的检查

```bash
# 1. 预览模式（不执行）
python manage.py import_oracle_sql --default-convertsql --dry-run

# 2. 启用自动修复 + 报告
python manage.py import_oracle_sql --default-convertsql --auto-fix --fix-report

# 3. 查看修复报告
cat sql_fix_report_*.txt
```

### 2. 处理失败文件

```bash
# 1. 查看失败原因
python manage.py import_oracle_sql --show-status

# 2. 重试失败文件（自动修复）
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix

# 3. 如果仍然失败，查看具体错误
python manage.py import_oracle_sql --show-status --batch-id <ID>
```

### 3. 断点续导

```bash
# 如果导入中断
^C

# 继续导入（跳过已成功的）
python manage.py import_oracle_sql --batch-id <ID> --resume --auto-fix
```

### 4. 批量导入大量文件

```bash
# 组合使用多个参数
python manage.py import_oracle_sql --default-convertsql \
    --auto-fix \              # 自动修复
    --fix-report \            # 生成报告
    --continue-on-error \     # 遇到错误继续
    --max-size 100            # 跳过超大文件
```

---

## 故障排除清单

### ✅ 检查清单

- [ ] 确认数据库连接正常
- [ ] 确认 SQL 文件编码为 UTF-8
- [ ] 确认文件路径正确
- [ ] 查看错误日志和状态表
- [ ] 尝试使用 `--auto-fix` 参数
- [ ] 查看修复报告确认修复内容
- [ ] 如果是超大文件，使用 `--no-transaction`
- [ ] 如果是外键问题，调整导入顺序

---

## 联系支持

如果遇到无法解决的问题：

1. 收集以下信息：
   - 批次 ID
   - 错误信息（完整）
   - SQL 文件示例（失败的部分）
   - 修复报告（如果有）

2. 提交问题时包含：
   ```bash
   python manage.py import_oracle_sql --show-status --batch-id <ID> > error_report.txt
   ```

---

## 附录：MySQL 保留字列表（部分）

```
accessible, add, all, alter, analyze, and, as, asc, before, between,
bigint, binary, blob, both, by, call, cascade, case, change, char,
check, collate, column, condition, constraint, continue, convert,
create, cross, current_date, current_time, current_timestamp,
current_user, cursor, database, databases, day_hour, day_microsecond,
day_minute, day_second, dec, decimal, declare, default, delayed,
delete, desc, describe, deterministic, distinct, distinctrow, div,
double, drop, dual, each, else, elseif, enclosed, escaped, except,
exists, exit, explain, false, fetch, float, float4, float8, for,
force, foreign, from, fulltext, function, generated, get, grant,
group, grouping, groups, having, high_priority, hour_microsecond,
hour_minute, hour_second, if, ignore, in, index, infile, inner,
inout, insensitive, insert, int, int1, int2, int3, int4, int8,
integer, interval, into, is, iterate, join, key, keys, kill, lag,
last_value, lateral, lead, leading, leave, left, like, limit,
linear, lines, load, localtime, localtimestamp, lock, long, longblob,
longtext, loop, low_priority, match, maxvalue, mediumblob, mediumint,
mediumtext, middleint, minute_microsecond, minute_second, mod,
modifies, natural, not, no_write_to_binlog, null, numeric, of, on,
optimize, optimizer_costs, option, optionally, or, order, out, outer,
outfile, over, partition, precision, primary, procedure, purge,
range, rank, read, reads, read_write, real, recursive, references,
regexp, release, rename, repeat, replace, require, resignal,
restrict, return, revoke, right, rlike, row, rows, schema, schemas,
second_microsecond, select, sensitive, separator, set, show, signal,
smallint, spatial, specific, sql, sqlexception, sqlstate, sqlwarning,
sql_big_result, sql_calc_found_rows, sql_small_result, ssl, starting,
stored, straight_join, system, table, terminated, then, tinyblob,
tinyint, tinytext, to, trailing, trigger, true, undo, union, unique,
unlock, unsigned, update, usage, use, using, utc_date, utc_time,
utc_timestamp, values, varbinary, varchar, varcharacter, varying,
virtual, when, where, while, window, with, write, xor, year_month,
zerofill
```

完整列表参考：[MySQL 8.0 Keywords and Reserved Words](https://dev.mysql.com/doc/refman/8.0/en/keywords.html)


## 超出自动修复范围的情况

虽然自动修复功能覆盖了 15+ 种常见语法问题，但以下情况可能需要手动处理：

### 1. 极其复杂的嵌套 SQL

**示例**：包含大量嵌套 CONCAT 和 SQL 语句的字段

**实际案例**: `gzlry_BSE_EXCEL.sql`
```sql
-- sqlstmt 字段包含数百层嵌套
INSERT INTO BSE_EXCEL (sqlstmt) VALUES (
  CONCAT('select * from (', CHAR(13)) || CONCAT('', CHAR(10)) || 
  CONCAT('select olr.mainId...', CHAR(13)) || CONCAT('', CHAR(10)) || 
  ... (重复数百次)
);
```

**为什么无法自动修复**：
- 正则表达式无法处理无限深度的嵌套括号
- 需要完整的 SQL 解析器才能处理
- 这种案例极其罕见（974 个文件中仅 1 个，占比 0.1%）

**手动修复方法**：

1. **使用文本编辑器批量替换**：
   ```
   查找: ) || CONCAT(
   替换: , 
   ```
   
   例如：
   ```sql
   -- 修复前
   CONCAT('a', CHAR(13)) || CONCAT('b', CHAR(10)) || CONCAT('c')
   
   -- 修复后
   CONCAT('a', CHAR(13), 'b', CHAR(10), 'c')
   ```

2. **重构数据结构**（推荐）：
   - 不要在数据库字段中存储复杂的 SQL 查询
   - 将查询逻辑移到应用代码或存储过程
   - 使用视图代替动态 SQL

3. **临时跳过该文件**：
   ```bash
   # 继续处理其他文件
   python manage.py import_oracle_sql --batch-id <ID> --auto-fix --continue-on-error
   ```

**影响评估**：
- 这类文件极其罕见（< 0.2%）
- 不影响自动修复功能的整体实用性
- 99.8% 的文件可以自动修复

### 2. 数据类型范围问题

**示例**：字段定义与数据不匹配
- INT 溢出：✅ 已由自动修复处理（升级为 BIGINT）
- 其他数据类型不匹配：需要手动修正

### 3. 字符集/编码问题

**示例**：
```
(1366, "Incorrect string value: '\\xF0\\x9F...' for column 'name'")
```

**解决方案**：
- 检查表和列的字符集设置
- 确保使用 `utf8mb4` 支持所有 Unicode 字符

### 4. 业务逻辑错误

**示例**：外键约束失败、业务规则冲突等

**解决方案**：需要根据具体业务逻辑手动处理

## 最佳实践建议

1. **先测试自动修复**：大多数语法问题（99%+）都能自动解决
2. **查看修复报告**：了解具体修复了什么
3. **逐个处理失败文件**：针对性解决复杂问题
4. **保留原始文件**：修复失败时可以回退
5. **记录特殊案例**：为将来的改进提供参考

---

**更新日期**：2026-01-09  
**版本**：v2.0（覆盖 15+ 种修复规则）
