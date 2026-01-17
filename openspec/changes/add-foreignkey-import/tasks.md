# 任务清单

## 1. 数据库表设计

- [x] 1.1 创建外键关系元数据表 `table_foreignkey_metadata`，包含字段：
  - `id`：主键
  - `source_table`：源表名（带前缀）
  - `source_columns`：源字段（JSON 数组或逗号分隔）
  - `target_table`：目标表名（带前缀）
  - `target_columns`：目标字段（JSON 数组或逗号分隔）
  - `constraint_name`：约束名（带前缀）
  - `on_delete`：删除规则
  - `source_file`：来源 JSON 文件
  - `created_at`：创建时间

## 2. 核心功能实现

- [x] 2.1 创建 `ForeignKeyMetadataImporter` 类，负责读取 JSON 文件
- [x] 2.2 实现表名前缀补全逻辑（源表、目标表、约束名）
- [x] 2.3 实现批量插入逻辑

## 3. CLI 命令实现

- [x] 3.1 新增 `import-foreignkey-metadata` 命令，支持参数：
  - `<json_dir>`：JSON 文件目录
  - `--prefix`：表名前缀（默认 `gzlry_`）
  - `--dry-run`：预览模式
  - `--truncate`：导入前清空表
- [x] 3.2 实现导入进度显示和统计报告

## 4. 测试

- [x] 4.1 编写单元测试（前缀补全、数据转换）
- [x] 4.2 编写集成测试（实际导入测试）
