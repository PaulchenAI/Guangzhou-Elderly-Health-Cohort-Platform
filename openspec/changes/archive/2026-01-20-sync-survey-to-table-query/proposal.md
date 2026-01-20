# 变更：问卷数据同步到表查询系统

## 为什么

问卷系统和表查询系统的数据结构不同，导致数据查询不方便：
- 问卷系统使用 JSON 字段存储数据（survey_data, patient_info, scores 等），查询时需要解析 JSON
- 表查询系统使用关系型数据库表结构，支持动态查询和联合查询
- 两个系统的数据查询方式不一致，用户需要在两个系统间切换

通过将问卷数据同步到表查询系统，可以实现：
- 统一的数据查询体验
- 支持联合查询（将问卷数据与其他表关联）
- 更好的查询性能和索引支持
- 利用表查询系统的动态查询能力

## 变更内容

- **新增功能**：问卷数据自动同步到表查询系统
  - 每次同步问卷数据时，自动将数据导入到对应的表查询配置中
  - 根据不同的问卷类型建立不同的表（如 `survey_personality`, `survey_outdoor_activity` 等）
  - 将 JSON 字段展开为关系型表的列（参考前端数据展示方式）

- **数据转换**：JSON 数据扁平化处理
  - 将 `survey_data`、`patient_info`、`scores` 等 JSON 字段展开为独立列
  - 处理嵌套结构（如 `personalityScores.totalScore` → `personalityScores_totalScore`）
  - 保留原始 JSON 字段用于完整数据查询

- **配置管理**：自动创建和维护表查询配置
  - 根据问卷 Schema 自动生成表查询配置
  - 字段类型推断和显示名称映射
  - 支持可搜索、可排序字段配置

- **同步机制**：集成到现有同步流程
  - 在 `SurveyService.import_data()` 中增加表查询系统同步逻辑
  - 支持增量同步和全量同步
  - 错误处理和回滚机制

## 影响

- **受影响规范**：
  - `survey`：新增数据同步到表查询系统的需求
  - `database-table-query`：新增自动配置创建和数据导入的需求

- **受影响代码**：
  - `core/survey/survey_service.py`：增加表查询系统同步逻辑
  - `core/survey/survey_model.py`：可能需要增加同步状态字段
  - `core/table_query/table_query_service.py`：新增数据导入和配置生成功能
  - `core/table_query/table_query_model.py`：可能需要增加同步元数据

- **数据库变更**：
  - 为每个问卷类型创建对应的数据表（如 `survey_personality`）
  - 表结构包含展开后的字段和原始 JSON 字段
