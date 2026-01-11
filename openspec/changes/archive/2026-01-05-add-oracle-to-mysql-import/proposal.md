# 变更：添加 Oracle SQL 导入 MySQL 功能

## 为什么

项目需要将 `docs/hospital/sql/` 目录下的历史 Oracle 数据库导出文件（约 400+ 个 SQL 文件）导入到 MySQL 数据库中。这些文件包含医院管理系统的基础数据表结构和初始数据。

## 变更内容

- 新增 Oracle 到 MySQL 的 SQL 语法转换工具（`tools/oracle_to_mysql.py`）
- 新增批量导入转换后 SQL 文件的管理命令（`python manage.py import_oracle_sql`）
- 转换工具功能：
  - 只保留表结构和数据（`CREATE TABLE` 和 `INSERT INTO` 语句）
  - `VARCHAR2` → `VARCHAR`，`NUMBER` → `DECIMAL`/`INT`，`DATE` → `DATETIME`
  - 移除 Oracle 特有的 `tablespace`、`storage`、`pctfree` 等子句
  - 移除 `prompt`、`set feedback`、`set define` 等 PL/SQL 命令
  - 转换 `to_date()` → `STR_TO_DATE()`，`chr()` → `CHAR()`
  - 转换 `||` 连接符 → `CONCAT()`
  - 支持文件名前缀（`--prefix` 参数）
  - 转换后的文件保存到指定目录（默认：`docs/hospital/convertsql/`）
- 导入命令功能：
  - 读取转换后的 MySQL SQL 文件
  - 支持单个文件或目录批量导入
  - 自动处理外键检查
  - 支持预览模式（`--dry-run`）

## 影响

- 受影响规范：新增 `sql-import` 功能模块
- 受影响代码：
  - `tools/oracle_to_mysql.py` - Oracle 到 MySQL 转换工具
  - `backend-django/core/management/commands/import_oracle_sql.py` - Django 导入命令
- 新增目录：
  - `docs/hospital/convertsql/` - 存放转换后的 MySQL SQL 文件

