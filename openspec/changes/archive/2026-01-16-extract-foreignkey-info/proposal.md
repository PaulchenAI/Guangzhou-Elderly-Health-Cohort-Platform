# 变更：从 SQL 文件中提取外键关联信息并保存为 JSON

## 为什么

`docs/hospital/sql` 目录包含 954 个 Oracle SQL 文件，这些文件中包含了大量的外键约束信息（`alter table ... add constraint ... foreign key` 语句）。这些外键关系定义了表与表之间的关联关系，对于理解数据库结构、生成 ER 图、进行数据迁移分析等场景非常重要。

目前这些外键信息分散在各个 SQL 文件中，没有统一的提取和结构化存储方式。需要一个工具能够：
1. 解析 SQL 文件中的外键约束定义
2. 提取完整的关联信息（约束名称、源表、源字段、目标表、目标字段、删除规则等）
3. 以 JSON 格式统一保存到 `docs/hospital/foreignkey` 目录

## 变更内容

- 添加 SQL 外键信息提取功能到 `sql-import` 模块
- **多策略提取**：支持多种 SQL 格式的外键约束解析
  - 策略 1：正则表达式提取（标准 Oracle 格式）
  - 策略 2：自定义解析脚本（特殊格式）
  - 策略 3：LLM 辅助生成提取脚本（未知格式）
- **智能格式识别**：自动判断 SQL 文件格式并选择合适的提取策略
- **LLM 集成**：使用 Claude API 分析未知格式并生成提取脚本
- 提取外键的完整元数据信息
- 将提取结果保存为结构化的 JSON 文件
- 支持单文件和批量提取两种模式
- 生成外键关系统计报告和格式分析报告

## 影响

- 受影响规范：`sql-import`、`aiagent`
- 受影响代码：
  - 新增：`AIagent/sql_import/foreignkey_extractor.py` - 外键提取器（多策略）
  - 新增：`AIagent/sql_import/foreignkey_strategies.py` - 提取策略集合
  - 新增：`AIagent/sql_import/foreignkey_llm_helper.py` - LLM 辅助脚本生成
  - 新增：`AIagent/sql_import/foreignkey_cli.py` - CLI 命令
  - 修改：`AIagent/sql_import/__init__.py` - 导出新功能
  - 新增：`docs/hospital/foreignkey/` - 存储 JSON 文件
  - 新增：`docs/hospital/foreignkey/generated_strategies/` - LLM 生成的提取脚本
