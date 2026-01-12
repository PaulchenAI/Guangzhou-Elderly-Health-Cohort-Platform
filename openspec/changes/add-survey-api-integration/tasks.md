# 任务清单

## 1. 基础设施

- [ ] 1.1 创建 `core/survey/` 模块目录结构
- [ ] 1.2 创建外部 API 客户端 `survey_api_client.py`（含 JWT 认证）
- [ ] 1.3 添加配置项到 `settings.py`（从 `.env` 读取 `SURVEY_API_URL`, `SURVEY_API_ADMIN`, `SURVEY_API_PASSWORD`）

## 2. Schema 同步

- [ ] 2.1 实现 JWT Token 获取（`/api/auth/token`）和自动刷新
- [ ] 2.2 实现问卷类型列表获取 (`/api/survey-types`)
- [ ] 2.3 实现问卷 Schema 获取 (`/api/survey-schema/{type}`)
- [ ] 2.4 创建 Schema 解析器，将外部 Schema 转换为 Django 字段定义
- [ ] 2.5 创建 `SurveySchemaConfig` 模型存储 Schema 元数据
- [ ] 2.6 实现 `sync_survey_schemas` 管理命令

## 3. 动态模型生成

- [ ] 3.1 创建 `SurveyRecord` 基础模型（使用 JSON 字段存储问卷数据）
- [ ] 3.2 创建 `SurveyImportLog` 导入日志模型
- [ ] 3.3 实现模型字段动态映射

## 4. 数据导入

- [ ] 4.1 实现外部 API 数据查询 (`/api/search`，需要 JWT 认证)
- [ ] 4.2 创建数据转换器（外部格式 → 本地格式）
- [ ] 4.3 实现批量数据导入逻辑
- [ ] 4.4 实现增量导入（基于 surveyId 去重）
- [ ] 4.5 实现 `import_survey_data` 管理命令
- [ ] 4.6 添加导入进度显示和日志记录

## 5. 定时任务

- [ ] 5.1 创建定时任务函数 `scheduler/module/survey_tasks.py`
- [ ] 5.2 实现 `sync_survey_schemas_task` 定时同步 Schema 任务
- [ ] 5.3 实现 `import_survey_data_task` 定时增量导入任务
- [ ] 5.4 创建默认的 `SchedulerJob` 记录（通过管理命令或 Fixture）

## 6. 查询 API

- [ ] 6.1 创建问卷数据查询 API (`survey_api.py`)
- [ ] 6.2 实现问卷记录列表、详情、导出接口
- [ ] 6.3 实现 Schema 列表、详情接口
- [ ] 6.4 注册路由到 `core/router.py`

## 7. 前端页面

- [ ] 7.1 创建前端 API 文件 `web/apps/web-ele/src/api/core/survey.ts`
- [ ] 7.2 创建问卷查询页面 `web/apps/web-ele/src/views/survey/index.vue`（参考 `table-query/index.vue`）
- [ ] 7.3 实现左侧问卷类型选择器
- [ ] 7.4 实现右侧动态表格展示（根据 Schema 动态生成列）
- [ ] 7.5 实现搜索表单（根据可搜索字段动态生成）
- [ ] 7.6 实现数据导出功能

## 8. 菜单初始化

- [ ] 8.1 创建 `init_survey_menus` 管理命令
- [ ] 8.2 创建"问卷管理"父菜单
- [ ] 8.3 创建"问卷数据查询"子菜单

## 9. 测试与文档

- [ ] 9.1 编写单元测试
- [ ] 9.2 编写集成测试（模拟外部 API）
- [ ] 9.3 更新 API 文档

