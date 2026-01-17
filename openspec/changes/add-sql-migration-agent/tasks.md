## 1. 基础架构

- [ ] 1.1 创建 `MigrationState` 状态模型（AIagent/src/sql_import/migration_state.py）
- [ ] 1.2 创建 `SQLMigrationAgent` 智能体类（AIagent/src/agents/sql_migration_agent.py）
- [ ] 1.3 创建阶段检查器 `StageChecker`（AIagent/src/sql_import/stage_checker.py）

## 2. 阶段实现

- [ ] 2.1 实现阶段1：Oracle 转 MySQL（集成现有 convert-all 命令）
- [ ] 2.2 实现阶段2：MySQL 脚本修复（调用现有修复逻辑）
- [ ] 2.3 实现阶段3：MySQL 导入（集成现有 import-all 命令，支持批次管理）
- [ ] 2.4 实现阶段4：Table Config 生成（集成 batch_create_table_configs Django 命令）
- [ ] 2.5 实现阶段5：中文含义推理（集成 infer-dir 命令，支持 CSV 上下文）
- [ ] 2.6 实现阶段6：含义导入 Config（更新 TableQueryConfig 的 displayName 字段）

## 3. LangGraph 工作流

- [ ] 3.1 创建迁移工作流图（AIagent/src/sql_import/migration_workflow.py）
- [ ] 3.2 实现节点函数（convert_node, fix_node, import_node, config_node, infer_node, apply_node）
- [ ] 3.3 实现条件路由逻辑（根据阶段状态决定流向）
- [ ] 3.4 集成 Claude Code CLI 执行器

## 4. CLI 接口

- [ ] 4.1 创建 migration_cli.py 命令行入口
- [ ] 4.2 实现 `start` 命令（启动新迁移）
- [ ] 4.3 实现 `status` 命令（查看当前进度）
- [ ] 4.4 实现 `resume` 命令（断点续做）
- [ ] 4.5 实现 `retry-failed` 命令（重试失败项）

## 5. 自然语言交互

- [ ] 5.1 创建自然语言接口模块（AIagent/src/sql_import/nl_interface.py）
- [ ] 5.2 实现意图识别器 IntentRecognizer（使用 LLM 解析用户意图）
- [ ] 5.3 实现意图路由器 IntentRouter（将意图映射到具体操作）
- [ ] 5.4 实现响应生成器 ResponseGenerator（生成友好的中文响应）
- [ ] 5.5 实现 `chat` 命令（交互式对话模式）
- [ ] 5.6 集成到 LangGraph 工作流（添加 chat_node 节点）

## 6. 测试与文档

- [ ] 6.1 编写单元测试（状态模型、阶段检查器、意图识别）
- [ ] 6.2 编写集成测试（完整流程模拟、自然语言交互）
- [ ] 6.3 更新 AIagent/README.md 文档

## 依赖关系

```
1.1 ──┬──> 2.* (所有阶段实现依赖状态模型)
      │
1.2 ──┼──> 3.* (工作流依赖智能体类)
      │
1.3 ──┴──> 4.* (CLI 依赖检查器)

2.* ──> 3.* (工作流节点依赖阶段实现)

3.* ──> 4.* (CLI 依赖工作流)

4.* ──> 5.* (自然语言交互依赖 CLI)

5.* ──> 6.* (测试依赖所有模块)
```
