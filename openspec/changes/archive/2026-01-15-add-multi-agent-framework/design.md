# 技术设计：多智能体AI框架

## 上下文

### 背景
zq-platform需要AI能力增强，支持代码分析、智能生成、知识检索等场景。采用**Claude Code CLI作为核心引擎**，提供本地文件操作和coding能力，结合LangChain + LangGraph进行多智能体编排和协调。

### 约束
- 作为独立顶层模块，与Django后端松耦合
- **Claude Code CLI是核心代码处理引擎**，所有本地文件操作和coding通过它完成
- 需支持多种知识源的RAG检索
- 需要完善的日志和监控
- 配置驱动，支持YAML定义Prompts和工作流

### 利益相关者
- 开发团队：使用AI辅助开发
- 运维团队：监控和维护AI服务
- 最终用户：通过API使用AI功能

## 目标 / 非目标

### 目标
- **以Claude Code CLI为核心**，提供本地文件操作和coding能力
- 构建可扩展的多智能体协作框架（LangChain + LangGraph）
- 实现高质量的RAG检索增强
- 提供持久化的上下文记忆
- 支持YAML配置Prompts和工作流
- 完善的日志和监控能力

### 非目标
- 不替代现有业务逻辑
- 不提供实时流式UI（可后续扩展）
- 不支持多租户隔离（当前版本）

## 架构设计

### 核心架构理念

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户请求 / API调用                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LangGraph 编排层 (Orchestrator)                  │
│  - 任务分解和路由                                                 │
│  - 智能体调度                                                    │
│  - 结果汇总                                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │  RAG Agent    │   │ Memory Agent  │   │ Planning Agent│
    │  知识检索增强   │   │  上下文记忆    │   │   任务规划     │
    └───────────────┘   └───────────────┘   └───────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              ★ Claude Code CLI 核心引擎 ★                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    本地文件操作                          │    │
