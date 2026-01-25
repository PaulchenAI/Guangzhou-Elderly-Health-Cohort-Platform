# doc-api Specification

## Purpose
提供后台 API 接口，支持查询从 Word 文档解析生成的 OpenAPI JSON 文档信息，包括接口列表、接口详情、接口搜索等功能。

## 新增需求

### 需求：文档接口列表查询

系统必须提供 API 接口，支持查询所有文档接口的列表信息。

#### 场景：获取所有接口列表

- **当** 调用 `GET /api/core/doc-api/endpoints`
- **那么** 系统必须返回所有接口的列表
- **并且** 每个接口必须包含以下信息：
  - `operation_id`：接口操作 ID
  - `name`：接口名称
  - `method`：HTTP 方法（GET/POST/PUT/DELETE 等）
  - `path`：接口路径
  - `summary`：接口摘要（如果有）
- **并且** 响应格式必须为：
  ```json
  {
    "total": 84,
    "items": [
      {
        "operation_id": "PER_BASE_0001",
        "name": "患者信息接口",
        "method": "POST",
        "path": "/dcp-inex-invoke/api/v1/invoke/market_api/PER_BASE_0001/v1/service",
        "summary": "患者信息接口"
      }
    ]
  }
  ```

#### 场景：支持分页查询

- **当** 调用 `GET /api/core/doc-api/endpoints?page=1&page_size=20`
- **那么** 系统必须返回分页结果
- **并且** 响应必须包含分页信息：
  - `total`：总记录数
  - `page`：当前页码
  - `page_size`：每页数量
  - `items`：当前页数据列表

#### 场景：文件不存在时返回错误

- **当** 系统无法找到 `docs/his/openapi.json` 文件
- **那么** 系统必须返回 404 错误
- **并且** 错误消息必须说明文件不存在

---

### 需求：文档接口详情查询

系统必须提供 API 接口，支持查询指定接口的详细信息。

#### 场景：获取接口详情

- **当** 调用 `GET /api/core/doc-api/endpoints/{operation_id}`
- **并且** `operation_id` 对应的接口存在
- **那么** 系统必须返回接口的完整信息
- **并且** 响应必须包含：
  - 接口基本信息（operation_id、name、method、path、summary、description）
  - 请求参数信息（parameters、requestBody）
  - 响应信息（responses）
  - 示例数据（如果有）

#### 场景：接口不存在时返回 404

- **当** 调用 `GET /api/core/doc-api/endpoints/{operation_id}`
- **并且** `operation_id` 对应的接口不存在
- **那么** 系统必须返回 404 错误
- **并且** 错误消息必须说明接口不存在

---

### 需求：文档接口搜索

系统必须提供 API 接口，支持按条件搜索文档接口。

#### 场景：按名称搜索接口

- **当** 调用 `POST /api/core/doc-api/endpoints/search`
- **并且** 请求体包含 `name` 参数（支持模糊匹配）
- **那么** 系统必须返回名称匹配的接口列表
- **并且** 支持部分匹配（如"患者"可匹配"患者信息接口"）

#### 场景：按路径搜索接口

- **当** 调用 `POST /api/core/doc-api/endpoints/search`
- **并且** 请求体包含 `path` 参数（支持模糊匹配）
- **那么** 系统必须返回路径匹配的接口列表

#### 场景：按方法筛选接口

- **当** 调用 `POST /api/core/doc-api/endpoints/search`
- **并且** 请求体包含 `method` 参数（如 "POST"）
- **那么** 系统必须返回指定 HTTP 方法的接口列表

#### 场景：组合条件搜索

- **当** 调用 `POST /api/core/doc-api/endpoints/search`
- **并且** 请求体包含多个搜索条件（如 `name`、`method`、`path`）
- **那么** 系统必须返回同时满足所有条件的接口列表
- **并且** 支持分页查询

---

### 需求：文档摘要信息查询

系统必须提供 API 接口，支持查询文档的摘要统计信息。

#### 场景：获取文档摘要

- **当** 调用 `GET /api/core/doc-api/summary`
- **那么** 系统必须返回文档摘要信息
- **并且** 响应必须包含：
  - `title`：文档标题
  - `version`：文档版本
  - `endpoint_count`：接口总数
  - `issue_count`：问题数量（如果有）
  - `openapi_error_count`：OpenAPI 错误数量（如果有）

