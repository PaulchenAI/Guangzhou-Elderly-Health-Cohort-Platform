# 数据完整性与断点续导使用指南

## 核心特性

### 1. 事务管理

每个 SQL 文件作为一个事务单元：
- **成功**：所有语句成功，自动提交
- **失败**：任何语句失败，自动回滚整个文件

### 2. 状态追踪

系统自动记录每个文件的导入状态：
- `pending`: 待处理
- `processing`: 处理中
- `success`: 成功
- `failed`: 失败
- `skipped`: 跳过

### 3. 断点续导

导入中断后可以继续，已成功的文件不会重复导入。

## 使用场景

### 场景 1：首次全量导入

```bash
# 开始导入（自动生成批次ID）
python manage.py import_oracle_sql --default-convertsql --skip-large-files --continue-on-error
```

输出示例：
```
批次 ID: a1b2c3d4
使用默认转换目录: docs/hospital/convertsql/
跳过 19 个大文件（超过 100MB）：
  - gzlry_EG_REQUEST_LOG.sql (2.32GB)
  ...

找到 955 个待处理的 SQL 文件
[1/955] 处理: gzlry_BS_DEPARTMENT.sql (12.5KB)
  导入成功（25 条语句，耗时 0.2秒）
[2/955] 处理: gzlry_BS_DICT.sql (45.3KB)
  导入成功（150 条语句，耗时 0.5秒）
...

==================================================
批次 ID: a1b2c3d4
处理完成: 成功 950/955, 失败 5, 跳过 19

失败文件:
  - gzlry_SOME_TABLE.sql: (1064, "You have an error in your SQL syntax...")

提示: 使用以下命令重试失败的文件:
  python manage.py import_oracle_sql --batch-id a1b2c3d4 --retry-failed
```

### 场景 2：导入中断，断点续导

如果导入过程中被中断（Ctrl+C、网络断开、服务器重启等）：

```bash
# 使用相同的批次ID继续导入
python manage.py import_oracle_sql --batch-id a1b2c3d4 --resume --continue-on-error
```

系统将：
1. 跳过已成功导入的文件
2. 继续导入剩余的文件
3. 保证数据不重复

### 场景 3：重试失败的文件

导入完成后，针对失败的文件进行重试：

```bash
# 只重试上次失败的文件
python manage.py import_oracle_sql --batch-id a1b2c3d4 --retry-failed
```

### 场景 4：查看导入状态

```bash
# 查看最近的导入批次
python manage.py import_oracle_sql --show-status
```

输出：
```
最近的导入批次：
批次ID       总数     成功     失败     开始时间             更新时间
------------------------------------------------------------------------------------
a1b2c3d4       955      950        5     2026-01-09 10:30:15  2026-01-09 11:45:30
b2c3d4e5       100       98        2     2026-01-09 09:00:00  2026-01-09 09:15:20

提示: 使用 --batch-id <ID> --show-status 查看详细信息
```

查看特定批次的详细状态：

```bash
# 查看特定批次的文件列表
python manage.py import_oracle_sql --show-status --batch-id a1b2c3d4
```

输出：
```
批次 a1b2c3d4 的导入状态：

文件名                                               大小      语句数          状态  错误信息
----------------------------------------------------------------------------------------------------------------------------------
gzlry_SOME_TABLE.sql                               1.2MB         500        failed  (1064, "You have an error in your SQL...")
gzlry_ANOTHER_TABLE.sql                            3.5MB        1200        failed  (1215, "Cannot add foreign key constraint")
gzlry_BS_DEPARTMENT.sql                            12.5KB         25       success
gzlry_BS_DICT.sql                                  45.3KB        150       success
...

==================================================================================================================================
统计: 成功 950, 失败 5, 处理中 0, 待处理 0, 跳过 19
```

### 场景 5：强制重新导入

如果需要更新数据（例如源文件已修改）：

```bash
# 忽略状态表，强制重新导入
python manage.py import_oracle_sql --default-convertsql --force
```