│  │  - 文件读取 (Read)      - 文件写入 (Write)              │    │
│  │  - 文件搜索 (Glob/Grep) - 目录浏览 (LS)                 │    │
│  │  - 文件编辑 (Edit)      - 文件删除 (Delete)             │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Coding能力                           │    │
│  │  - 代码分析和理解        - 代码生成                      │    │
│  │  - 代码重构和优化        - Bug修复                       │    │
│  │  - 代码审查和建议        - 测试生成                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    上下文理解                            │    │
│  │  - 项目结构分析          - 依赖关系分析                   │    │
│  │  - 代码库语义理解        - 本地上下文感知                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
AIagent/
├── .env.example               # 环境变量模板
├── .env                       # 环境变量配置（不提交git）
├── .gitignore                 # Git忽略配置
├── config/                    # 配置目录
│   ├── agents.yaml            # 智能体配置
│   ├── prompts/               # Prompts模板
│   │   ├── orchestrator.yaml  # 编排智能体提示词
│   │   ├── rag.yaml           # RAG检索提示词
│   │   ├── memory.yaml        # 记忆管理提示词
│   │   └── planning.yaml      # 任务规划提示词
│   ├── workflows.yaml         # 工作流配置
│   └── settings.yaml          # 全局设置
├── src/
│   ├── __init__.py
│   ├── claude_code/           # ★ Claude Code CLI 核心封装
│   │   ├── __init__.py
│   │   ├── client.py          # CLI客户端封装
│   │   ├── executor.py        # 命令执行器
│   │   ├── parser.py          # 输出解析器
│   │   ├── session.py         # 会话管理
│   │   └── tools.py           # 工具定义（供LangChain使用）
│   ├── agents/                # 智能体实现
│   │   ├── __init__.py
│   │   ├── base_agent.py      # 基础智能体类
│   │   ├── orchestrator.py    # 编排智能体
│   │   ├── rag_agent.py       # RAG检索智能体
│   │   ├── memory_agent.py    # 记忆管理智能体
│   │   └── planning_agent.py  # 任务规划智能体（集成OpenSpec）
│   ├── openspec/              # ★ OpenSpec集成模块
│   │   ├── __init__.py
│   │   ├── client.py          # OpenSpec CLI封装
│   │   ├── parser.py          # OpenSpec文件解析器
│   │   ├── generator.py       # 提案生成器
│   │   ├── validator.py       # 提案验证器
│   │   └── manager.py         # 提案管理器
│   ├── llm/                   # LLM客户端封装（支持多种提供商）
│   │   ├── __init__.py
│   │   ├── base.py            # LLM基类接口
│   │   ├── factory.py         # LLM工厂（根据配置创建实例）
│   │   ├── anthropic.py      # Anthropic Claude封装
│   │   ├── openai.py         # OpenAI封装
│   │   ├── local.py          # 本地模型封装（Ollama等）
│   │   └── azure_openai.py   # Azure OpenAI封装
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── graph.py           # LangGraph工作流定义
│   │   ├── state.py           # 状态管理
│   │   └── router.py          # 智能体路由
│   ├── memory/                # 记忆系统
│   │   ├── __init__.py
│   │   ├── base_memory.py     # 记忆基类
│   │   ├── conversation.py    # 对话记忆
│   │   ├── long_term.py       # 长期记忆
│   │   └── vector_store.py    # 向量存储
│   ├── rag/                   # RAG模块
│   │   ├── __init__.py
│   │   ├── indexer.py         # 文档索引器
│   │   ├── retriever.py       # 检索器
│   │   ├── loaders/           # 文档加载器
│   │   │   ├── code_loader.py # 代码加载（可调用Claude Code）
│   │   │   ├── doc_loader.py  # 文档加载
│   │   │   └── db_loader.py   # 数据库元数据加载
│   │   └── embeddings.py      # 向量嵌入
│   ├── logging/               # 日志系统
│   │   ├── __init__.py
│   │   ├── logger.py          # 日志记录器
│   │   ├── handlers.py        # 日志处理器
│   │   └── formatters.py      # 日志格式化
│   └── utils/                 # 工具函数
│       ├── __init__.py
│       ├── env_loader.py      # 环境变量加载器
│       ├── config_loader.py   # 配置加载器
│       └── helpers.py         # 辅助函数
├── tests/                     # 测试目录
│   ├── __init__.py
│   ├── test_claude_code.py    # Claude Code CLI测试
│   ├── test_openspec.py       # OpenSpec集成测试
│   ├── test_agents.py
│   ├── test_rag.py
│   └── test_memory.py
├── logs/                      # 日志目录
├── data/                      # 数据目录（向量库等）
├── requirements.txt           # 依赖
├── setup.py                   # 安装配置
└── README.md                  # 说明文档
```

### Claude Code CLI 核心封装设计

#### 1. Claude Code Client（客户端封装）

```python
# src/claude_code/client.py

class ClaudeCodeClient:
    """Claude Code CLI 客户端封装"""
    
    def __init__(self, config: ClaudeCodeConfig):
        self.claude_path = config.claude_code_path
        self.timeout = config.timeout
        self.max_concurrent = config.max_concurrent
        self.working_dir = config.working_dir
    
    # ===== 本地文件操作 =====
    async def read_file(self, path: str) -> str:
        """读取文件内容"""
        
    async def write_file(self, path: str, content: str) -> bool:
        """写入文件内容"""
        
    async def edit_file(self, path: str, old_str: str, new_str: str) -> bool:
        """编辑文件（字符串替换）"""
        
    async def search_files(self, pattern: str, path: str = ".") -> List[str]:
        """搜索文件（glob模式）"""
        
    async def grep(self, pattern: str, path: str = ".") -> List[GrepResult]:
        """搜索文件内容（正则表达式）"""
        
    async def list_dir(self, path: str) -> List[FileInfo]:
        """列出目录内容"""
    
    # ===== Coding能力 =====
    async def analyze_code(self, path: str, question: str) -> AnalysisResult:
        """分析代码，回答问题"""
        
    async def generate_code(self, prompt: str, context: str = None) -> str:
        """根据需求生成代码"""
        
    async def refactor_code(self, path: str, instruction: str) -> RefactorResult:
        """重构代码"""
        
    async def fix_bug(self, path: str, bug_description: str) -> FixResult:
        """修复Bug"""
        
    async def review_code(self, path: str) -> ReviewResult:
        """代码审查"""
    
    # ===== 上下文理解 =====
    async def understand_project(self, path: str = ".") -> ProjectContext:
        """理解项目结构"""
        
    async def analyze_dependencies(self, path: str) -> DependencyGraph:
        """分析依赖关系"""
        
    async def semantic_search(self, query: str, path: str = ".") -> List[CodeChunk]:
        """语义搜索代码"""
