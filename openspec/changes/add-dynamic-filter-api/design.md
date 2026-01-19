# 设计文档：为所有 API 模块添加动态过滤查询功能

## 上下文

### 背景

当前系统中有两类查询模式：

1. **动态过滤模式**（table_query、survey）：
   - 支持 `FilterCondition` 格式：`{"field": "name", "operator": "like", "value": "张"}`
   - 支持多种操作符：eq、ne、gt、gte、lt、lte、like、in、between
   - 提供可搜索字段查询接口

2. **预定义过滤模式**（user、role、dept 等）：
   - 使用 `FuFilters` Schema 预定义查询字段和操作符
   - 查询方式固定，无法动态指定操作符

为了统一查询体验，需要为后者也添加动态过滤能力。

### 约束

- 必须保持向后兼容，现有的分页列表接口不能改变
- 安全性：所有查询字段必须经过白名单验证
- 性能：避免全表扫描，必要时限制可搜索字段

### 利益相关者

- AI Agent：需要统一的动态查询接口
- 前端开发者：需要更灵活的查询能力
- 后端开发者：需要维护一致的 API 设计模式

## 目标 / 非目标

### 目标

1. 为所有核心模块提供统一的动态查询接口
2. 提供可搜索字段查询接口，支持 AI Agent 预先获取字段信息
3. 统一操作符验证和错误提示机制
4. 保持与 table_query_api、survey_api 的一致性

### 非目标

1. 不替换现有的分页列表接口（保持向后兼容）
2. 不实现复杂的聚合查询功能
3. 不实现字段级权限控制

## 决策

### 决策 1：API 设计模式

**选择**：采用与 table_query_api 一致的设计模式。

**新增端点**：
```
POST /api/core/{module}/query          # 动态查询
GET  /api/core/{module}/searchable-fields  # 获取可搜索字段
```

**请求格式**：
```json
{
  "page": 1,
  "page_size": 20,
  "filters": [
    {"field": "name", "operator": "like", "value": "张"},
    {"field": "status", "operator": "eq", "value": 1}
  ],
  "order_by": "-create_datetime"
}
```

**理由**：
- 与现有动态查询接口保持一致
- AI Agent 可以使用相同的脚本模板
- 减少学习成本

### 决策 2：可搜索字段定义

**选择**：通过 Schema 类属性定义可搜索字段。

**实现**：
```python
# user_schema.py
class UserSearchableFields:
    """用户模块可搜索字段定义"""
    FIELDS = [
        {"name": "id", "display_name": "用户ID", "type": "string", "operators": ["eq", "in"]},
        {"name": "name", "display_name": "姓名", "type": "string", "operators": ["eq", "like"]},
        {"name": "username", "display_name": "用户名", "type": "string", "operators": ["eq", "like"]},
        {"name": "user_status", "display_name": "状态", "type": "integer", "operators": ["eq", "ne", "in"]},
        {"name": "create_datetime", "display_name": "创建时间", "type": "datetime", "operators": ["gt", "gte", "lt", "lte", "between"]},
    ]
```

**理由**：
- 集中管理可搜索字段配置
- 便于维护和扩展
- 可以为不同字段指定允许的操作符

### 决策 3：通用查询函数

**选择**：在 `common/fu_crud.py` 中添加通用的动态查询函数。

**实现**：
```python
# fu_crud.py
def dynamic_query(
    model: Type[Model],
    filters: List[FilterCondition],
    searchable_fields: List[dict],
    allowed_operators: dict,
    page: int = 1,
    page_size: int = 20,
    order_by: str = None
) -> Tuple[QuerySet, int]:
    """
    通用动态查询函数
    
    Args:
        model: Django 模型类
        filters: 过滤条件列表
        searchable_fields: 可搜索字段配置
        allowed_operators: 允许的操作符映射
        page: 页码
        page_size: 每页数量
        order_by: 排序字段
    
    Returns:
        (查询结果, 总数)
    """
```

**理由**：
- 避免在每个模块中重复实现查询逻辑
- 统一的验证和错误处理
- 便于维护和测试

### 决策 4：操作符统一定义

**选择**：在 `common/fu_schema.py` 中定义全局操作符常量。

**实现**：
```python
# fu_schema.py
ALLOWED_OPERATORS = {
    "eq": "等于",
    "ne": "不等于",
    "gt": "大于",
    "gte": "大于等于",
    "lt": "小于",
    "lte": "小于等于",
    "like": "模糊匹配",
    "in": "包含",
    "between": "范围",
}

class FilterCondition(Schema):
    """通用过滤条件"""
    field: str = Field(..., description="字段名")
    operator: str = Field("eq", description="操作符: eq/ne/gt/gte/lt/lte/like/in/between")
    value: Any = Field(..., description="过滤值")
```

**理由**：
- 所有模块使用相同的操作符定义
- 便于统一错误提示
- 减少代码重复

### 考虑的替代方案

1. **扩展现有 FuFilters**
   - 优点：改动小
   - 缺点：无法支持动态操作符选择
   - 结论：不采用

2. **GraphQL 查询**
   - 优点：更灵活的查询能力
   - 缺点：需要引入新技术栈，改动大
   - 结论：不采用

3. **OData 风格查询参数**
   - 优点：标准化的查询语法
   - 缺点：学习成本高，与现有模式不一致
   - 结论：不采用

## 风险 / 权衡

### 风险 1：性能问题

**风险**：动态查询可能产生低效的 SQL。

**缓解措施**：
- 限制可搜索字段，只允许有索引的字段
- 对 like 查询强制要求前缀匹配或限制结果数量
- 添加查询超时机制

### 风险 2：安全风险

**风险**：动态查询可能被滥用进行数据探测。

**缓解措施**：
- 严格的字段白名单验证
- 记录查询日志
- 限制单次查询的数据量

### 风险 3：维护成本

**风险**：需要为每个模块配置可搜索字段。

**缓解措施**：
- 提供合理的默认配置
- 创建配置生成工具
- 编写详细的开发文档

## 迁移计划

### 阶段 1：基础设施（1 天）
1. 在 `fu_schema.py` 中添加 `FilterCondition` 和 `ALLOWED_OPERATORS`
2. 在 `fu_crud.py` 中添加 `dynamic_query` 函数
3. 编写单元测试

### 阶段 2：核心模块实现（2 天）
按优先级顺序实现：
1. user、role、dept（高频使用）
2. post、dict、dict_item（中等频率）
3. menu、permission、login_log、file_manager（低频使用）

### 阶段 3：验证和文档（1 天）
1. 端到端测试
2. 更新 API 文档
3. 更新开发指南

### 回滚计划

- 新增接口可直接删除，不影响现有功能
- 通用函数可通过配置开关禁用

## 待决问题

1. **是否需要支持字段别名？**
   - 例如：允许用户使用 "姓名" 代替 "name"
   - 建议：在 AI Agent 层面处理，后端只接受字段名

2. **是否需要支持复合条件？**
   - 例如：OR 条件、嵌套条件
   - 建议：当前版本只支持 AND 条件，复杂查询作为后续扩展

3. **是否需要添加查询缓存？**
   - 对于频繁的相同查询可以缓存结果
   - 建议：根据实际性能需求决定，当前版本不实现
