# 变更：添加 AI 友好的模糊查询 API

## 为什么

当前后端 API 设计需要精确的 ID 参数（如 `schema_id`、`user_id`、`role_id` 等），但 AI/LLM 在处理用户自然语言请求时，只能获取到名称（如"户外活动记录表"、"管理员"），无法直接获取 UUID。这导致 AI 调用 API 时出现 404 错误，降低了 AI 访问系统的可用性。

**问题示例**：
```
用户请求: "获取问卷管理中的户外活动记录表问卷"
LLM 提取参数: {"schema_id": "户外活动记录表"}
实际需要: {"schema_id": "550e8400-e29b-41d4-a716-446655440000"}
结果: 404 Not Found
```

## 变更内容

### 1. 问卷管理模块

- **新增** `GET /api/core/survey/schemas/by-name/{survey_name}` - 按问卷名称查询配置
- **增强** `POST /api/core/survey/query` - 支持 `survey_name` 参数
- **增强** `POST /api/core/survey/export` - 支持 `survey_name` 参数

### 2. 用户管理模块

- **新增** `GET /api/core/user/by-name/{name}` - 按用户名/姓名查询用户
- **新增** `GET /api/core/user/by-username/{username}` - 按登录名查询用户

### 3. 角色管理模块

- **新增** `GET /api/core/role/by-name/{name}` - 按角色名称查询角色
- **新增** `GET /api/core/role/by-code/{code}` - 按角色编码查询角色

### 4. 部门管理模块

- **新增** `GET /api/core/dept/by-name/{name}` - 按部门名称查询部门
- **新增** `GET /api/core/dept/by-code/{code}` - 按部门编码查询部门

### 5. 岗位管理模块

- **新增** `GET /api/core/post/by-name/{name}` - 按岗位名称查询岗位
- **新增** `GET /api/core/post/by-code/{code}` - 按岗位编码查询岗位

### 6. 字典管理模块

- **新增** `GET /api/core/dict/by-name/{name}` - 按字典名称查询字典
- **新增** `GET /api/core/dict/by-code/{code}` - 按字典编码查询字典（已有类似功能，需确认）

### 7. 表查询配置模块

- **新增** `GET /api/core/table-query/configs/by-name/{name}` - 按配置名称查询
- **增强** `POST /api/core/table-query/query` - 支持 `config_name` 参数

### 8. 通用设计原则

所有新增的按名称查询 API 遵循以下规则：
- 支持精确匹配和模糊匹配
- 优先返回完全匹配的结果
- 无匹配时返回 404 错误
- 返回结果包含完整的实体信息（包括 ID）

### 9. 开发文档规范优化

更新 `docs/backend-api-development-guide.md`，新增以下内容：

#### 9.1 AI 友好的 API 设计规范

- **按名称查询 API 设计模式**：说明何时以及如何提供 `/by-name/{name}`、`/by-code/{code}` 等替代 ID 的查询方式
- **请求体名称参数设计**：说明如何在 POST 请求中支持名称参数作为 ID 的替代

#### 9.2 OpenAPI 描述增强规范

- **AI 调用建议**：在 description 中说明 AI 优先使用的参数
- **参数说明格式**：同时支持 ID 和名称时的标准描述格式
- **模糊匹配说明**：明确说明哪些参数支持模糊匹配

#### 9.3 路径命名规范扩展

新增按名称/编码查询的路径规范：
```
/resource/by-name/{name}     # 按名称查询（模糊匹配）
/resource/by-code/{code}     # 按编码查询（模糊匹配）
/resource/by-username/{username}  # 按用户名查询
```

## 影响

- 受影响规范：`backend-api`
- 受影响代码：
  - `backend-django/core/survey/survey_api.py`
  - `backend-django/core/user/user_api.py`
  - `backend-django/core/role/role_api.py`
  - `backend-django/core/dept/dept_api.py`
  - `backend-django/core/post/post_api.py`
  - `backend-django/core/dict/dict_api.py`
  - `backend-django/core/table_query/table_query_api.py`
  - 对应的 `*_schema.py` 文件
- 受影响文档：
  - `docs/backend-api-development-guide.md`
- 向后兼容：是（原有 ID 参数继续有效）
