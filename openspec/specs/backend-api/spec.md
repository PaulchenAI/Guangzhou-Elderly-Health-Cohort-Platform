# backend-api Specification

## Purpose
TBD - created by archiving change improve-openapi-descriptions. Update Purpose after archive.
## 需求
### 需求：OpenAPI 描述规范

系统的所有 API 端点必须提供符合规范的 OpenAPI 描述，以支持 AI 意图理解和文档生成。

#### 场景：Summary 使用中文

- **当** 定义 API 端点时
- **那么** summary 参数必须使用中文
- **并且** 格式为 "动词 + 名词（补充说明）"

**示例**：
```python
# 正确 - 使用中文 summary，格式：动词 + 名词（补充说明）
@router.get("/user", response=List[UserSchemaOut], summary="获取用户列表（分页）")
@router.post("/user", response=UserSchemaOut, summary="创建用户")
@router.get("/user/{user_id}", response=UserSchemaDetail, summary="获取用户详情")
@router.put("/user/{user_id}", response=UserSchemaOut, summary="更新用户")
@router.delete("/user/{user_id}", response=UserSchemaOut, summary="删除用户")

# 错误
@router.get("/user")  # 缺少 summary，Django Ninja 自动生成英文（如 "List User"）
@router.get("/user", summary="List User")  # 英文 summary，AI 难以匹配中文意图
```

#### 场景：Description 结构化格式

- **当** API 有复杂参数或返回值时
- **那么** description 必须使用结构化格式说明
- **并且** 包含参数说明和返回值说明

**示例**：
```python
@router.get("/user", response=List[UserSchemaOut], summary="获取用户列表（分页）")
@paginate(MyPagination)
def list_user(request, filters: UserFilters = Query(...)):
    """
    获取用户列表（分页）
    
    查询参数:
    - page: 页码（默认 1）
    - pageSize: 每页数量（默认 10）
    - name: 用户名（模糊查询）
    - user_status: 用户状态（0-禁用，1-正常，2-锁定）
    - dept_ids[]: 部门ID列表
    
    返回:
    - items: 用户列表
    - total: 总数
    """
    query_set = retrieve(request, User, filters)
    return query_set
```

**说明**：Django Ninja 会自动将函数的 docstring 作为 OpenAPI 的 description。

#### 场景：Tags 命名规范

- **当** 定义 API 端点的 tags 时
- **那么** tags 应遵循现有的模块命名规范
- **并且** 在路由注册时统一指定

**说明**：
- 当前项目 tags 使用 `Core-模块名` 格式（如 `Core-User`）
- 部分模块已使用中文 tags（如 `问卷管理`）
- Tags 统一规范化将作为后续独立变更处理

**示例**：
```python
# 在 router.py 中统一指定 tags
core_router.add_router("", user_router, tags=["Core-User"])
core_router.add_router("", role_router, tags=["Core-Role"])
```

### 需求：动词标准化

API summary 中的动词必须使用标准化的中文动词，确保语义一致性。

#### 场景：CRUD 操作动词

- **当** 定义 CRUD 操作的 API 时
- **那么** 必须使用以下标准动词：

| HTTP 方法 | 操作类型 | 标准动词 | 示例 |
|-----------|---------|---------|------|
| POST | 创建 | 创建 | 创建用户 |
| GET | 读取单个 | 获取 | 获取用户详情 |
| GET | 读取列表 | 获取 | 获取用户列表（分页） |
| GET | 读取全部 | 获取所有 | 获取所有用户 |
| PUT | 完全更新 | 更新 | 更新用户 |
| PATCH | 部分更新 | 部分更新 | 部分更新用户 |
| DELETE | 删除 | 删除 | 删除用户 |
| DELETE | 批量删除 | 批量删除 | 批量删除用户 |

#### 场景：扩展操作动词

- **当** 定义非 CRUD 操作的 API 时
- **那么** 必须使用以下标准动词：

| 操作类型 | 标准动词 | 示例 |
|---------|---------|------|
| 搜索 | 搜索 | 搜索用户 |
| 导出 | 导出 | 导出用户数据 |
| 导入 | 导入 | 导入用户数据 |
| 同步 | 同步/触发同步 | 触发数据同步 |
| 验证 | 验证/检查 | 检查用户权限 |
| 重置 | 重置 | 重置用户密码 |

### 需求：AI 友好的描述

API 描述必须对 AI 意图理解友好，包含足够的语义信息。

#### 场景：包含业务语义

- **当** 编写 API description 时
- **那么** 必须包含业务语义描述
- **并且** 使用用户可能使用的自然语言表达

