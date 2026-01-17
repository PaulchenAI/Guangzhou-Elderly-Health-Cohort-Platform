## 1. 实施

### 1.1 核心推断器
- [x] 创建 `sql_meaning_llm.py`，实现 SQLMeaningInferencer 类
- [x] 实现 SQL 文件读取功能
- [x] 实现 LLM 提示词构建
- [x] 集成 AIagent LLM 客户端（支持多提供商）
- [x] 支持配置表名前缀忽略（参数 `ignore_prefix`，默认 `gzlry_`）
- [x] 支持自定义提示词模板
- [x] 实现单文件推断 `infer_file()`
- [x] 实现批量推断 `infer_directory()`

### 1.2 JSON 格式验证
- [x] 定义 Pydantic 验证模型（MeaningInfo, FieldInfo, LLMOutputSchema）
- [x] 实现 `_get_validation_errors()` 方法
- [x] 实现 `_validate_output()` 方法

### 1.3 重试机制
- [x] 实现带上下文的重试 `_infer_with_llm()`
- [x] 实现重试提示词构建 `_build_retry_prompt()`
- [x] 支持最多 3 次重试（1 次初始 + 2 次重试）
- [x] 将验证错误信息作为上下文传递给 LLM

### 1.4 CLI 命令行接口
- [x] 创建 `sql_meaning_cli.py`，实现 CLI 命令
- [x] 实现 `infer-file` 命令（单文件推断）
- [x] 实现 `infer-dir` 命令（批量推断）
- [x] 支持输出路径参数（`-o` 或 `--output`）
- [x] 支持表名前缀配置参数（`--ignore-prefix`，默认 `gzlry_`）
- [x] 支持自定义提示词模板参数（`--prompt-template <file>`）
- [x] 默认输出到 `docs/hospital/commentsql` 目录
- [x] 支持 `--skip-existing` 参数（跳过已存在结果）
- [x] 支持 `--retry-failed` 参数（只重试失败任务）
- [x] 实现 `clear-errors` 命令（清除错误日志）

### 1.5 错误日志与任务管理
- [x] 实现错误日志记录 `_save_error_log()`
- [x] 实现获取失败任务列表 `_get_failed_files()`
- [x] 实现清除错误日志 `clear_error_log()`
- [x] 支持跳过已存在结果的逻辑

### 1.6 并发处理
- [x] 使用 `asyncio.Semaphore` 控制并发数量
- [x] 实现 `_process_file_with_semaphore()` 方法
- [x] 支持 `-c/--concurrency` CLI 参数
- [x] 默认并发数为 1（顺序处理）

### 1.7 模块导出
- [x] 更新 `sql_import/__init__.py`，导出 SQLMeaningInferencer

### 1.8 清理旧实现
- [x] 删除 `sql_parser_agent.py`（已废弃）
- [x] 删除 `meaning_inference_agent.py`（已废弃）
- [x] 删除 `result_writer_agent.py`（已废弃）
- [x] 删除 `graph_sql_meaning.py`（已废弃）
- [x] 删除 `table_meaning_cli.py`（已废弃）
- [x] 删除 `table_meaning_schema.py`（已废弃）
- [x] 更新 `agents/__init__.py`，移除已删除的导出
- [x] 更新 `core/__init__.py`，移除已删除的导出
- [x] 清理 `core/state.py` 中的 SQL 相关字段

## 2. 测试

- [x] 使用真实 SQL 文件测试单文件推断功能
- [x] 验证输出 JSON 格式正确性（Pydantic 验证通过）
- [x] 验证表名前缀忽略功能（`--ignore-prefix gzlry_`）
- [x] 验证 CLI 帮助信息和参数解析

## 3. 文档

- [x] 为 SQLMeaningInferencer 添加文档字符串
- [x] 为 CLI 命令添加帮助信息
- [x] 更新 `AIagent/README.md`，添加 SQL 含义推断功能说明
- [x] 添加使用示例、CLI 命令说明、输出格式示例
