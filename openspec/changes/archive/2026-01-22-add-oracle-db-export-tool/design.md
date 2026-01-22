## 上下文

本变更只定义“从 Oracle 数据库导出 SQL”的工具能力，不替代现有的 `oracle_to_mysql.py` 转换与导入链路。

导出结果目标是“可读、可复用、可审计”的 SQL 文件集合，默认输出 Oracle 兼容的 `CREATE TABLE` / `INSERT INTO` / `COMMENT ON ...`（如需要 MySQL 兼容，可在后续阶段通过现有转换工具处理）。

## 目标 / 非目标

### 目标

- 提供一个可脚本化运行的导出工具类，支持：
  - 连接 Oracle（用户/密码或 DSN）
  - 选择 schema 与表集合
  - 导出 DDL 与 DML
  - 全量导出与增量导出
  - 可重复运行（幂等输出策略：可选择覆盖/跳过）
- 增量导出具备明确、可验证的“水位线”与 checkpoint 存储规则。

### 非目标

- 不在本变更中实现“导出直接生成 MySQL 兼容 DDL/DML”（可作为后续扩展）。
- 不在本变更中实现 CDC（LogMiner / GoldenGate 等）级别的实时增量。
- 不保证跨表事务一致性快照（除非用户明确启用一致性选项；默认以最小实现为主）。

## 决策

### 决策：Oracle 连接库选择

- 默认使用 Oracle 官方 Python 驱动 `python-oracledb`。
- 默认优先使用 **thin 模式**（纯 Python，无需安装 Oracle Instant Client），以降低环境依赖。
- 当用户环境已具备 Oracle Instant Client 或需要特定能力时，可启用 **thick 模式**（后续实现中以参数/环境变量控制）。

**原因**：`python-oracledb` 为官方维护库，兼容性和维护性最好；thin 模式对 CI/开发机最友好。

### 决策：配置加载约定

- 数据库连接配置默认从项目根目录 `.env` 读取（例如 `ORACLE_HOST/ORACLE_PORT/ORACLE_SERVICE_NAME/ORACLE_USER/ORACLE_PASSWORD`），并允许命令行参数覆盖。
- 增量列通过一个 JSON 配置文件表达（按表指定 `incremental_column`，可选 `default_incremental_column`）。
- 当未提供增量列（既未显式指定也未提供 JSON 配置文件）时，默认走全量导出。

### 决策：增量导出的最小可行定义

- 增量导出以“用户显式指定的增量列（单列）”作为水位线依据：
  - 例如 `UPDATE_TIME`、`LAST_MODIFIED_AT`、`ID`（单调递增）
- 工具在每次导出结束后，将各表的最大增量列值写入 checkpoint 文件（JSON）。
- 下次增量导出从 checkpoint 读取水位线，仅导出满足 `incremental_column > last_value` 的记录。

**原因**：该方案最简单、可解释且可验收，不依赖 Oracle 特定的 SCN/ORA_ROWSCN 语义差异。

### 决策：DDL 获取策略

DDL 优先使用 Oracle 提供的元数据接口（例如 `DBMS_METADATA`）导出，以尽量保真；若在目标环境不可用，再回退到 `ALL_TAB_COLUMNS/ALL_CONSTRAINTS` 组装（后续扩展）。

### 决策：输出目录结构

默认输出目录包含：
- `create/`：按表输出 DDL
- `insert/`：按表输出 DML
- `manifest.json`：导出清单（表列表、行数、时间、checkpoint 摘要）

## 风险 / 权衡

- **增量列不可用**：部分表可能没有合适的增量列。工具需明确报错或允许跳过，并在报告中呈现。
- **数据类型与转义**：CLOB/BLOB/日期等类型需要明确的序列化策略；本变更先规范行为，具体实现按规范完成。
- **一致性**：全库一致性需要额外成本；默认以最小实现为主，可通过“单表读取一致性”或“导出前设置会话一致性”作为后续扩展。

## 迁移计划

- 本变更为新增能力，不影响现有导入/转换工具；后续可在 `SQLMigrationAgent` 中将“导出 Oracle DB→得到 Oracle SQL 文件”作为可选阶段 0。

## 待决问题

- 是否需要支持基于 SCN/ORA_ROWSCN 的增量模式（作为可选策略）？
- 是否需要支持导出视图/同义词/序列等对象（默认仅表）？

