## 运行教程
### 克隆项目
```bash
git clone https://github.com/jiangzhikj/zq-platform
# 进入项目目录
cd zq-platform/backend-django
```

### 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 在 `env/dev_env.py` 中配置数据库信息
```bash
# 默认是Postgres SQL
# 数据库类型 MYSQL/SQLSERVER/SQLITE3/POSTGRESQL
DATABASE_TYPE = "MYSQL"
# 数据库地址
DATABASE_HOST = "127.0.0.1"
# 数据库端口
DATABASE_PORT = 3306
# 数据库用户名
DATABASE_USER = "fuadmin"
# 数据库密码
DATABASE_PASSWORD = "fuadmin"
# 数据库名
DATABASE_NAME = os.environ.get('DEV_DB_NAME') or os.environ.get('DB_NAME') or "fu_admin_pro"
```

### 安装依赖环境
```bash
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
```

### 执行迁移命令
```bash
python manage.py makemigrations core scheduler
```
```bash
python manage.py migrate
```

### 迁移状态检查和修复

如果重置过数据库或遇到迁移记录与数据库表不一致的情况，可以使用以下命令进行检查和修复。

#### 检查迁移状态
```bash
# 检查所有应用的迁移状态
python manage.py check_migrations

# 检查指定应用（如 core）
python manage.py check_migrations --app core

# 显示详细信息（包括表和迁移记录详情）
python manage.py check_migrations --app core --detailed
```

#### 修复迁移不一致问题

当迁移记录与数据库表不一致时（例如：迁移记录显示已应用，但表不存在；或表已存在，但迁移记录缺失）：

**方法 1：使用自动修复命令（推荐）**
```bash
# 先查看将要执行的操作（模拟模式）
python manage.py fix_migrations --app core --dry-run

# 执行实际修复
python manage.py fix_migrations --app core
```

**方法 2：手动修复（最直接）**

如果遇到 `0005_table_query` 迁移记录存在但表不存在的情况：
```bash
python manage.py shell
```

在 Django shell 中执行：
```python
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

# 删除错误的迁移记录
MigrationRecorder.Migration.objects.filter(app='core', name='0005_table_query').delete()

# 如果 0006 的表已存在但记录缺失，创建迁移记录
if not MigrationRecorder.Migration.objects.filter(app='core', name='0006_add_survey_models').exists():
    MigrationRecorder.Migration.objects.create(
        app='core',
        name='0006_add_survey_models',
        applied=timezone.now()
    )

exit()
```

然后重新应用迁移：
```bash
# 应用 0005 迁移创建表
python manage.py migrate core 0005

# 如果 0006 的表已存在，伪造迁移记录
python manage.py migrate core 0006 --fake

# 验证修复结果
python manage.py check_migrations --app core --detailed
```

#### 常见问题

1. **表不存在但迁移记录显示已应用**
   - 解决：删除迁移记录后重新应用迁移

2. **表已存在但迁移记录缺失**
   - 解决：使用 `--fake` 参数伪造迁移记录：`python manage.py migrate <app> <migration> --fake`

3. **重置数据库后迁移状态不同步**
   - 解决：运行检查命令查看状态，然后根据提示修复

### 初始化数据
```bash
python manage.py loaddata db_init.json
```

### 初始化菜单（可选）

```bash
# 初始化表查询菜单
python manage.py init_table_query_menus

# 初始化问卷管理菜单
python manage.py init_survey_menus

# 强制重建菜单（删除现有后重建）
python manage.py init_table_query_menus --force
python manage.py init_survey_menus --force
```

**注意**：
- 如果表查询相关的表（`table_query_config`、`table_query_log`）不存在，菜单初始化命令会显示警告，但不会中断执行
- 表不存在时，请先运行迁移：`python manage.py migrate core`
- 如果遇到迁移问题，参考上面的"迁移状态检查和修复"章节

### 同步问卷 Schema（可选）
从外部问卷调查 API 同步问卷 Schema 定义到本地数据库。
```bash
# 测试 API 连接
python manage.py sync_survey_schemas --test-connection

# 同步所有类型
python manage.py sync_survey_schemas

# 同步指定类型
python manage.py sync_survey_schemas --type fried --type rockwood
```

### 导入问卷数据（可选）
从外部问卷调查 API 导入问卷数据。
```bash
# 增量导入所有类型
python manage.py import_survey_data

# 导入指定类型
python manage.py import_survey_data --type fried

# 导入指定日期范围
python manage.py import_survey_data --start-date 2024-01-01 --end-date 2024-12-31

# 全量导入（不跳过已存在的记录）
python manage.py import_survey_data --full
```

