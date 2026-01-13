# SQL修复工具集

专门用于修复Oracle SQL转MySQL SQL过程中的各种兼容性问题。

## 目录结构

```
tools/
├── oracle_to_mysql.py           # Oracle转MySQL转换工具（支持自动调用修复）
└── sql-fix-tools/               # 规则修复工具
    ├── fix_sql_main.py          # 一键修复脚本
    ├── fix_special_sql_issues.py# 特殊问题修复
    └── fix_remaining_concat.py  # CONCAT残留修复
```

---

## 🚀 推荐工作流

### 方式一：自动化集成（推荐）

使用 `oracle_to_mysql.py` 的 `--auto-fix` 参数，转换完成后自动调用修复工具：

```bash
# 转换并自动修复（一步完成）
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml \
    --enable-comments \
    --auto-fix

# 输出目录结构：
# docs/hospital/convertsql/
# ├── create/    # DDL 文件（表结构）
# └── insert/    # DML 文件（数据）
```

### 方式二：手动分步执行

```bash
# 步骤1: 转换（不自动修复）
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml

# 步骤2: 手动修复
cd tools/sql-fix-tools
python fix_sql_main.py --target-dir ../../docs/hospital/convertsql/create
python fix_sql_main.py --target-dir ../../docs/hospital/convertsql/insert

# 步骤3: 导入验证
cd ../../backend-django
python manage.py import_oracle_sql --batch-id test001 --default-convertsql
```

### 方式三：传统工作流（兼容旧版本）

```bash
# 步骤1: 规则修复（处理常见问题）
cd /mnt/f/work/zq-platform/tools/sql-fix-tools
python fix_sql_main.py

# 步骤2: 导入SQL（测试修复效果）
cd ../../backend-django
python manage.py import_oracle_sql --batch-id test001 --default-convertsql --continue-on-error --auto-fix

# 步骤3: 根据错误日志手动修复剩余问题
# 查看日志: logs/import_test001.log

# 步骤4: 重新导入验证
python manage.py import_oracle_sql --batch-id test001 --retry-failed
```

---

## 📖 工具说明

### 规则修复工具（sql-fix-tools/）

**适用**：可预测的、有明确模式的SQL转换问题

#### 命令行参数

```bash
python fix_sql_main.py [选项]

选项：
  --target-dir, -t DIR    指定要修复的目录（默认使用配置文件中的目录）
  --quiet, -q             减少输出信息（适合自动化调用）
  -h, --help              显示帮助信息
```

#### 一键修复

```bash
# 修复默认目录
cd /mnt/f/work/zq-platform/tools/sql-fix-tools
python fix_sql_main.py

# 修复指定目录
python fix_sql_main.py --target-dir /path/to/sql/files

# 静默模式（适合脚本调用）
python fix_sql_main.py --target-dir /path/to/sql/files --quiet
```

#### 分离模式下的修复

当使用 `oracle_to_mysql.py --split-ddl-dml` 时，DDL 和 DML 会分离到不同目录，需要分别修复：

```bash
# 修复 DDL 文件（表结构）
python fix_sql_main.py --target-dir docs/hospital/convertsql/create

# 修复 DML 文件（数据）
python fix_sql_main.py --target-dir docs/hospital/convertsql/insert
```

#### 分步修复

##### 步骤1: 修复特殊SQL问题
```bash
python fix_special_sql_issues.py
```

**修复内容**：
- HR_CEREBRAL_STROKE.sql - 缺失列定义
- OL_RECORD.sql - Oracle sysdate函数
- WM_USE_REGISTER.sql - 引号问题
- WM_PURCHASE.sql - 引号问题
- 7个文件的CONCAT不完整转换

##### 步骤2: 修复残留的CONCAT问题
```bash
python fix_remaining_concat.py
```

**修复内容**：
- 处理复杂的嵌套CONCAT结构
- 合并多个CONCAT调用

---

## 已修复的问题类型

### ✅ 规则修复（自动）

#### 1. 表结构相关
- **缺失列定义** - HR_CEREBRAL_STROKE表缺少quit_smoking和quit_drinking列
- **sysdate函数** - OL_RECORD表的create_time默认值从sysdate改为CURRENT_TIMESTAMP(6)

#### 2. 字符串拼接
- **Oracle || 转换** - 修复CONCAT不完整转换
- **嵌套CONCAT** - 处理复杂的CONCAT嵌套结构
- **CONCAT合并** - `CONCAT(...) || CONCAT(...)` → `CONCAT(..., ...)`

