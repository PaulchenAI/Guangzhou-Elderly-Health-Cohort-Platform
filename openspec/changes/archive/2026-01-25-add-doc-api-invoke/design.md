# 设计文档

## 上下文

当前系统已有：
- 后端 `doc_api` 模块：提供接口文档查询功能
- 前端 `doc-api` 页面：展示接口列表和详情
- 访问控制配置：`docs/his/access_control.json`
- HIS API 配置：`DOC_API_URL` 和 `DOC_API_TOKEN` 环境变量

需要扩展支持：
- 实际调用 HIS 接口并返回数据
- 保存调用历史
- 前端展示访问状态和调用功能

## 目标 / 非目标

**目标：**
- 提供安全的 HIS 接口代理调用能力
- 支持用户自定义请求参数
- 提供默认测试参数便于快速测试
- 持久化保存调用历史
- 前端清晰展示接口访问状态

**非目标：**
- 不实现批量调用功能
- 不实现定时调度调用
- 不实现接口性能监控

## 决策

### 1. 数据库模型设计

新增 `DocApiInvokeLog` 模型：

```python
class DocApiInvokeLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    operation_id = models.CharField(max_length=100, db_index=True)  # 接口操作 ID
    endpoint_name = models.CharField(max_length=200)  # 接口名称
    method = models.CharField(max_length=10)  # HTTP 方法
    path = models.CharField(max_length=500)  # 接口路径
    request_params = models.JSONField(default=dict)  # 请求参数
    response_data = models.JSONField(default=dict)  # 响应数据
    response_status = models.IntegerField()  # HTTP 状态码
    duration_ms = models.IntegerField()  # 耗时（毫秒）
    success = models.BooleanField()  # 是否成功
    error_message = models.TextField(blank=True)  # 错误信息
    user_id = models.CharField(max_length=100, blank=True)  # 调用用户
    sys_create_datetime = models.DateTimeField(auto_now_add=True)
```

**理由**：保存完整的请求和响应信息，便于追溯和调试

### 2. API 代理设计

```
POST /api/core/doc-api/invoke/{operation_id}
```

请求体：
```json
{
    "params": {
        "key1": "value1",
        "key2": "value2"
    }
}
```

响应：
```json
{
    "success": true,
    "status_code": 200,
    "duration_ms": 150,
    "data": { ... },  // HIS 返回的原始数据
    "log_id": "uuid"  // 日志记录 ID
}
```

**安全考虑**：
- 只允许调用 `access_control.json` 中标记为 `true` 的接口
- 请求必须经过认证
- 记录所有调用日志

### 3. 前端访问状态展示

在接口列表中增加 `accessible` 字段：

| operation_id | name | method | path | accessible |
|--------------|------|--------|------|------------|
| ENC_INP_0001 | 住院就诊信息 | POST | /api/... | ✅ 可访问 |
| PER_BASE_0001 | 患者信息 | POST | /api/... | ❌ 不可访问 |

**颜色约定**：
- 可访问：绿色标签（success）
- 不可访问：灰色标签（info）

### 4. 调用面板设计

在接口详情抽屉中增加"调用测试"Tab：

```
┌─────────────────────────────────────────────┐
│ [基本信息] [请求参数] [响应定义] [调用测试]  │
├─────────────────────────────────────────────┤
│ 请求参数                    [加载默认参数]   │
│ ┌─────────────────────────────────────────┐ │
│ │ {                                       │ │
│ │   "patientId": "12345",                 │ │
│ │   "startDate": "2024-01-01"             │ │
│ │ }                                       │ │
│ └─────────────────────────────────────────┘ │
│                              [发送请求]     │
├─────────────────────────────────────────────┤
│ 响应结果                    耗时: 150ms     │
│ ┌─────────────────────────────────────────┐ │
│ │ 表格展示 / JSON 展示 切换               │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 5. 默认测试参数

从接口定义的 `request_example` 字段获取默认参数，如果不存在则根据 `request_body` schema 生成空模板。

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|----------|
| HIS 接口调用可能超时 | 设置合理超时（30秒），前端显示加载状态 |
| 响应数据可能很大 | 表格展示时支持分页/虚拟滚动 |
| 敏感数据泄露 | 只允许调用已授权接口，记录审计日志 |
| 调用历史数据增长 | 可配置保留天数，定期清理 |

## 文件结构

```
backend-django/core/doc_api/
├── doc_api.py              # 新增 invoke 和 logs API
├── doc_api_service.py      # 新增代理调用逻辑
├── doc_api_model.py        # 新增（调用历史模型）
└── doc_api_schema.py       # 新增调用相关 Schema

web/apps/web-ele/src/views/doc-api/
├── index.vue               # 增加 accessible 列
└── components/
    ├── EndpointDetail.vue  # 增加调用测试 Tab
    ├── InvokePanel.vue     # 新增（调用面板组件）
    └── InvokeHistory.vue   # 新增（调用历史组件）
```

## 待决问题

- 调用历史保留多长时间？（建议：30天，可配置）
- 是否需要导出调用历史？（暂不实现）
