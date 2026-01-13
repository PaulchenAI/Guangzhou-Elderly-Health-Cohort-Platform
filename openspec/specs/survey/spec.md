# survey Specification

## Purpose
TBD - created by archiving change add-survey-sync-button. Update Purpose after archive.
## 需求
### 需求：手动触发数据同步

用户必须能够在问卷数据查询页面手动触发数据同步，以便在需要时立即获取最新的问卷数据。

#### 场景：成功同步数据

- **当** 用户在问卷数据查询页面点击"同步数据"按钮
- **那么** 系统调用后端同步 API 触发增量数据导入
- **并且** 按钮显示 loading 状态直到同步完成
- **并且** 同步完成后显示结果消息（成功数、跳过数、失败数）
- **并且** 数据表格自动刷新展示最新数据

#### 场景：同步过程中禁止重复触发

- **当** 用户点击"同步数据"按钮后，同步任务正在进行中
- **那么** 按钮保持禁用状态
- **并且** 用户无法重复触发同步操作

#### 场景：同步失败处理

- **当** 同步过程中发生错误
- **那么** 系统显示错误提示消息
- **并且** 按钮恢复可点击状态
- **并且** 用户可以重新尝试同步

### 需求：同步 API 端点

系统必须提供 `POST /api/core/survey/sync` API 端点，支持手动触发问卷数据同步。

#### 场景：调用同步 API

- **当** 前端发送 POST 请求到 `/api/core/survey/sync`
- **那么** 后端调用 `SurveyService.import_data()` 执行数据同步
- **并且** 返回同步结果（batch_id、total、success、skipped、failed）
- **并且** 导入日志的 `trigger_type` 记录为 `manual`

#### 场景：支持指定问卷类型同步

- **当** 请求参数包含 `survey_type` 字段
- **那么** 只同步指定类型的问卷数据
- **当** 请求参数不包含 `survey_type` 字段
- **那么** 同步所有类型的问卷数据

