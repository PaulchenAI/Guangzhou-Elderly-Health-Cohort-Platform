# 变更：SQL 表名和字段名中文含义推断

## 为什么

`docs/hospital/convertsql/create` 目录包含大量已转换的 MySQL SQL 文件（约 100+ 个），这些文件中的表名和字段名存在以下问题：

1. **命名不统一**：部分表/字段有中文 COMMENT，部分没有
2. **拼音缩写难以理解**：如 `xh`（序号）、`zyh`（住院号）、`xm`（姓名）等
3. **英文缩写含义不明确**：如 `WM_WAREHOUSE`、`WORKFLOW_BILL` 等需要推断中文含义
4. **前缀干扰**：所有表名都有 `gzlry_` 前缀，需要忽略

目前缺乏自动化工具来推断这些表名和字段名的中文含义。需要一个工具能够：
1. 读取 SQL 文件内容
2. 使用 LLM 智能推断表名和字段名的中文含义
3. 验证 LLM 输出格式，支持自动重试
4. 输出结构化的 JSON 结果，包含推断含义、置信度、推理过程等

## 变更内容

- 新增 `SQLMeaningInferencer` 类，直接使用 LLM 处理原始 SQL：
  - 读取 SQL 文件，发送给 LLM 进行解析和推断
  - 使用 Pydantic 模型验证 LLM 输出的 JSON 格式
  - 支持带上下文的重试机制（验证失败时传递错误信息给 LLM）
  - 支持单文件和批量处理
- 输出结构化 JSON，包含表含义、字段含义、置信度、推理过程
- 提供 CLI 命令行接口：
  - `infer-file`：单文件推断
  - `infer-dir`：批量推断
  - 支持自定义输出路径、前缀忽略、提示词模板
- 默认输出到 `docs/hospital/commentsql` 目录

## 影响

- 受影响规范：`sql-import`
- 受影响代码：
  - 新增：`AIagent/src/sql_import/sql_meaning_llm.py` - 核心推断器
  - 新增：`AIagent/src/sql_import/sql_meaning_cli.py` - CLI 命令行接口
  - 修改：`AIagent/src/sql_import/__init__.py` - 导出新功能
