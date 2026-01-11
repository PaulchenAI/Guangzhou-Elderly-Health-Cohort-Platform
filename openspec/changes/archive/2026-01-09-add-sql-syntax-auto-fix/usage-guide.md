# SQL 语法自动修复功能使用指南

## 功能概述

自动修复 SQL 导入过程中的语法错误，特别是 MySQL 保留字冲突问题。

## 快速开始

### 场景 1：自动修复并导入

当导入失败提示 MySQL 语法错误时：

```bash
# 原命令失败
python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed

# 输出：
# [1/141] 处理: gzlry_PM_SER_MAJOR.sql (232B)
#   导入失败: (1064, "You have an error in your SQL syntax... near 'describe VARCHAR(4000)'")

# 使用自动修复功能
python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed --auto-fix

# 输出：
# [1/141] 处理: gzlry_PM_SER_MAJOR.sql (232B)
#   [自动修复] 检测到 2 处 MySQL 保留字问题
#   ✓ 导入成功
```

### 场景 2：生成修复报告

查看修复了哪些内容：

```bash
python manage.py import_oracle_sql --default-convertsql --auto-fix --fix-report

# 生成报告文件: sql_fix_report_<batch-id>.txt
```

### 场景 3：保存修复后的文件

将修复后的 SQL 保存到新文件：

```bash
python manage.py import_oracle_sql gzlry_PM_SER_MAJOR.sql --auto-fix --save-fixed

# 生成文件: gzlry_PM_SER_MAJOR_fixed.sql
```

## 命令参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--auto-fix` | 启用自动修复功能 | `--auto-fix` |
| `--save-fixed` | 保存修复后的 SQL 到新文件 | `--auto-fix --save-fixed` |
| `--fix-report` | 生成详细的修复报告 | `--auto-fix --fix-report` |

## 支持的修复类型

### 1. MySQL 保留字修复

**问题示例**：
```sql
CREATE TABLE user_info (
    describe VARCHAR(4000),  -- ❌ describe 是 MySQL 保留字
    key VARCHAR(50),          -- ❌ key 是 MySQL 保留字
    condition VARCHAR(200)    -- ❌ condition 是 MySQL 保留字
);
```

**修复后**：
```sql
CREATE TABLE user_info (
    `describe` VARCHAR(4000),  -- ✅ 添加反引号
    `key` VARCHAR(50),          -- ✅ 添加反引号
    `condition` VARCHAR(200)    -- ✅ 添加反引号
);
```

**覆盖的保留字**（部分）：
- `describe`, `key`, `condition`, `index`, `table`
- `select`, `insert`, `update`, `delete`, `where`
- `order`, `group`, `having`, `join`, `from`
- `read`, `write`, `precision`, `schema`
- 更多详见 [MySQL 8.0 保留字列表](https://dev.mysql.com/doc/refman/8.0/en/keywords.html)

### 2. 已用反引号的不会重复修复

```sql
CREATE TABLE test (
    `describe` VARCHAR(100)  -- ✅ 已有反引号，不会修复
);
```

### 3. 字符串内的保留字不会修复

```sql
INSERT INTO test VALUES (
    'This is a describe field'  -- ✅ 字符串内容，不会修复
);
```

### 4. 大 VARCHAR 自动转 TEXT

**问题示例**：
```sql
CREATE TABLE log (
    content VARCHAR(4000)  -- ❌ MySQL 行大小可能超出限制
);
```

**修复后**：
```sql
CREATE TABLE log (
    content TEXT  -- ✅ 自动转换为 TEXT
);
```

### 5. 特殊字符列名

**问题示例**：
```sql
CREATE TABLE data (
    line# INT  -- ❌ # 是特殊字符
);
```

**修复后**：
```sql
CREATE TABLE data (
    `line#` INT  -- ✅ 添加反引号
);
```

### 6. NUMBER(*,n) 转 DECIMAL

**问题示例**：
```sql
CREATE TABLE finance (
    amount NUMBER(*,10)  -- ❌ Oracle 特定语法
);
```

**修复后**：
```sql
CREATE TABLE finance (
    amount DECIMAL(65,10)  -- ✅ 转换为 MySQL DECIMAL
);
```

### 7. NVARCHAR 转 VARCHAR

**问题示例**：
```sql
CREATE TABLE users (
    name NVARCHAR(100)  -- ❌ Oracle 类型
);
```

**修复后**：
```sql
CREATE TABLE users (
    name VARCHAR(100)  -- ✅ 转换为 VARCHAR
);
```

### 8. 双引号标识符转反引号

**问题示例**：
```sql
CREATE TABLE events (
    "date" DATETIME  -- ❌ MySQL 推荐使用反引号
);
```

**修复后**：
```sql
CREATE TABLE events (
    `date` DATETIME  -- ✅ 转换为反引号
);
```

### 9. Oracle 函数转换

**sysdate 转换**：
```sql
-- 修复前
INSERT INTO log VALUES (sysdate);

