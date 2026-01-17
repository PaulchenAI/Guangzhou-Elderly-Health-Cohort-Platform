# 任务清单

## 1. 基础设施

- [x] 1.1 在 `requirements.txt` 中添加 `httpx>=0.25.0` 依赖
- [x] 1.2 创建 `AIagent/src/django_api/` 目录结构
- [x] 1.3 在 `config/settings.yaml` 中添加 Django API 配置节

## 2. 核心客户端实现

- [x] 2.1 实现 `DjangoAPIConfig` 数据类（配置模型）
- [x] 2.2 实现 `APIEndpoint` 数据类（API 端点描述）
- [x] 2.3 实现 `OpenAPIAwareClient` 核心类
  - [x] 2.3.1 `load_openapi_schema()` - 加载 OpenAPI Schema
  - [x] 2.3.2 `_parse_schema()` - 解析 Schema 构建端点索引
  - [x] 2.3.3 `get_api_summary_for_ai()` - 生成 AI 可理解的摘要
  - [x] 2.3.4 `get_endpoints_by_keyword()` - 关键词搜索 API
  - [x] 2.3.5 `find_endpoint()` - 意图匹配 API
  - [x] 2.3.6 `login()` - 登录获取 Token
  - [x] 2.3.7 `call_api()` - 通用 API 调用
  - [x] 2.3.8 `call_by_intent()` - 根据意图调用 API
  - [x] 2.3.9 `call_api_by_path()` - 按路径直接调用 API

## 3. RAG 检索支持（大规模 API）

- [x] 3.1 实现 `APIEndpointIndexer` 向量索引类
  - [x] 3.1.1 `build_index()` - 为 API 端点构建向量索引
  - [x] 3.1.2 `search()` - 向量相似度检索
  - [x] 3.1.3 `update_index()` - 增量更新索引
- [x] 3.2 实现分层检索策略 `HierarchicalRetriever`
  - [x] 3.2.1 第一层：tag/关键词快速过滤
  - [x] 3.2.2 第二层：向量语义检索
  - [x] 3.2.3 结果融合与排序
- [x] 3.3 集成现有 RAG 模块（复用 `src/rag/`）

## 4. 智能体集成

- [x] 4.1 实现 `DjangoAPIAgent` 智能体类
  - [x] 4.1.1 `initialize()` - 初始化（加载 Schema、构建索引、登录）
  - [x] 4.1.2 `get_system_prompt()` - 生成系统提示词（仅包含检索到的 API）
  - [x] 4.1.3 `process_query()` - 处理用户查询（分层检索 + LLM 选择）
- [x] 4.2 在 `agents/__init__.py` 中导出新智能体

## 5. 配置集成

- [x] 5.1 在 `config_models.py` 中添加 `DjangoAPIConfig` 模型
- [x] 5.2 在 `config_manager.py` 中添加 `get_django_api_config()` 方法
- [x] 5.3 支持 `.env` 环境变量配置
- [x] 5.4 添加 RAG 检索相关配置（top_k、相似度阈值等）

## 6. 测试验证

- [x] 6.1 编写 `test_openapi_client.py` 单元测试
- [x] 6.2 测试 OpenAPI Schema 加载和解析
- [x] 6.3 测试 API 端点搜索和意图匹配
- [x] 6.4 测试 RAG 向量检索功能
- [x] 6.5 测试登录和 API 调用（需要 backend-django 运行）

## 7. 文档

- [x] 7.1 更新 `AIagent/README.md` 添加 Django API 集成说明
- [x] 7.2 添加使用示例代码
- [x] 7.3 添加 RAG 检索配置说明

## 8. 命令行工具 (CLI)

- [x] 8.1 实现 `cli.py` 命令行工具模块
  - [x] 8.1.1 `info` - 显示 API 信息
  - [x] 8.1.2 `login` - 测试登录
  - [x] 8.1.3 `search` - 搜索 API 端点
  - [x] 8.1.4 `call` - 根据意图调用 API
  - [x] 8.1.5 `summary` - 生成 AI 摘要
  - [x] 8.1.6 `list-tags` - 列出所有 Tag
  - [x] 8.1.7 `list-endpoints` - 列出所有端点
  - [x] 8.1.8 `generate` - 生成多步骤查询脚本
- [x] 8.2 创建 `__main__.py` 入口文件
- [x] 8.3 更新 `__init__.py` 导出 CLI
- [x] 8.4 更新 `README.md` 添加 CLI 使用文档

## 9. LangGraph 脚本生成器

- [x] 9.1 实现 `script_generator.py` 脚本生成器模块
  - [x] 9.1.1 `plan_intent()` - LLM 意图拆解，生成执行计划
  - [x] 9.1.2 `generate_script()` - 根据计划生成 Python 脚本
  - [x] 9.1.3 `execute_script()` - 执行生成的脚本
  - [x] 9.1.4 `validate_result()` - LLM 验证执行结果
  - [x] 9.1.5 `debug_and_decide()` - 调试并决定是否迭代
- [x] 9.2 构建 LangGraph 工作流
  - [x] 9.2.1 定义 `ScriptGeneratorState` 状态类型
  - [x] 9.2.2 连接节点：plan → generate → execute → validate → debug
  - [x] 9.2.3 实现条件边：失败时重新生成

## 10. 脚本生成器改进（步骤验证）

- [x] 10.1 增加默认迭代次数到 10
- [x] 10.2 添加 `validate_steps()` 节点 - 直接调用 API 验证执行计划
  - [x] 10.2.1 在生成脚本前先执行每个 API 步骤
  - [x] 10.2.2 记录实际的输入输出（响应字段、数据量、样例数据）
  - [x] 10.2.3 检测 API 路径和参数是否正确
- [x] 10.3 添加 `fix_execution_plan()` 节点 - 修正执行计划
  - [x] 10.3.1 如果步骤验证失败，使用 LLM 修正计划
  - [x] 10.3.2 限制最大修正次数（2 次）防止无限循环
- [x] 10.4 改进 `generate_script()` - 将步骤验证的输入输出加入上下文
- [x] 10.5 更新工作流：plan → validate_steps → (fix_plan?) → generate → execute → validate → debug
- [x] 10.6 更新 CLI 显示步骤验证结果
  - [x] 10.6.1 显示每个步骤的输入、输出、状态
  - [x] 10.6.2 显示样例数据和数据字段
  - [x] 10.6.3 显示计划修正次数

## 依赖关系

- 任务 2 依赖任务 1 完成
- 任务 3（RAG）依赖任务 2 完成，可复用现有 `src/rag/` 模块
- 任务 4（智能体）依赖任务 2、3 完成
- 任务 5 可与任务 2 并行
- 任务 6 依赖任务 2、3、4、5 完成
- 任务 7 可在任务 6 之后或并行进行
- 任务 9 依赖任务 2、8 完成
- 任务 10 依赖任务 9 完成