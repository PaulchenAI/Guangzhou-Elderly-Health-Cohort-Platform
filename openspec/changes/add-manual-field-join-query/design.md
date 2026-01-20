# 设计文档：支持手动字段匹配的联合查询

## 上下文

当前联合查询基于外键元数据（`ForeignKeyMetadata`）自动发现关联关系。但实际业务中，有些表之间虽然没有外键关系，但可以通过字段值匹配进行关联（如问卷调查的 `patient_name` 与 `BS_OLDER` 的 `name`）。

用户需要：
1. 保留原有的外键关联功能（不影响现有功能）
2. 能够手动指定字段匹配规则进行关联
3. 两种关联方式可以同时使用

## 目标 / 非目标

**目标：**
- 保留原有外键关联功能，完全向后兼容
- 支持用户手动指定字段匹配关联
- 两种关联方式可以同时使用
- 支持精确匹配和模糊匹配
- 自动处理重复关联（避免同一表被关联两次）

**非目标：**
- 不修改外键关联逻辑
- 不创建新的关联规则管理表（直接在查询时指定）
- 不提供关联规则持久化功能
- 不支持手动关联的多级递归（手动关联深度固定为1）

## 决策

### 决策 1：在查询参数中支持手动关联

**选择**：在 `JoinQueryIn` Schema 中新增 `manual_joins` 参数，格式如下：

```json
{
  "primary_table": "survey_record",
  "manual_joins": [
    {
      "source_field": "patient_name",
      "target_table": "BS_OLDER",
      "target_field": "name",
      "match_type": "exact"
    }
  ],
  "filters": [...],
  "page": 1,
  "page_size": 20
}
```

**理由：**
- 灵活，每次查询可以指定不同的关联规则
- 不需要额外的配置管理
- 与现有 API 参数格式一致
- 简单直接，易于理解和使用

**替代方案：**
- 创建关联规则管理表：会增加复杂度，且用户可能只需要临时关联
- 修改外键元数据表：会污染外键数据，且不符合语义

### 决策 2：手动关联与外键关联合并处理

**选择**：在 `JoinQueryBuilder` 中，将手动关联转换为 `JoinRelation` 对象，与外键关联统一处理。

**实现方式：**
```python
# 1. 解析外键关联（原有逻辑）
fk_relations = self._parse_foreign_key_relations()

# 2. 转换手动关联为 JoinRelation
manual_relations = []
for manual_join in manual_joins:
    relation = JoinRelation(
        table_name=manual_join["target_table"],
        join_depth=1,  # 手动关联默认深度为1
        source_table=primary_table,
        source_columns=[manual_join["source_field"]],
        target_columns=[manual_join["target_field"]],
    )
    manual_relations.append(relation)

# 3. 合并两种关联，去重
all_relations = self._merge_and_deduplicate(fk_relations, manual_relations)
```

**理由：**
- 复用现有的 SQL 构建逻辑
- 代码改动最小
- 保持一致性
- 易于维护

### 决策 3：手动关联的 JOIN 条件构建

**选择**：根据 `match_type` 构建不同的 JOIN 条件：

- `exact`（精确匹配，默认）：`source_table.source_field = target_table.target_field`
- `fuzzy`（模糊匹配）：`source_table.source_field LIKE CONCAT('%', target_table.target_field, '%')`

**理由：**
- 精确匹配性能好，适合大多数场景
- 模糊匹配提供灵活性，适合名称不完全一致的情况
- 默认使用精确匹配，符合用户预期

**注意**：模糊匹配可能导致性能下降，建议在文档中说明。

### 决策 4：重复关联处理

**选择**：如果手动关联的目标表已在外键关联中存在，则跳过手动关联（外键关联优先）。

**理由：**
- 避免重复 JOIN 同一张表
- 外键关联更可靠（有明确的元数据支持）
- 减少 SQL 复杂度

### 决策 5：手动关联深度限制

**选择**：手动关联的深度固定为 1（只关联一级），不支持递归关联。

**理由：**
- 简化实现
- 避免复杂的递归逻辑
- 如果用户需要多级关联，可以通过多次查询或外键关联实现

## 风险 / 权衡

### 风险 1：性能问题
- **风险**：模糊匹配可能导致性能下降，特别是大数据量时
- **缓解措施**：
  - 默认使用精确匹配
  - 在文档中说明模糊匹配的性能影响
  - 建议在关联字段上建立索引
  - 限制手动关联表数量（最多5个）

### 风险 2：字段名冲突
- **风险**：手动关联的字段可能与外键关联字段冲突
- **缓解措施**：
  - 使用表名前缀区分字段（现有机制）
  - 检查重复关联（同一表只关联一次）

### 风险 3：参数验证复杂度
- **风险**：需要验证表名、字段名的存在性
- **缓解措施**：
  - 复用现有的表存在性检查函数
  - 在构建 SQL 前进行验证
  - 提供清晰的错误信息

## 实现细节

### Schema 扩展

```python
class ManualJoin(Schema):
    """手动字段匹配关联"""
    source_field: str = Field(..., description="源字段名（主表的字段）")
    target_table: str = Field(..., description="目标表名")
    target_field: str = Field(..., description="目标字段名")
    match_type: str = Field("exact", description="匹配类型: exact(精确) | fuzzy(模糊)")

class JoinQueryIn(Schema):
    # ... 现有字段 ...
    manual_joins: Optional[List[ManualJoin]] = Field(
        None,
        description="手动字段匹配关联列表"
    )
```

### JOIN 条件构建

在 `JoinSQLBuilder.build_from_clause` 中，根据 `match_type` 构建不同的 JOIN 条件：

```python
# 精确匹配
if match_type == "exact":
    join_condition = f"{source_table}.{source_field} = {target_table}.{target_field}"
# 模糊匹配
else:
    join_condition = f"{source_table}.{source_field} LIKE CONCAT('%', {target_table}.{target_field}, '%')"
```

### 关联去重逻辑

```python
def _merge_and_deduplicate(fk_relations, manual_relations):
    """合并外键关联和手动关联，去除重复"""
    all_relations = list(fk_relations)
    fk_target_tables = {r.table_name for r in fk_relations}
    
    for manual_relation in manual_relations:
        # 如果手动关联的目标表已在外键关联中存在，跳过
        if manual_relation.table_name not in fk_target_tables:
            all_relations.append(manual_relation)
    
    return all_relations
```

## 迁移计划

1. **阶段 1**：扩展 Schema，添加 `manual_joins` 参数
2. **阶段 2**：修改 `JoinQueryBuilder`，支持手动关联
3. **阶段 3**：更新 API，处理手动关联参数
4. **阶段 4**：测试和文档

## 待决问题

- 是否支持手动关联的多级递归？**决定**：不支持，固定深度为1
- 模糊匹配的性能影响如何评估？**决定**：在文档中说明，建议使用精确匹配
- 是否需要支持反向关联（目标表 → 主表）？**决定**：暂不支持，保持简单