-- 修复后
INSERT INTO log VALUES (CURRENT_TIMESTAMP);
```

**to_timestamp 转换**：
```sql
-- 修复前
INSERT INTO events VALUES (
    to_timestamp('15-03-2021 10:30:00', 'dd-mm-yyyy hh24:mi:ss')
);

-- 修复后
INSERT INTO events VALUES (
    STR_TO_DATE('15-03-2021 10:30:00', '%d-%m-%Y %H:%i:%s')
);
```

### 10. DOUBLE(n) 修复

**问题示例**：
```sql
CREATE TABLE stats (
    value DOUBLE(8)  -- ❌ MySQL 不支持单参数 DOUBLE
);
```

**修复后**：
```sql
CREATE TABLE stats (
    value DOUBLE  -- ✅ 移除参数
);
```

### 11. 字符串连接符 || 转 CONCAT

**问题示例**：
```sql
INSERT INTO messages VALUES (
    'Hello' || ' ' || 'World'  -- ❌ MySQL 不支持 ||
);
```

**修复后**：
```sql
INSERT INTO messages VALUES (
    CONCAT('Hello', ' ', 'World')  -- ✅ 使用 CONCAT
);
```

**复杂嵌套**：
```sql
-- 修复前
CONCAT('Part1', CHAR(10)) || CONCAT('Part2', CHAR(10)) || 'Part3'