```

#### 2. Claude Code Executor（执行器）

```python
# src/claude_code/executor.py

class ClaudeCodeExecutor:
    """Claude Code CLI 命令执行器"""
    
    def __init__(self, client: ClaudeCodeClient):
        self.client = client
        self.semaphore = asyncio.Semaphore(client.max_concurrent)
    
    async def execute(self, prompt: str, **kwargs) -> ExecutionResult:
        """执行Claude Code命令"""
        async with self.semaphore:  # 并发控制
            process = await asyncio.create_subprocess_exec(
                self.client.claude_path,
                '--print',  # 非交互模式
                '--output-format', 'json',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.client.working_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=self.client.timeout
            )
            
            return self._parse_result(stdout, stderr, process.returncode)
```

#### 3. Claude Code Tools（LangChain工具）

```python
# src/claude_code/tools.py
from langchain.tools import Tool

def create_claude_code_tools(client: ClaudeCodeClient) -> List[Tool]:
    """创建供LangChain使用的Claude Code工具集"""
    
    return [
        Tool(
            name="read_file",
            description="读取本地文件内容",
            func=lambda path: asyncio.run(client.read_file(path))
        ),
        Tool(
            name="write_file", 
            description="写入内容到本地文件",
            func=lambda args: asyncio.run(client.write_file(**args))
        ),
        Tool(
            name="edit_file",
            description="编辑本地文件（替换内容）",
            func=lambda args: asyncio.run(client.edit_file(**args))
        ),
        Tool(
            name="search_code",
            description="在代码库中搜索",
            func=lambda query: asyncio.run(client.grep(query))
        ),
        Tool(
            name="analyze_code",
            description="分析代码并回答问题",
            func=lambda args: asyncio.run(client.analyze_code(**args))
        ),
        Tool(
            name="generate_code",
            description="根据需求生成代码",
            func=lambda prompt: asyncio.run(client.generate_code(prompt))
        ),
        # ... 更多工具
    ]
```

### 智能体设计（精简版）

#### 1. Orchestrator Agent（编排智能体）
```
职责：
- 接收用户请求，分析意图
- 分解任务为子任务
- 决定是否需要：
  - 直接调用Claude Code CLI执行
  - 先通过RAG检索上下文
  - 通过Memory获取历史信息
- 汇总结果返回用户

核心逻辑：
1. 分析请求类型（文件操作/代码生成/问答/...）
2. 如需上下文 -> 调用RAG Agent
3. 如需历史 -> 调用Memory Agent
4. 组装完整上下文 -> 调用Claude Code CLI执行
5. 返回结果
```

#### 2. RAG Agent（检索智能体）
```
职责：
- 从向量数据库检索相关代码/文档
- 增强Claude Code CLI的上下文输入

数据来源：
- 代码库索引（通过Claude Code CLI读取后向量化）
- 文档知识库
- 数据库Schema
```

#### 3. Memory Agent（记忆智能体）
```
职责：
- 管理对话历史
- 存储重要上下文到长期记忆
- 检索相关历史信息

