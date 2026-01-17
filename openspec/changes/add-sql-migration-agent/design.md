## 上下文

Oracle 到 MySQL 迁移是一个多阶段、长时间运行的任务，需要：
- 大文件处理能力
- 进度追踪和状态持久化
- 错误恢复和断点续做
- 与现有 CLI 工具集成（convert、import、infer 等命令）

当前 AIagent 项目已有 LangGraph 架构和 sql_import 模块，本变更将在此基础上扩展。

## 目标 / 非目标

**目标：**
- 统一管理迁移流程的 6 个阶段
- 提供进度检查和状态报告
- 支持通过 Claude Code CLI 执行命令
- 集成现有的 sql_import 模块工具
- **支持自然语言交互**，用户可以用中文与智能体对话

**非目标：**
- 不重写现有的转换/导入逻辑
- 不提供 GUI 界面
- 不实现并行处理（保持简单）

## 决策

### 架构决策：LangGraph 多阶段工作流

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │              SQLMigrationAgent (Orchestrator)                │
                    │  - 任务分解与调度                                              │
                    │  - 进度检查与状态管理                                           │
                    │  - 错误处理与重试决策                                           │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │
        ┌──────────────┬──────────────┬───────────┼───────────┬──────────────┬──────────────┐
        ▼              ▼              ▼           ▼           ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌─────────┐
   │  阶段1   │   │  阶段2   │   │  阶段3   │  │  阶段4   │  │  阶段5   │  │  阶段6   │   │ Claude  │
   │ Oracle  │   │  MySQL  │   │  MySQL  │  │ Table   │  │  中文    │  │ 导入    │   │  Code   │
   │ 转换    │   │  修复   │   │  导入   │  │ Config  │  │ 推理    │  │ Config  │   │  CLI    │
   └─────────┘   └─────────┘   └─────────┘  └─────────┘  └─────────┘  └─────────┘   └─────────┘
```

### 状态模型设计

```python
class MigrationState(TypedDict):
    # 阶段状态
    current_stage: str  # convert | fix | import | config | infer | apply
    stage_status: Dict[str, StageStatus]  # 每个阶段的状态
    
    # 进度追踪
    total_files: int
    processed_files: int
    failed_files: List[str]
    
    # 配置
    source_dir: str  # Oracle SQL 目录
    output_dir: str  # 转换后 MySQL SQL 目录
    meaning_dir: str  # 中文含义 JSON 目录
    csv_context_file: Optional[str]  # 外部 CSV 上下文
    
    # 批次管理
    batch_id: str
    batch_status: Dict[str, Any]
```

### 阶段定义

| 阶段 | 名称 | 输入 | 输出 | 检查点 |
|------|------|------|------|--------|
| 1 | convert | Oracle SQL 文件 | MySQL SQL 文件 | 转换后文件数量 |
| 2 | fix | MySQL SQL 文件 | 修复后的 SQL | 语法验证通过 |
| 3 | import | MySQL SQL 文件 | 数据库表 | sql_import_log 表状态 |
| 4 | config | 数据库表 | TableQueryConfig | 配置记录数量 |
| 5 | infer | SQL 文件 | *_meaning.json | JSON 文件数量 |
| 6 | apply | meaning.json | 更新的 Config | 字段含义更新数 |

### Claude Code CLI 集成

智能体通过 `ClaudeCodeClient` 执行命令，支持以下操作：
- 执行 Python 模块命令（如 `python -m AIagent.src.sql_import convert`）
- 执行 Django 管理命令（如 `python manage.py batch_create_table_configs`）
- 读取文件内容验证结果
- 搜索文件统计数量

### 自然语言交互架构

```
用户自然语言输入
        │
        ▼
┌───────────────────┐
│  意图识别 (LLM)    │  ← 使用 LLM 解析用户意图
│  - 查询类意图       │     (status/progress/help)
│  - 操作类意图       │     (start/resume/retry/skip)
│  - 配置类意图       │     (set source/output/etc)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  意图路由器        │  ← 将意图映射到具体操作
│  IntentRouter     │
└─────────┬─────────┘
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
┌─────┐┌─────┐┌─────┐
│查询 ││操作 ││配置 │
│处理 ││执行 ││更新 │
└─────┘└─────┘└─────┘
          │
          ▼
┌───────────────────┐
│  响应生成 (LLM)    │  ← 生成友好的中文响应
└───────────────────┘
```

**支持的自然语言指令示例：**

| 用户输入 | 识别意图 | 执行操作 |
|---------|---------|---------|
| "当前进度怎么样？" | query_status | 调用 StageChecker，返回进度报告 |
| "开始迁移任务" | start_migration | 执行 start 命令 |
| "继续上次的任务" | resume_migration | 执行 resume 命令 |
| "跳过当前阶段" | skip_stage | 标记当前阶段完成，进入下一阶段 |
| "重试失败的文件" | retry_failed | 执行 retry-failed 命令 |
| "有哪些文件失败了？" | query_failed | 列出失败文件 |
| "帮助" / "怎么使用？" | help | 显示使用说明 |
| "设置源目录为 xxx" | set_config | 更新配置 |

**意图识别 Prompt 模板：**

```
你是一个 SQL 迁移助手。根据用户输入，识别其意图并返回 JSON 格式结果。

可能的意图类型：
- query_status: 查询进度/状态
- query_failed: 查询失败文件
- start_migration: 开始新迁移
- resume_migration: 继续迁移
- retry_failed: 重试失败
- skip_stage: 跳过阶段
- set_config: 设置配置
- help: 帮助

用户输入: {user_input}

返回 JSON: {"intent": "xxx", "params": {...}}
```

## 风险 / 权衡

- **风险**：大文件处理可能导致内存问题 → 使用流式处理和批次管理
- **风险**：LLM 调用失败 → 实现重试机制和错误日志
- **权衡**：单智能体 vs 多智能体 → 选择单智能体，内部分阶段，简化状态管理
- **权衡**：串行 vs 并行处理 → 选择串行处理，保持简单，后续可优化

## 待决问题

- [ ] CSV 上下文文件的具体格式规范（建议复用 NHMS_WORKFLOW_BILL.xlsx 格式）
