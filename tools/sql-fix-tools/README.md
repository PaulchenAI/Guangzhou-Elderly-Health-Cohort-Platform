# SQL修复工具集

专门用于修复Oracle SQL转MySQL SQL过程中的各种兼容性问题。

## 目录结构

```
tools/
└── sql-fix-tools/                # 规则修复工具
    ├── fix_sql_main.py          # 一键修复脚本
    ├── fix_special_sql_issues.py# 特殊问题修复
    └── fix_remaining_concat.py  # CONCAT残留修复
```

---

## 🚀 推荐工作流

### 完整的SQL修复流程

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

#### 一键修复
```bash
cd /mnt/f/work/zq-platform/tools/sql-fix-tools
python fix_sql_main.py
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

## 🎉 下一步

1. 运行规则修复：`cd sql-fix-tools && python fix_sql_main.py`
2. 测试导入效果：`cd ../../backend-django && python manage.py import_oracle_sql...`
3. 查看错误日志：`cat backend-django/logs/import_*.log`
4. 根据日志手动修复剩余问题

---

最后更新: 2026-01-10
