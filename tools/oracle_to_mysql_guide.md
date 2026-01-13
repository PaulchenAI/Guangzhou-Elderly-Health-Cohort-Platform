# Oracle 到 MySQL SQL 转换工具使用指南

## 概述

`oracle_to_mysql.py` 是一个功能强大的 Oracle SQL 到 MySQL SQL 转换工具，支持以下功能：

- **基础转换**：将 Oracle 数据类型、函数转换为 MySQL 兼容格式
- **COMMENT 转换**：保留表注释和列注释
- **表名前缀**：为表名添加自定义前缀
- **DDL/DML 分离**：将表结构和数据分离到不同文件
- **自动修复**：转换完成后自动调用修复工具

---

## 快速开始

### 基本用法

```bash
# 转换单个文件
python tools/oracle_to_mysql.py convert docs/hospital/sql/BS_AREA.sql

# 转换整个目录
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ -o docs/hospital/convertsql
```

### 推荐用法（全功能）

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml \
    --enable-comments \
    --table-prefix gzlry_ \
    --auto-fix
```

---

## 命令行参数

### convert 命令（单文件转换）

```bash
python tools/oracle_to_mysql.py convert <文件路径> [选项]

参数：
  文件路径              Oracle SQL 文件路径

选项：
  -o, --output PATH     输出文件路径
  --output-dir DIR      输出目录（默认: docs/hospital/convertsql）
  --prefix PREFIX       输出文件名前缀
  --table-prefix PREFIX 表名前缀（在 SQL 语句中添加）
  --enable-comments     启用 COMMENT 转换
  --force               强制重新转换
  --skip-existing       跳过已存在的文件
```

### convert-all 命令（批量转换）

```bash
python tools/oracle_to_mysql.py convert-all <目录路径> -o <输出目录> [选项]

参数：
  目录路径              包含 Oracle SQL 文件的目录

必需选项：
  -o, --output-dir DIR  输出目录

可选选项：
  --prefix PREFIX       输出文件名前缀
  --table-prefix PREFIX 表名前缀（在 SQL 语句中添加）
  --split-ddl-dml       分离 DDL 和 DML 文件
  --enable-comments     启用 COMMENT 转换
  --auto-fix            转换后自动调用修复工具
  --force               强制重新转换所有文件
  --skip-existing       跳过已存在且完整的文件
```

---

## 功能详解

### 1. COMMENT 转换（--enable-comments）

将 Oracle 的 `COMMENT ON TABLE` 和 `COMMENT ON COLUMN` 语句转换为 MySQL 格式。

**Oracle 原始格式：**
```sql
CREATE TABLE BS_AREA (
  mainid VARCHAR2(50) not null,
  areaname VARCHAR2(50)
);
COMMENT ON TABLE BS_AREA IS '院区表';
COMMENT ON COLUMN BS_AREA.mainid IS '主键ID';
COMMENT ON COLUMN BS_AREA.areaname IS '院区名称';
```

**MySQL 转换结果：**
```sql
CREATE TABLE BS_AREA (
  mainid VARCHAR(50) NOT NULL COMMENT '主键ID',
  areaname VARCHAR(50) COMMENT '院区名称'
) COMMENT='院区表'
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2. 表名前缀（--table-prefix）

为所有表名添加指定前缀，适用于多租户场景或避免表名冲突。

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --table-prefix gzlry_
```

**转换效果：**
- `CREATE TABLE BS_AREA` → `CREATE TABLE gzlry_BS_AREA`
- `DROP TABLE IF EXISTS BS_AREA` → `DROP TABLE IF EXISTS gzlry_BS_AREA`
- `INSERT INTO BS_AREA` → `INSERT INTO gzlry_BS_AREA`

### 3. DDL/DML 分离（--split-ddl-dml）

将表结构定义（DDL）和数据插入语句（DML）分离到不同的目录和文件。

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml
```

**输出目录结构：**
```
docs/hospital/convertsql/
├── create/                    # DDL 目录（表结构）
│   ├── BS_AREA.sql
│   ├── BS_BUILDINGS.sql
│   └── ...
└── insert/                    # DML 目录（数据）
    ├── BS_AREA_data.sql
    ├── BS_BUILDINGS_data.sql
    └── ...
```

**DDL 文件内容示例（create/BS_AREA.sql）：**
```sql
DROP TABLE IF EXISTS BS_AREA;

CREATE TABLE BS_AREA (
  mainid VARCHAR(50) NOT NULL COMMENT '主键ID',
  areaname VARCHAR(50) COMMENT '院区名称'
) COMMENT='院区表'
ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**DML 文件内容示例（insert/BS_AREA_data.sql）：**
```sql
INSERT INTO BS_AREA (mainid, areaname) VALUES ('1', '总院');

