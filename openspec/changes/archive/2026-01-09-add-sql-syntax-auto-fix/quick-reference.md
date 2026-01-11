# SQL 自动修复功能 - 快速参考卡片

## 🚀 快速开始

### 基本用法

```bash
# 自动修复并导入
python manage.py import_oracle_sql --default-convertsql --auto-fix

# 重试失败的文件（自动修复）
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix
```

## 📝 新增参数

| 参数 | 说明 |
|------|------|
| `--auto-fix` | 启用自动修复 |
| `--save-fixed` | 保存修复后的文件 |
| `--fix-report` | 生成修复报告 |

## 🔧 常见场景

### 场景 1：导入失败，看到保留字错误

```bash
# 错误提示
(1064, "... near 'describe VARCHAR(4000)'")

# 解决方案
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix
```

### 场景 2：批量导入 + 自动修复

```bash
python manage.py import_oracle_sql --default-convertsql \
    --auto-fix \
    --fix-report \
    --continue-on-error
```

### 场景 3：只修复文件，不导入

```bash
python manage.py import_oracle_sql file.sql \
    --auto-fix \
    --save-fixed \
    --dry-run
```

## ✅ 支持的修复（15+ 种）

### 基础修复
1. ✅ MySQL 保留字（250+ 个：`describe`, `key`, `explain`, `condition`）
2. ✅ 大 VARCHAR 转 TEXT（`VARCHAR(4000)` → `TEXT`）
3. ✅ 特殊字符列名（`line#` → `` `line#` ``）
4. ✅ 尾随逗号清理（CREATE TABLE 最后一列）

### 数据类型修复
5. ✅ NUMBER(*,n) → DECIMAL(65,n)
6. ✅ NVARCHAR → VARCHAR
7. ✅ DOUBLE(n) → DOUBLE
8. ✅ INT 溢出 → BIGINT（智能检测数据值）

### 函数和操作符修复
9. ✅ sysdate → CURRENT_TIMESTAMP
10. ✅ to_timestamp → STR_TO_DATE（含格式转换）
11. ✅ || 字符串连接 → CONCAT()

### 标识符修复
12. ✅ 双引号 → 反引号（`"date"` → `` `date` ``）
13. ✅ INSERT 列名保留字

### 字符串修复
14. ✅ 反斜杠转义（`'\'` → `'\\'`）
15. ✅ SQL 转义单引号支持（`''`）

### Oracle 特定语法
16. ✅ ALTER TABLE ENABLE ALL TRIGGERS（注释掉）

## 🛡️ 安全保证

- ✅ 不修改源文件
- ✅ 不修复字符串内的内容
- ✅ 不修复已有反引号的标识符
- ✅ 不改变 SQL 语义

## 📊 查看结果

```bash
# 查看状态
python manage.py import_oracle_sql --show-status --batch-id <ID>

# 查看报告
cat sql_fix_report_<ID>.txt
```

## 🐛 故障排除

```bash
# 1. 查看错误
python manage.py import_oracle_sql --show-status

# 2. 重试（自动修复）
python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix

# 3. 查看修复报告
cat sql_fix_report_*.txt
```

## 📖 相关文档

- 详细使用指南：`usage-guide.md`
- 错误处理指南：`error-handling-guide.md`
- 设计文档：`design.md`
- 实施总结：`implementation-summary.md`

---

**提示**：所有参数都是可选的，不会影响现有功能。