存储：
- 短期：内存
- 中期：Redis
- 长期：向量数据库
```

#### 4. Planning Agent（规划智能体）★ OpenSpec集成
```
职责：
- 复杂任务的分解和规划
- 将复杂任务拆解为多个OpenSpec变更提案
- 创建、验证、管理OpenSpec提案
- 生成执行计划（多步骤）
- 监控执行进度和提案状态

核心能力：
1. OpenSpec提案创建
   - 分析任务，识别需要创建提案的场景
   - 生成符合OpenSpec规范的proposal.md
   - 创建tasks.md和design.md（如需要）
   - 生成规范增量（specs/目录）

2. OpenSpec提案管理
   - 列出活动提案
   - 验证提案完整性
   - 检查提案冲突
   - 归档已完成的提案

3. 任务拆解
   - 将大型任务拆解为多个独立的OpenSpec提案
   - 识别提案间的依赖关系
   - 生成提案执行顺序

4. 提案执行跟踪
   - 跟踪提案状态（待批准/进行中/已完成）
   - 监控任务完成进度
   - 生成执行报告

输出：
- OpenSpec提案列表
- 提案依赖关系图
- 执行顺序建议
- 提案状态报告
```

### OpenSpec集成模块设计

#### 1. OpenSpec Client（CLI封装）

```python
# src/openspec/client.py

class OpenSpecClient:
    """OpenSpec CLI 客户端封装"""
    
    def __init__(self, openspec_dir: str = "openspec"):
        self.openspec_dir = openspec_dir
        self.cli_path = "openspec-cn"
    
    async def list_changes(self) -> List[ChangeInfo]:
        """列出所有活动变更"""
        # 调用: openspec-cn list --json
        
    async def list_specs(self) -> List[SpecInfo]:
        """列出所有规范"""
        # 调用: openspec-cn list --specs --json
        
    async def show_change(self, change_id: str) -> ChangeDetail:
        """显示变更详情"""
        # 调用: openspec-cn show <change-id> --json
        
    async def validate_change(self, change_id: str, strict: bool = True) -> ValidationResult:
        """验证变更提案"""
        # 调用: openspec-cn validate <change-id> --strict
        
    async def archive_change(self, change_id: str) -> bool:
        """归档变更"""
        # 调用: openspec-cn archive <change-id> --yes
```

#### 2. OpenSpec Parser（文件解析器）

```python
# src/openspec/parser.py

class OpenSpecParser:
    """解析OpenSpec文件结构"""
    
    def parse_proposal(self, proposal_path: str) -> Proposal:
        """解析proposal.md"""
        
    def parse_tasks(self, tasks_path: str) -> List[Task]:
        """解析tasks.md"""
        
    def parse_design(self, design_path: str) -> Design:
        """解析design.md"""
        
    def parse_spec(self, spec_path: str) -> Spec:
        """解析spec.md规范增量"""
        
    def parse_change_structure(self, change_dir: str) -> ChangeStructure:
        """解析整个变更目录结构"""
```

#### 3. OpenSpec Generator（提案生成器）

```python
# src/openspec/generator.py

class OpenSpecGenerator:
    """生成OpenSpec变更提案"""
    
    def __init__(self, client: OpenSpecClient, parser: OpenSpecParser):
        self.client = client
        self.parser = parser
    
    async def create_proposal(
        self,
        change_id: str,
        description: str,
        why: str,
        changes: List[str],
        impacts: Dict[str, Any]
    ) -> Proposal:
        """创建新的变更提案"""
        # 1. 生成proposal.md
        # 2. 创建目录结构
        # 3. 生成tasks.md骨架
        # 4. 返回提案对象
    
    async def generate_spec_increment(
        self,
        change_id: str,
        capability: str,
        requirements: List[Requirement]
    ) -> Spec:
        """生成规范增量"""
        # 1. 分析需求
        # 2. 生成spec.md
        # 3. 确保符合OpenSpec格式
    
    async def generate_tasks(
        self,
        change_id: str,
        plan: List[TaskStep]
    ) -> List[Task]:
        """根据执行计划生成tasks.md"""
    
    async def check_conflicts(
        self,
        new_change_id: str,
        new_specs: List[Spec]
    ) -> List[Conflict]:
        """检查与现有提案的冲突"""