INSERT INTO BS_AREA (mainid, areaname) VALUES ('2', '分院');
```

### 4. 自动修复（--auto-fix）

转换完成后自动调用 `sql-fix-tools` 进行修复，处理常见的兼容性问题。

```bash
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml \
    --auto-fix
```

---

## 分阶段导入指南

使用 `--split-ddl-dml` 分离后，可以分阶段导入数据库：

### 步骤 1：导入表结构（DDL）

```bash
cd backend-django

# 导入 create/ 目录中的所有表结构
python manage.py import_oracle_sql \
    --batch-id create_001 \
    --sql-dir ../docs/hospital/convertsql/create \
    --continue-on-error
```

### 步骤 2：验证表结构

```bash
# 查看导入状态
python manage.py import_oracle_sql --show-status --batch-id create_001

# 或者直接查看数据库
python manage.py dbshell
mysql> SHOW TABLES;
mysql> DESCRIBE gzlry_BS_AREA;
```

### 步骤 3：导入数据（DML）

```bash
# 导入 insert/ 目录中的所有数据
python manage.py import_oracle_sql \
    --batch-id insert_001 \
    --sql-dir ../docs/hospital/convertsql/insert \
    --continue-on-error
```

### 步骤 4：验证数据

```bash
# 查看导入状态
python manage.py import_oracle_sql --show-status --batch-id insert_001

# 验证数据
python manage.py dbshell
mysql> SELECT COUNT(*) FROM gzlry_BS_AREA;
```

---

## 常见用例

### 用例 1：简单转换

```bash
# 不使用任何新功能，保持原有行为
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql
```

### 用例 2：多租户场景

```bash
# 为不同客户生成不同前缀的表
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql_clientA \
    --table-prefix clientA_

python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql_clientB \
    --table-prefix clientB_
```

### 用例 3：保留完整文档

```bash
# 保留所有 COMMENT 信息
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --enable-comments
```

### 用例 4：生产环境部署

```bash
# 分离 DDL/DML，便于分阶段部署
python tools/oracle_to_mysql.py convert-all docs/hospital/sql/ \
    -o docs/hospital/convertsql \
    --split-ddl-dml \
    --enable-comments \
    --table-prefix prod_ \
    --auto-fix
```

---

## 故障排查

### 问题 1：COMMENT 中的特殊字符

如果 Oracle COMMENT 包含单引号，工具会自动转义为 `''`。

**原始：**
```sql
COMMENT ON COLUMN BS_AREA.name IS '院区''s名称';
```

**转换后：**
```sql
name VARCHAR(50) COMMENT '院区''s名称'
```

### 问题 2：空表处理

如果表没有数据（0 个 INSERT 语句），分离模式下只会生成 DDL 文件，不会创建空的 DML 文件。

**日志输出：**
```
[INFO] BSE_DATA_PUSH_RECORD: 无数据（仅生成 DDL）
```

### 问题 3：大文件处理

工具使用流式处理，即使处理超大文件（如 100MB+）也不会占用过多内存。

**日志输出：**
```
[INFO] 开始转换大文件（15.2 MB），请稍候...
[INFO] 进度: 已转换 10,000 个语句，文件读取 45.2%
[INFO] 转换完成: 共处理 50,000 行，转换 45,678 个语句
```

### 问题 4：导入失败

如果导入失败，请检查：

1. **MySQL 保留字**：某些列名可能是 MySQL 保留字，需要用反引号包裹
2. **数据类型不兼容**：检查是否有未转换的 Oracle 特有类型
3. **字符编码问题**：确保数据库使用 utf8mb4 编码

---

## 最佳实践

1. **始终使用 --split-ddl-dml**：便于分阶段导入和问题定位
2. **始终使用 --enable-comments**：保留数据库文档
3. **测试环境先行**：先在测试环境验证，再部署到生产环境
4. **使用 --auto-fix**：自动处理常见兼容性问题
5. **检查转换日志**：关注警告和错误信息
6. **保留原始文件**：转换不会修改原始 Oracle SQL 文件

---

## 相关文档

- [SQL 修复工具集](sql-fix-tools/README.md)
- [SQL 导入规范](../openspec/specs/sql-import/spec.md)
- [后端 API 开发指南](../docs/backend-api-development-guide.md)

---

最后更新: 2026-01-13
