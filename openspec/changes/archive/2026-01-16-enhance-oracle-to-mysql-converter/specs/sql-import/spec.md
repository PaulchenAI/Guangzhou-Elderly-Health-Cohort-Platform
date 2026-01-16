## 新增需求

### 需求：Oracle COMMENT 转换为 MySQL 注释

系统必须将 Oracle 的 `COMMENT ON TABLE` 和 `COMMENT ON COLUMN` 语句转换为 MySQL 兼容的注释格式。

#### 场景：收集表注释

- **当** 解析 Oracle SQL 文件时
- **那么** 识别 `COMMENT ON TABLE table_name IS 'comment_text';` 语句
- **并且** 将表名和注释文本存储到内存字典中

#### 场景：收集列注释

- **当** 解析 Oracle SQL 文件时
- **那么** 识别 `COMMENT ON COLUMN table_name.column_name IS 'comment_text';` 语句
- **并且** 将表名.列名和注释文本存储到内存字典中

#### 场景：注入列注释到 CREATE TABLE

- **当** 转换 CREATE TABLE 语句时
- **那么** 在对应列的数据类型定义后添加 `COMMENT 'comment_text'`
- **例如**：`mainid VARCHAR(50) NOT NULL` → `mainid VARCHAR(50) NOT NULL COMMENT '主键ID'`

#### 场景：注入表注释到 CREATE TABLE

- **当** 转换 CREATE TABLE 语句时
- **那么** 在 ENGINE 子句前添加表注释：`COMMENT='comment_text'`
- **例如**：`ENGINE=InnoDB` → `COMMENT='院区表' ENGINE=InnoDB`

#### 场景：处理注释中的特殊字符

- **当** COMMENT 文本包含单引号 `'` 时
- **那么** 转义为两个单引号 `''`（MySQL 标准）
- **并且** 确保生成的 SQL 语法正确

#### 场景：默认行为保持不变

- **当** 用户未启用 COMMENT 转换功能时
- **那么** 转换行为与当前版本一致，忽略所有 COMMENT 语句
- **并且** 保持向后兼容性

---

### 需求：SQL 语句中的表名前缀

系统必须支持在转换后的 SQL 语句中为表名添加自定义前缀，以支持多租户或避免表名冲突场景。

#### 场景：为 CREATE TABLE 添加表名前缀

- **当** 用户指定 `--table-prefix gzlry_` 参数
- **并且** 转换 `CREATE TABLE BS_AREA` 语句时
- **那么** 生成 `CREATE TABLE gzlry_BS_AREA`

#### 场景：为 DROP TABLE 添加表名前缀

- **当** 用户指定 `--table-prefix gzlry_` 参数
- **并且** 转换生成 `DROP TABLE IF EXISTS BS_AREA` 语句时
- **那么** 生成 `DROP TABLE IF EXISTS gzlry_BS_AREA`

#### 场景：为 INSERT INTO 添加表名前缀

- **当** 用户指定 `--table-prefix gzlry_` 参数
- **并且** 转换 `INSERT INTO BS_AREA` 语句时
- **那么** 生成 `INSERT INTO gzlry_BS_AREA`

#### 场景：文件名前缀与表名前缀独立

- **当** 用户同时指定 `--prefix mysql_` 和 `--table-prefix gzlry_` 参数
- **那么** 输出文件名为 `mysql_BS_AREA.sql`
- **并且** SQL 语句中的表名为 `gzlry_BS_AREA`

#### 场景：只使用文件名前缀

- **当** 用户只指定 `--prefix mysql_` 参数（不指定 `--table-prefix`）
- **那么** 输出文件名为 `mysql_BS_AREA.sql`
- **并且** SQL 语句中的表名保持原样 `BS_AREA`

#### 场景：只使用表名前缀

