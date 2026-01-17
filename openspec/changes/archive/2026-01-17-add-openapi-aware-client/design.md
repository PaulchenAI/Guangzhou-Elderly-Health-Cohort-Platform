# 设计文档：OpenAPI-Aware Django API 客户端

## 上下文

### 背景
- AIagent 是一个多智能体 AI 框架，需要与外部系统集成
- backend-django 是基于 Django Ninja 的后台 API，原生支持 OpenAPI 3.0
- 当前 AIagent 没有 HTTP 客户端能力（无 requests/httpx/aiohttp）
- 需要让 AI 能够"读懂"并动态调用 Django API

### 约束
- 必须支持异步调用（与现有 LLM 客户端保持一致）
- 必须支持 Bearer Token 认证（backend-django 的认证方式）
- 应尽量减少硬编码，利用 OpenAPI Schema 实现动态调用

### 利益相关者
- AIagent 开发者：需要简单易用的 API 集成方式
- 业务用户：通过 AI 查询和操作业务数据
- 运维人员：需要可配置的连接参数

## 目标 / 非目标

### 目标
- 自动从 OpenAPI Schema 学习 API 结构
- 生成 AI 可理解的 API 描述
- 支持意图到 API 的智能匹配
- 提供通用的 API 调用能力
- 与现有智能体框架无缝集成

### 非目标
- 不实现完整的 OpenAPI 客户端生成器
- 不支持 OAuth2 等复杂认证流程（当前只需 Bearer Token）
- 不实现 API 响应的自动类型转换
- 不处理文件上传/下载等特殊场景

## 决策

### 决策 1：使用 httpx 作为 HTTP 客户端

**选择**：httpx

**理由**：
- 原生支持异步（async/await）
- API 与 requests 兼容，学习成本低
- 支持 HTTP/2
- 活跃维护，社区支持好

**考虑的替代方案**：
- `requests`：不支持原生异步，需要配合 asyncio 使用
- `aiohttp`：API 不够直观，与 requests 差异大
- `urllib3`：太底层，需要更多封装

### 决策 2：OpenAPI Schema 解析策略

**选择**：轻量级自定义解析

**理由**：
- 只需要提取 paths、operations、parameters 等核心信息
- 避免引入重量级 OpenAPI 库（如 openapi-core）
- 可以针对 AI 理解进行优化转换

**考虑的替代方案**：
- `openapi-core`：功能完整但过于复杂
- `prance`：主要用于 Schema 验证，不适合客户端场景

### 决策 3：意图匹配策略（含 RAG）

**选择**：三层分层检索（关键词 + RAG + LLM）

**理由**：
- 关键词匹配：快速、低成本、适合简单场景
- RAG 向量检索：语义理解、处理大规模 API（>50 个端点）
- LLM 精选：智能、准确、最终决策
- 分层设计兼顾性能和准确性

**实现**：
```
用户意图: "查询护理人员信息"
         ↓
┌────────────────────────────────────┐
│ 第一层：关键词/Tag 过滤（成本=0）    │
│ - 匹配 tag: "用户管理", "人员"       │
│ - 匹配 path: /user, /staff          │
│ - 结果: ~20 个候选端点               │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ 第二层：RAG 向量检索（成本=低）      │
│ - 查询向量化                        │
│ - 与候选端点向量计算相似度           │
│ - 返回 Top-K（默认 10）             │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│ 第三层：LLM 精选（成本=中）         │
│ - 将 Top-K 端点描述放入 context     │
│ - LLM 理解意图选择最匹配的 API      │
│ - 返回最终选择 + 参数构造           │
└────────────────────────────────────┘
         ↓
    最匹配的 API 端点
```

**性能对比**：

| 端点数量 | 纯 LLM | 分层检索 + LLM |
|---------|--------|---------------|
| 50 | 2000 tokens | 500 tokens |
| 200 | 8000 tokens | 500 tokens |
| 500 | 超出限制 | 500 tokens |

**考虑的替代方案**：
- 纯 LLM：所有 API 放入 context，超过 50 个端点时不可行
- 纯关键词：无法处理语义相关但关键词不匹配的情况

### 决策 4：配置管理

**选择**：复用现有配置系统

**理由**：
- 与 LLM 配置保持一致的体验
- 支持 .env 环境变量覆盖
- 支持 YAML 默认值

**配置项**：
```yaml
django_api:
  base_url: "http://localhost:8000"
  username: ""
  password: ""
  timeout: 30
```

## 架构设计

### 模块结构

```
AIagent/src/django_api/
├── __init__.py           # 模块导出
├── client.py             # OpenAPIAwareClient 核心类
├── models.py             # 数据模型（APIEndpoint, DjangoAPIConfig）
├── indexer.py            # APIEndpointIndexer 向量索引
├── retriever.py          # HierarchicalRetriever 分层检索
└── agent.py              # DjangoAPIAgent 智能体
```

