# 变更：为所有 API 模块添加动态过滤查询功能

## 为什么

当前系统中，只有 `table_query` 和 `survey` 模块支持动态过滤条件查询（通过 `FilterCondition` 格式指定字段、操作符和值）。其他核心模块（user、role、dept、post、dict 等）使用的是预定义的 `FuFilters` 过滤器，无法支持灵活的动态查询需求。这限制了 AI Agent 和前端的查询能力。

## 变更内容

为以下 API 模块添加动态过滤查询功能，参考 `table_query_api` 和 `survey_api` 的实现模式：

### 目标模块
- `user` - 用户管理
- `role` - 角色管理
- `dept` - 部门管理
- `post` - 岗位管理
- `dict` - 字典管理
- `dict_item` - 字典项管理
- `menu` - 菜单管理
- `permission` - 权限管理
- `login_log` - 登录日志
- `file_manager` - 文件管理

### 新增功能

1. **动态过滤查询接口** (`POST /api/core/{module}/query`)
   - 支持 `FilterCondition` 格式的过滤条件
   - 支持操作符：`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`, `between`
   - 不支持的操作符返回清晰的错误提示和支持列表

2. **可搜索字段查询接口** (`GET /api/core/{module}/searchable-fields`)
   - 返回模块支持搜索的字段列表
   - 包含字段名、显示名称、数据类型

3. **统一操作符验证**
   - 当使用不支持的操作符时，返回错误提示并列出所有支持的操作符

## 影响

- 受影响规范：`backend-api`
- 受影响代码：
  - `backend-django/core/*/` 下的 `*_api.py` 和 `*_schema.py`
  - `backend-django/common/fu_crud.py`（可能需要添加通用查询方法）
