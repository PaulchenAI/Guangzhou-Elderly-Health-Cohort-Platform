# 变更：添加 OpenAPI-Aware Django API 客户端模块

## 为什么

AIagent 需要与 backend-django 后台 API 进行集成，以便智能体能够查询和操作业务数据。backend-django 基于 Django Ninja 框架，原生支持 OpenAPI 规范。通过创建一个 OpenAPI 感知的客户端，AI 可以自动理解 API 结构，无需硬编码即可动态调用任意 API。

## 变更内容

- 新增 `AIagent/src/django_api/` 模块，提供 OpenAPI-Aware 客户端
- 新增 `OpenAPIAwareClient` 类，自动加载和解析 OpenAPI Schema
- 新增 `DjangoAPIAgent` 智能体，集成 LLM 进行意图理解和 API 调用
- 新增 API 端点搜索、意图匹配、通用 API 调用能力
- **新增 RAG 分层检索**：支持大规模 API（>50 端点）的高效检索
  - `APIEndpointIndexer`：API 端点向量索引
  - `HierarchicalRetriever`：三层分层检索（关键词→向量→LLM）
- 新增配置支持（通过 .env 配置 Django API 连接信息）
- 新增 `httpx` 依赖用于异步 HTTP 请求

## 影响

- 受影响规范：`aiagent`（新增 Django API 集成能力）
- 受影响代码：
  - `AIagent/src/django_api/` - 新模块
  - `AIagent/src/utils/config_manager.py` - 新增配置项
  - `AIagent/requirements.txt` - 新增依赖
  - `AIagent/config/settings.yaml` - 新增配置节

## 设计要点

1. **OpenAPI Schema 自动解析**：从 `/api/openapi.json` 获取完整 API 描述
2. **AI 可理解的 API 摘要**：将 Schema 转换为 LLM 可理解的文本描述
3. **三层分层检索**（解决大规模 API 问题）：
   - 第一层：关键词/Tag 快速过滤（成本=0）
   - 第二层：向量语义检索（成本=低，复用现有 RAG 模块）
   - 第三层：LLM 精选（成本=中，仅处理 Top-K 端点）
4. **通用 API 调用**：根据 Schema 自动处理路径参数、查询参数、请求体
5. **Bearer Token 认证**：支持登录获取 Token 并自动附加到请求头