**注意**：
- 会尝试重新导入所有文件
- 依赖数据库的唯一键约束防止重复数据
- 如果表已存在，会忽略 "Table already exists" 错误
- 如果数据已存在，会忽略 "Duplicate entry" 错误

## 事务回滚机制

### 自动回滚

当文件导入失败时，系统会自动回滚该文件的所有更改：

```python
# 文件: gzlry_EXAMPLE.sql
CREATE TABLE example (id INT PRIMARY KEY);
INSERT INTO example VALUES (1);
INSERT INTO example VALUES (2);
INSERT INTO example VALUES (1);  -- 错误：重复键

# 结果：
# - CREATE TABLE 会成功（DDL 不在事务中）
# - 所有 INSERT 会回滚（DML 在事务中）
# - 表结构存在，但数据为空
```

### DDL 和 DML 分离

系统智能分离 DDL 和 DML 语句：

```
DDL（不使用事务）:
  - CREATE TABLE
  - ALTER TABLE
  - DROP TABLE

DML（使用事务）:
  - INSERT INTO
  - UPDATE
  - DELETE

执行顺序：
  1. 执行所有 DDL（逐条执行，隐式提交）
  2. 执行所有 DML（使用事务，要么全部成功，要么全部回滚）
```

### 禁用事务（超大文件）

对于超大文件（> 1GB），可以禁用事务避免超时：

```bash
# 禁用事务
python manage.py import_oracle_sql ../docs/hospital/convertsql/huge_file.sql --no-transaction
```

**权衡**：
- ✅ 避免事务超时
- ✅ 减少内存占用
- ❌ 失败后无法回滚
- ❌ 需要手动清理数据

## 防止数据重复

### 机制 1：状态表检查

```bash
# 使用 --resume 跳过已成功的文件
python manage.py import_oracle_sql --batch-id a1b2c3d4 --resume
```

### 机制 2：唯一键约束

系统会自动忽略以下错误：
- 1062: Duplicate entry（重复键）
- 1050: Table already exists（表已存在）
- 1061: Duplicate key name（重复索引名）

这意味着：
- 重复运行导入命令是安全的
- 不会产生重复数据（如果表有主键/唯一键）

### 机制 3：批次隔离

每次导入使用独立的批次ID：
```bash
# 第一次导入
python manage.py import_oracle_sql --default-convertsql
# 批次 ID: a1b2c3d4

# 第二次导入（新批次）
python manage.py import_oracle_sql --default-convertsql
# 批次 ID: e5f6g7h8

# 可以查看和对比两次导入
python manage.py import_oracle_sql --show-status --batch-id a1b2c3d4
python manage.py import_oracle_sql --show-status --batch-id e5f6g7h8
```

## 故障恢复流程

### 情况 1：导入进行到一半，服务器重启

```bash
# 步骤 1：查看导入状态
python manage.py import_oracle_sql --show-status

# 步骤 2：找到未完成的批次ID（例如：a1b2c3d4）
# 步骤 3：继续导入
python manage.py import_oracle_sql --batch-id a1b2c3d4 --resume --continue-on-error
```

### 情况 2：部分文件导入失败

```bash
# 步骤 1：查看失败原因
python manage.py import_oracle_sql --show-status --batch-id a1b2c3d4

# 步骤 2：修复问题（如果需要）
# 例如：修改源文件、调整数据库配置等

# 步骤 3：重试失败的文件
python manage.py import_oracle_sql --batch-id a1b2c3d4 --retry-failed
```

### 情况 3：数据导入错误，需要回滚

**单个文件**：
- 系统已自动回滚该文件的 DML 语句
- DDL 语句（CREATE TABLE）无法回滚，需要手动删除表

**多个文件**：
```sql
-- 手动清理（根据需要）
DROP TABLE IF EXISTS table1;
DROP TABLE IF EXISTS table2;
...
```

