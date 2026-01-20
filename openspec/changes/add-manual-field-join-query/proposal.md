# 变更：支持手动字段匹配的联合查询

## 为什么

当前联合查询功能仅支持基于外键关系的自动关联查询。但在实际业务场景中，需要将没有外键关系的表进行关联查询（如问卷调查的 `patient_name` 与 `BS_OLDER` 表的 `name` 字段）。用户希望能够手动选择主表的某个字段和另一个表的某个字段进行匹配关联，同时保留原有的外键关联功能。

## 变更内容

- **保留原有外键关联功能**：继续支持基于 `ForeignKeyMetadata` 的自动关联查询
- **新增手动字段匹配关联**：允许用户在查询时手动指定字段匹配规则
- **两种关联方式共存**：外键关联和手动关联可以同时使用
- **支持精确匹配和模糊匹配**：手动关联支持 `exact`（精确）和 `fuzzy`（模糊）两种匹配方式
- **自动去重**：如果手动关联的目标表已在外键关联中存在，则跳过手动关联（避免重复）

## 影响

- 受影响规范：`join-query-api`（新增需求）
- 受影响代码：
  - `backend-django/core/table_query/table_query_schema.py` - 扩展 `JoinQueryIn` Schema，新增 `ManualJoin` Schema
  - `backend-django/core/table_query/join_query_utils.py` - 支持手动关联构建和 JOIN 条件生成
  - `backend-django/core/table_query/table_query_api.py` - 处理手动关联参数和验证
