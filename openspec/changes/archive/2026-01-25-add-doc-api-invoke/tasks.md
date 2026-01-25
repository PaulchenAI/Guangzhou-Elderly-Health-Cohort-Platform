# 任务清单

## 1. 后端数据模型

- [x] 1.1 创建 `doc_api_model.py`
  - 定义 `DocApiInvokeLog` 模型
  - 包含字段：operation_id, endpoint_name, method, path, request_params, response_data, response_status, duration_ms, success, error_message, user_id, sys_create_datetime

- [x] 1.2 生成并执行数据库迁移
  - 创建 `doc_api_invoke_log` 表
  - 添加索引（operation_id, sys_create_datetime）

## 2. 后端 API 扩展

- [x] 2.1 扩展 `doc_api_service.py`
  - 实现 `invoke_his_endpoint()` 代理调用函数
  - 实现 `save_invoke_log()` 保存调用历史
  - 实现 `get_invoke_logs()` 查询调用历史
  - 实现 `get_default_params()` 获取默认测试参数

- [x] 2.2 扩展 `doc_api_schema.py`
  - 定义 `DocInvokeRequestIn` - 调用请求参数
  - 定义 `DocInvokeResponseOut` - 调用响应
  - 定义 `DocInvokeLogOut` - 调用历史记录
  - 定义 `DocEndpointWithAccessOut` - 带访问状态的接口信息

- [x] 2.3 扩展 `doc_api.py`
  - `POST /doc-api/invoke/{operation_id}` - 调用 HIS 接口
  - `GET /doc-api/invoke-logs` - 查询调用历史（分页）
  - `GET /doc-api/endpoints/{operation_id}/default-params` - 获取默认参数
  - 修改接口列表返回 `accessible` 字段

## 3. 前端 API 扩展

- [x] 3.1 扩展 `doc-api.ts`
  - 添加类型定义：`DocInvokeRequest`, `DocInvokeResponse`, `DocInvokeLog`
  - 实现 `invokeDocEndpointApi()` - 调用接口
  - 实现 `getDocInvokeLogsApi()` - 获取调用历史
  - 实现 `getDocDefaultParamsApi()` - 获取默认参数
  - 更新 `DocEndpoint` 类型增加 `accessible` 字段

## 4. 前端视图组件

- [x] 4.1 修改 `index.vue`
  - 接口列表增加"访问状态"列
  - 可访问显示绿色标签，不可访问显示灰色标签

- [x] 4.2 创建 `InvokePanel.vue`
  - JSON 编辑器（请求参数编辑）
  - "加载默认参数"按钮
  - "发送请求"按钮（带 loading 状态）
  - 响应结果展示（表格/JSON 切换）
  - 耗时和状态码显示

- [x] 4.3 修改 `EndpointDetail.vue`
  - 增加"调用测试"Tab（仅可访问接口显示）
  - 集成 InvokePanel 组件

- [x] 4.4 创建 `InvokeHistory.vue`
  - 调用历史列表（operation_id, 时间, 状态, 耗时）
  - 点击查看详情（请求参数、响应数据）

## 5. 验证与测试

- [x] 5.1 后端功能验证
  - 验证代理调用正常转发
  - 验证调用历史正确保存
  - 验证访问控制生效

- [x] 5.2 前端功能验证
  - 验证访问状态正确显示
  - 验证调用面板功能
  - 验证历史记录展示
