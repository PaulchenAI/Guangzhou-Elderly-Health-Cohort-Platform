# 任务清单：多智能体AI框架

## 1. 项目初始化
- [x] 1.1 创建AIagent目录结构
- [x] 1.2 创建requirements.txt（依赖管理）
- [x] 1.3 创建setup.py（包配置）
- [x] 1.4 创建README.md（使用说明）
- [x] 1.5 创建.env.example（环境变量模板，包含Claude Code CLI配置）
- [x] 1.6 创建.gitignore（排除.env等敏感文件）

## 2. 配置系统
- [x] 2.1 实现.env环境变量加载器（env_loader.py）
- [x] 2.2 实现YAML配置加载器（config_loader.py）
- [x] 2.3 创建settings.yaml（全局配置模板）
- [x] 2.4 创建agents.yaml（智能体配置）
- [x] 2.5 创建Prompts模板目录和初始模板
  - [x] orchestrator.yaml
  - [x] rag.yaml
  - [x] memory.yaml
  - [x] planning.yaml
- [x] 2.6 实现配置验证（Pydantic Settings Schema）
- [x] 2.7 实现配置优先级合并（系统env > .env > yaml）

## 3. 日志系统
- [x] 3.1 实现核心日志记录器（logger.py）
- [x] 3.2 实现日志处理器（文件、控制台）
- [x] 3.3 实现日志格式化器（JSON、文本）
- [x] 3.4 添加Claude Code CLI调用追踪装饰器
- [x] 3.5 添加智能体交互日志记录

## 4. Claude Code CLI核心封装（优先级最高）
- [x] 4.1 实现Claude Code客户端（claude_code/client.py）
  - [x] CLI路径验证和可用性检查
  - [x] 基础命令封装
- [x] 4.2 实现命令执行器（claude_code/executor.py）
  - [x] 异步subprocess调用
  - [x] 超时控制
  - [x] 并发控制（信号量）
  - [x] 错误处理和重试
- [x] 4.3 实现输出解析器（claude_code/parser.py）
  - [x] JSON输出解析
  - [x] 错误信息提取
- [x] 4.4 实现文件操作接口
  - [x] read_file() - 读取文件
  - [x] write_file() - 写入文件
  - [x] edit_file() - 编辑文件
  - [x] search_files() - 文件搜索（glob）
  - [x] grep() - 内容搜索（正则）
  - [x] list_dir() - 目录列表
- [x] 4.5 实现Coding能力接口
  - [x] analyze_code() - 代码分析
  - [x] generate_code() - 代码生成
  - [x] refactor_code() - 代码重构
  - [x] fix_bug() - Bug修复
  - [x] review_code() - 代码审查
- [x] 4.6 实现上下文理解接口
  - [x] understand_project() - 项目理解
  - [x] analyze_dependencies() - 依赖分析
  - [x] semantic_search() - 语义搜索
- [x] 4.7 创建LangChain工具集（claude_code/tools.py）
  - [x] 将Claude Code接口封装为LangChain Tool
  - [x] 供智能体调用
- [x] 4.8 实现会话管理（claude_code/session.py）
  - [x] 会话上下文保持
  - [x] 工作目录管理

## 5. LLM客户端封装（支持多种提供商）
- [x] 5.1 实现LLM基类接口（llm/base.py）
  - [x] 定义BaseLLMClient抽象类
  - [x] 定义invoke()和stream()方法
  - [x] 定义get_langchain_model()方法
- [x] 5.2 实现LLM工厂（llm/factory.py）
  - [x] 根据LLM_PROVIDER创建对应实例
  - [x] 支持anthropic, openai, local, azure_openai等
- [x] 5.3 实现Anthropic客户端（llm/anthropic.py）
  - [x] 封装ChatAnthropic
  - [x] 支持配置参数
- [x] 5.4 实现OpenAI客户端（llm/openai.py）
  - [x] 封装ChatOpenAI
  - [x] 支持自定义base_url
- [x] 5.5 实现本地模型客户端（llm/local.py）
  - [x] 支持Ollama等本地模型
  - [x] 支持自定义端点
- [x] 5.6 实现Azure OpenAI客户端（llm/azure_openai.py）
  - [x] 封装AzureChatOpenAI
  - [x] 支持Azure特定配置
- [x] 5.7 更新配置加载器支持LLM配置
  - [x] 从.env加载LLM配置
  - [x] LLMConfig数据类（已包含在config_models.py中）

