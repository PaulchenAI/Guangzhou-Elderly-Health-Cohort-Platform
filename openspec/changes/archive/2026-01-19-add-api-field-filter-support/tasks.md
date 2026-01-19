# 任务清单

## 1. 后端 API 优化

- [x] 1.1 在表查询 API 的错误响应中包含可搜索字段列表
- [x] 1.2 添加 `/table-query/configs/{id}/searchable-fields` 端点返回可搜索字段
- [x] 1.3 在问卷查询 API 中增加字段白名单验证
- [x] 1.4 优化 `batch_create_table_configs` 命令，为常用字段类型默认启用 searchable

## 2. AI Agent 增强

- [x] 2.1 在获取配置时同时获取可搜索字段信息
- [x] 2.2 在生成脚本时，将可搜索字段信息传递给 LLM
- [x] 2.3 在脚本验证阶段检查过滤字段是否可搜索
- [x] 2.4 遇到字段不支持搜索错误时，自动获取可用字段并重试

## 3. 测试验证

- [x] 3.1 测试表查询 API 的字段验证和错误提示
- [x] 3.2 测试问卷查询 API 的字段验证
- [x] 3.3 测试 AI Agent 生成带过滤条件的查询脚本
- [x] 3.4 验证自动修正功能正常工作

## 实施摘要

### 后端 API 变更

1. **table_query_api.py**:
   - 修改 `build_where_clause` 函数，当字段不支持搜索时返回包含 `available_fields` 的错误响应
   - 添加 `get_searchable_fields` 端点：`GET /table-query/configs/{config_id}/searchable-fields`
   - 添加 `get_searchable_fields_by_name` 端点：`GET /table-query/configs/by-name/{name}/searchable-fields`

2. **survey_api.py**:
   - 在 `query_records` 函数中添加字段白名单验证逻辑
   - 支持模型固定字段（patient_name, survey_type 等）和 Schema 可搜索字段
   - 添加 `get_schema_searchable_fields` 端点：`GET /survey/schemas/{schema_id}/searchable-fields`
   - 添加 `get_schema_searchable_fields_by_name` 端点：`GET /survey/schemas/by-name/{name}/searchable-fields`

3. **batch_create_table_configs.py**:
   - 优化 `is_searchable` 默认值逻辑
   - 支持更多字段类型：字符串、整数ID字段、主键、名称字段、日期时间字段

### AI Agent 变更

1. **script_generator.py**:
   - 增强错误响应解析，支持新的包含 `available_fields` 的错误格式
   - 添加调用新的 `/searchable-fields` 端点获取可搜索字段的逻辑
   - 支持表查询和问卷查询两种 API 类型