### 类图

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenAPIAwareClient                        │
├─────────────────────────────────────────────────────────────┤
│ - config: DjangoAPIConfig                                   │
│ - access_token: str                                         │
│ - _client: httpx.AsyncClient                                │
│ - _endpoints: Dict[str, APIEndpoint]                        │
│ - _endpoints_by_tag: Dict[str, List[APIEndpoint]]           │
│ - _schema: Dict                                             │
├─────────────────────────────────────────────────────────────┤
│ + load_openapi_schema() -> Dict                             │
│ + get_api_summary_for_ai() -> str                           │
│ + get_endpoints_by_keyword(keyword) -> List[APIEndpoint]    │
│ + find_endpoint(intent) -> APIEndpoint                      │
│ + login() -> bool                                           │
│ + call_api(endpoint, params) -> Dict                        │
│ + call_by_intent(intent, params) -> Dict                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      APIEndpoint                             │
├─────────────────────────────────────────────────────────────┤
│ + path: str                                                 │
│ + method: str                                               │
│ + operation_id: str                                         │
│ + summary: str                                              │
│ + description: str                                          │
│ + tags: List[str]                                           │
│ + parameters: List[Dict]                                    │
│ + request_body: Dict                                        │
├─────────────────────────────────────────────────────────────┤
│ + to_ai_description() -> str                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    DjangoAPIAgent                            │
├─────────────────────────────────────────────────────────────┤
│ - api_client: OpenAPIAwareClient                            │
│ - retriever: HierarchicalRetriever                          │
│ - llm_client: BaseLLMClient                                 │
├─────────────────────────────────────────────────────────────┤
│ + initialize() -> None                                      │
│ + get_system_prompt(relevant_apis) -> str                   │
│ + process_query(query) -> Dict                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  APIEndpointIndexer                          │
├─────────────────────────────────────────────────────────────┤
│ - embeddings: Embeddings                                    │
│ - vectorstore: VectorStore                                  │
├─────────────────────────────────────────────────────────────┤
│ + build_index(endpoints) -> None                            │
│ + search(query, top_k) -> List[APIEndpoint]                 │
│ + update_index(endpoints) -> None                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 HierarchicalRetriever                        │
├─────────────────────────────────────────────────────────────┤
│ - endpoints: Dict[str, APIEndpoint]                         │
│ - indexer: APIEndpointIndexer                               │
├─────────────────────────────────────────────────────────────┤
│ + retrieve(query, top_k) -> List[APIEndpoint]               │
│ - _keyword_filter(query) -> List[APIEndpoint]               │
│ - _semantic_search(query, candidates) -> List[APIEndpoint]  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

```
1. 初始化流程：
   Client 创建 → load_openapi_schema() → _parse_schema() → build_index() → 就绪

2. API 调用流程（简单场景，<50 端点）：
   用户意图 → find_endpoint() → call_api() → HTTP 请求 → 响应

3. 智能体流程（复杂场景，支持 RAG）：
   用户查询 
       → HierarchicalRetriever.retrieve()
           → 关键词过滤 → 向量检索 → Top-K 端点
       → get_system_prompt(Top-K 端点)
       → LLM 选择最匹配的 API
       → call_api() → 结果

4. 向量索引流程：
   APIEndpoint → to_ai_description() → Embedding → VectorStore
```

## 风险 / 权衡

### 风险 1：OpenAPI Schema 格式变化
- **风险**：Django Ninja 版本升级可能改变 Schema 格式
- **缓解**：使用宽松解析，对缺失字段提供默认值

### 风险 2：API 认证 Token 过期
- **风险**：长时间运行时 Token 可能过期
- **缓解**：实现 Token 刷新机制（使用 refresh_token）

### 风险 3：意图匹配准确性
- **风险**：关键词匹配可能不够准确
- **缓解**：提供 LLM 辅助匹配作为后备

### 权衡：简单性 vs 完整性
- **选择**：优先简单性
- **理由**：先实现核心功能，后续按需扩展

## 迁移计划

无需迁移，这是新增功能。

## 待决问题

1. **是否需要支持 API Key 认证？**
   - backend-django 同时支持 Bearer Token 和 API Key
   - 当前设计只实现 Bearer Token，后续可扩展

2. **是否需要缓存 OpenAPI Schema？**
   - 当前每次初始化都重新加载
   - 如果 Schema 较大，可考虑本地缓存

3. **如何处理 API 错误响应？**
   - 当前简单抛出异常
   - 可考虑封装为统一的错误类型
