# 变更：从 meaning.json 文件更新表查询配置的中文名称

## 为什么

`docs/hospital/commentsql` 目录下已经通过 AI 生成了大量表和字段的中文含义推断文件（`*_meaning.json`），这些文件包含了表名和字段名的中文翻译、推断含义、置信度等信息。目前 `batch_create_table_configs` 命令只支持从数据库 COMMENT 或简单的 JSON 映射文件获取中文名称，无法利用这些已有的高质量语义信息来更新表查询配置。

## 变更内容

- 增强 `batch_create_table_configs` 命令，支持从 `*_meaning.json` 文件读取表名和字段名的中文含义
- 新增 `--meaning-dir` 参数，指定 meaning.json 文件所在目录
- 新增 `--table-prefix` 参数，配置数据库表名前缀（匹配 meaning.json 时忽略此前缀）
- 更新名称获取优先级：
  1. 数据库 COMMENT（最高优先级）
  2. meaning.json 文件中的 `inferred_meaning`（新增）
  3. 配置文件映射（`--config-file`）
  4. 表名/字段名本身（最低优先级）
- 支持批量更新现有配置的中文名称（`--update` 模式）

## 影响

- 受影响规范：`database-table-query`
- 受影响代码：
  - `backend-django/core/management/commands/batch_create_table_configs.py`
- 无破坏性变更，完全向后兼容
