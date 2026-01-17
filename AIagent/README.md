# AIagent - 多智能体AI框架

基于 **LangChain + LangGraph + Claude Code CLI** 的多智能体协作框架，提供代码分析、智能生成、知识检索等AI能力。

## 核心特性

### 🤖 多智能体架构
- **Orchestrator Agent**：任务分解、智能体调度、结果汇总
- **RAG Agent**：知识库检索、上下文增强
- **Memory Agent**：对话历史、长期记忆管理
- **Planning Agent**：任务规划、OpenSpec集成

### 🔧 Claude Code CLI 核心引擎
- **本地文件操作**：读取、写入、编辑、搜索文件
- **Coding能力**：代码分析、生成、重构、Bug修复
- **上下文理解**：项目结构分析、依赖分析

### 📚 RAG 检索增强
- 代码库向量索引和语义检索
- 业务文档知识库
- 数据库元数据检索

### 🧠 上下文记忆系统
- 短期对话记忆（会话级）
- 长期知识记忆（持久化）
- 分层存储（内存/Redis/向量数据库）

### 📋 OpenSpec 集成
- 将复杂任务拆解为多个OpenSpec变更提案
- 自动创建、验证、管理提案
- 提案依赖关系分析和执行计划

## 前置条件

- Python >= 3.10
- [Claude Code CLI](https://claude.ai) 已安装并可用
- [openspec-cn CLI](https://github.com/openspec) 已安装（用于OpenSpec集成）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Claude Code CLI配置
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/path/to/your/project

# LLM配置（支持多种提供商）
LLM_PROVIDER=anthropic  # anthropic, openai, local, azure_openai
LLM_API_KEY=your_api_key
LLM_MODEL=claude-sonnet-4-20250514

# 向量数据库配置
CHROMA_PERSIST_DIR=./data/chroma

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=./logs
```

### 3. 初始化

```bash
# 初始化向量数据库
python scripts/init_db.py

# 索引代码库（可选）
python scripts/index_codebase.py
```

### 4. 使用示例

```python
from src.utils.config_manager import ConfigManager
from src.core import build_graph, WorkflowExecutor
from src.agents import OrchestratorAgent, RAGAgent, MemoryAgent, PlanningAgent
from src.openspec.manager import OpenSpecManager
from src.rag.indexer import RAGIndexer
from src.rag.retriever import RAGRetriever
from src.memory.manager import MemoryManager
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document

# 最小可运行示例（不调用外部 LLM/Claude Code CLI）
cm = ConfigManager()

# RAG：用 FakeEmbeddings + Chroma 建一个最小索引
embeddings = FakeEmbeddings(size=8)
indexer = RAGIndexer(persist_dir="./data/chroma", collection_name="aiagent_demo", embeddings=embeddings)
indexer.add_documents([Document(page_content="项目使用 Django", metadata={"source": "demo_doc"})])
retriever = RAGRetriever(indexer.vectorstore)

# Memory：使用本地内存后端（避免依赖 Redis）
mm = MemoryManager(
    memory_config=cm.get_memory_config(),
    vector_db_config=cm.get_vector_db_config(),
)

# OpenSpec：规划使用 OpenSpecManager（不依赖 openspec-cn）
osm = OpenSpecManager(openspec_root="openspec")

# 构建工作流
graph = build_graph(
    orchestrator=OrchestratorAgent(),
    rag=RAGAgent(retriever),
    memory=MemoryAgent(mm),
    planning=PlanningAgent(osm),
)
executor = WorkflowExecutor(graph)

# 执行任务
result = await executor.run("请检索项目文档")
print(result.get("final_response"))
```

## API 文档（最小版）

### Claude Code CLI 接口

- 入口类：`src.claude_code.client.ClaudeCodeClient`
- **文件操作**：`read_file` / `write_file` / `edit_file` / `search_files` / `grep` / `list_dir`
- **Coding 能力**：`analyze_code` / `generate_code` / `refactor_code` / `fix_bug` / `review_code`
- **上下文理解**：`understand_project` / `analyze_dependencies` / `semantic_search`

### LLM 客户端接口

- 入口类：`src.llm.factory.LLMFactory`
- 基类：`src.llm.base.BaseLLMClient`
- 常用方法：`invoke` / `stream` / `invoke_prompt` / `stream_prompt` / `get_langchain_model`

### OpenSpec 集成接口

- CLI 封装：`src.openspec.client.OpenSpecClient`（依赖本机 `openspec-cn`）
- 解析器：`src.openspec.parser.OpenSpecParser`
- 生成器：`src.openspec.generator.OpenSpecGenerator`
- 验证器：`src.openspec.validator.OpenSpecValidator`
- 管理器：`src.openspec.manager.OpenSpecManager`

### 智能体 API

- 基类：`src.agents.base_agent.BaseAgent`（统一 `run(state) -> AgentResult`）
- 编排：`src.agents.orchestrator.OrchestratorAgent`
- 检索：`src.agents.rag_agent.RAGAgent`
- 记忆：`src.agents.memory_agent.MemoryAgent`
- 规划：`src.agents.planning_agent.PlanningAgent`

## 使用示例（补充）

### 复杂任务拆解示例

```python
from src.openspec.manager import OpenSpecManager

mgr = OpenSpecManager(openspec_root="openspec")
stubs = mgr.break_down_task("用户认证、权限管理、审计日志")
plan = mgr.create_proposal_plan(stubs)
print([p.change_id for p in plan.ordered])
```

### OpenSpec 提案管理示例

```python
from src.openspec.client import OpenSpecClient

client = OpenSpecClient()
changes = await client.list_changes()
print(changes[:3])
```

### 配置示例

```python
from src.utils.config_manager import ConfigManager

cm = ConfigManager()
print(cm.get_rag_config())
print(cm.get_memory_config())
```

### SQL 外键提取工具

AIagent 提供了强大的 SQL 外键信息提取工具，支持从 Oracle SQL 文件中提取外键约束信息。

#### 快速开始

```bash
# 单文件提取
python -m AIagent.src.sql_import extract-foreignkey \
  docs/hospital/sql/YOUR_TABLE.sql \
  --output docs/hospital/foreignkey

# 批量提取
python -m AIagent.src.sql_import extract-foreignkey-all \
  docs/hospital/sql \
  --output docs/hospital/foreignkey \
  --verbose
```

#### 核心特性

- **多策略提取**：支持标准正则表达式、格式变体脚本库、LLM 辅助生成
- **大文件优化**：自动检测大文件（>1MB），使用流式处理和片段提取
- **LLM 集成**：默认启用 LLM 辅助，自动处理非标准格式（支持多种 LLM 提供商）
- **智能缓存**：LLM 生成的脚本自动缓存，相同格式直接复用
- **结构化输出**：JSON 格式，包含完整的外键元数据

#### 使用示例

```python
from AIagent.src.sql_import.foreignkey_extractor import ForeignKeyExtractor

# 创建提取器（默认启用 LLM）
extractor = ForeignKeyExtractor()

# 提取单个文件
table_fks = extractor.extract_from_file('path/to/file.sql')

# 保存为 JSON
output_file = extractor.save_to_json(table_fks, 'output_dir')
```

#### 详细文档

- [快速开始指南](../../docs/hospital/docs/QUICK_START.md)
- [LLM 使用指南](../../docs/hospital/docs/LLM_USAGE_GUIDE.md)
- [通用 LLM 支持](../../docs/hospital/docs/GENERIC_LLM_SUPPORT.md)

### SQL 表名和字段名中文含义推断

AIagent 提供 SQL 表名和字段名中文含义推断工具，使用 LLM 分析 SQL 文件并推断表名和字段名的中文含义。

#### 快速开始

```bash
# 单文件推断
python -m AIagent.src.sql_import.sql_meaning_cli infer-file \
  docs/hospital/convertsql/create/BS_STAFF_TYPE.sql \
  --ignore-prefix gzlry_

# 批量推断
python -m AIagent.src.sql_import.sql_meaning_cli infer-dir \
  docs/hospital/convertsql/create \
  --ignore-prefix gzlry_
```

#### 核心特性

- **直接 LLM 处理**：将完整 SQL 发送给 LLM，同时完成解析和推断
- **JSON 格式验证**：使用 Pydantic 模型验证 LLM 输出格式
- **智能重试**：验证失败时带上下文重试，将错误信息反馈给 LLM
- **结构化输出**：JSON 格式，包含表/字段含义、置信度、推理过程
- **可配置前缀**：支持忽略表名前缀（默认 `gzlry_`）
- **自定义模板**：支持自定义提示词模板

#### 输出示例

```json
{
  "file_path": "docs/hospital/convertsql/create/BS_STAFF_TYPE.sql",
  "table": {
    "table_name": "BS_STAFF_TYPE",
    "original_comment": "人员分类",
    "inferred_meaning": "人员分类信息表",
    "confidence": 0.95,
    "reasoning": "表名为 BS_STAFF_TYPE，结合注释'人员分类'...",
    "fields": [
      {
        "field_name": "mainid",
        "field_type": "VARCHAR(50)",
        "original_comment": "mainId",
        "inferred_meaning": "主键ID",
        "confidence": 0.95,
        "reasoning": "字段名为 mainid，通常表示主键标识符"
      }
    ]
  },
  "metadata": {
    "processed_at": "2026-01-16T21:31:33",
    "llm_model": "qwen-plus",
    "llm_provider": "openai"
  }
}
```

#### 使用示例

```python
from AIagent.src.sql_import import SQLMeaningInferencer

# 创建推断器
inferencer = SQLMeaningInferencer(
    ignore_prefix='gzlry_',
    skip_existing=True,  # 跳过已存在结果
    concurrency=3        # 并发数量
)

# 单文件推断
result = await inferencer.infer_file('path/to/file.sql')

# 批量推断（并发处理）
results = await inferencer.infer_directory('path/to/sql_dir')

# 只重试失败的任务
results = await inferencer.infer_directory('path/to/sql_dir', retry_failed=True)

# 清除错误日志
inferencer.clear_error_log()
```

#### CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出路径 | `docs/hospital/commentsql/` |
| `--ignore-prefix` | 忽略的表名前缀 | `gzlry_` |
| `--prompt-template` | 自定义提示词模板文件 | 内置模板 |
| `--skip-existing` | 跳过已存在结果的文件 | 否 |
| `--retry-failed` | 只重试之前失败的任务 | 否 |
| `-c, --concurrency` | 并发处理数量 | `1` |

#### 批量处理高级用法

```bash
# 跳过已存在结果，只处理新文件
python -m AIagent.src.sql_import.sql_meaning_cli infer-dir ./sql --skip-existing

# 并发处理（5 个任务同时执行）
python -m AIagent.src.sql_import.sql_meaning_cli infer-dir ./sql -c 5

# 跳过已存在 + 并发处理
python -m AIagent.src.sql_import.sql_meaning_cli infer-dir ./sql --skip-existing -c 3

# 只重试之前失败的任务
python -m AIagent.src.sql_import.sql_meaning_cli infer-dir ./sql --retry-failed

# 清除错误日志
python -m AIagent.src.sql_import.sql_meaning_cli clear-errors
```

#### 基于 Excel 元数据重新推断

如果有 Excel 文件包含表单的业务元数据（如表单分类、中文名称），可以利用这些上下文信息重新推断，提高准确性：

```bash
# 预览模式（查看将处理哪些表）
python -m AIagent.src.sql_import.sql_meaning_cli reinfer-from-excel \
  docs/hospital/docs/NHMS_WORKFLOW_BILL.xlsx \
  --dry-run

# 实际执行（并发处理）
python -m AIagent.src.sql_import.sql_meaning_cli reinfer-from-excel \
  docs/hospital/docs/NHMS_WORKFLOW_BILL.xlsx \
  -c 3

# 跳过已重新推断过的表
python -m AIagent.src.sql_import.sql_meaning_cli reinfer-from-excel \
  docs/hospital/docs/NHMS_WORKFLOW_BILL.xlsx \
  --skip-existing -c 3
```

**Excel 文件格式要求**：
- `TABLENAME`：表名
- `FORMDES`：表单分类描述（如 "院前评估"、"服务评估表"）
- `NAMELABEL`：表单中文名称（如 "社会参与评估表"、"跌倒/坠床风险评估"）

**工作原理**：
1. 读取 Excel 中的表单元数据
2. 在 `commentsql` 目录中查找对应的 JSON 文件
3. 如果 JSON 存在，读取原始 SQL 文件并结合 Excel 元数据重新推断
4. 如果 JSON 不存在，跳过该表

#### 错误日志

批量处理时，失败的任务会记录到 `error_log.json` 文件中：

```json
{
  "updated_at": "2026-01-16T10:30:00",
  "total_failed": 2,
  "failed_tasks": [
    {
      "file": "/path/to/failed.sql",
      "file_name": "failed.sql",
      "error": "LLM 调用超时",
      "failed_at": "2026-01-16T10:25:00"
    }
  ]
}
```

### Django API 集成

AIagent 提供 OpenAPI-Aware 的 Django API 客户端，支持自动理解并调用 backend-django 后台 API。

#### 快速开始

```python
from AIagent.src.django_api import OpenAPIAwareClient, DjangoAPIConfig

# 配置
config = DjangoAPIConfig(
    base_url="http://localhost:8000",
    username="admin",
    password="admin123"
)

# 创建客户端
async with OpenAPIAwareClient(config) as client:
    # 加载 OpenAPI Schema（让 AI 读懂 API）
    await client.load_openapi_schema()
    
    # 登录
    await client.login()
    
    # 根据意图调用 API
    result = await client.call_by_intent("查询用户列表")
    print(result)
```

#### 核心特性

- **OpenAPI Schema 自动解析**：从 `/api/openapi.json` 获取完整 API 描述
- **AI 可理解的 API 摘要**：将 Schema 转换为 LLM 可理解的文本描述
- **三层分层检索**（支持大规模 API）：
  - 第一层：关键词/Tag 快速过滤（成本=0）
  - 第二层：向量语义检索（RAG）
  - 第三层：LLM 精选
- **通用 API 调用**：根据 Schema 自动处理路径参数、查询参数、请求体
- **Bearer Token 认证**：支持登录获取 Token 并自动附加到请求头

#### 使用智能体

```python
from AIagent.src.django_api import DjangoAPIAgent, DjangoAPIConfig
from AIagent.src.llm.factory import LLMFactory

# 创建智能体
config = DjangoAPIConfig(base_url="http://localhost:8000")
llm_client = LLMFactory.create()

agent = DjangoAPIAgent(config, llm_client=llm_client)
await agent.initialize()

# 处理用户查询
result = await agent.process_query("帮我查看最近的问卷数据")
print(result)
```

#### 命令行工具 (CLI)

Django API 模块提供强大的命令行工具，支持交互式测试和调试。在项目根目录执行：

```bash
# 显示帮助
python -m AIagent.src.django_api --help

# 显示 API 信息（端点数量、Tag 分组等）
python -m AIagent.src.django_api info

# 测试登录
python -m AIagent.src.django_api login

# 搜索 API 端点
python -m AIagent.src.django_api search user           # 搜索包含 'user' 的端点
python -m AIagent.src.django_api search 问卷 -v        # 详细搜索，显示参数

# 根据意图调用 API
python -m AIagent.src.django_api call "获取当前用户信息"
python -m AIagent.src.django_api call "获取用户列表" -p '{"page":1}'

# 生成 AI 摘要（导出 LLM 可理解的 API 描述）
python -m AIagent.src.django_api summary
python -m AIagent.src.django_api summary -o api_summary.md

# 列出所有 Tag
python -m AIagent.src.django_api list-tags

# 列出端点（支持过滤）
python -m AIagent.src.django_api list-endpoints --tag Core-Auth -v
python -m AIagent.src.django_api list-endpoints --method GET -l 20

# 生成多步骤查询脚本（LangGraph 工作流）
python -m AIagent.src.django_api generate "查询用户列表前10个"
python -m AIagent.src.django_api generate "查询问卷数据中的户外活动记录表" -v
python -m AIagent.src.django_api generate "查询表数据查询中的老人档案表前10个" --max-iter 10
```

**CLI 命令说明**：

| 命令 | 说明 | 常用参数 |
|------|------|----------|
| `info` | 显示 API 信息 | - |
| `login` | 测试登录认证 | - |
| `search` | 搜索 API 端点 | `-l` 限制结果数, `-v` 详细输出 |
| `call` | 根据意图调用 API | `-p` 参数, `--no-auth` 跳过认证 |
| `summary` | 生成 AI 摘要 | `-o` 输出文件, `-l` 字符限制 |
| `list-tags` | 列出所有 Tag | - |
| `list-endpoints` | 列出端点 | `--tag` 按 Tag 过滤, `--method` 按方法过滤 |
| `generate` | 生成多步骤查询脚本 | `--max-iter` 最大迭代次数, `-v` 详细输出 |

#### 脚本生成器（LangGraph 工作流）

`generate` 命令使用 LangGraph 工作流自动生成多步骤 API 查询脚本，特别适合复杂的数据查询场景。

**工作流程**：

```
用户意图 → 计划生成 → 步骤验证 → (计划修正?) → 脚本生成 → 执行 → 验证 → (调试迭代?)
```

**核心特性**：

1. **智能意图拆解**：LLM 分析用户意图，生成包含登录、API 调用等步骤的执行计划
2. **步骤验证**：在生成脚本前，直接调用 API 验证每个步骤的正确性
   - 检查 API 路径和参数是否正确
   - 记录实际的输入输出（响应字段、数据量、样例数据）
   - 如果验证失败，自动修正执行计划（最多 2 次）
3. **上下文增强**：将步骤验证的实际输入输出加入脚本生成上下文
4. **迭代调试**：脚本执行失败时，LLM 分析错误并自动修复（最多 10 次迭代）

**使用示例**：

```bash
# 基础用法
python -m AIagent.src.django_api generate "查询用户列表前10个"

# 查询问卷数据
python -m AIagent.src.django_api generate "查询问卷数据中的户外活动记录表前5个"

# 查询动态表数据
python -m AIagent.src.django_api generate "查询表数据查询中的老人档案表前10个"

# 详细输出（显示执行计划、步骤验证、脚本内容）
python -m AIagent.src.django_api generate "查询用户列表" -v

# 增加迭代次数
python -m AIagent.src.django_api generate "复杂查询" --max-iter 15
```

**输出说明**：

```
📋 执行计划
├── 步骤 1: 登录 - 获取认证 Token
└── 步骤 2: 查询 - 调用 /api/core/survey/query

✅ 步骤验证结果
├── 步骤 1: ✓ 成功
│   └── 响应字段: accessToken, refreshToken, ...
└── 步骤 2: ✓ 成功
    ├── 数据量: 10 条
    └── 样例: {"id": 1, "name": "..."}

📊 结果
└── 查询成功，返回 10 条记录
```

#### 配置说明

环境变量配置：

```bash
# Django API 配置
DJANGO_API_BASE_URL=http://localhost:8000
DJANGO_API_USERNAME=admin
DJANGO_API_PASSWORD=your_password
DJANGO_API_TIMEOUT=30

# RAG 检索配置
DJANGO_API_ENABLE_RAG=true
DJANGO_API_KEYWORD_FILTER_THRESHOLD=20
DJANGO_API_RETRIEVAL_TOP_K=10
DJANGO_API_SIMILARITY_THRESHOLD=0.5

# Embedding 配置（阿里云百炼示例）
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-xxxx
EMBEDDING_DIMENSIONS=1024
```

或在 `config/settings.yaml` 中配置：

```yaml
django_api:
  base_url: "http://localhost:8000"
  username: ""
  password: ""
  timeout: 30
  retrieval:
    enable_rag: true
    keyword_filter_threshold: 20
    top_k: 10
    similarity_threshold: 0.5
```

## 架构设计

```
用户请求
   ↓
LangGraph 编排层 (Orchestrator)
   ↓
[RAG/Memory/Planning] 提供上下文
   ↓
★ Claude Code CLI 核心引擎 ★        ★ Django API 智能体 ★
  - 文件操作                          - OpenAPI 解析
  - Coding能力                        - 分层检索（RAG）
  - 上下文理解                        - API 调用
   ↓                                    ↓
返回结果                              返回数据
```

## 目录结构

```
AIagent/
├── src/                    # 源代码
│   ├── claude_code/        # Claude Code CLI封装
│   ├── llm/                # LLM客户端（支持多提供商）
│   ├── agents/             # 智能体实现
│   ├── django_api/         # Django API 集成
│   ├── openspec/           # OpenSpec集成
│   ├── core/               # LangGraph工作流
│   ├── memory/             # 记忆系统
│   ├── rag/                # RAG模块
│   ├── logging/            # 日志系统
│   └── utils/              # 工具函数
├── config/                 # 配置文件
│   ├── prompts/            # Prompts模板
│   ├── agents.yaml         # 智能体配置
│   └── settings.yaml       # 全局设置
├── tests/                  # 测试
├── scripts/                # 脚本
├── logs/                   # 日志
└── data/                   # 数据（向量库等）
```

## 开发指南

### 运行测试

```bash
# 单元测试
pytest tests/

# 集成测试
pytest tests/test_integration.py
```

### 代码规范

- 遵循 PEP 8 规范
- 使用中文编写注释和文档字符串
- 使用类型提示

## 许可证

MIT License

## 联系方式

- 项目主页：https://github.com/zq-platform/AIagent
- 问题反馈：https://github.com/zq-platform/AIagent/issues
