# 变更：增强 Oracle 到 MySQL 转换工具

## 为什么

当前的 Oracle 到 MySQL SQL 转换工具（`tools/oracle_to_mysql.py`）存在以下问题：

1. **丢失重要的元数据信息**：转换过程中忽略了 Oracle 的 `COMMENT ON TABLE` 和 `COMMENT ON COLUMN` 语句，导致表和列的注释信息完全丢失，影响数据库可维护性和可读性。

2. **表名前缀功能缺失**：虽然工具支持 `--prefix` 参数用于文件名前缀，但没有实现对 SQL 语句中实际表名的前缀添加功能。这对于多租户场景或避免表名冲突的情况非常重要（例如：需要将 `BS_AREA` 转换为 `gzlry_BS_AREA`）。

3. **缺少自动化修复流程**：Oracle 转 MySQL 后，经常需要手动运行 `sql-fix-tools` 工具集进行二次修复（如保留字处理、特殊字符转义等）。这两个步骤分离，增加了操作复杂度和出错概率。

这些问题导致：
- 数据库缺少字段说明，开发者需要查看原始 Oracle 文件才能理解字段含义
- 无法为不同客户/项目的表添加标识前缀，可能产生表名冲突
- 需要记住两步转换流程，容易遗漏修复步骤

## 变更内容

### 1. 保留 COMMENT 注释信息

- 转换 Oracle 的 `COMMENT ON TABLE` 语句为 MySQL 的 `ALTER TABLE ... COMMENT='...'`
- 转换 Oracle 的 `COMMENT ON COLUMN` 语句为列定义中的 `COMMENT '...'`
- 支持在 CREATE TABLE 语句中内联添加列注释
- 支持在表创建后追加表注释的 ALTER TABLE 语句

### 2. 实现 SQL 表名前缀功能

- 新增 `--table-prefix` 参数，用于在 SQL 语句中为表名添加前缀
- 自动识别 CREATE TABLE、INSERT INTO、ALTER TABLE 等语句中的表名并添加前缀
- 保持 `--prefix` 参数用于文件名前缀（向后兼容）
- 支持仅修改表名前缀或同时修改文件名和表名前缀

### 3. DDL 和 DML 文件分离

- 将 CREATE TABLE（DDL）和 INSERT INTO（DML）语句分离到不同文件
- DDL 文件保存到 `create/` 子目录，包含表结构定义
- DML 文件保存到 `insert/` 子目录，包含数据插入语句
- 便于分阶段导入：先创建表结构，再批量导入数据
- 支持重复导入数据（保留表结构，只重新导入数据）

### 4. 集成自动化修复流程

- 在转换完成后自动调用 `sql-fix-tools` 进行修复
- 新增 `--auto-fix` 参数，启用自动化修复流程
- 自动修复分别处理 `create/` 和 `insert/` 目录
- 支持通过 `--skip-auto-fix` 跳过自动修复（兼容旧流程）
- 修复完成后生成统一的转换报告，包含转换和修复的详细信息

## 影响

### 受影响规范
- **sql-import**: 需要新增需求来定义 COMMENT 转换、表名前缀和自动修复集成的行为

### 受影响代码
- `tools/oracle_to_mysql.py`: 
  - `OracleToMySQLConverter` 类需要新增 COMMENT 和表名前缀处理逻辑
  - `convert_file` 函数需要支持分离 DDL 和 DML 到不同文件
  - `convert_directory` 函数需要创建 `create/` 和 `insert/` 子目录
  - `main` 函数需要添加新的命令行参数（`--split-ddl-dml`）
- `tools/sql-fix-tools/`: 需要提供可编程调用的接口，支持分别处理多个目录
- `backend-django/core/management/commands/import_oracle_sql.py`: 需要支持分阶段导入（先导入 create/，再导入 insert/）

### 数据库影响
- 转换后的 MySQL 表将包含完整的注释信息（表注释和列注释）
- 如果使用 `--table-prefix` 参数，生成的表名将包含指定前缀
- 如果使用 `--split-ddl-dml` 参数，生成的文件将分离为：
  - `convertsql/create/BS_AREA.sql` - 表结构定义
  - `convertsql/insert/BS_AREA_data.sql` - 数据插入语句

### 向后兼容性
- **完全向后兼容**：所有现有参数和行为保持不变
- 新功能通过可选参数启用
- 默认行为与当前版本一致（不添加 COMMENT，不添加表名前缀，不分离 DDL/DML，不自动修复）
- 如果不使用 `--split-ddl-dml`，所有 SQL 语句仍保存在同一个文件中（原有行为）
