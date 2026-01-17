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

**示例**：
```python
# 正确 - 包含业务语义
description="""
获取问卷数据列表（分页）

用于查询已填写的问卷记录，支持按问卷类型、患者姓名、日期范围筛选。
"""

# 错误 - 缺乏业务语义
description="获取问卷数据列表"
```

#### 场景：关键词覆盖

- **当** 编写 API summary 和 description 时
- **那么** 应包含用户可能使用的同义词或相关词汇

**示例**：
```python
# 问卷数据 API - 包含 "数据"、"记录" 等同义词
summary="获取问卷数据列表（分页）"
description="""
获取问卷数据列表（分页）

查询已填写的问卷记录，返回问卷数据列表。
"""
```