#### 3. 引号和转义
- **单引号嵌套** - WM_USE_REGISTER和WM_PURCHASE表的数据
- **转义字符** - 特殊字符的正确转义

#### 4. 保留字和特殊字符
- **MySQL保留字** - 如 `describe`、`key` 等需要用反引号包裹
- **特殊字符列名** - 如 `line#` 需要用反引号包裹

### 常见错误类型

| 错误码 | 类型 | 修复方法 | 示例 |
|--------|------|----------|------|
| 1064 | SQL语法错误 | 检查保留字、特殊字符 | `describe` → `` `describe` `` |
| 1292 | 数据类型转换错误 | 检查CONCAT函数、引号嵌套 | 修复字符串拼接 |
| 1054 | 字段不存在 | 添加缺失列定义 | 补充表结构 |
| 1118 | 行大小过大 | VARCHAR转TEXT | 调整字段类型 |

---

## 📊 修复效果统计

### 规则修复（已验证）

- ✅ 修复文件数: 11个
- ✅ 问题类型: 7种
- ✅ 成功率: ~80%

---

## 💡 最佳实践

1. **优先使用规则修复**：规则修复快速可靠，应优先使用
2. **增量测试**：修复一批后及时测试，避免积累问题
3. **仔细阅读日志**：详细日志中包含错误位置和SQL片段
4. **保留备份**：修复前备份重要文件
5. **手动审核**：自动修复后检查关键表结构

---

## 🔧 手动修复指南

### 1. MySQL保留字问题

**错误示例**：
```sql
create table EXAMPLE (
  describe VARCHAR(100)  -- 错误：describe是MySQL保留字
);
```

**修复方法**：
```sql
create table EXAMPLE (
  `describe` VARCHAR(100)  -- 正确：使用反引号包裹
);
```

### 2. 特殊字符列名

**错误示例**：
```sql
create table EXAMPLE (
  line# INT  -- 错误：#是特殊字符
);
```

**修复方法**：
```sql
create table EXAMPLE (
  `line#` INT  -- 正确：使用反引号包裹
);
```

### 3. CONCAT函数问题

**错误示例**：
```sql
-- Oracle语法
column_value || CONCAT('text', value) || 'end'
```

**修复方法**：
```sql
-- MySQL语法
CONCAT(column_value, 'text', value, 'end')
```

---

## 🔧 故障排查

### 规则修复问题

详见 [修复总结.md](修复总结.md)

### 常见导入错误

1. **错误1064** - SQL语法错误
   - 检查是否使用了MySQL保留字
   - 检查列名是否包含特殊字符
   - 检查引号是否正确闭合

2. **错误1292** - 数据类型转换错误
   - 检查CONCAT函数的参数
   - 检查字符串中的特殊字符

3. **错误1054** - 字段不存在
   - 检查表结构定义
   - 确认INSERT语句中的列名

---

## 📚 相关文档

- **规则修复详情**：[修复总结.md](修复总结.md)
- **使用示例**：[使用示例.md](使用示例.md)
- **SQL导入规范**：[../../openspec/specs/sql-import/spec.md](../../openspec/specs/sql-import/spec.md)

---

## 🔄 自动化集成

### oracle_to_mysql.py 集成

`oracle_to_mysql.py` 支持在转换完成后自动调用本工具进行修复：

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --auto-fix
```

当同时使用 `--split-ddl-dml` 和 `--auto-fix` 时，会自动分别修复 `create/` 和 `insert/` 目录：

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml \
    --auto-fix
```

### 工作流程图

```
Oracle SQL 文件
       ↓
oracle_to_mysql.py (转换)
       ↓
   ┌───┴───┐
   │       │
   ↓       ↓
create/  insert/   (--split-ddl-dml 模式)
   │       │
   ↓       ↓
sql-fix-tools (--auto-fix 自动调用)
   │       │
   ↓       ↓
修复后的 MySQL SQL
       ↓
import_oracle_sql (导入数据库)
```

---

## 🎉 下一步

1. **推荐**：使用自动化集成
   ```bash
   python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
       -o docs/hospital/convertsql --split-ddl-dml --auto-fix
   ```

2. 或者手动运行规则修复：
   ```bash
   cd sql-fix-tools && python fix_sql_main.py --target-dir ../docs/hospital/convertsql
   ```

3. 测试导入效果：
   ```bash
   cd backend-django && python manage.py import_oracle_sql --batch-id test001 --default-convertsql
   ```

4. 查看错误日志：`cat backend-django/logs/import_*.log`

5. 根据日志手动修复剩余问题

---

最后更新: 2026-01-13