```

#### 4. OpenSpec Validator（验证器）

```python
# src/openspec/validator.py

class OpenSpecValidator:
    """验证OpenSpec提案"""
    
    def __init__(self, client: OpenSpecClient):
        self.client = client
    
    async def validate_proposal(self, change_id: str) -> ValidationResult:
        """验证提案完整性"""
        # 1. 检查文件结构
        # 2. 调用openspec-cn validate
        # 3. 返回验证结果
    
    async def validate_spec_format(self, spec_path: str) -> bool:
        """验证规范格式"""
        # 检查需求格式、场景格式等
    
    async def check_required_files(self, change_dir: str) -> List[str]:
        """检查必需文件是否存在"""
```

#### 5. OpenSpec Manager（提案管理器）

```python
# src/openspec/manager.py

class OpenSpecManager:
    """管理OpenSpec变更提案"""
    
    def __init__(self, client: OpenSpecClient, generator: OpenSpecGenerator):
        self.client = client
        self.generator = generator
    
    async def break_down_task(
        self,
        task_description: str,
        context: Dict[str, Any]
    ) -> List[Proposal]:
        """将复杂任务拆解为多个提案"""
        # 1. 分析任务复杂度
        # 2. 识别可拆分的部分
        # 3. 为每个部分创建独立提案
        # 4. 识别依赖关系
        # 5. 返回提案列表和依赖图
    
    async def create_proposal_plan(
        self,
        proposals: List[Proposal]
    ) -> ProposalPlan:
        """创建提案执行计划"""
        # 1. 分析依赖关系
        # 2. 生成执行顺序
        # 3. 识别可并行执行的提案
    
    async def track_progress(
        self,
        change_id: str
    ) -> ProgressReport:
        """跟踪提案执行进度"""
        # 1. 读取tasks.md
        # 2. 统计完成的任务
        # 3. 生成进度报告
```

### LLM客户端封装设计（支持多种提供商）

#### 1. LLM基类接口

```python
# src/llm/base.py

from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage

class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    async def invoke(self, messages: List[BaseMessage], **kwargs) -> str:
        """调用LLM"""
        
    @abstractmethod
    async def stream(self, messages: List[BaseMessage], **kwargs):
        """流式调用LLM"""
        
    @abstractmethod
    def get_langchain_model(self) -> BaseLanguageModel:
        """获取LangChain兼容的模型实例"""
```

#### 2. LLM工厂

```python
# src/llm/factory.py

class LLMFactory:
    """根据配置创建LLM实例"""
    
    @staticmethod
    def create_llm(config: LLMConfig) -> BaseLLMClient:
        """根据LLM_PROVIDER创建对应的LLM客户端"""
        provider = config.provider.lower()
        
        if provider == "anthropic":
            return AnthropicLLMClient(config)
        elif provider == "openai":
            return OpenAILLMClient(config)
        elif provider == "local":
            return LocalLLMClient(config)
        elif provider == "azure_openai":
            return AzureOpenAILLMClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
```

#### 3. 各提供商实现示例

```python
# src/llm/anthropic.py
from langchain_anthropic import ChatAnthropic

