# 变更：添加文档 API 查询接口

## 为什么

当前系统已经通过 `api-doc-extractor` 工具将 Word 文档解析为 OpenAPI JSON 格式，并存储在 `docs/his` 目录中。为了支持通过后台 API 查询这些文档接口信息，需要：

1. 提供统一的 API 接口供前端或其他系统查询文档接口信息
2. 支持从外部文档服务查询接口（如果文档服务提供 API）
3. 将文档服务的配置（token 和 url）统一管理在 backend 的 `.env` 文件中

## 变更内容

- **新增**：文档 API 查询模块（`core/doc_api/`）
  - 提供查询 OpenAPI JSON 文档的 API 接口
  - 支持查询接口列表、接口详情、接口搜索等功能
  - 支持从本地文件系统读取 `docs/his/openapi.json` 和 `docs/his/report.json`
  - 支持从外部文档服务 API 查询（如果配置了外部服务 URL）

- **新增**：文档 API 客户端（`core/doc_api/doc_api_client.py`）
  - 封装与外部文档服务 API 的通信逻辑
  - 支持 Token 认证
  - 处理请求超时和错误重试

- **新增**：环境变量配置
  - `DOC_API_URL`：文档服务 API 地址（可选，如果为空则仅从本地文件读取）
  - `DOC_API_TOKEN`：文档服务 API 认证 Token（可选）

- **新增**：API 路由
  - `GET /api/core/doc-api/endpoints`：获取所有接口列表
  - `GET /api/core/doc-api/endpoints/{operation_id}`：获取指定接口详情
  - `POST /api/core/doc-api/endpoints/search`：搜索接口
  - `GET /api/core/doc-api/summary`：获取文档摘要信息

## 影响

- **受影响规范**：
  - `backend-api`：新增文档 API 查询相关接口规范
  - `api-doc-extractor`：无变更，仅作为数据源使用

- **受影响代码**：
  - 新增模块：`backend-django/core/doc_api/`
  - 环境配置：`backend-django/.env`（需要添加新配置项）
  - 路由注册：需要在主路由中注册新的 doc-api 路由

- **依赖关系**：
  - 依赖 `docs/his/openapi.json` 和 `docs/his/report.json` 文件存在
  - 如果使用外部文档服务，需要外部服务可访问
