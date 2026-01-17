# 变更：基于 Excel 预设表单名称重新推断表含义

## 为什么

`docs/hospital/docs/NHMS_WORKFLOW_BILL.xlsx` 文件包含 330 个预设表单的元数据，包括：
- `TABLENAME`：表名（如 `formtable_main_59`、`FORMTABLE_MAIN_41`）
- `FORMDES`：表单分类描述（如 "院前评估"、"服务评估表"、"康复报工服务表单"）
- `NAMELABEL`：表单的中文名称（如 "社会参与评估表（院前评估）"、"跌倒/坠床风险评估"）

目前 `docs/hospital/commentsql/` 目录中已有这些表的推断结果（如 `FORMTABLE_MAIN_29_meaning.json`），但这些推断是基于 SQL 字段名进行的，缺乏业务上下文。

通过将 Excel 中的 `FORMDES` 和 `NAMELABEL` 作为上下文信息提供给 LLM，可以显著提高推断的准确性：
1. **表含义更准确**：直接使用 `NAMELABEL` 作为表的中文名称
2. **字段推断更精准**：LLM 知道表的业务用途后，能更准确地推断字段含义
3. **置信度更高**：有明确的业务上下文，推断结果更可靠

## 变更内容

- 新增 `reinfer-from-excel` CLI 命令：
  - 读取 Excel 文件中的表名和业务描述
  - 在 `commentsql` 目录中查找对应的 JSON 文件
  - 如果 JSON 存在，读取原始 SQL 文件并结合 Excel 元数据重新推断
  - 如果 JSON 不存在，跳过该表
- 扩展 `SQLMeaningInferencer` 类：
  - 新增 `infer_with_context()` 方法，支持传入业务上下文
  - 新增 `reinfer_from_excel()` 方法，批量处理 Excel 中的表
- 新增专用提示词模板，包含表单分类和中文名称上下文

## 影响

- 受影响规范：`sql-import`
- 受影响代码：
  - 修改：`AIagent/src/sql_import/sql_meaning_llm.py` - 新增上下文推断方法
  - 修改：`AIagent/src/sql_import/sql_meaning_cli.py` - 新增 CLI 命令
