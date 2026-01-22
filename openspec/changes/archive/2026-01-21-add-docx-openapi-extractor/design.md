## 上下文

本变更旨在将存量 Word（`.docx`）接口规范文档解析为 **OpenAPI 3.x JSON**，并覆盖：

- A：接口基本信息（接口名称/说明、HTTP method、path）
- B：入参/出参（字段名、类型、必填、说明等，映射为 OpenAPI parameters / requestBody / responses schema）
- C：示例请求/响应（映射为 OpenAPI examples）

项目已有 OpenAPI 相关规范（`openspec/specs/backend-api/spec.md`）与 OpenAPI-Aware 客户端（`openspec/specs/aiagent/spec.md` 中的 Django API 集成）。本能力关注 **“从 DOCX 生成 OpenAPI”**，用于补足“文档来源不是 OpenAPI 时的结构化导入”链路。

## 目标 / 非目标

**目标：**
- 输入 `.docx` 文档，输出符合 OpenAPI 3.x 结构的 JSON。
- 对每个接口尽量提取 method/path、入参/出参、示例请求/响应。
- 输出可用于后续工具链（Swagger UI、代码生成、AI 调用编排等）。
- 对解析失败/缺字段提供可操作的错误报告，便于人工修订源文档或补充规则。

**非目标：**
- 不保证一次性把文档中的所有业务语义都结构化（例如字段枚举含义、复杂约束推导）。
- 不在本变更中实现与后端代码的自动对齐（例如对比实际路由并生成 diff）。
- 不在本变更中支持除 `.docx` 以外的格式（如 PDF、图片）；后续可扩展。

## 决策

### 决策：解析策略采用“确定性优先 + LLM 可选兜底”

原因：接口文档通常包含表格与固定栏目（例如“接口名称/入参/出参/示例”），适合用确定性解析拿到稳定结构；但也会出现格式不一致、段落混排、字段缺失等情况，LLM 可作为可配置兜底，提升覆盖率。

**原则：**
- 默认不将整份文档发送给 LLM；仅对局部片段（某接口块）进行辅助解析。
- LLM 辅助仅用于结构识别/补全建议；最终输出仍需通过 OpenAPI 结构校验。

### 决策：引入中间模型，避免 DOCX 结构直接耦合 OpenAPI

建立 `IntermediateSpec`（建议命名）：
- `DocumentSpec`：文档级元信息（标题、版本、服务名等）
- `EndpointSpec`：接口级信息（name、operationId、method、path、summary/description）
- `SchemaSpec`：请求/响应 schema（对象、数组、基本类型）
- `ExampleSpec`：示例请求/响应（按 content-type 分类）

好处：
- 解析与生成解耦，后续可扩展更多输入格式或输出格式（仍保持本变更范围内只做 OpenAPI）。
- 更容易做单元测试（固定中间模型断言）。

### 决策：表格解析规则最小化，类型映射可配置

文档中的“类型”字段可能是：
- 语言类型（string/int/long/boolean）
- 数据库类型（VARCHAR/NUMBER）
- 业务类型（code/name 等）

因此类型映射采取：
- 默认映射到 OpenAPI 基本类型（string/integer/number/boolean/object/array）
- 对未知类型降级为 `string` 并保留原始类型到 `description`/`x-original-type`
- 支持配置文件补充映射（不在本提案中规定具体配置格式，实施阶段按最小实现落地）

## 风险 / 权衡

- **风险：DOCX 格式变化** → 缓解：分层解析（标题/段落/表格），并用“接口块”启发式识别；提供失败定位报告。
- **风险：示例混杂** → 缓解：示例提取按 “请求示例/响应示例/示例” 标记 + 代码块样式/JSON 解析尝试组合。
- **权衡：LLM 调用成本与隐私** → 缓解：默认关闭或低频；仅发送最小片段；对文本做简单脱敏（如身份证号/手机号模式）可作为后续增强。

## 产出物（实施阶段）

- `openapi.json`：OpenAPI 3.x JSON 输出
- `report.json` / `report.md`（建议）：解析报告（成功/失败接口、缺失字段、定位线索）

## 待决问题

- [ ] 文档中的“接口编号”（如 `PER_OUTP_0004`）是否应作为 OpenAPI `operationId` 的主来源？若缺失，使用何种生成策略（例如 method+path 或接口名称拼音化）。
- [ ] 文档是否包含统一的 basePath/host 信息？若没有，OpenAPI `servers` 如何填充（留空/从配置读取）。