class AnthropicLLMClient(BaseLLMClient):
    def __init__(self, config: LLMConfig):
        self.api_key = config.api_key
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    def get_langchain_model(self) -> BaseLanguageModel:
        return ChatAnthropic(
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

# src/llm/openai.py
from langchain_openai import ChatOpenAI

class OpenAILLMClient(BaseLLMClient):
    def __init__(self, config: LLMConfig):
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = config.base_url  # 可选，用于自定义端点
        # ...
    
    def get_langchain_model(self) -> BaseLanguageModel:
        return ChatOpenAI(
            api_key=self.api_key,
            model=self.model,
            base_url=self.base_url,
            # ...
        )

# src/llm/local.py
from langchain_community.llms import Ollama

class LocalLLMClient(BaseLLMClient):
    def __init__(self, config: LLMConfig):
        self.base_url = config.base_url or "http://localhost:11434"
        self.model = config.model
    
    def get_langchain_model(self) -> BaseLanguageModel:
        return Ollama(
            base_url=self.base_url,
            model=self.model
        )
```

#### 4. 配置加载

```python
# src/utils/config_loader.py

@dataclass
class LLMConfig:
    provider: str  # anthropic, openai, local, etc.
    api_key: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        return cls(
            provider=os.getenv("LLM_PROVIDER", "anthropic"),
            api_key=os.getenv("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            base_url=os.getenv("LLM_BASE_URL")
        )
```

### Planning Agent 与 OpenSpec 集成流程

```
用户："实现用户认证、权限管理和审计日志功能"

1. Planning Agent 分析：
   - 识别这是大型任务
   - 需要拆解为多个OpenSpec提案
   
2. 任务拆解：
   - Proposal 1: add-user-authentication
   - Proposal 2: add-permission-management  
   - Proposal 3: add-audit-logging
   - 识别依赖：Proposal 2 依赖 Proposal 1
   
3. 创建OpenSpec提案：
   - 调用OpenSpecGenerator创建每个提案
   - 生成proposal.md, tasks.md, specs/
   - 验证提案格式
   
4. 生成执行计划：
   - 按依赖关系排序
   - 生成执行顺序建议
   - 返回提案列表和计划
   
5. 用户批准后：
   - 按计划执行提案
   - 跟踪每个提案的进度
   - 完成后归档提案
```

### LangGraph工作流

```python
# 状态定义
class AgentState(TypedDict):
    messages: List[BaseMessage]       # 消息历史
    current_task: str                 # 当前任务
    context: Dict[str, Any]           # RAG检索的上下文
    memory: Dict[str, Any]            # 记忆上下文
    plan: List[TaskStep]              # 执行计划
    openspec_proposals: List[Proposal]  # OpenSpec提案列表
    openspec_plan: ProposalPlan       # 提案执行计划
    claude_code_result: Any           # Claude Code执行结果
    final_response: str               # 最终响应

# 工作流图
graph = StateGraph(AgentState)

# 节点
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("rag", rag_node)
graph.add_node("memory", memory_node)
graph.add_node("planning", planning_node)
graph.add_node("openspec", openspec_node)  # OpenSpec提案管理节点
graph.add_node("claude_code", claude_code_node)  # 核心执行节点

# 路由逻辑
graph.add_conditional_edges(
    "orchestrator",
    route_decision,
    {
        "need_context": "rag",
        "need_memory": "memory", 
        "need_plan": "planning",
        "need_openspec": "openspec",  # 需要创建/管理提案
        "execute": "claude_code",  # 直接执行
        "end": END
    }
)

# Planning Agent -> OpenSpec (创建提案)
graph.add_edge("planning", "openspec")

# OpenSpec -> Claude Code (执行提案)
graph.add_edge("openspec", "claude_code")

# RAG/Memory完成后 -> Claude Code执行
graph.add_edge("rag", "claude_code")
graph.add_edge("memory", "claude_code")
graph.add_edge("planning", "claude_code")

# Claude Code执行完成 -> 返回Orchestrator汇总
graph.add_edge("claude_code", "orchestrator")
```

### 典型执行流程

```
用户："帮我在user_api.py中添加一个获取用户列表的接口"

1. Orchestrator 分析：
   - 任务类型：代码生成
   - 需要上下文：是（了解现有代码结构）
   
2. RAG Agent 检索：
   - 检索 user_api.py 相关代码片段
   - 检索 API开发规范文档
   
3. Memory Agent 检索：
   - 检索之前的相关对话
   
4. Claude Code CLI 执行：
   - 输入：用户请求 + RAG上下文 + 记忆上下文
   - 操作：
     a. read_file("user_api.py") 读取当前代码
     b. analyze_code() 理解结构
     c. generate_code() 生成新接口代码
     d. edit_file() 写入修改
   - 输出：修改结果

5. Orchestrator 汇总：
   - 整理执行结果
   - 返回给用户
```

## 决策

### 决策1：Claude Code CLI作为核心引擎
- **选择**：所有本地文件操作和coding能力通过Claude Code CLI实现
- **理由**：
  - Claude Code CLI具有完整的本地上下文理解能力
  - 原生支持代码分析、生成、修改
  - 支持项目级别的语义理解
  - 避免重复实现文件操作逻辑
- **架构影响**：
  - 其他智能体负责编排和上下文增强
  - Claude Code CLI是唯一的执行引擎

### 决策2：向量数据库选择
- **选择**：ChromaDB
- **理由**：
  - 轻量级，易于部署
  - Python原生支持
  - 支持持久化
  - LangChain集成良好
- **替代方案**：
  - FAISS：性能更好，但不支持持久化元数据
  - Milvus：功能强大，但部署复杂

### 决策3：记忆持久化策略
- **选择**：分层存储
  - 短期：内存（会话级）
  - 中期：Redis（跨会话，TTL）
  - 长期：ChromaDB（永久）
- **理由**：平衡性能和持久性

### 决策4：配置管理
- **选择**：.env + YAML + Pydantic验证
- **理由**：
  - .env管理敏感信息（API密钥、连接字符串）
  - YAML管理非敏感配置（Prompts、工作流）
  - Pydantic提供类型安全和验证
  - python-dotenv自动加载环境变量
- **配置优先级**：环境变量 > .env文件 > YAML默认值

### 决策5：.env配置项设计

```bash
# .env.example 模板

# ===== Claude Code CLI配置（核心）=====
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_TIMEOUT=300
CLAUDE_CODE_MAX_CONCURRENT=2
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform

# ===== LLM配置（用于RAG等智能体）=====
# LLM提供商：anthropic, openai, local, azure_openai, google等
LLM_PROVIDER=anthropic
LLM_API_KEY=your_llm_api_key
LLM_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
# 对于本地模型或自定义端点
# LLM_BASE_URL=http://localhost:8000/v1
# 对于OpenAI兼容的API
# LLM_API_TYPE=open_ai
# 对于Azure OpenAI
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_VERSION=2024-02-15-preview

# ===== 向量数据库配置 =====
VECTOR_DB_TYPE=chromadb
CHROMA_PERSIST_DIR=./data/chroma

# ===== 记忆系统配置 =====
MEMORY_BACKEND=redis
REDIS_URL=redis://localhost:6379/1
MEMORY_TTL=86400

# ===== 日志配置 =====
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_FORMAT=json
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5

# ===== RAG配置 =====
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
RAG_TOP_K=5
# 嵌入模型配置（可选，默认使用LLM提供商的嵌入模型）
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your_embedding_api_key
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|----------|
| Claude Code CLI不可用 | 启动时检查，给出明确错误提示 |
| Claude Code CLI执行超时 | 可配置超时，支持取消操作 |
| 并发调用资源竞争 | 信号量控制并发数 |
| 向量索引过大 | 增量索引，分片存储 |
| Prompts质量 | 提供调试模式，Prompt版本管理 |

## 迁移计划

无需迁移，新增模块。

### 部署步骤
1. 确保Claude Code CLI已安装并可用
2. 安装依赖：`pip install -r AIagent/requirements.txt`
3. 复制并配置环境变量：`cp .env.example .env`
4. 初始化向量数据库：`python -m AIagent.scripts.init_db`
5. 索引代码库（可选）：`python -m AIagent.scripts.index_codebase`

## 待决问题

1. 是否需要提供REST API暴露AI能力？
2. 是否需要与Django后端深度集成？
3. 向量数据库是否需要独立部署？