#### 场景：关键词覆盖

- **当** 编写 API summary 和 description 时
- **那么** 应包含用户可能使用的同义词或相关词汇

#### 场景：支持名称参数的 API 描述

- **当** API 同时支持 ID 和名称参数时
- **那么** description 必须说明两种参数的使用方式
- **并且** 说明名称参数支持模糊匹配
- **并且** 提供 AI 调用建议

### 需求：按名称查询问卷配置

系统必须提供按问卷名称查询配置的 API，支持模糊匹配，以便 AI/LLM 能够通过自然语言中的名称找到对应的问卷配置。

#### 场景：按名称精确匹配查询

- **当** 调用 `GET /api/core/survey/schemas/by-name/{survey_name}` 且名称完全匹配
- **那么** 返回匹配的问卷配置
- **并且** 返回的配置包含 `id`（schema_id）字段

#### 场景：按名称模糊匹配查询

- **当** 调用 `GET /api/core/survey/schemas/by-name/{survey_name}` 且名称部分匹配
- **那么** 返回名称包含该关键字的第一个问卷配置
- **并且** 优先返回名称完全匹配的配置

#### 场景：名称不存在时返回 404

- **当** 调用 `GET /api/core/survey/schemas/by-name/{survey_name}` 且无匹配配置
- **那么** 返回 404 Not Found 错误
- **并且** 错误消息说明未找到匹配的问卷配置

### 需求：问卷查询支持按名称

系统的问卷查询 API 必须支持通过问卷名称进行查询，作为 `schema_id` 的替代方案。

#### 场景：使用 survey_name 参数查询

- **当** 调用 `POST /api/core/survey/query` 且请求体包含 `survey_name` 参数
- **那么** 系统自动将 `survey_name` 解析为对应的 `schema_id`
- **并且** 执行问卷数据查询并返回结果

#### 场景：survey_name 和 schema_id 同时提供

- **当** 请求体同时包含 `survey_name` 和 `schema_id`
- **那么** 优先使用 `schema_id` 进行查询
- **并且** 忽略 `survey_name` 参数

#### 场景：survey_name 无匹配时返回错误

- **当** 提供的 `survey_name` 无法匹配任何问卷配置
- **那么** 返回 400 Bad Request 错误
- **并且** 错误消息说明未找到匹配的问卷类型

### 需求：问卷导出支持按名称

系统的问卷导出 API 必须支持通过问卷名称进行导出，作为 `schema_id` 的替代方案。

#### 场景：使用 survey_name 参数导出

- **当** 调用 `POST /api/core/survey/export` 且请求体包含 `survey_name` 参数
- **那么** 系统自动将 `survey_name` 解析为对应的 `schema_id`
- **并且** 执行问卷数据导出

### 需求：按名称查询用户

系统必须提供按用户名称查询用户的 API，支持模糊匹配。

#### 场景：按姓名查询用户

- **当** 调用 `GET /api/core/user/by-name/{name}` 
- **那么** 返回姓名匹配的用户信息
- **并且** 支持模糊匹配（如"张"可匹配"张三"）
- **并且** 优先返回完全匹配的用户

#### 场景：按登录名查询用户

- **当** 调用 `GET /api/core/user/by-username/{username}`
- **那么** 返回登录名匹配的用户信息
- **并且** 支持模糊匹配

### 需求：按名称查询角色

系统必须提供按角色名称或编码查询角色的 API，支持模糊匹配。

#### 场景：按角色名称查询

- **当** 调用 `GET /api/core/role/by-name/{name}`
- **那么** 返回名称匹配的角色信息
- **并且** 支持模糊匹配（如"管理"可匹配"系统管理员"）

#### 场景：按角色编码查询

- **当** 调用 `GET /api/core/role/by-code/{code}`
- **那么** 返回编码匹配的角色信息
- **并且** 支持模糊匹配

### 需求：按名称查询部门

系统必须提供按部门名称或编码查询部门的 API，支持模糊匹配。

#### 场景：按部门名称查询

- **当** 调用 `GET /api/core/dept/by-name/{name}`
- **那么** 返回名称匹配的部门信息
- **并且** 支持模糊匹配

#### 场景：按部门编码查询

- **当** 调用 `GET /api/core/dept/by-code/{code}`
- **那么** 返回编码匹配的部门信息
- **并且** 支持模糊匹配

### 需求：按名称查询岗位

系统必须提供按岗位名称或编码查询岗位的 API，支持模糊匹配。

#### 场景：按岗位名称查询

