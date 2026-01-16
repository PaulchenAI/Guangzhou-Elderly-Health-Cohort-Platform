# 变更：增强表配置中文名称支持

## 为什么

当前 `batch_create_table_configs` 命令在批量创建表查询配置时，生成的 `display_name` 仅基于表名前缀映射，缺少中文名称。这导致：
1. 无法利用数据库中已存在的表注释（COMMENT）信息
2. 对于没有注释的表，无法通过外部配置文件提供中文名称
3. 生成的配置中文名称不够准确和完整

## 变更内容

- **修改需求**：批量创建表配置时，优先从数据库表注释获取中文名称
- **新增需求**：支持从外部 JSON 配置文件读取表名和字段的中文名称映射
- **新增需求**：字段配置中的 `displayName` 支持从数据库字段注释或配置文件获取

## 影响

- **受影响规范**：`database-table-query` - 表查询配置管理
- **受影响代码**：
  - `backend-django/core/management/commands/batch_create_table_configs.py`
  - 可能需要新增配置文件：`backend-django/core/management/commands/table_name_mapping.json`（可选）
