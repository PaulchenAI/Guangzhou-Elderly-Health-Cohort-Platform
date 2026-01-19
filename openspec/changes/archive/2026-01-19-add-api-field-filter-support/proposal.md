# 变更：增强 AI 对表数据和问卷数据的字段过滤查询能力

## 为什么

当前系统存在以下问题：

1. **后端 API 字段搜索限制**：表查询 API 和问卷查询 API 会验证字段是否标记为 `searchable: true`，如果字段未标记为可搜索，API 会返回 "字段 xxx 不支持搜索" 错误。然而，许多表的字段虽然在配置中存在，但未正确标记 `searchable` 属性。

2. **AI 无法获取可过滤字段信息**：AI Agent 在生成查询脚本时，无法准确知道哪些字段支持过滤查询，导致生成的脚本使用了不支持搜索的字段，执行时报错。

3. **问卷数据查询无字段验证**：问卷查询 API (`/survey/query`) 的过滤条件直接传递给 Django ORM，但没有验证字段是否存在于 Schema 配置中，可能导致查询失败或安全问题。

## 变更内容

### 1. 增强 AI Agent 的字段感知能力
- 在获取配置列表时，同时获取每个配置的可搜索字段列表
- 在生成查询脚本时，AI 必须只使用配置中标记为 `searchable: true` 的字段
- 在脚本验证阶段，检查过滤条件中的字段是否在可搜索字段列表中

### 2. 优化后端 API 的字段搜索配置
- 为常用查询字段（如姓名、ID、日期等）默认启用 `searchable: true`
- 在批量创建表配置时，根据字段类型智能设置 `searchable` 属性
- 提供 API 端点查询指定配置的可搜索字段列表

### 3. 问卷查询 API 增加字段验证
- 在 `/survey/query` API 中增加字段白名单验证
- 只允许使用 Schema 中定义的字段进行过滤
- 返回清晰的错误信息，说明哪些字段可用于过滤

### 4. 改进错误提示和用户体验
- 当字段不支持搜索时，返回可用的搜索字段列表
- AI Agent 在遇到字段不支持搜索错误时，自动获取可用字段并重新生成脚本

## 影响

- 受影响规范：`aiagent`、`database-table-query`、`survey`
- 受影响代码：
  - `backend-django/core/table_query/table_query_api.py` - 增强错误提示
  - `backend-django/core/survey/survey_api.py` - 增加字段验证
  - `backend-django/core/management/commands/batch_create_table_configs.py` - 优化 searchable 默认值
  - `AIagent/src/django_api/script_generator.py` - 增强字段感知
  - `AIagent/src/django_api/client.py` - 获取可搜索字段信息