### 批量创建表查询配置（可选）
自动检测数据库表结构并创建查询配置。
```bash
# 列出所有可配置的表
python manage.py batch_create_table_configs --list

# 按前缀过滤并列出表
python manage.py batch_create_table_configs --list --prefix WORKFLOW

# 为指定前缀的所有表创建配置
python manage.py batch_create_table_configs --prefix WORKFLOW

# 更新现有配置（重新检测表结构）
python manage.py batch_create_table_configs --prefix BS --update
```

### 导入 Oracle 转换后的 SQL 文件（可选）
将 Oracle 转换为 MySQL 后的 SQL 文件导入到数据库。支持自动修复 MySQL 语法问题、断点续导、失败重试等功能。

#### 基本用法
```bash
# 导入单个文件
python manage.py import_oracle_sql ../docs/hospital/convertsql/BS_DEPARTMENT.sql

# 导入目录下所有文件
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all

# 快捷导入默认转换目录
python manage.py import_oracle_sql --default-convertsql
```

#### 自动修复 MySQL 语法问题
```bash
# 启用自动修复（推荐）- 自动处理 MySQL 保留字等问题
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --auto-fix

# 自动修复 + 生成修复报告
python manage.py import_oracle_sql --default-convertsql --auto-fix --fix-report
```

#### 断点续导与失败重试
```bash
# 指定批次 ID（用于跟踪导入状态）
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --batch-id my_batch_001

# 断点续导：跳过已成功的文件，继续导入（推荐用于中断后恢复）
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --batch-id my_batch_001 --resume

# 重试失败的文件
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --batch-id my_batch_001 --retry-failed --auto-fix

# 遇到错误继续执行下一个文件
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --continue-on-error
```

#### 查看导入状态
```bash
# 查看所有批次状态
python manage.py import_oracle_sql --show-status

# 查看指定批次的详细状态
python manage.py import_oracle_sql --show-status --batch-id my_batch_001
```

#### 其他选项
```bash
# 预览模式（不执行，只显示 SQL）
python manage.py import_oracle_sql ../docs/hospital/convertsql/BS_DEPARTMENT.sql --dry-run

# 跳过大文件（超过 100MB）
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --skip-large-files

# 指定文件大小上限（MB）
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --max-size 50

# 强制重新导入（忽略状态检查）
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --batch-id my_batch_001 --force
```

#### 完整导入示例（DDL + DML 分离）
```bash
# 使用分阶段导入脚本（推荐）
./tools/import_ddl_dml.sh --sql-dir docs/hospital/convertsql

# 或手动分阶段导入
# 1. 先导入表结构（DDL）
python manage.py import_oracle_sql ../docs/hospital/convertsql/create --all --batch-id ddl_batch --auto-fix --continue-on-error

# 2. 再导入数据（DML）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert --all --batch-id dml_batch --auto-fix --continue-on-error
```

#### 流式处理超大文件（推荐用于 100MB+ 文件）

对于超大文件（如几 GB 的 SQL 文件），推荐使用流式处理模式，避免内存溢出（OOM）并提升性能：

```bash
# 自动流式处理（文件超过 100MB 自动启用）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert/PM_DAILYWORK_DETAIL_data.sql --auto-fix --continue-on-error

# 手动启用流式模式（任何大小的文件）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert/PM_DAILYWORK_DETAIL_data.sql --streaming --batch-size 50000 --auto-fix --continue-on-error

# 超大文件推荐配置（批量大小 50000+）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert/PM_DAILYWORK_DETAIL_data.sql \
  --streaming --batch-size 50000 --auto-fix --continue-on-error --batch-id import_large_file
```

**流式模式特点**：
- ✅ **内存占用极低**：逐语句处理，不会一次性加载整个文件
- ✅ **性能优化**：自动禁用唯一性检查和外键检查以加速导入（不影响数据完整性）
- ✅ **断点续导**：支持 `--resume` 参数，可中断后继续
- ✅ **进度显示**：实时显示处理速度、成功/重复/失败数量

**性能建议**：
- 小文件（<100MB）：使用默认模式即可
- 中等文件（100MB-500MB）：自动流式模式，批量大小 10000（默认）
- 超大文件（>500MB）：手动指定 `--streaming --batch-size 50000` 或更大

#### 关于数据重复保护

**重要说明**：流式处理模式会临时禁用 MySQL 的唯一性检查（`UNIQUE_CHECKS = 0`）以提升性能，但这**不会导致数据重复**：