- **当** 调用 `GET /api/core/post/by-name/{name}`
- **那么** 返回名称匹配的岗位信息
- **并且** 支持模糊匹配

#### 场景：按岗位编码查询

- **当** 调用 `GET /api/core/post/by-code/{code}`
- **那么** 返回编码匹配的岗位信息
- **并且** 支持模糊匹配

### 需求：按名称查询字典

系统必须提供按字典名称或编码查询字典的 API，支持模糊匹配。

#### 场景：按字典名称查询

- **当** 调用 `GET /api/core/dict/by-name/{name}`
- **那么** 返回名称匹配的字典信息
- **并且** 支持模糊匹配

#### 场景：按字典编码查询

- **当** 调用 `GET /api/core/dict/by-code/{code}`
- **那么** 返回编码匹配的字典信息
- **并且** 支持模糊匹配

### 需求：按名称查询表查询配置

系统必须提供按配置名称查询表查询配置的 API，支持模糊匹配。

#### 场景：按配置名称查询

- **当** 调用 `GET /api/core/table-query/configs/by-name/{name}`
- **那么** 返回名称匹配的配置信息
- **并且** 支持模糊匹配

### 需求：表查询支持按配置名称

系统的表查询 API 必须支持通过配置名称进行查询，作为 `config_id` 的替代方案。

#### 场景：使用 config_name 参数查询

- **当** 调用 `POST /api/core/table-query/query` 且请求体包含 `config_name` 参数
- **那么** 系统自动将 `config_name` 解析为对应的 `config_id`
- **并且** 执行表数据查询并返回结果

### 需求：AI 友好的按名称查询 API 设计规范

开发文档必须包含 AI 友好的按名称查询 API 设计规范，指导开发者为每个资源提供名称查询能力。

#### 场景：路径命名规范

- **当** 开发者需要新增按名称查询的 API 时
- **那么** 开发文档必须提供标准的路径命名规范
- **并且** 包含以下路径模式示例

```
# 按名称查询（模糊匹配）
/resource/by-name/{name}

# 按编码查询（模糊匹配）
/resource/by-code/{code}

# 按用户名查询（用户模块特有）
/user/by-username/{username}
```

#### 场景：API 实现模板

- **当** 开发者实现按名称查询 API 时
- **那么** 开发文档必须提供标准的实现模板
- **并且** 包含模糊匹配和优先返回完全匹配的逻辑

```python
@router.get(
    "/resource/by-name/{name}", 
    response=ResourceSchemaOut, 
    summary="按名称查询资源"
)
def get_resource_by_name(request, name: str):
    """
    按名称查询资源（支持模糊匹配）
    
    路径参数:
    - name: 资源名称（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回名称完全匹配的资源
    2. 如果没有完全匹配，返回名称包含关键字的第一个资源
    3. 如果都没有匹配，返回 404 错误
    
    AI 调用建议: 直接传入用户提到的名称，无需获取 ID。
    """
    # 优先精确匹配
    resource = Resource.objects.filter(name=name, is_deleted=False).first()
    if resource:
        return resource
    
    # 模糊匹配
    resource = Resource.objects.filter(
        name__icontains=name, 
        is_deleted=False
    ).first()
    if resource:
        return resource
    
    raise HttpError(404, f"未找到名称匹配 '{name}' 的资源")
```

### 需求：支持名称参数的 API Description 规范

开发文档必须规范如何编写同时支持 ID 和名称参数的 API description，确保 AI 能够理解参数的使用方式。

#### 场景：Description 标准格式

- **当** API 同时支持 ID 和名称参数时
- **那么** description 必须包含以下内容
- **并且** 遵循标准格式

```python
description="""
查询资源数据

支持两种方式指定资源：
1. resource_id: 资源 ID（精确匹配，UUID 格式）
2. resource_name: 资源名称（支持模糊匹配）

参数优先级：resource_id > resource_name

AI 调用建议：优先使用 resource_name 参数，传入用户提到的名称即可。
"""
```

#### 场景：Schema 字段描述规范

- **当** Schema 包含名称参数时
- **那么** 字段描述必须说明该参数支持模糊匹配
- **并且** 说明与 ID 参数的关系

```python
class ResourceQueryIn(Schema):
    resource_id: Optional[str] = Field(
        None, 
        description="资源 ID（精确匹配，优先级高于 resource_name）"
    )
    resource_name: Optional[str] = Field(
        None, 
        description="资源名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
```

### 需求：ForeignKey 字段描述规范

所有 ForeignKey 字段的 `help_text` 必须包含关联关系信息，便于 AI 理解表之间的关联。

