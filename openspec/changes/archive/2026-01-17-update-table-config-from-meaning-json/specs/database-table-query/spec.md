# 数据库表查询管理 - 规范增量

## 修改需求

### 需求：表查询配置管理

系统必须提供 JSON 配置方式定义表的查询规则，包括可见字段、可搜索字段、排序字段等。

#### 场景：创建表查询配置

- **当** 管理员创建新的表查询配置
- **那么** 系统保存配置到 `table_query_config` 表
- **并且** 配置包含表名、显示名称、字段定义、分页设置等

#### 场景：批量创建配置

- **当** 使用 `batch_create_table_configs` 命令
- **那么** 系统自动检测表结构并批量生成配置
- **并且** 支持按表名前缀过滤
- **并且** 表的中文显示名称（`display_name`）按以下优先级获取：
  1. 数据库表的 COMMENT（如果存在）
  2. meaning.json 文件中的 `inferred_meaning`（如果指定了 `--meaning-dir` 且文件存在）
  3. JSON 配置文件中 `tables` 部分的映射（如果配置文件存在且包含该表）
  4. 表名本身

#### 场景：从数据库 COMMENT 获取表名

- **当** 执行 `batch_create_table_configs` 命令
- **那么** 系统查询 `INFORMATION_SCHEMA.TABLES` 获取表的 `TABLE_COMMENT`
- **并且** 如果 COMMENT 存在且非空，使用 COMMENT 作为表的 `display_name`

#### 场景：从 meaning.json 获取表名

- **当** 执行 `batch_create_table_configs` 命令并指定 `--meaning-dir` 参数
- **那么** 系统扫描目录下所有 `*_meaning.json` 文件
- **并且** 解析 JSON 文件中的 `table.inferred_meaning` 作为表的中文名称
- **并且** 如果数据库 COMMENT 不存在，使用 meaning.json 中的含义作为 `display_name`

#### 场景：从配置文件获取表名

- **当** 执行 `batch_create_table_configs` 命令并指定 `--config-file` 参数
- **那么** 系统读取 JSON 配置文件
- **并且** 如果配置文件的 `tables` 部分包含该表的映射，使用映射值作为 `display_name`
- **并且** 如果配置文件不存在或格式错误，降级使用默认逻辑（COMMENT 或表名）

#### 场景：字段中文名称配置

- **当** 批量创建表配置时
- **那么** 字段配置中的 `displayName` 按以下优先级获取：
  1. 数据库字段的 `COLUMN_COMMENT`（如果存在）
  2. meaning.json 文件中对应字段的 `inferred_meaning`（如果指定了 `--meaning-dir` 且文件存在）
  3. JSON 配置文件中 `fields[table_name][field_name]` 的映射（如果配置文件存在且包含该映射）
  4. 字段名本身
- **并且** 如果字段 COMMENT 或配置文件中存在中文名称，使用该名称作为 `displayName`

#### 场景：配置文件格式

- **当** 使用 `--config-file` 参数指定配置文件
- **那么** 配置文件必须是有效的 JSON 格式
- **并且** 配置文件结构包含 `tables` 和 `fields` 两个部分：
  - `tables`: 对象，键为表名，值为中文名称
  - `fields`: 对象，键为表名，值为对象，内层对象键为字段名，值为中文名称
- **并且** 如果配置文件格式错误，命令显示警告并继续使用默认逻辑

## 新增需求

### 需求：从 meaning.json 文件加载语义信息

系统必须支持从 `*_meaning.json` 文件批量加载表和字段的中文含义信息。

#### 场景：指定 meaning.json 目录

- **当** 执行 `batch_create_table_configs` 命令时
- **那么** 支持 `--meaning-dir` 参数指定 meaning.json 文件所在目录
- **并且** 如果未指定，默认查找 `docs/hospital/commentsql` 目录
- **并且** 如果目录不存在，忽略 meaning.json 功能，使用其他优先级逻辑

#### 场景：配置数据库表名前缀

- **当** 执行 `batch_create_table_configs` 命令并指定 `--table-prefix` 参数
- **那么** 系统在匹配 meaning.json 时，会先去掉数据库表名的指定前缀
- **并且** 例如数据库表名为 `dbo_XY_TABLE`，指定 `--table-prefix dbo_` 后，会用 `XY_TABLE` 去匹配 meaning.json
- **并且** 如果未指定前缀，直接使用完整表名进行匹配

#### 场景：解析 meaning.json 文件

- **当** 指定的目录存在且包含 `*_meaning.json` 文件
- **那么** 系统扫描并解析所有匹配的 JSON 文件
- **并且** 忽略 `all_meanings.json` 文件（该文件是合并文件，格式不同）
- **并且** 从 `table.table_name` 获取表名
- **并且** 从 `table.inferred_meaning` 获取表的中文含义
- **并且** 从 `table.fields[].field_name` 和 `table.fields[].inferred_meaning` 获取字段的中文含义
- **并且** 构建内存中的映射结构供后续查询使用

#### 场景：meaning.json 文件格式

- **当** 解析 meaning.json 文件时
- **那么** 文件必须包含以下结构：
  ```json
  {
    "table": {
      "table_name": "表名",
      "inferred_meaning": "表的中文含义",
      "fields": [
        {
          "field_name": "字段名",
          "inferred_meaning": "字段的中文含义"
        }
      ]
    }
  }
  ```
- **并且** 如果文件格式不正确，跳过该文件并输出警告

#### 场景：meaning.json 读取失败处理

- **当** meaning.json 文件读取或解析失败
- **那么** 系统输出警告信息
- **并且** 跳过该文件继续处理其他文件
- **并且** 不影响命令的整体执行
