# 变更：增强 OpenAPI 字段描述的上下文信息

## 为什么

当前 Django 后端的 OpenAPI 描述中，字段的 `description` 缺少足够的上下文信息，导致 AI 在生成跨表查询时无法正确理解不同表之间字段的对应关系。例如：

- `core_user.dept_id` 字段的描述是"所属部门"，但没有说明它关联到 `core_dept.id`
- `core_post.dept_id` 字段的描述是"所属部门"，同样没有说明关联关系
- AI 无法从 OpenAPI Schema 中推断出 `dept_id` 应该与 `core_dept` 表的 `id` 字段进行 JOIN

这导致 AI 在处理涉及多表关联的查询时（如"查询某部门下的所有用户"）无法正确生成 JOIN 语句。

## 变更内容

1. **增强 Model 字段的 `help_text`**：
   - 为所有 ForeignKey 字段添加关联表和关联字段的说明
   - 格式：`{业务含义}，关联 {目标表}.{目标字段}`
   - 示例：`help_text="所属部门，关联 core_dept.id"`

2. **增强 Schema 字段的 `description`**：
   - 为所有关联字段添加关联关系说明
   - 格式：`{业务含义}（关联 {目标表}.{目标字段}）`
   - 示例：`description="所属部门ID（关联 core_dept.id）"`

3. **新增 Django management command `enhance_field_descriptions`**：
   - 自动扫描所有 Django 模型
   - 生成增强后的字段描述建议
   - 支持 `--dry-run` 预览模式
   - 支持 `--output` 输出到文件

4. **更新 OpenAPI 描述规范**：
   - 在 `backend-api` 规范中新增字段描述规范
   - 明确关联字段的描述格式要求

## 影响

- 受影响规范：`backend-api`
- 受影响代码：
  - `backend-django/core/*/` 下的所有 `*_model.py` 和 `*_schema.py` 文件
  - `backend-django/core/management/commands/enhance_field_descriptions.py`（新增）
