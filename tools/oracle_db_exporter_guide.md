# Oracle 数据库导出工具使用指南

## 概述

`oracle_db_exporter.py` 是一个连接 Oracle 数据库并导出表结构（DDL）与数据（DML）为 SQL 文件的工具。支持全量导出与增量导出。

---

## 前置条件

### 1. 安装依赖

```bash
pip install -r tools/requirements.txt
```

或单独安装：

```bash
pip install oracledb python-dotenv
```

### 2. 配置数据库连接

在项目根目录创建或编辑 `.env` 文件：

```bash
# Oracle 数据库连接配置
ORACLE_HOST=your-oracle-host
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=your-service-name
ORACLE_USER=your-username
ORACLE_PASSWORD=your-password
```

也可以使用完整 DSN：

```bash
ORACLE_DSN=your-oracle-host:1521/your-service-name
ORACLE_USER=your-username
ORACLE_PASSWORD=your-password
```

---

## 基本用法

### 全量导出

```bash
# 导出指定 schema 下的所有表
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export
```

### 预览模式（不实际导出）

```bash
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --dry-run
```

### 仅导出 DDL（表结构）

```bash
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --ddl-only
```

### 仅导出 DML（数据）

```bash
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --dml-only
```

### 指定表过滤

```bash
# 仅导出指定表
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export \
    --include EMPLOYEES DEPARTMENTS

# 排除某些表
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export \
    --exclude TEMP_TABLE LOG_TABLE
```

---

## 增量导出

增量导出基于用户指定的"增量列"（如 `UPDATE_TIME`、`ID` 等），仅导出新增/变更的数据。

### 1. 创建增量配置文件

创建 JSON 配置文件（例如 `incremental_config.json`）：

```json
{
    "default_incremental_column": "UPDATE_TIME",
    "tables": {
        "EMPLOYEES": {
            "incremental_column": "LAST_MODIFIED"
        },
        "DEPARTMENTS": {
            "incremental_column": "UPDATE_TIME"
        },
        "ORDERS": {
            "incremental_column": "ORDER_ID"
        }
    }
}
```

配置说明：
- `default_incremental_column`：默认增量列，适用于未单独配置的表
- `tables`：按表单独指定增量列（优先于默认值）

### 2. 执行增量导出

```bash
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export \
    --incremental-config incremental_config.json
```

### 3. 增量机制说明

1. **首次导出**：导出全部数据，并在 `checkpoint.json` 中记录每张表的水位线
2. **再次导出**：读取 checkpoint，仅导出 `incremental_column > last_value` 的记录
3. **导出完成**：自动更新 checkpoint 中的水位线

---

## 输出目录结构

```
docs/oracle_export/
├── create/                 # DDL 文件目录
│   ├── EMPLOYEES.sql       # 每张表一个 DDL 文件
│   ├── DEPARTMENTS.sql
│   └── ...
├── insert/                 # DML 文件目录
│   ├── EMPLOYEES_data.sql  # 每张表一个数据文件
│   ├── DEPARTMENTS_data.sql
│   └── ...
├── manifest.json           # 导出清单（时间、表列表、行数统计）
└── checkpoint.json         # 增量水位线（仅增量模式）
```

### manifest.json 示例

```json
{
    "exported_at": "2026-01-22T10:30:00",
    "schema": "HR",
    "output_dir": "docs/oracle_export",
    "tables": [
        {"name": "EMPLOYEES", "ddl": "create/EMPLOYEES.sql", "dml": "insert/EMPLOYEES_data.sql", "rows": 107},
        {"name": "DEPARTMENTS", "ddl": "create/DEPARTMENTS.sql", "dml": "insert/DEPARTMENTS_data.sql", "rows": 27}
    ],
    "total_rows": 134,
    "errors": []
}
```

### checkpoint.json 示例

```json
{
    "created_at": "2026-01-22T10:30:00",
    "updated_at": "2026-01-22T10:35:00",
    "tables": {
        "EMPLOYEES": {
            "last_value": "2026-01-22T10:00:00",
            "incremental_column": "LAST_MODIFIED",
            "row_count": 107
        }
    }
}
```

---

## 命令行参数

```
usage: oracle_db_exporter.py export [-h] --schema SCHEMA --output OUTPUT
                                     [--host HOST] [--port PORT]
                                     [--service-name SERVICE_NAME]
                                     [--user USER] [--password PASSWORD]
                                     [--dsn DSN]
                                     [--include INCLUDE [INCLUDE ...]]
                                     [--exclude EXCLUDE [EXCLUDE ...]]
                                     [--ddl-only] [--dml-only] [--no-comments]
                                     [--skip-existing]
                                     [--incremental-config INCREMENTAL_CONFIG]
                                     [--dry-run] [--verbose]

必需参数:
  --schema, -s          Schema 名称
  --output, -o          输出目录

连接参数（优先于 .env）:
  --host                Oracle 主机
  --port                Oracle 端口
  --service-name        Oracle 服务名
  --user, -u            用户名
  --password, -p        密码
  --dsn                 完整 DSN

表过滤:
  --include             要包含的表
  --exclude             要排除的表

导出选项:
  --ddl-only            仅导出 DDL
  --dml-only            仅导出 DML
  --no-comments         DDL 不包含注释
  --skip-existing       跳过已存在的文件

增量配置:
  --incremental-config  增量配置 JSON 文件路径

其他:
  --dry-run             预览模式
  --verbose, -v         详细输出
```

---

## 与现有工具链集成

导出的 SQL 文件可以直接交给现有的转换/导入工具处理：

```bash
# 1. 从 Oracle 导出
python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export

# 2. 转换为 MySQL 格式
python tools/oracle_to_mysql.py convert-all docs/oracle_export/create \
    -o docs/mysql_sql/create --table-prefix gzlry_ --enable-comments

python tools/oracle_to_mysql.py convert-all docs/oracle_export/insert \
    -o docs/mysql_sql/insert --table-prefix gzlry_

# 3. 导入 MySQL
cd backend-django
python manage.py import_oracle_sql --sql-dir ../docs/mysql_sql/create
python manage.py import_oracle_sql --sql-dir ../docs/mysql_sql/insert
```

---

## 常见问题

### Q: 连接失败提示 "DPY-6001: cannot connect to database"

确保：
1. Oracle 数据库可达（网络/防火墙）
2. 服务名正确（不是 SID）
3. 用户名密码正确
4. 使用的是 thin 模式（默认），如需 thick 模式需安装 Oracle Instant Client

### Q: 某些表没有合适的增量列怎么办？

如果表没有在增量配置中指定且没有默认增量列，该表会使用全量导出。

### Q: 如何重新全量导出？

删除输出目录下的 `checkpoint.json` 文件，或不使用 `--incremental-config` 参数。

---

## 技术说明

- **连接库**：使用 Oracle 官方 `python-oracledb`（thin 模式，无需 Instant Client）
- **DDL 获取**：通过查询 `ALL_TAB_COLUMNS`、`ALL_TAB_COMMENTS`、`ALL_COL_COMMENTS` 组装
- **批量读取**：DML 导出使用 fetchmany（默认 1000 行/批）避免内存溢出
- **输出格式**：Oracle SQL 方言（可通过 `oracle_to_mysql.py` 转换为 MySQL）
