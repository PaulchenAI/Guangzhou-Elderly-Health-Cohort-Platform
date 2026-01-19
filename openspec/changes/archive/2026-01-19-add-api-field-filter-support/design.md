# 设计文档：增强 AI 对表数据和问卷数据的字段过滤查询能力

## 上下文

### 背景

当前系统中，AI Agent 在尝试对表数据或问卷数据进行字段过滤查询时经常失败。主要原因是：

1. 后端 API 对字段的 `searchable` 属性进行严格验证
2. 许多表的字段配置中没有正确设置 `searchable: true`
3. AI Agent 在生成脚本时无法获知哪些字段支持过滤

### 约束

- 必须保持向后兼容，不能破坏现有的 API 接口
- 安全性考虑：不能允许任意字段查询，防止 SQL 注入
- 性能考虑：不能在每次查询时都返回所有字段信息

### 利益相关者

- AI Agent 用户：需要能够通过自然语言查询数据
- 后端开发者：需要维护 API 的安全性和稳定性
- 系统管理员：需要配置表和字段的查询权限

## 目标 / 非目标

### 目标

1. AI Agent 能够准确知道哪些字段支持过滤查询
2. 当使用不支持的字段时，提供清晰的错误信息和可用字段列表
3. 自动修正机制能够根据可用字段重新生成正确的查询脚本
4. 问卷查询 API 具有与表查询 API 一致的字段验证机制

### 非目标

1. 不修改现有的字段配置数据（由管理员手动配置）
2. 不改变 API 的认证和授权机制
3. 不实现复杂的字段级权限控制

## 决策

### 决策 1：在错误响应中包含可用字段信息

**选择**：修改后端 API，当字段不支持搜索时，在错误响应中包含可搜索字段列表。

**理由**：
- 减少 AI Agent 的 API 调用次数
- 提供即时的修正信息
- 对现有功能影响最小

**实现**：

```python
# table_query_api.py
if field_upper not in searchable_fields:
    available_fields = [f['name'] for f in config.config_json.get('fields', []) 
                        if f.get('searchable', False)]
    raise HttpError(400, {
        "message": f"字段 {field} 不支持搜索",
        "available_fields": available_fields
    })
```

### 决策 2：添加专用端点查询可搜索字段

**选择**：添加 `/table-query/configs/{id}/searchable-fields` 端点。

**理由**：
- AI Agent 可以在生成脚本前获取可用字段
- 避免在配置列表 API 中返回过多数据
- 支持按需加载

**实现**：

```python
@router.get("/table-query/configs/{config_id}/searchable-fields")
def get_searchable_fields(request, config_id: str):
    config = get_object_or_404(TableQueryConfig, id=config_id, is_deleted=False)
    fields = config.config_json.get('fields', [])
    searchable = [
        {
            "name": f['name'],
            "display_name": f.get('displayName', f['name']),
            "type": f.get('type', 'string')
        }
        for f in fields if f.get('searchable', False)
    ]
    return {"config_name": config.display_name, "searchable_fields": searchable}
```

### 决策 3：问卷查询 API 增加字段验证

**选择**：在 `/survey/query` API 中增加字段白名单验证，与表查询 API 保持一致。

**理由**：
- 安全性：防止查询任意字段
- 一致性：与表查询 API 行为一致
- 可维护性：统一的验证逻辑

**实现**：

```python
# survey_api.py - query_records 函数
def query_records(request, data: SurveyQueryIn):
    # ... 获取 schema ...
    
    # 获取可搜索字段
    searchable_fields = {f.get('name', '').lower() for f in schema.get_searchable_fields()}
    
    # 验证过滤字段
    if data.filters:
        for condition in data.filters:
            field = condition.get("field", "").lower()
            if field and field not in searchable_fields:
                available = [f.get('name') for f in schema.get_searchable_fields()]
                raise HttpError(400, {
                    "message": f"字段 {field} 不支持搜索",
                    "available_fields": available
                })
```

### 决策 4：AI Agent 增强字段感知

**选择**：在 AI Agent 的上下文中包含可搜索字段信息。

**理由**：
- LLM 可以在生成脚本时直接使用正确的字段
- 减少因字段错误导致的重试
- 提高脚本生成的成功率

**实现**：

在 `script_generator.py` 中，当检测到用户意图涉及数据过滤时：

1. 先获取目标配置的可搜索字段列表
2. 将字段信息包含在 LLM 提示中
3. 在验证阶段检查生成的过滤条件

```python
# 在生成脚本前获取可搜索字段
if '查询' in intent or '筛选' in intent or '过滤' in intent:
    # 尝试识别目标配置
    config_name = self._extract_config_name(intent)
    if config_name:
        searchable_fields = await self._get_searchable_fields(config_name)
        context['searchable_fields'] = searchable_fields
```

### 考虑的替代方案

1. **在配置列表 API 中返回所有字段信息**
   - 优点：减少 API 调用
   - 缺点：响应数据量大，影响性能
   - 结论：不采用

2. **完全移除字段验证**
   - 优点：简化实现
   - 缺点：安全风险，可能导致 SQL 注入
   - 结论：不采用

3. **在前端进行字段验证**
   - 优点：减少后端负担
   - 缺点：无法保护 API 直接调用
   - 结论：不采用

## 风险 / 权衡

### 风险 1：API 响应格式变更

**风险**：修改错误响应格式可能影响现有客户端。

**缓解措施**：
- 保持原有的错误消息字段
- 新增字段作为可选信息
- 在 API 文档中说明变更

### 风险 2：性能影响

**风险**：增加字段验证可能影响查询性能。

**缓解措施**：
- 字段验证在内存中进行，不涉及数据库查询
- 可搜索字段列表已经在配置中缓存
- 影响可忽略不计

### 风险 3：AI Agent 重试循环

**风险**：如果可用字段仍然不满足用户需求，可能导致无限重试。

**缓解措施**：
- 设置最大重试次数（已有 `--max-retries` 参数）
- 在重试失败后，向用户说明可用字段的限制
- 建议用户联系管理员配置更多可搜索字段

## 迁移计划

### 阶段 1：后端 API 增强（无破坏性变更）

1. 添加新的 API 端点
2. 增强错误响应信息
3. 问卷查询增加字段验证

### 阶段 2：AI Agent 集成

1. 更新 AI Agent 获取可搜索字段
2. 修改脚本生成逻辑
3. 增强自动修正功能

### 阶段 3：验证和文档

1. 端到端测试
2. 更新 API 文档
3. 更新用户指南

### 回滚计划

- 后端变更：新增端点可直接删除，错误响应增强不影响现有功能
- AI Agent 变更：可通过配置开关禁用新功能

## 待决问题

1. **是否需要为问卷查询添加更多可搜索字段？**
   - 当前问卷 Schema 中的 `searchable` 字段配置可能不完整
   - 需要与业务方确认哪些字段需要支持搜索

2. **是否需要支持嵌套字段的搜索？**
   - 问卷数据中有嵌套的 JSON 字段（如 `survey_data.summary.totalActivities`）
   - 当前实现不支持嵌套字段搜索，是否需要扩展？

3. **字段搜索的性能优化**
   - 对于大数据量的表，某些字段的模糊搜索可能很慢
   - 是否需要添加索引建议或查询限制？
