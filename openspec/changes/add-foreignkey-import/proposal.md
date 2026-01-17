# 变更：导入外键关系元数据到 MySQL 数据库

## 为什么

已从 Oracle SQL 文件中提取了 955 个表的外键信息（存储在 `docs/hospital/foreignkey/` 目录下的 JSON 文件中），其中 281 个表包含共计 535 个外键约束关系。这些外键关系信息需要作为元数据存储到 MySQL 数据库中，便于查询表之间的关联关系。

关键点：
1. JSON 文件中的表名没有前缀（如 `BS_DEPARTMENT`），导入时需要补上前缀（如 `gzlry_BS_DEPARTMENT`）
2. 只是存储外键关系信息，不是在表上创建实际的外键约束
3. 需要创建一张元数据表来存储这些关系

## 变更内容

- 新增外键关系元数据表 `table_foreignkey_metadata`（或类似名称）
- 新增 `import-foreignkey-metadata` CLI 命令，从 JSON 文件批量导入外键关系到元数据表
- 支持 `--prefix` 参数指定表名前缀（默认 `gzlry_`）
- 支持 `--dry-run` 预览模式
- 支持覆盖/追加模式

## 影响

- 受影响规范：sql-import（新增需求）
- 受影响代码：
  - `backend-django/core/management/commands/import_foreignkey_metadata.py`（新增）
