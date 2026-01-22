# 变更：新增 Oracle 数据库导出 SQL 工具类（全量/增量）

## 为什么

当前项目的 SQL 迁移与导入链路主要面向“已导出的 Oracle SQL 文件”（例如 PL/SQL Developer 导出的脚本），并提供转换、修复与导入能力（见 `tools/oracle_to_mysql.py`、`specs/sql-import/spec.md`）。

但在实际迁移/同步场景中，往往需要**直接连接 Oracle 数据库**，将指定 schema 下的表结构（DDL）与数据（DML）导出为 SQL 文件，以便后续：
- 在离线环境进行转换/修复/导入
- 将导出结果纳入版本控制与审计
- 支持周期性增量导出（减少全量导出的时间与体积）

因此需要在 `tools/` 下新增一个“连接 Oracle 导出 SQL”的工具类，并定义其全量/增量导出行为与可验收的输出格式。

## 变更内容

- 新增一个 Oracle 数据库导出工具类（位于 `tools/`），能够：
  - 连接 Oracle 数据库
    - 使用 Oracle 官方 Python 驱动 `python-oracledb`（默认 thin 模式）
  - 按表导出 DDL（表结构）与 DML（数据 INSERT）
  - 支持**全量导出**与**增量导出**
  - 输出为可复用的 SQL 文件（可继续交给现有 `tools/oracle_to_mysql.py` 转换/修复/导入）
- 新增 OpenSpec 能力规范：`oracle-db-export`

## 影响

- 受影响规范：
  - 新增 `oracle-db-export`
- 受影响代码（规划）：
  - `tools/oracle_db_exporter.py`（新增：工具类与 CLI 入口）
  - （可选，后续集成）`AIagent/src/...`：供 `SQLMigrationAgent` 将“导出”作为迁移阶段的第一步