## 6. 记忆系统
- [x] 5.1 实现记忆基类（memory/base_memory.py）
- [x] 5.2 实现对话记忆（memory/conversation.py）
  - [x] 短期记忆（内存）
  - [x] 会话管理
- [x] 5.3 实现长期记忆（memory/long_term.py）
  - [x] 向量存储集成
  - [x] 记忆检索和更新
- [x] 5.4 实现向量存储封装（memory/vector_store.py）
  - [x] ChromaDB集成
  - [x] 记忆向量化
- [x] 5.5 集成Redis缓存（可选）
  - [x] 中期记忆存储
  - [x] TTL管理

## 7. RAG模块
- [x] 6.1 实现代码加载器（rag/loaders/code_loader.py）
  - [x] 通过Claude Code CLI读取代码文件
  - [x] 代码分块处理
- [x] 6.2 实现文档加载器（rag/loaders/doc_loader.py）
  - [x] Markdown、TXT等格式支持
- [x] 6.3 实现数据库加载器（rag/loaders/db_loader.py）
  - [x] 数据库Schema提取
- [x] 6.4 实现向量嵌入封装（rag/embeddings.py）
  - [x] 嵌入模型集成
  - [x] 文本向量化
- [x] 6.5 实现文档索引器（rag/indexer.py）
  - [x] 增量索引
  - [x] 索引更新
- [x] 6.6 实现检索器（rag/retriever.py）
  - [x] 语义检索
  - [x] 混合检索（关键词+语义）
  - [x] 结果排序和过滤

## 8. OpenSpec集成模块
- [x] 7.1 实现OpenSpec CLI客户端（openspec/client.py）
  - [x] 封装openspec-cn命令调用
  - [x] list_changes() - 列出活动变更
  - [x] list_specs() - 列出规范
  - [x] show_change() - 显示变更详情
  - [x] validate_change() - 验证提案
  - [x] archive_change() - 归档提案
- [x] 7.2 实现OpenSpec文件解析器（openspec/parser.py）
  - [x] 解析proposal.md
  - [x] 解析tasks.md
  - [x] 解析design.md
  - [x] 解析spec.md规范增量
  - [x] 解析变更目录结构
- [x] 7.3 实现OpenSpec提案生成器（openspec/generator.py）
  - [x] create_proposal() - 创建新提案
  - [x] generate_spec_increment() - 生成规范增量
  - [x] generate_tasks() - 生成tasks.md
  - [x] check_conflicts() - 检查冲突
- [x] 7.4 实现OpenSpec验证器（openspec/validator.py）
  - [x] validate_proposal() - 验证提案完整性
  - [x] validate_spec_format() - 验证规范格式
  - [x] check_required_files() - 检查必需文件
- [x] 7.5 实现OpenSpec管理器（openspec/manager.py）
  - [x] break_down_task() - 任务拆解为提案
  - [x] create_proposal_plan() - 创建执行计划
  - [x] track_progress() - 跟踪进度

## 9. 智能体实现
- [x] 8.1 实现智能体基类（agents/base_agent.py）
  - [x] 基础接口定义
  - [x] 工具集成
  - [x] 日志记录
- [x] 8.2 实现编排智能体（agents/orchestrator.py）
  - [x] 任务意图分析
  - [x] 智能体路由决策
  - [x] 结果汇总
- [x] 8.3 实现RAG智能体（agents/rag_agent.py）
  - [x] 知识检索
  - [x] 上下文增强
- [x] 8.4 实现记忆智能体（agents/memory_agent.py）
  - [x] 对话历史管理
  - [x] 长期记忆存储和检索
- [x] 8.5 实现规划智能体（agents/planning_agent.py）
  - [x] 复杂任务分解
  - [x] 集成OpenSpec Manager
  - [x] 提案创建和管理
  - [x] 执行计划生成
  - [x] 进度监控

## 10. LangGraph工作流
- [x] 9.1 定义状态模型（core/state.py）
  - [x] AgentState定义（包含openspec_proposals和openspec_plan）
  - [x] 状态验证
- [x] 9.2 实现智能体路由（core/router.py）
  - [x] 路由决策逻辑
  - [x] 条件边定义（包含need_openspec路由）
- [x] 9.3 构建LangGraph工作流（core/graph.py）
  - [x] 节点定义（orchestrator, rag, memory, planning, openspec, claude_code）
  - [x] 边定义（路由和顺序，包含OpenSpec相关边）
  - [x] 工作流编译
