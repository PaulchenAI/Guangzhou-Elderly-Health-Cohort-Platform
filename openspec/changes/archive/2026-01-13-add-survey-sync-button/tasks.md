# 任务清单

## 1. 后端实现

- [x] 1.1 在 `survey_schema.py` 添加同步请求/响应 Schema
  - `SurveySyncIn`: 同步请求参数（incremental: bool, survey_type: str | None）
  - `SurveySyncOut`: 同步结果（batch_id, total, success, skipped, failed, message）

- [x] 1.2 在 `survey_api.py` 添加同步 API 端点
  - `POST /api/core/survey/sync` - 触发数据同步
  - 复用 `SurveyService.import_data()` 方法
  - 设置 `trigger_type="manual"` 以区分手动触发

## 2. 前端实现

- [x] 2.1 在 `survey.ts` 添加同步 API 调用函数
  - `triggerSurveySyncApi(params)` - 调用后端同步接口
  - 定义 `SurveySyncParams` 和 `SurveySyncResult` 类型

- [x] 2.2 在 `index.vue` 添加同步按钮
  - 在导出按钮旁边添加"同步数据"按钮
  - 添加 loading 状态处理
  - 添加同步结果消息提示

## 3. 验证

- [x] 3.1 代码实现完成
  - 后端 API 已实现
  - 前端按钮和调用已实现
  - loading 状态正常切换

## 依赖关系

- 1.1 → 1.2 → 2.1 → 2.2 → 3.1（顺序依赖）
