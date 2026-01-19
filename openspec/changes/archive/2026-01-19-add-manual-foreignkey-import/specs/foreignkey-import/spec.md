## 新增需求

### 需求：手动外键关系导入命令

系统必须提供 Django 管理命令 `import_manual_foreignkeys`，用于导入业务逻辑上存在但未在原始 SQL 中定义的外键关系。

#### 场景：预览模式查看待导入的外键关系

- **当** 执行 `python manage.py import_manual_foreignkeys --dry-run`
- **那么** 系统显示将要导入的所有外键关系列表
- **并且** 不执行实际的数据库写入操作
- **并且** 显示固定定义的外键关系数量
- **并且** 显示动态发现的表（`FORMTABLE_MAIN_*` 和 `DC_FORM_*`）数量

#### 场景：导入固定外键关系

- **当** 执行 `python manage.py import_manual_foreignkeys`
- **那么** 系统导入以下预定义的外键关系：
  - `OL_RECORD_HISTORY.olderid` → `BS_OLDER.mainid`
  - `WORKFLOW_REQUESTBASE.recordid` → `OL_RECORD_HISTORY.mainid`
  - `WORKFLOW_REQUESTBASE.olderid` → `BS_OLDER.mainid`
  - `HR_HEALTH_RECORDS.bs_older_id` → `BS_OLDER.mainid`
  - `HR_HEALTH_RECORDS.ol_record_id` → `OL_RECORD_HISTORY.mainid`
  - `HR_HH_DRUG.health_records_id` → `HR_HEALTH_RECORDS.mainid`
- **并且** 每条记录的 `source_file` 字段标记为 `manual_import`

#### 场景：动态发现并导入表单表外键

- **当** 执行 `python manage.py import_manual_foreignkeys`
- **那么** 系统查询数据库中所有以 `FORMTABLE_MAIN_` 开头的表
- **并且** 验证表中存在 `requestid` 字段
- **并且** 为每个有效表生成 `requestid` → `WORKFLOW_REQUESTBASE.requestid` 的外键关系
- **并且** 导入到 `table_foreignkey_metadata` 表

#### 场景：动态发现并导入数据采集表单外键

- **当** 执行 `python manage.py import_manual_foreignkeys`
- **那么** 系统查询数据库中所有以 `DC_FORM_` 开头的表
- **并且** 验证表中存在 `requestid` 字段
- **并且** 为每个有效表生成 `requestid` → `WORKFLOW_REQUESTBASE.requestid` 的外键关系
- **并且** 导入到 `table_foreignkey_metadata` 表

#### 场景：验证固定外键关系的表和字段存在性

- **当** 执行 `python manage.py import_manual_foreignkeys`
- **那么** 系统先验证每个固定外键关系的源表和目标表是否存在
- **并且** 再验证源字段和目标字段是否存在
- **并且** 跳过表或字段不存在的外键关系
- **并且** 显示跳过的原因

#### 场景：验证动态表的目标表存在性

- **当** 执行 `python manage.py import_manual_foreignkeys`
- **那么** 系统先验证 `WORKFLOW_REQUESTBASE` 表是否存在
- **如果** 目标表不存在，则跳过所有动态表的外键关系
- **并且** 显示跳过的原因

#### 场景：指定表名前缀

- **当** 执行 `python manage.py import_manual_foreignkeys --prefix custom_`
- **那么** 系统使用 `custom_` 作为表名前缀
- **并且** 生成的外键关系中表名带有该前缀（如 `custom_OL_RECORD_HISTORY`）

#### 场景：清空手动导入记录后重新导入

- **当** 执行 `python manage.py import_manual_foreignkeys --truncate-manual`
- **那么** 系统先删除 `source_file = 'manual_import'` 的所有记录
- **并且** 然后重新导入所有手动定义的外键关系
- **并且** 不影响从 JSON 文件导入的外键记录

---

### 需求：外键关系数据标识

手动导入的外键关系必须与自动导入的外键关系有明确区分。

#### 场景：手动导入记录标识

- **当** 通过 `import_manual_foreignkeys` 命令导入外键关系
- **那么** 记录的 `source_file` 字段值为 `manual_import`
- **并且** 可通过该字段区分手动导入和自动导入的记录
