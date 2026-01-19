## 新增需求

### 需求：通用动态过滤查询接口

系统必须为所有核心 API 模块提供统一的动态过滤查询接口，支持灵活的字段过滤和操作符选择。

#### 场景：使用动态过滤条件查询数据

- **当** 调用 `POST /api/core/{module}/query` 且请求体包含 `filters` 参数
- **那么** 系统根据过滤条件执行查询
- **并且** 返回分页的查询结果

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

**支持的模块**：
- `/api/core/user/query` - 用户查询
- `/api/core/role/query` - 角色查询
- `/api/core/dept/query` - 部门查询
- `/api/core/post/query` - 岗位查询
- `/api/core/dict/query` - 字典查询
- `/api/core/dict-item/query` - 字典项查询
- `/api/core/menu/query` - 菜单查询
- `/api/core/permission/query` - 权限查询
- `/api/core/login-log/query` - 登录日志查询
- `/api/core/file/query` - 文件查询

#### 场景：使用不支持的操作符时返回错误

- **当** 调用动态查询接口且 `operator` 不在支持列表中
- **那么** 返回 400 错误
- **并且** 错误消息包含支持的操作符列表

**支持的操作符**：
- `eq` - 等于
- `ne` - 不等于
- `gt` - 大于
- `gte` - 大于等于
- `lt` - 小于
- `lte` - 小于等于
- `like` - 模糊匹配
- `in` - 包含
- `between` - 范围

**错误响应示例**：
```
不支持的操作符: ==。支持的操作符: eq(等于), ne(不等于), gt(大于), gte(大于等于), lt(小于), lte(小于等于), like(模糊匹配), in(包含), between(范围)
```

#### 场景：使用不可搜索字段时返回错误

- **当** 调用动态查询接口且 `field` 不在可搜索字段列表中
- **那么** 返回 400 错误
- **并且** 错误消息包含可用的搜索字段列表

### 需求：可搜索字段查询接口

系统必须为所有核心 API 模块提供查询可搜索字段的接口，以便 AI Agent 和前端获取字段信息。

#### 场景：获取模块的可搜索字段列表

- **当** 调用 `GET /api/core/{module}/searchable-fields`
- **那么** 返回该模块支持搜索的字段列表
- **并且** 每个字段包含 `name`（字段名）、`display_name`（显示名称）、`type`（数据类型）

**支持的模块**：
- `/api/core/user/searchable-fields` - 用户可搜索字段
- `/api/core/role/searchable-fields` - 角色可搜索字段
- `/api/core/dept/searchable-fields` - 部门可搜索字段
- `/api/core/post/searchable-fields` - 岗位可搜索字段
- `/api/core/dict/searchable-fields` - 字典可搜索字段
- `/api/core/dict-item/searchable-fields` - 字典项可搜索字段
- `/api/core/menu/searchable-fields` - 菜单可搜索字段
- `/api/core/permission/searchable-fields` - 权限可搜索字段
- `/api/core/login-log/searchable-fields` - 登录日志可搜索字段
- `/api/core/file/searchable-fields` - 文件可搜索字段

**响应格式**：
```json
{
  "module": "user",
  "display_name": "用户管理",
  "searchable_fields": [
    {"name": "id", "display_name": "用户ID", "type": "string"},
    {"name": "name", "display_name": "姓名", "type": "string"},
    {"name": "username", "display_name": "用户名", "type": "string"},
    {"name": "user_status", "display_name": "状态", "type": "integer"},
    {"name": "create_datetime", "display_name": "创建时间", "type": "datetime"}
  ]
}
```

### 需求：通用 FilterCondition Schema

系统必须在公共模块中定义统一的 `FilterCondition` Schema，供所有动态查询接口使用。

#### 场景：FilterCondition 包含必要字段

- **当** 定义动态查询的过滤条件
- **那么** 必须包含 `field`（字段名）、`operator`（操作符）、`value`（值）三个字段
- **并且** `operator` 默认值为 `eq`

**Schema 定义**：
```python
class FilterCondition(Schema):
    field: str = Field(..., description="字段名")
    operator: str = Field("eq", description="操作符: eq/ne/gt/gte/lt/lte/like/in/between")
    value: Any = Field(..., description="过滤值")
```

### 需求：通用操作符常量定义

系统必须在公共模块中定义统一的操作符常量，确保所有模块使用一致的操作符。

#### 场景：ALLOWED_OPERATORS 包含所有支持的操作符

- **当** 验证查询条件的操作符
- **那么** 必须使用公共定义的 `ALLOWED_OPERATORS` 常量
- **并且** 包含中文描述用于错误提示

**常量定义**：
```python
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
```