#### 场景：摘要信息来自 report.json

- **当** 系统读取文档摘要信息时
- **那么** 系统必须优先从 `docs/his/report.json` 读取
- **并且** 如果 `report.json` 不存在，则从 `openapi.json` 的 `info` 字段提取基本信息

---

### 需求：本地文件数据源

系统必须支持从本地文件系统读取文档数据。

#### 场景：从本地文件读取 OpenAPI 数据

- **当** 系统需要获取接口数据时
- **并且** 未配置外部文档 API URL（`DOC_API_URL` 为空）
- **那么** 系统必须从 `docs/his/openapi.json` 读取数据
- **并且** 文件路径必须相对于项目根目录或 `settings.BASE_DIR`

#### 场景：从本地文件读取报告数据

- **当** 系统需要获取文档摘要时
- **并且** 未配置外部文档 API URL
- **那么** 系统必须从 `docs/his/report.json` 读取数据
- **并且** 如果文件不存在，则从 `openapi.json` 提取基本信息

#### 场景：文件读取缓存

- **当** 系统读取本地文件数据时
- **那么** 系统必须实现缓存机制
- **并且** 缓存时间至少为 5 分钟
- **并且** 文件修改后缓存必须自动失效

---

### 需求：外部文档 API 数据源（可选）

系统必须支持从外部文档服务 API 查询数据（如果配置了外部服务 URL）。

#### 场景：从外部 API 读取数据

- **当** 系统配置了 `DOC_API_URL` 环境变量
- **那么** 系统必须优先使用外部 API 获取数据
- **并且** 请求必须包含认证 Token（如果配置了 `DOC_API_TOKEN`）
- **并且** 请求头必须包含 `Authorization: Bearer {token}`

#### 场景：外部 API 失败时降级到本地文件

- **当** 系统配置了外部 API URL
- **并且** 外部 API 请求失败（网络错误、超时、认证失败等）
- **那么** 系统必须自动降级到使用本地文件
- **并且** 记录错误日志

#### 场景：外部 API 请求超时

- **当** 系统调用外部 API 时
- **那么** 请求超时时间必须设置为 30 秒
- **并且** 超时后必须触发降级策略

---

### 需求：环境变量配置

系统必须支持通过环境变量配置文档 API 相关参数。

#### 场景：配置文档 API URL

- **当** 在 `.env` 文件中配置 `DOC_API_URL` 环境变量
- **那么** 系统必须从该 URL 读取文档数据
- **并且** 如果未配置，则使用本地文件作为数据源

#### 场景：配置文档 API Token

- **当** 在 `.env` 文件中配置 `DOC_API_TOKEN` 环境变量
- **并且** 系统使用外部 API 时
- **那么** 系统必须在请求头中包含该 Token
- **并且** Token 格式为 `Bearer {token}`

#### 场景：环境变量为可选

- **当** 系统启动时
- **那么** `DOC_API_URL` 和 `DOC_API_TOKEN` 必须为可选配置
- **并且** 未配置时系统必须能够正常工作（使用本地文件）

---

### 需求：API 接口规范

所有文档 API 接口必须遵循项目的 API 开发规范。

#### 场景：使用中文 Summary

- **当** 定义文档 API 接口时
- **那么** 所有接口的 `summary` 参数必须使用中文
- **并且** 格式为 "动词 + 名词（补充说明）"

**示例**：
```python
@router.get("/endpoints", summary="获取文档接口列表（分页）")
@router.get("/endpoints/{operation_id}", summary="获取文档接口详情")
@router.post("/endpoints/search", summary="搜索文档接口")
@router.get("/summary", summary="获取文档摘要信息")
```

#### 场景：提供详细的 Description

- **当** 定义文档 API 接口时
- **那么** 所有接口必须提供详细的 `description`
- **并且** 说明参数、返回值和使用方式

#### 场景：使用统一的 Tags

- **当** 注册文档 API 路由时
- **那么** 必须使用统一的 tags（如 `Core-DocAPI`）
- **并且** 与项目其他模块的 tags 命名规范保持一致
