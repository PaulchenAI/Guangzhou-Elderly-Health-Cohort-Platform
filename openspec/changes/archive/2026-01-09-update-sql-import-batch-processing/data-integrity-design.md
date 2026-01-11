# 数据导入完整性设计方案

## 问题分析

当前 `import_oracle_sql` 命令存在以下数据完整性风险：

### 1. **缺少事务管理**
- 每个 SQL 语句独立执行，没有整体事务保护
- 导入失败时已执行的语句无法回滚
- 可能导致数据处于不一致状态

### 2. **无法防止重复导入**
- 没有导入状态记录
- 重复运行命令会导致数据重复插入
- INSERT 语句会重复执行

### 3. **无法断点续导**
- 导入中断后不知道哪些文件已完成
- 必须重新从头开始
- 浪费时间和资源

## 解决方案

### 方案 A：文件级事务（推荐）

**优点**：
- 实现简单
- 每个文件作为一个事务单元
- 失败自动回滚该文件的所有更改
- 支持断点续导

**实现**：
```python
# 每个文件使用一个事务
with transaction.atomic():
    execute_sql_file(file)
```

**适用场景**：
- 文件数量多（974 个）
- 单文件相对较小（< 100MB）
- 需要精确控制每个文件的导入状态

### 方案 B：语句级事务

**优点**：
- 最细粒度控制
- 可以记录每条 SQL 的执行状态

**缺点**：
- 性能开销大
- 需要复杂的状态表
- 对于大量 INSERT 语句不实用

**不推荐**：INSERT 语句太多（数百万条）

### 方案 C：全量事务

**优点**：
- 最简单
- 要么全部成功，要么全部失败

**缺点**：
- 长时间锁定数据库
- 失败后需要重新导入所有文件
- 不支持断点续导

**不推荐**：文件太多，导入时间太长

## 推荐方案详细设计

### 核心机制：文件级事务 + 状态追踪

#### 1. 创建导入状态表

```sql
CREATE TABLE IF NOT EXISTS sql_import_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    status ENUM('pending', 'processing', 'success', 'failed', 'skipped') NOT NULL,
    error_message TEXT,
    start_time DATETIME,
    end_time DATETIME,
    batch_id VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_file_batch (file_name, batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2. 导入流程

```
1. 生成批次 ID（batch_id）
2. 扫描目录，记录所有文件到状态表（status='pending'）
3. 对每个文件：
   a. 检查状态（跳过已完成的文件）
   b. 更新状态为 'processing'
   c. 开启事务
   d. 执行 SQL
   e. 提交事务
   f. 更新状态为 'success'
   g. 如果失败：
      - 回滚事务
      - 更新状态为 'failed'
      - 记录错误信息
4. 生成报告
```

#### 3. 断点续导

```bash
# 查看上次导入状态
python manage.py import_oracle_sql --default-convertsql --show-status

# 继续上次未完成的导入
python manage.py import_oracle_sql --default-convertsql --resume

# 重新导入失败的文件
python manage.py import_oracle_sql --default-convertsql --retry-failed
```

#### 4. 防止重复导入

使用幂等性策略：

**策略 1：基于状态表**
```python
# 检查文件是否已成功导入
if file already imported successfully:
    skip this file
```

**策略 2：基于数据库状态（推荐）**
```python
# 忽略重复键错误（当前已实现）
# INSERT 语句如果主键/唯一键冲突，自动跳过
```

#### 5. 回滚策略

**文件级回滚**：
```python
try:
    with transaction.atomic():
        # 执行整个文件的所有 SQL
        for stmt in statements:
            cursor.execute(stmt)
        # 成功则自动提交
except Exception as e:
    # 失败则自动回滚整个文件
    log_error(file, e)
```

**注意**：
- CREATE TABLE 语句在 MySQL 中会隐式提交事务
- 需要将 DDL 和 DML 分开处理

### 实现策略

#### 阶段 1：状态追踪（优先级高）
- 添加导入状态表
- 记录每个文件的导入状态
- 支持查看导入历史

#### 阶段 2：事务管理（优先级高）
- 每个文件使用独立事务
- 失败自动回滚
- 成功自动提交

#### 阶段 3：断点续导（优先级中）
- 支持 `--resume` 参数
- 自动跳过已成功的文件
- 只导入 pending 和 failed 状态的文件

#### 阶段 4：智能重试（优先级低）
- 支持 `--retry-failed` 参数
- 只重试上次失败的文件
- 可配置重试次数

## 数据完整性保证

### 1. 原子性（Atomicity）
- ✅ 每个文件作为一个原子单元
- ✅ 要么全部成功，要么全部回滚

### 2. 一致性（Consistency）
- ✅ 事务保证数据库始终处于一致状态
- ✅ 外键约束在事务内检查

### 3. 隔离性（Isolation）
- ✅ 使用默认的事务隔离级别
- ⚠️  并发导入需要额外处理（通过批次 ID 区分）

### 4. 持久性（Durability）
- ✅ 提交后数据持久化到磁盘
- ✅ 状态表记录导入历史

## 兼容性考虑

### DDL 语句的特殊处理

MySQL 中 DDL 语句（CREATE TABLE、ALTER TABLE 等）会导致隐式提交。

**解决方案**：
```python
# 分离 DDL 和 DML
ddl_statements = [stmt for stmt in statements if is_ddl(stmt)]
dml_statements = [stmt for stmt in statements if not is_ddl(stmt)]

# DDL 不使用事务（已经是隐式提交）
for stmt in ddl_statements:
    execute(stmt)

# DML 使用事务
with transaction.atomic():
    for stmt in dml_statements:
        execute(stmt)
```

## 使用示例

### 场景 1：首次导入

```bash
# 开始导入
python manage.py import_oracle_sql --default-convertsql

# 如果中断，继续导入
python manage.py import_oracle_sql --default-convertsql --resume
```

### 场景 2：查看导入状态

```bash
# 查看所有导入记录
python manage.py import_oracle_sql --show-status

# 查看特定批次
python manage.py import_oracle_sql --show-status --batch-id abc123
```

### 场景 3：重试失败的文件

```bash
# 只重新导入上次失败的文件
python manage.py import_oracle_sql --default-convertsql --retry-failed
```

### 场景 4：强制重新导入

```bash
# 忽略状态表，强制重新导入（适用于数据更新）
python manage.py import_oracle_sql --default-convertsql --force
```

## 性能影响

| 特性 | 性能影响 | 说明 |
|------|---------|------|
| 文件级事务 | 轻微 | 每个文件一个事务，开销可控 |
| 状态表记录 | 很小 | 只在文件开始/结束时写入 |
| 断点续导 | 无影响 | 只是跳过已完成的文件 |
| 事务回滚 | 中等 | 只在失败时触发 |

**预期**：总体性能影响 < 5%

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 事务超时 | 大文件导入失败 | 对超大文件禁用事务 |
| 锁等待 | 并发冲突 | 建议单进程导入 |
| 状态表冲突 | 并发写入失败 | 使用批次 ID 隔离 |
| 磁盘空间不足 | 导入中断 | 预先检查磁盘空间 |

## 建议

1. **优先实现阶段 1 和 2**：状态追踪 + 事务管理
2. **对于超大文件（> 1GB）**：考虑关闭事务或分批处理
3. **定期清理状态表**：避免历史记录过多
4. **测试回滚**：确保事务回滚正常工作

