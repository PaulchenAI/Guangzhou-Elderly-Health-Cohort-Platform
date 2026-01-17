# 任务清单

## 1. 问卷管理模块

- [x] 1.1 新增 `GET /api/core/survey/schemas/by-name/{survey_name}` API 端点
- [x] 1.2 修改 `SurveyQueryIn` Schema，添加可选的 `survey_name` 字段
- [x] 1.3 修改 `SurveyExportIn` Schema，添加可选的 `survey_name` 字段
- [x] 1.4 修改 `query_records` 函数，支持按 `survey_name` 解析 `schema_id`
- [x] 1.5 修改 `export_records` 函数，支持按 `survey_name` 解析 `schema_id`

## 2. 用户管理模块

- [x] 2.1 新增 `GET /api/core/user/by-name/{name}` API 端点
- [x] 2.2 新增 `GET /api/core/user/by-username/{username}` API 端点

## 3. 角色管理模块

- [x] 3.1 新增 `GET /api/core/role/by-name/{name}` API 端点
- [x] 3.2 新增 `GET /api/core/role/by-code/{code}` API 端点

## 4. 部门管理模块

- [x] 4.1 新增 `GET /api/core/dept/by-name/{name}` API 端点
- [x] 4.2 新增 `GET /api/core/dept/by-code/{code}` API 端点

## 5. 岗位管理模块

- [x] 5.1 新增 `GET /api/core/post/by-name/{name}` API 端点
- [x] 5.2 新增 `GET /api/core/post/by-code/{code}` API 端点

## 6. 字典管理模块

- [x] 6.1 新增 `GET /api/core/dict/by-name/{name}` API 端点
- [x] 6.2 新增 `GET /api/core/dict/by-code/{code}` API 端点

## 7. 表查询配置模块

- [x] 7.1 新增 `GET /api/core/table-query/configs/by-name/{name}` API 端点
- [x] 7.2 修改 `TableQueryIn` Schema，添加可选的 `config_name` 字段
- [x] 7.3 修改 `ExportParams` Schema，添加可选的 `config_name` 字段
- [x] 7.4 修改 `execute_query` 函数，支持按 `config_name` 解析 `config_id`
- [x] 7.5 修改 `export_data` 函数，支持按 `config_name` 解析 `config_id`

## 8. 开发文档规范优化

- [x] 8.1 更新 `docs/backend-api-development-guide.md` 第 4.4 节：新增按名称/编码查询的路径命名规范
- [x] 8.2 在 4.5.4 节新增"支持名称参数的 API description 编写规范"
- [x] 8.3 新增第 4.6 节"AI 友好的按名称查询 API 设计模式"
- [x] 8.4 新增第 4.6.4 节"已实现的按名称查询 API"表格

## 9. 验证测试

- [x] 9.1 测试各模块按名称精确匹配查询
- [x] 9.2 测试各模块按名称模糊匹配查询
- [x] 9.3 测试 AI CLI 工具调用新 API
- [x] 9.4 验证原有 ID 参数仍然有效（向后兼容）