然后重新导入：
```bash
python manage.py import_oracle_sql --batch-id a1b2c3d4 --force
```

## 性能优化建议

### 1. 按文件大小分批导入

```bash
# 第一批：小文件（快速完成）
python manage.py import_oracle_sql --default-convertsql --max-size 10

# 第二批：中等文件
python manage.py import_oracle_sql --default-convertsql --max-size 100 --resume

# 第三批：大文件（手动处理，可选择禁用事务）
python manage.py import_oracle_sql ../docs/hospital/convertsql/huge_file.sql --no-transaction
```

### 2. 并行导入（高级）

如果有多台服务器或多个数据库实例：

```bash
# 服务器 1：导入前 500 个文件
python manage.py import_oracle_sql --batch-id batch1 ...

# 服务器 2：导入后 500 个文件
python manage.py import_oracle_sql --batch-id batch2 ...
```

### 3. 错误继续处理

```bash
# 不因单个文件失败而停止
python manage.py import_oracle_sql --default-convertsql --continue-on-error
```

## 最佳实践

### ✅ 推荐做法

1. **首次导入使用 `--skip-large-files`**
   ```bash
   python manage.py import_oracle_sql --default-convertsql --skip-large-files --continue-on-error
   ```

2. **记录批次ID**
   ```bash
   python manage.py import_oracle_sql --default-convertsql | tee import.log
   ```

3. **导入前备份数据库**
   ```bash
   mysqldump -u user -p database > backup.sql
   ```

4. **定期清理历史记录**
   ```sql
   -- 删除 30 天前的导入记录
   DELETE FROM sql_import_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
   ```

### ❌ 避免的做法

1. **不要在同一批次ID中并行运行**
   - 会导致状态冲突

2. **不要对超大文件使用事务**
   - 使用 `--no-transaction` 参数

3. **不要在生产环境使用 `--force`**
   - 除非确实需要重新导入

## 监控和日志

### 实时监控

```bash
# 在另一个终端中查看状态
watch -n 5 'python manage.py import_oracle_sql --show-status --batch-id a1b2c3d4'
```

### 导出日志

```bash
# 导出导入状态
python manage.py dbshell <<EOF
SELECT * FROM sql_import_log 
WHERE batch_id = 'a1b2c3d4' 
INTO OUTFILE '/tmp/import_status.csv'
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
EOF
```

## 常见问题

### Q1: 导入中断后如何恢复？

使用 `--resume` 参数：
```bash
python manage.py import_oracle_sql --batch-id <ID> --resume
```

### Q2: 如何避免数据重复？

1. 使用状态表（自动）
2. 数据库唯一键约束（自动忽略重复键错误）
3. 不要使用 `--force` 参数

### Q3: 事务回滚后表结构还在？

是的。DDL 语句（CREATE TABLE）会立即提交，无法回滚。只有 DML 语句（INSERT）会回滚。

### Q4: 如何处理超大文件？

```bash
# 方案 1：禁用事务
python manage.py import_oracle_sql file.sql --no-transaction

# 方案 2：拆分文件（使用工具）
split -l 100000 huge_file.sql split_
```

### Q5: 导入失败如何清理？

```sql
-- 查看已创建的表
SHOW TABLES LIKE 'gzlry_%';

-- 根据需要删除
DROP TABLE IF EXISTS table_name;
```

## 总结

新的导入命令提供了完整的数据完整性保证：

| 特性 | 说明 | 命令参数 |
|------|------|---------|
| 事务管理 | 文件级原子性 | 默认启用 |
| 状态追踪 | 记录导入历史 | 自动 |
| 断点续导 | 继续未完成的导入 | `--resume` |
| 失败重试 | 只重试失败的文件 | `--retry-failed` |
| 防止重复 | 自动跳过已成功的文件 | 自动 |
| 查看状态 | 查看导入历史和详情 | `--show-status` |

这些特性组合起来，确保了即使在导入中断、失败等情况下，也能保证数据的完整性和一致性。

