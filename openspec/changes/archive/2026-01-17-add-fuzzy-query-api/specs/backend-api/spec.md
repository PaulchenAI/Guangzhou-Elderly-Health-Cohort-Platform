## 新增需求

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

## 修改需求

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
