## 1. 实施

- [x] 1.1 创建文档 API 模块目录结构
  - [x] 创建 `backend-django/core/doc_api/` 目录
  - [x] 创建 `__init__.py` 文件
  - [x] 创建 `doc_api_service.py`（业务逻辑层，包含外部 API 客户端功能）
  - [x] 创建 `doc_api_schema.py`（Pydantic Schema 定义）
  - [x] 创建 `doc_api.py`（Django Ninja Router）

- [x] 1.2 实现文档数据读取服务
  - [x] 实现从本地文件读取 `docs/his/openapi.json`
  - [x] 实现从本地文件读取 `docs/his/report.json`
  - [x] 实现数据缓存机制（避免频繁读取文件）
  - [x] 处理文件不存在或格式错误的情况

- [x] 1.3 实现外部文档 API 客户端（可选）
  - [x] 实现从环境变量读取 `DOC_API_URL` 和 `DOC_API_TOKEN`
  - [x] 预留 HTTP 请求封装接口（支持 Token 认证）
  - [x] 实现请求超时和错误处理
  - [x] 实现数据缓存机制

- [x] 1.4 实现 API 接口
  - [x] 实现 `GET /api/core/doc-api/endpoints`（获取接口列表）
  - [x] 实现 `GET /api/core/doc-api/endpoints/{operation_id}`（获取接口详情）
  - [x] 实现 `POST /api/core/doc-api/endpoints/search`（搜索接口）
  - [x] 实现 `GET /api/core/doc-api/summary`（获取文档摘要）

- [x] 1.5 定义 Schema
  - [x] 定义 `DocEndpointSchemaOut`（接口信息输出）
  - [x] 定义 `DocEndpointDetailSchemaOut`（接口详情输出）
  - [x] 定义 `DocEndpointSearchIn`（搜索输入）
  - [x] 定义 `DocSummarySchemaOut`（文档摘要输出）

- [x] 1.6 注册路由
  - [x] 在主路由文件中注册 `doc_api` 路由
  - [x] 设置正确的 tags（`Core-DocAPI`, `文档API查询`）

- [x] 1.7 更新环境变量配置
  - [x] 在 `env/dev_env.py` 中添加 `DOC_API_URL` 和 `DOC_API_TOKEN` 配置说明

## 2. 测试

- [ ] 2.1 单元测试
  - [ ] 测试本地文件读取功能
  - [ ] 测试数据解析和格式化
  - [ ] 测试错误处理（文件不存在、格式错误等）

- [ ] 2.2 API 测试
  - [ ] 测试接口列表查询
  - [ ] 测试接口详情查询
  - [ ] 测试接口搜索功能
  - [ ] 测试文档摘要查询
  - [ ] 测试错误场景（接口不存在、参数错误等）

- [ ] 2.3 集成测试（如果使用外部 API）
  - [ ] 测试外部 API 连接
  - [ ] 测试 Token 认证
  - [ ] 测试请求超时和重试

## 3. 文档

- [x] 3.1 API 文档
  - [x] 确保所有接口都有正确的中文 summary
  - [x] 确保所有接口都有详细的 description
  - [ ] 验证 Swagger UI 中接口文档显示正确

- [ ] 3.2 开发文档
  - [x] 更新环境变量配置说明
  - [ ] 添加文档 API 使用示例