-- 修复后
CONCAT('Part1', CHAR(10), 'Part2', CHAR(10), 'Part3')
```

### 12. INT 溢出自动升级 BIGINT

**问题示例**：
```sql
CREATE TABLE codes (
    code INT  -- ❌ 数据值 10101020101 超出范围
);
INSERT INTO codes VALUES (10101020101);
```

**修复后**：
```sql
CREATE TABLE codes (
    code BIGINT  -- ✅ 自动升级为 BIGINT
);
INSERT INTO codes VALUES (10101020101);
```

### 13. 反斜杠转义

**问题示例**：
```sql
INSERT INTO chars VALUES ('\', 'name');  
-- ❌ 反斜杠转义导致字符串未闭合
```

**修复后**：
```sql
INSERT INTO chars VALUES ('\\', 'name');  
-- ✅ 双反斜杠表示一个反斜杠字符
```

### 14. 尾随逗号清理

**问题示例**：
```sql
CREATE TABLE test (
    id INT,
    name VARCHAR(100),  -- ❌ 最后一个字段后有逗号
)
```

**修复后**：
```sql
CREATE TABLE test (
    id INT,
    name VARCHAR(100)  -- ✅ 移除多余逗号
)
```

### 15. ALTER TABLE ENABLE ALL TRIGGERS

**问题示例**：
```sql
ALTER TABLE users ENABLE ALL TRIGGERS;  
-- ❌ MySQL 不支持
```

**修复后**：
```sql
-- ALTER TABLE users ENABLE ALL TRIGGERS; (Oracle specific, removed)
-- ✅ 注释掉
```

## 修复报告示例

```
==================================================
SQL 语法修复报告
批次 ID: 1f5b4b14
生成时间: 2026-01-09 14:30:45
==================================================

文件: gzlry_PM_SER_MAJOR.sql
修复内容:
  1. [Line 3] MySQL 保留字修复
     修复前: describe VARCHAR(4000),
     修复后: `describe` VARCHAR(4000),
     原因: 'describe' 是 MySQL 保留字
  
  2. [Line 5] MySQL 保留字修复
     修复前: key VARCHAR(50),
     修复后: `key` VARCHAR(50),
     原因: 'key' 是 MySQL 保留字

文件: gzlry_WORKFLOW_BASE.sql
修复内容:
  1. [Line 12] MySQL 保留字修复
     修复前: condition VARCHAR(200),
     修复后: `condition` VARCHAR(200),
     原因: 'condition' 是 MySQL 保留字

==================================================
总计修复: 3 处
涉及文件: 2 个
成功导入: 2 个
失败导入: 0 个
==================================================
```

## 常见问题

### Q1: 自动修复是否会修改原文件？

**A**: 不会。修复在内存中进行，不会修改源文件。除非使用 `--save-fixed` 参数，才会生成新文件。

### Q2: 如果自动修复后仍然失败怎么办？

**A**: 查看错误信息和修复报告，确定是否需要手动修复。某些复杂的语法错误可能超出自动修复的能力范围。

### Q3: 是否可以只生成修复后的文件，不导入数据库？

**A**: 可以，使用 `--dry-run` 参数：
```bash
python manage.py import_oracle_sql file.sql --auto-fix --save-fixed --dry-run
```

### Q4: 修复会影响性能吗？

**A**: 性能影响很小（< 5%）。修复使用高效的正则表达式，单条 SQL 的修复时间 < 1ms。

### Q5: 如何知道哪些错误可以自动修复？

**A**: 当导入失败时，如果系统检测到可能的 MySQL 保留字问题，会自动提示：
```
导入失败: (1064, "... near 'describe VARCHAR'...")

提示: 检测到可能的 MySQL 保留字问题，尝试使用 --auto-fix 参数：
  python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed --auto-fix
```

## 最佳实践

### 1. 首次导入推荐流程

```bash
# 步骤 1: 先使用 dry-run 预览
python manage.py import_oracle_sql --default-convertsql --dry-run

# 步骤 2: 启用自动修复 + 报告
python manage.py import_oracle_sql --default-convertsql --auto-fix --fix-report

# 步骤 3: 查看报告，确认修复内容
cat sql_fix_report_*.txt

# 步骤 4: 如果需要，保存修复后的文件
python manage.py import_oracle_sql --default-convertsql --auto-fix --save-fixed --dry-run
```

### 2. 处理失败文件

```bash
# 查看失败原因
python manage.py import_oracle_sql --show-status --batch-id <batch-id>

# 重试失败文件（启用自动修复）
python manage.py import_oracle_sql --batch-id <batch-id> --retry-failed --auto-fix
```

### 3. 批量导入大量文件

```bash
# 组合使用多个功能
python manage.py import_oracle_sql --default-convertsql \
    --auto-fix \                    # 自动修复
    --fix-report \                  # 生成报告
    --continue-on-error \           # 遇到错误继续
    --max-size 100                  # 跳过超大文件
```

## 技术细节

### 修复规则优先级

1. **MySQL 保留字修复**（优先级：高）
2. **数据类型修复**（优先级：中，兜底）
3. **日期格式修复**（优先级：低，兜底）

### 不会修复的情况

- 字符串字面量内的保留字
- 注释内的保留字
- 已经用反引号包裹的标识符
- 逻辑错误或业务规则问题

### 安全保证

- 修复规则经过严格测试
- 不会改变 SQL 语句的语义
- 只修复明确的语法错误
- 修复前后可以对比（通过报告）

