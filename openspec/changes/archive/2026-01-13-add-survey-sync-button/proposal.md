# 变更：问卷数据查询页面添加同步数据按钮

## 为什么

当前问卷数据查询页面只能查看已导入的数据，用户无法主动触发数据同步。虽然后台已配置定时任务自动同步，但用户可能需要在某些场景下立即获取最新数据（如刚录入问卷后查看）。

## 变更内容

- 在问卷数据查询页面的操作栏添加"同步数据"按钮
- 新增后端 API 支持手动触发数据同步
- 支持同步进度状态展示和结果反馈
- 复用现有的 `SurveyService.import_data()` 方法，确保与定时任务行为一致

## 影响

- 受影响规范：survey（问卷管理）
- 受影响代码：
  - `backend-django/core/survey/survey_api.py` - 新增同步 API
  - `backend-django/core/survey/survey_schema.py` - 新增请求/响应 Schema
  - `web/apps/web-ele/src/api/core/survey.ts` - 新增 API 调用函数
  - `web/apps/web-ele/src/views/survey/index.vue` - 添加同步按钮
