# 变更：改进 backend-django 的 OpenAPI 描述

## 为什么

AIagent 的 OpenAPI-Aware 客户端依赖 backend-django 的 OpenAPI Schema 进行意图匹配。当前约 28% 的 API 端点 summary 为英文（如 "Create Dict"、"List Schemas"），导致 AI 意图理解不准确。通过统一使用中文 summary 和规范化的 description，可以显著提升 AI 对 API 的理解能力。

## 变更内容

- 为所有缺少中文 summary 的 API 端点添加中文 summary
- 为复杂 API 添加结构化 description（查询参数、返回值说明）
- 统一 OpenAPI 描述格式规范（动词标准化）
- 更新 `docs/backend-api-development-guide.md` 添加 OpenAPI 描述规范章节

**注**：Tags 统一规范化将作为后续独立变更处理，本次不涉及。

### 影响范围

需要修改的模块（共约 78 个端点）：
- `core/dict/dict_api.py` - 字典管理（5 个端点）
- `core/dict_item/dict_item_api.py` - 字典项管理（6 个端点）
- `core/survey/survey_api.py` - 问卷管理（11 个端点）
- `core/table_query/table_query_api.py` - 表查询管理（9 个端点）
- 其他模块的部分端点

## 影响

- 受影响规范：`backend-api`（新增 OpenAPI 描述规范）
- 受影响代码：
  - `backend-django/core/*/` - 各模块的 `*_api.py` 文件
  - `backend-django/docs/` - API 开发规范文档
- 受益系统：
  - AIagent 意图理解准确率提升
  - Swagger/ReDoc 文档可读性提升
