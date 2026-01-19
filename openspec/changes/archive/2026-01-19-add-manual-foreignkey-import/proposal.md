# 变更：添加手动外键关系导入命令

## 为什么

当前系统的外键关系元数据是通过解析 Oracle SQL 文件自动提取的，但存在一些业务表之间的逻辑外键关系未在原始 SQL 中定义（如 `OL_record_history`、`WORKFLOW_REQUESTBASE`、`HR_HEALTH_RECORDS` 等表之间的关联）。需要提供一个 Django 管理命令来手动导入这些缺失的外键关系，以支持 AI Agent 的多表关联查询功能。

## 变更内容

- 新增 Django 管理命令 `import_manual_foreignkeys`，用于导入手动定义的外键关系
- 支持以下外键关系的导入：
  1. `OL_RECORD_HISTORY.olderid` → `BS_OLDER.mainid`（老人记录关联老人基本信息）
  2. `WORKFLOW_REQUESTBASE.recordid` → `OL_RECORD_HISTORY.mainid`（工作流关联老人记录）
  3. `WORKFLOW_REQUESTBASE.olderid` → `BS_OLDER.mainid`（工作流关联老人）
  4. `HR_HEALTH_RECORDS.bs_older_id` → `BS_OLDER.mainid`（健康档案关联老人）
  5. `HR_HEALTH_RECORDS.ol_record_id` → `OL_RECORD_HISTORY.mainid`（健康档案关联老人记录）
  6. `HR_HH_DRUG.health_records_id` → `HR_HEALTH_RECORDS.mainid`（用药记录关联健康档案）
  7. `FORMTABLE_MAIN_*.requestid` → `WORKFLOW_REQUESTBASE.requestid`（表单数据关联工作流）
  8. `DC_FORM_*.requestid` → `WORKFLOW_REQUESTBASE.requestid`（数据采集表单关联工作流）
- 命令支持 `--dry-run` 预览模式
- 命令支持 `--prefix` 指定表名前缀（默认 `gzlry_`）
- 命令支持 `--truncate-manual` 清空手动导入的记录后重新导入
- 自动检测数据库中存在的 `FORMTABLE_MAIN_*` 和 `DC_FORM_*` 表并生成对应的外键关系
- 验证动态发现的表中是否存在 `requestid` 字段

## 影响

- 受影响规范：`foreignkey-api`（扩展外键数据源）
- 受影响代码：
  - `backend-django/core/management/commands/` - 新增命令文件
  - `table_foreignkey_metadata` 表 - 新增手动导入的外键记录
