# 变更：添加 SQL 迁移智能体

## 为什么

Oracle 到 MySQL 的迁移流程涉及多个复杂步骤（转换、修复、导入、配置生成、中文含义推理），目前需要手动依次执行多个命令，容易出错且难以追踪进度。需要一个基于 LangGraph + Claude Code CLI 的智能体来自动化管理整个流程，并能智能检查每个阶段的完成进度。

## 变更内容

- 新增 `SQLMigrationAgent` 智能体，基于 LangGraph + Claude Code CLI
- 支持 6 个阶段的任务管理：
  1. Oracle 脚本转 MySQL 脚本
  2. MySQL 脚本修复
  3. MySQL 脚本导入（大文件和批次管理）
  4. Table config 生成导入
  5. 中文含义 LLM 推理（支持外部 CSV 上下文）
  6. 将中文含义导入 table config
- 智能检查每个阶段的完成进度
- 支持断点续做和失败重试
- 提供 CLI 命令行使用方式
- **支持自然语言交互**：用户可以通过自然语言与智能体对话，查询进度、执行操作、获取帮助

## 影响

- 受影响规范：sql-import（新增需求）
- 受影响代码：
  - `AIagent/src/agents/sql_migration_agent.py`（新增）
  - `AIagent/src/sql_import/migration_workflow.py`（新增）
  - `AIagent/src/sql_import/migration_state.py`（新增）
  - `AIagent/src/sql_import/migration_cli.py`（新增）
  - `AIagent/src/sql_import/stage_checker.py`（新增）
  - `AIagent/src/sql_import/nl_interface.py`（新增 - 自然语言接口）