1. ✅ **主键和唯一索引约束仍然有效**：`UNIQUE_CHECKS = 0` 只是性能优化，数据库层面的主键和唯一索引约束仍然会阻止重复数据插入
2. ✅ **重复数据自动跳过**：如果尝试插入重复数据，系统会显示"重复数据已跳过"，不会计入错误
3. ✅ **避免重复导入**：推荐使用 `--resume` 参数，系统会跳过已经成功导入的文件

**示例**：
```bash
# 第一次导入（487万条数据，约需 3-5 小时）
python manage.py import_oracle_sql ... --streaming --batch-size 50000 --batch-id import_001

# 如果中断后继续（使用 --resume，会跳过已成功的文件，不会重复导入）
python manage.py import_oracle_sql ... --streaming --batch-size 50000 --batch-id import_001 --resume
```

**注意**：如果表没有主键或唯一索引，重复运行导入命令可能会插入重复数据。建议：
- 在导入前先清空表：`TRUNCATE TABLE table_name`
- 或为表添加主键/唯一索引以保护数据完整性

#### 参数说明
| 参数 | 说明 |
|------|------|
| `--all` | 处理目录下所有 SQL 文件 |
| `--auto-fix` | 自动修复 MySQL 语法问题（保留字、特殊字符等）|
| `--batch-id` | 指定批次 ID，用于状态跟踪和断点续导 |
| `--resume` | 断点续导，跳过已成功的文件 |
| `--retry-failed` | 只重试失败的文件 |
| `--continue-on-error` | 遇到错误继续执行下一个文件 |
| `--force` | 强制重新导入，忽略状态检查 |
| `--dry-run` | 预览模式，不实际执行 |
| `--show-status` | 显示导入状态 |
| `--skip-large-files` | 跳过超过 100MB 的大文件 |
| `--max-size` | 指定文件大小上限（MB）|
| `--streaming` | 启用流式处理模式（用于超大文件，内存占用低）|
| `--batch-size N` | 流式处理时每批提交的语句数（默认 10000，大文件建议 50000+）|

### 启动项目
```bash
python manage.py runserver 0.0.0.0:8000
```

### 启动任务调度器（可选）
```bash
# 生产环境
python start_scheduler.py
```

### 备份数据（可选）
```bash
python manage.py dumpdata core scheduler --indent 4 > db_init.json
```

---

## 数据初始化与导入（汇总）

本节提供从“空库”到“可用数据”的推荐执行顺序，便于一键照做。更详细的参数说明请参考本文前面的对应章节，以及 `core/management/commands/` 下的命令源码。

### 0. 前置准备

1. 配置数据库连接：`env/dev_env.py`
2. 安装依赖并激活虚拟环境
3. 进入目录：`zq-platform/backend-django`

### 1. 必做：迁移 + 初始数据

```bash
# 1) 生成迁移（如已有迁移文件可跳过）
python manage.py makemigrations core scheduler

# 2) 执行迁移
python manage.py migrate

# 3) 初始化基础数据
python manage.py loaddata db_init.json
```

如遇到“迁移记录与表不一致”，先执行：

```bash
python manage.py check_migrations --app core --detailed
python manage.py fix_migrations --app core --dry-run
python manage.py fix_migrations --app core
```

### 2. 可选：菜单初始化

```bash
python manage.py init_table_query_menus
python manage.py init_survey_menus
```

强制重建（会删除现有后重建）：

```bash
python manage.py init_table_query_menus --force
python manage.py init_survey_menus --force
```

### 3. 可选：导入 Oracle 转换后的 SQL（导入业务全量表与数据）

命令：`python manage.py import_oracle_sql ...`（支持自动修复、断点续导、失败重试、流式导入等）。

推荐按 DDL + DML 分阶段导入：

```bash
# 1) 先导入表结构（DDL）
python manage.py import_oracle_sql ../docs/hospital/convertsql/create --all --batch-id ddl_batch --auto-fix --continue-on-error

# 2) 再导入数据（DML）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert --all --batch-id dml_batch --auto-fix --continue-on-error
```

中断后继续（跳过已成功文件）：

```bash
python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --batch-id my_batch_001 --resume
```

### 4. 可选：外键关系元数据导入（用于表查询/元数据能力）

```bash
# 外键 JSON 元数据导入（默认探测 docs/hospital/foreignkey/）
python manage.py import_foreignkey_metadata --truncate

# 业务逻辑补充的手动外键关系
python manage.py import_manual_foreignkeys --truncate-manual
```

`import_manual_foreignkeys` 说明：