- **当** 用户只指定 `--table-prefix gzlry_` 参数（不指定 `--prefix`）
- **那么** 输出文件名保持原样 `BS_AREA.sql`
- **并且** SQL 语句中的表名为 `gzlry_BS_AREA`

#### 场景：表名前缀的合法性

- **当** 用户指定的表名前缀包含非法字符（如空格、特殊符号）时
- **那么** 工具应记录警告信息
- **并且** 允许用户自行保证前缀的合法性（不强制校验）

---

### 需求：DDL 和 DML 文件分离

系统必须支持将表结构定义（DDL）和数据插入语句（DML）分离到不同的文件和目录，以支持分阶段导入和更灵活的数据管理。

#### 场景：启用 DDL/DML 分离

- **当** 用户指定 `--split-ddl-dml` 参数
- **那么** CREATE TABLE 和 DROP TABLE 语句保存到 `create/` 子目录
- **并且** INSERT INTO 语句保存到 `insert/` 子目录

#### 场景：DDL 文件命名

- **当** 转换表 `BS_AREA` 并启用分离模式
- **那么** DDL 文件保存为 `convertsql/create/BS_AREA.sql`
- **并且** 文件包含 DROP TABLE 和 CREATE TABLE 语句

#### 场景：DML 文件命名

- **当** 转换表 `BS_AREA` 并启用分离模式
- **那么** DML 文件保存为 `convertsql/insert/BS_AREA_data.sql`
- **并且** 文件包含所有 INSERT INTO 语句
- **注意**：文件名添加 `_data` 后缀以区别于 DDL 文件

#### 场景：自动创建子目录

- **当** 使用 `convert-all` 批量转换并启用 `--split-ddl-dml`
- **那么** 自动创建 `convertsql/create/` 和 `convertsql/insert/` 目录
- **并且** 所有 DDL 文件保存到 create/ 目录
- **并且** 所有 DML 文件保存到 insert/ 目录

#### 场景：空表处理

- **当** 表没有任何 INSERT 语句（空表）
- **那么** 只创建 DDL 文件（`create/表名.sql`）
- **并且** 不创建空的 DML 文件
- **并且** 在转换日志中标记"无数据"

#### 场景：大表数据分离

- **当** 转换包含大量 INSERT 语句的表（如 BS_OLDER.sql，8000+ INSERT）
- **那么** 将 INSERT 语句独立保存到 `insert/BS_OLDER_data.sql`
- **并且** 保持流式处理，不增加内存占用
- **并且** CREATE TABLE 保存到相对较小的 `create/BS_OLDER.sql`

#### 场景：与其他功能组合

- **当** 同时使用 `--split-ddl-dml`、`--table-prefix gzlry_` 和 `--enable-comments`
- **那么** DDL 文件包含带前缀的表名和完整注释
- **并且** DML 文件的 INSERT INTO 语句使用带前缀的表名
- **例如**：
  ```sql
  -- create/BS_AREA.sql
  CREATE TABLE gzlry_BS_AREA (...) COMMENT='院区表';
  
  -- insert/BS_AREA_data.sql
  INSERT INTO gzlry_BS_AREA (...) VALUES (...);
  ```

#### 场景：向后兼容 - 不启用分离

- **当** 用户未指定 `--split-ddl-dml` 参数
- **那么** 所有语句（DDL 和 DML）保存在同一个文件中
- **并且** 文件直接保存在输出目录根目录（不创建 create/ 和 insert/ 子目录）
- **并且** 保持与当前版本完全一致的行为

---

### 需求：自动化 SQL 修复集成

系统必须支持在 Oracle 到 MySQL 转换完成后，自动调用 `sql-fix-tools` 工具集进行二次修复，实现一键转换流程。

#### 场景：启用自动修复

- **当** 用户指定 `--auto-fix` 参数
- **并且** 转换完成后
- **那么** 自动调用 `tools/sql-fix-tools/fix_sql_main.py` 脚本
- **并且** 对转换后的目录进行原地修复