- [x] 9.4 实现工作流执行器
  - [x] 异步执行
  - [x] 状态管理
  - [x] 错误恢复

## 11. 测试
- [x] 10.1 编写Claude Code CLI封装测试（test_claude_code.py）
  - [x] 文件操作测试
  - [x] Coding能力测试
  - [x] 并发控制测试
  - [x] 超时处理测试
- [x] 11.2 编写LLM客户端测试（test_llm.py）
  - [x] 各提供商客户端测试
  - [x] LLM工厂测试
  - [x] 配置加载测试
- [x] 11.3 编写OpenSpec集成测试（test_openspec.py）
  - [x] OpenSpec CLI调用测试
  - [x] 提案生成测试
  - [x] 提案验证测试
  - [x] 任务拆解测试
  - [x] 冲突检查测试
- [x] 11.4 编写智能体单元测试（test_agents.py）
- [x] 11.5 编写RAG模块测试（test_rag.py）
- [x] 11.6 编写记忆系统测试（test_memory.py）
- [x] 11.7 编写集成测试（test_integration.py）
  - [x] 端到端工作流测试
  - [x] 多智能体协作测试
  - [x] OpenSpec提案创建和执行测试

## 12. 文档和脚本
- [x] 12.1 编写API文档
  - [x] Claude Code CLI接口文档
  - [x] LLM客户端接口文档
  - [x] OpenSpec集成接口文档
  - [x] 智能体API文档
- [x] 12.2 创建初始化脚本（scripts/init_db.py）
  - [x] 向量数据库初始化
  - [x] 配置验证
- [x] 12.3 创建索引脚本（scripts/index_codebase.py）
  - [x] 代码库索引
  - [x] 文档索引
- [x] 12.4 创建Claude Code CLI验证脚本（scripts/verify_claude_code.py）
- [x] 12.5 创建LLM验证脚本（scripts/verify_llm.py）
- [x] 12.6 创建OpenSpec验证脚本（scripts/verify_openspec.py）
- [x] 12.7 编写使用示例
  - [x] 基础使用示例
  - [x] 复杂任务拆解示例
  - [x] OpenSpec提案管理示例
  - [x] 配置示例

## 依赖关系

```
1. 项目初始化
   ↓
2. 配置系统 ──→ 3. 日志系统
   ↓               ↓
4. Claude Code CLI核心封装（关键路径）
   ↓
5. LLM客户端封装（支持多种提供商）
   ↓
6. 记忆系统 ←── 7. RAG模块（使用LLM客户端）
   ↓               ↓
8. OpenSpec集成模块 ←─────┘
   ↓
9. 智能体实现（包含Planning Agent集成OpenSpec，使用LLM客户端）
   ↓
10. LangGraph工作流
   ↓
11. 测试 ──→ 12. 文档和脚本
```

**关键依赖说明**：
- Claude Code CLI封装是核心，其他模块依赖它
- RAG模块的代码加载器需要Claude Code CLI
- 智能体通过LangChain Tools调用Claude Code CLI
- LangGraph工作流协调所有智能体

## 验证标准

- [x] Claude Code CLI可用性检查通过
- [x] 所有配置可通过.env和YAML加载
- [x] 日志记录完整且可追踪（包括Claude Code CLI调用）
- [x] Claude Code CLI文件操作功能正常
- [x] Claude Code CLI Coding能力正常
- [x] LLM客户端支持多种提供商（anthropic/openai/local等）
- [x] LLM配置正确加载和使用
- [x] OpenSpec CLI调用正常
- [x] 能够创建符合规范的OpenSpec提案
- [x] 能够将复杂任务拆解为多个提案
- [x] 能够验证和检查提案冲突
- [x] RAG检索返回相关结果
- [x] 记忆系统正确存储和检索
- [x] 智能体可独立运行
- [x] LangGraph工作流可编排多智能体（包含OpenSpec节点）
- [x] 端到端任务执行成功（包含提案创建和执行）
- [x] 单元测试覆盖率 > 70%

### 验证记录
- Claude Code CLI：通过 `AIagent/scripts/claude_stub.py` + `AIagent/scripts/verify_claude_code.py --use-stub --run` 完成可用性/文件操作/Coding 能力的本地验证（用于 CI/开发环境）。真实 Claude Code CLI 仍需在目标环境安装后再次验证。
- OpenSpec CLI：通过 `AIagent/scripts/verify_openspec.py` 验证可用。
- 覆盖率：`pytest --cov=src --cov-fail-under=70` 通过（总覆盖率约 70%）。