#### 场景：标准 ForeignKey 字段描述

- **当** 定义 ForeignKey 字段
- **那么** `help_text` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}，关联 {模型名} 模型/表 {目标表db_table}.{目标字段}`
- **例如** `help_text="所属部门，关联 Dept 模型/表 core_dept.id"`

#### 场景：自引用 ForeignKey 字段描述

- **当** 定义自引用 ForeignKey 字段（如 parent、manager）
- **那么** `help_text` 必须说明是自引用关系
- **并且** 格式为 `{业务含义}，自引用 {模型名} 模型/表 {当前表db_table}.{目标字段}`
- **例如** `help_text="上级部门，自引用 Dept 模型/表 core_dept.id"`

#### 场景：可空 ForeignKey 字段描述

- **当** 定义可空的 ForeignKey 字段（null=True）
- **那么** `help_text` 应说明可空情况
- **例如** `help_text="所属部门（可空），关联 Dept 模型/表 core_dept.id"`

---

### 需求：Schema 关联字段描述规范

所有 Schema 中的关联字段（如 `dept_id`、`manager_id`）的 `description` 必须包含关联关系信息。

#### 场景：Schema 关联字段描述格式

- **当** 定义 Schema 中的关联字段
- **那么** `description` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}（关联 {模型名} 模型/表 {目标表db_table}.{目标字段}）`
- **例如** `description="所属部门ID（关联 Dept 模型/表 core_dept.id）"`

#### 场景：Schema 自引用字段描述格式

- **当** 定义 Schema 中的自引用字段
- **那么** `description` 必须说明是自引用关系
- **并且** 格式为 `{业务含义}（自引用 {模型名} 模型/表 {当前表db_table}.{目标字段}）`
- **例如** `description="上级部门ID（自引用 Dept 模型/表 core_dept.id）"`

---

### 需求：字段描述增强工具

系统必须提供 Django management command 来自动生成字段描述增强建议。

#### 场景：扫描并生成描述建议

- **当** 用户执行 `python manage.py enhance_field_descriptions`
- **那么** 系统扫描所有已注册的 Django 模型
- **并且** 识别所有 ForeignKey 和 ManyToManyField 字段
- **并且** 生成符合规范的字段描述建议
- **并且** 输出当前描述与建议描述的对比

#### 场景：预览模式

- **当** 用户执行 `python manage.py enhance_field_descriptions --dry-run`
- **那么** 系统仅显示建议，不做任何修改
- **并且** 输出需要更新的字段列表

#### 场景：输出到文件

- **当** 用户执行 `python manage.py enhance_field_descriptions --output suggestions.json`
- **那么** 系统将建议输出到指定文件
- **并且** 文件格式为 JSON，包含模型名、字段名、当前描述、建议描述

#### 场景：指定扫描范围

- **当** 用户执行 `python manage.py enhance_field_descriptions --app-labels core`
- **那么** 系统仅扫描指定 app 中的模型

#### 场景：排除指定 app

- **当** 用户执行 `python manage.py enhance_field_descriptions --exclude-apps admin,auth,contenttypes,sessions`
- **那么** 系统排除 Django 内置 app，扫描其余所有 app

#### 场景：JSON 输出格式

- **当** 用户指定 `--format json`
- **那么** 输出格式为：
```json
{
  "suggestions": [
    {
      "model": "core.User",
      "field": "dept",
      "field_type": "ForeignKey",
      "current_help_text": "所属部门",
      "suggested_help_text": "所属部门，关联 Dept 模型/表 core_dept.id",
      "target_model": "core.Dept",
      "target_table": "core_dept",
      "target_field": "id"
    }
  ],
  "summary": {
    "total_models": 20,
    "total_fields": 15,
    "fields_needing_update": 10
  }
}
```

---

### 需求：ManyToManyField 字段描述规范

ManyToManyField 字段的 `help_text` 必须说明关联的目标表和中间表信息。

#### 场景：标准 ManyToMany 字段描述

- **当** 定义 ManyToManyField 字段
- **那么** `help_text` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}，多对多关联 {模型名} 模型/表 {目标表db_table}，中间表 {中间表db_table}`
- **例如** `help_text="关联的角色，多对多关联 Role 模型/表 core_role，中间表 core_user_core_roles"`

#### 场景：自定义中间表的 ManyToMany 字段描述

- **当** 定义使用 `through` 参数的 ManyToManyField 字段
- **那么** `help_text` 必须说明自定义中间表
- **例如** `help_text="关联的权限，多对多关联 Permission 模型/表 core_permission，中间表 core_role_permissions"`

