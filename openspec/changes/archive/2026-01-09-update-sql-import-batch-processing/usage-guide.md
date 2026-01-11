# SQL 导入命令使用指南

## 命令概述

`import_oracle_sql` 命令用于将转换后的 MySQL SQL 文件批量导入到数据库中。该命令支持大文件处理、文件过滤、进度显示等功能。

## 基本用法

### 1. 快捷导入（推荐）

最简单的方式，直接导入 `docs/hospital/convertsql/` 目录下的所有文件：

```bash
cd backend-django
python manage.py import_oracle_sql --default-convertsql
```

### 2. 导入单个文件

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/gzlry_BS_DEPARTMENT.sql
```

### 3. 导入指定目录

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all
```

## 高级功能

### 跳过大文件

如果想跳过超过 100MB 的大文件（避免内存问题或导入时间过长）：

```bash
python manage.py import_oracle_sql --default-convertsql --skip-large-files
```

### 自定义文件大小上限

只导入小于 50MB 的文件：

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --max-size 50
```

### 预览模式（不实际导入）

查看文件内容和统计信息，但不执行导入：

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --dry-run
```

### 遇到错误继续处理

如果某个文件导入失败，继续处理剩余文件：

```bash
python manage.py import_oracle_sql --default-convertsql --continue-on-error
```

## 完整参数说明

| 参数 | 说明 |
|------|------|
| `path` | SQL 文件或目录路径（可选，使用 `--default-convertsql` 时不需要） |
| `--all` | 处理目录下所有 SQL 文件 |
| `--default-convertsql` | 快捷导入 `docs/hospital/convertsql/` 目录 |
| `--skip-large-files` | 自动跳过超过 100MB 的文件 |
| `--max-size N` | 跳过超过 N MB 的文件 |
| `--dry-run` | 预览模式，不执行导入 |
| `--continue-on-error` | 遇到错误时继续处理 |

## 实际案例

### 案例 1：首次全量导入（跳过超大文件）

```bash
# 导入所有小于 100MB 的文件
python manage.py import_oracle_sql --default-convertsql --skip-large-files --continue-on-error
```

预期输出：
```
使用默认转换目录: docs/hospital/convertsql/
跳过 19 个大文件（超过 100MB）：
  - gzlry_BSE_NURSE_INSPECTION.sql (109.2MB)
  - gzlry_BSE_NURSE_INSPECTION_OLDER.sql (240.4MB)
  - gzlry_CH_BANK.sql (257.3MB)
  - gzlry_CH_EXPENSE.sql (1.11GB)
  - gzlry_EG_REQUEST_LOG.sql (2.32GB)
  ... 和其他 14 个文件

找到 955 个待处理的 SQL 文件
[1/955] 处理: gzlry_BS_DEPARTMENT.sql (12.5KB)
  导入成功
[2/955] 处理: gzlry_BS_DICT.sql (45.3KB)
  导入成功
...
==================================================
处理完成: 成功 950/955, 失败 5, 跳过 19
```

### 案例 2：导入特定大小范围的文件

```bash
# 只导入 10MB - 50MB 的中等文件
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --max-size 50
```

### 案例 3：预览文件内容

```bash
# 查看某个文件的内容，不实际导入
python manage.py import_oracle_sql ../docs/hospital/convertsql/gzlry_BS_DEPARTMENT.sql --dry-run
```

## 性能优化

该命令针对大文件做了以下优化：

1. **流式读取**：超过 10MB 的文件使用逐行读取，避免内存溢出
2. **按大小排序**：优先处理小文件，快速看到导入效果
3. **文件过滤**：可以跳过超大文件，减少处理时间
4. **错误忽略**：自动忽略表已存在、重复键等常见错误

## 注意事项

1. **数据库连接**：确保 Django 的数据库配置正确
2. **外键约束**：命令会自动禁用外键检查，导入完成后恢复
3. **大文件处理**：对于 GB 级别的文件，建议使用 `--skip-large-files` 或手动处理
4. **备份数据**：建议在导入前备份数据库

## 常见问题

### Q: 如何查看有多少文件会被跳过？

A: 使用 `--dry-run` 参数预览：

```bash
python manage.py import_oracle_sql --default-convertsql --skip-large-files --dry-run
```

### Q: 导入失败后如何重试？

A: 命令支持重复执行，会自动忽略"表已存在"等错误。可以直接重新运行命令。

### Q: 如何只导入失败的文件？

A: 从输出报告中找到失败的文件名，然后单独导入：

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/failed_file.sql
```

### Q: 大文件导入太慢怎么办？

A: 可以使用 `--max-size` 参数跳过大文件，或者单独在非高峰期导入大文件。

## 文件统计（基于测试数据）

根据 `docs/hospital/convertsql/` 目录的实际情况：

- 总文件数：974 个
- 小文件（< 10MB）：897 个
- 中等文件（10MB - 100MB）：58 个
- 大文件（> 100MB）：19 个

建议策略：
1. 先导入所有小于 100MB 的文件（955 个）
2. 对于 19 个大文件，根据实际需求选择性导入

