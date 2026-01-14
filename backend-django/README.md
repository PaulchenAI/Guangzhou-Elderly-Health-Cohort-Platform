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
DATABASE_NAME = "fu_admin_pro"
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