- 用途：补齐业务逻辑上存在、但数据库未声明的外键关系（写入外键元数据表），提升“联合查询”等功能的关联覆盖率
- 常用参数：
  - `--dry-run`：预览模式，不写入
  - `--prefix gzlry_`：表名前缀（默认 `gzlry_`）
  - `--truncate-manual`：仅清空“手动导入”的记录后再导入（推荐在重复执行前使用）

示例（无参数导入）：

```text
$ python manage.py import_manual_foreignkeys
手动外键关系导入
============================================================
表名前缀: gzlry_

收集固定外键关系...
固定外键关系: 6 条（跳过 0 条）

发现动态表...
发现 FORMTABLE_MAIN_* 表: 229 个
发现 DC_FORM_* 表: 75 个

总外键关系数: 310

开始导入...
  已处理 50/310
  已处理 100/310
  已处理 150/310
  已处理 200/310
  已处理 250/310
  已处理 300/310
导入完成！

============================================================
导入报告
============================================================
固定外键关系: 6
FORMTABLE_MAIN_* 表: 229
DC_FORM_* 表: 75
总外键关系数: 310
成功导入: 310
```

### 5. 可选：批量创建表查询配置

```bash
# 先列出可配置表
python manage.py batch_create_table_configs --list

# 按表名前缀创建或更新配置（示例）
python manage.py batch_create_table_configs --prefix WORKFLOW
python manage.py batch_create_table_configs --prefix BS --update
```

如需使用 `docs/hospital/commentsql` 的注释映射（供表与字段中文名展示），直接在创建/更新配置时指定 `--meaning-dir`（默认即为 `docs/hospital/commentsql`）：

```bash
# 使用 docs/hospital/commentsql 的 *_meaning.json 作为中文映射来源
python manage.py batch_create_table_configs --prefix FORMTABLE --meaning-dir ../docs/hospital/commentsql
python manage.py batch_create_table_configs --prefix BS --update --meaning-dir ../docs/hospital/commentsql
```

中文名称来源与优先级说明：

- 表中文名：数据库表 COMMENT > meaning.json > 配置文件 > 表名
- 字段中文名（写入 `config_json.fields[].displayName`）：数据库字段 COMMENT > meaning.json > 配置文件 > 字段名
- meaning.json 取值规则：优先使用 `original_comment`，当 `original_comment` 为空时回退使用 `inferred_meaning`

`--prefix` 与 `--table-prefix` 的区别：

- `--prefix`：用于筛选“要处理哪些数据库表”（不传则必须使用 `--all` 或仅 `--list` 查看）
- `--table-prefix`：用于匹配 meaning.json 时忽略数据库表名前缀（例如数据库表为 `gzlry_bs_department`，meaning.json 表名为 `BS_DEPARTMENT`，则传 `--table-prefix gzlry_`）

常见场景：数据库表带前缀 `gzlry_`，且希望显示/同步 commentsql 的中文名：

```bash
# 先检查能否从 meaning.json 匹配到中文名（列表括号里会显示中文）
python manage.py batch_create_table_configs --list --prefix gzlry_BS --table-prefix gzlry_ --meaning-dir ../docs/hospital/commentsql

# 同步更新已入库的表查询配置（前端展示依赖数据库里的 TableQueryConfig.display_name / config_json）
python manage.py batch_create_table_configs --prefix gzlry_BS --update --table-prefix gzlry_ --meaning-dir ../docs/hospital/commentsql
```

### 6. 可选：问卷数据同步（依赖外部问卷 API）

1) 先同步 Schema：

```bash
python manage.py sync_survey_schemas --test-connection
python manage.py sync_survey_schemas
```

2) 再导入问卷数据：

```bash
# 默认增量
python manage.py import_survey_data

# 全量导入
python manage.py import_survey_data --full
```

3) 如需要把问卷数据同步到“表查询系统”对应的 `survey_{type}` 表：

```bash
python manage.py sync_survey_to_table_query
```

### 7. 可选：定时任务初始化与启动

初始化内置任务配置到数据库：

```bash
python manage.py init_scheduler_jobs
```

启动调度器：

```bash
python start_scheduler.py
```

### 8. 校验清单（建议每步执行后抽查）

- 迁移一致性：`python manage.py check_migrations --app core --detailed`
- Oracle SQL 导入：关注导入输出的“成功/失败/跳过”，并使用 `--show-status` 查看批次状态
- 外键元数据：检查 `table_foreignkey_metadata` 是否有数据
- 表查询配置：检查 `table_query_config` 是否生成了对应表配置
- 问卷导入：检查 `survey_record`、`survey_import_log` 的条数与最近批次状态