#### 场景：自动修复成功

- **当** 自动修复工具执行成功（返回码 0）
- **那么** 在转换报告中显示修复成功信息
- **并且** 打印修复工具的输出日志

#### 场景：自动修复失败

- **当** 自动修复工具执行失败（返回码非 0）
- **那么** 在转换报告中显示修复失败警告
- **并且** 打印修复工具的错误信息
- **但是** 不影响转换结果的保存（转换文件仍然可用）

#### 场景：跳过自动修复

- **当** 用户未指定 `--auto-fix` 参数
- **那么** 转换完成后不自动调用修复工具
- **并且** 保持原有的两步操作流程（向后兼容）

#### 场景：修复工具路径定位

- **当** 调用自动修复工具时
- **那么** 工具必须正确定位 `tools/sql-fix-tools/fix_sql_main.py` 的路径
- **并且** 如果修复工具不存在，记录错误并提示用户手动修复

#### 场景：分离模式下的修复

- **当** 启用 `--split-ddl-dml` 和 `--auto-fix` 参数
- **那么** 分别对 `convertsql/create/` 和 `convertsql/insert/` 目录执行修复
- **并且** DDL 修复重点处理保留字和特殊字符列名
- **并且** DML 修复重点处理 CONCAT 转换和字符串转义

#### 场景：生成合并报告

- **当** 启用自动修复并完成后
- **那么** 生成统一的转换报告，包含：
  - 转换阶段统计（成功/失败/跳过文件数）
  - 修复阶段统计（修复的问题数量和类型）
  - 总耗时

#### 场景：批量转换时的自动修复

- **当** 用户使用 `convert-all` 命令批量转换目录
- **并且** 指定 `--auto-fix` 参数
- **那么** 在所有文件转换完成后执行修复
- **并且** 如果启用 `--split-ddl-dml`，分别修复 create/ 和 insert/ 目录
- **而不是** 对每个文件单独修复（避免重复操作）

---

## 修改需求

### 需求：转换后文件保存

系统必须将转换后的 SQL 文件保存到指定目录。

#### 场景：保存到指定目录

- **当** 用户指定输出目录 `docs/hospital/convertsql/`
- **那么** 转换后的文件保存到该目录

#### 场景：文件名前缀

- **当** 用户使用 `--prefix` 参数（例如：`mysql_`）
- **那么** 转换后的文件名添加前缀（例如：`mysql_BS_DEPARTMENT.sql`）
- **注意**：此参数仅影响文件名，不影响 SQL 语句中的表名

#### 场景：表名前缀

- **当** 用户使用 `--table-prefix` 参数（例如：`gzlry_`）
- **那么** SQL 语句中的表名添加前缀（例如：`BS_AREA` → `gzlry_BS_AREA`）
- **注意**：此参数仅影响 SQL 语句，不影响输出文件名

#### 场景：批量转换

- **当** 用户使用 `convert-all` 命令转换目录下所有文件
- **那么** 必须指定输出目录（`-o` 参数），所有转换后的文件保存到该目录
- **并且** 如果启用 `--split-ddl-dml`，在输出目录下创建 create/ 和 insert/ 子目录

#### 场景：DDL/DML 分离后的文件组织

- **当** 使用 `--split-ddl-dml` 参数
- **那么** 输出目录结构为：
  ```
  convertsql/
  ├── create/
  │   ├── BS_AREA.sql
  │   └── BS_OLDER.sql
  └── insert/
      ├── BS_AREA_data.sql
      └── BS_OLDER_data.sql
  ```
- **并且** 如果同时使用 `--prefix mysql_`，文件名添加前缀：
  ```
  convertsql/
  ├── create/
  │   ├── mysql_BS_AREA.sql
  │   └── mysql_BS_OLDER.sql
  └── insert/
      ├── mysql_BS_AREA_data.sql
      └── mysql_BS_OLDER_data.sql
  ```
