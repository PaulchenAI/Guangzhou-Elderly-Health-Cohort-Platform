# api-doc-extractor Specification

## Purpose
TBD - created by archiving change add-docx-openapi-extractor. Update Purpose after archive.
## 需求
### 需求：DOCX 文档导出 OpenAPI 3.x JSON

系统必须支持将输入的 Word（`.docx`）接口规范文档解析为 **OpenAPI 3.x** 规范的 JSON 输出。

#### 场景：导出成功（最小接口信息）

- **当** 用户提供一个 `.docx` 接口文档路径
- **并且** 文档中存在可识别的接口定义（至少包含接口名称、HTTP 方法、path）
- **那么** 系统必须生成一个 OpenAPI 3.x JSON
- **并且** OpenAPI 中每个被识别的接口必须包含：
  - `paths` 下对应的 `path` 节点
  - `path` 下对应 `method`（GET/POST/PUT/DELETE/PATCH 等）
  - `operation.summary` 或 `operation.description`（至少一个）

#### 场景：导出失败（缺少关键字段）

- **当** 系统无法从文档中解析出任一接口的 HTTP 方法或 path
- **那么** 系统必须以失败结束（非静默忽略）
- **并且** 返回/输出错误报告，指出缺失字段类型（method/path）以及相关文档定位线索

---

### 需求：入参/出参映射到 OpenAPI Schema

系统必须将文档中的入参/出参表（字段名、类型、必填、说明等）映射为 OpenAPI 的参数与 schema 定义。

#### 场景：解析并生成请求参数（Query/Path）

- **当** 文档为某接口提供了入参字段列表
- **并且** 字段来源可识别为查询参数或路径参数（例如字段名出现在 path 模板中）
- **那么** 系统必须在对应 `operation.parameters` 中生成参数定义
- **并且** 必须包含字段名、类型、必填标识与说明

#### 场景：解析并生成请求体（JSON Body）

- **当** 文档为某接口提供了入参字段列表
- **并且** 字段来源被识别为请求体
- **那么** 系统必须生成 `operation.requestBody`（默认 content-type 为 `application/json`）
- **并且** requestBody schema 必须包含字段类型与字段说明

#### 场景：解析并生成响应结构

- **当** 文档为某接口提供了出参字段列表
- **那么** 系统必须在 `operation.responses` 中生成至少一个成功响应（如 `200`）
- **并且** 响应 schema 必须包含字段类型与字段说明

---

### 需求：示例请求与响应导出为 OpenAPI Examples

系统必须从文档中提取示例请求/响应，并导出为 OpenAPI 的 `examples` 或 `example` 字段，以提升机器可验证性与可读性。

#### 场景：导出示例请求

- **当** 文档包含某接口的请求示例（例如 JSON、表单字段、URL 示例）
- **那么** 系统必须将示例写入 OpenAPI
- **并且** 对于 `application/json`，示例必须写入 `requestBody.content['application/json'].example` 或 `examples`

#### 场景：导出示例响应

- **当** 文档包含某接口的响应示例（例如 JSON 响应体）
- **那么** 系统必须将示例写入 OpenAPI 的 `responses[status].content['application/json'].example` 或 `examples`

---

### 需求：OpenAPI 结构校验与错误报告

系统必须在输出前对生成的 OpenAPI JSON 做结构校验，并在失败时提供可操作的错误信息。

#### 场景：校验通过

- **当** 系统生成 OpenAPI 3.x JSON
- **那么** 系统必须通过 OpenAPI 结构校验
- **并且** 输出文件应被写入到用户指定位置

#### 场景：校验失败

- **当** 生成的 OpenAPI JSON 不满足 OpenAPI 3.x 结构要求
- **那么** 系统必须中止导出（或标记输出为无效）
- **并且** 错误报告必须包含：失败原因、涉及的接口/字段、以及来源片段/定位线索

---

### 需求：命令行导出接口（CLI）

系统必须提供命令行工具支持从 `.docx` 导出 OpenAPI 3.x JSON，便于集成到开发与 CI 流程。

#### 场景：命令行导出

- **当** 用户执行导出命令并提供输入 `.docx` 路径与输出文件路径
- **那么** 系统必须生成 OpenAPI 3.x JSON 并写入输出路径
- **并且** 命令行必须支持输出解析报告（成功/失败接口统计）

