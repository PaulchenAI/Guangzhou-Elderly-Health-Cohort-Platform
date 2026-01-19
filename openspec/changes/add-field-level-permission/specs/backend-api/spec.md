# 后端 API 规范增量

## 新增需求

### 需求：动态查询字段级权限控制

系统必须通过查询权限表来控制可搜索字段的访问权限，使用权限编码命名规范 `{module}:query:{field_name}`。

#### 场景：权限表存在字段权限且用户无权限

- **当** 权限表中存在 `{module}:query:{field_name}` 权限记录
- **并且** 用户不具有该权限
- **那么** `searchable-fields` 接口应排除该字段
- **并且** `query` 接口应拒绝使用该字段的查询条件

#### 场景：权限表存在字段权限且用户有权限

- **当** 权限表中存在 `{module}:query:{field_name}` 权限记录
- **并且** 用户具有该权限
- **那么** `searchable-fields` 接口应包含该字段
- **并且** `query` 接口应允许使用该字段的查询条件

#### 场景：权限表不存在字段权限

- **当** 权限表中不存在 `{module}:query:{field_name}` 权限记录
- **那么** 该字段对所有已认证用户可见
- **并且** 查询时不进行权限验证

#### 场景：无权限用户尝试使用受保护字段查询

- **当** 用户调用 `POST /{module}/query` 接口
- **并且** 查询条件中包含用户无权限的字段
- **那么** 系统应返回 403 错误
- **并且** 错误信息应包含缺少的权限编码

### 需求：用户敏感字段权限

用户模块的敏感字段（手机号、邮箱）必须在权限表中配置相应的权限记录。

#### 场景：管理员可见用户敏感字段

- **当** 权限表中存在 `user:query:mobile` 和 `user:query:email` 权限记录
- **并且** 用户具有这两个权限
- **那么** `GET /user/searchable-fields` 应包含 `mobile` 和 `email` 字段

#### 场景：普通用户不可见用户敏感字段

- **当** 权限表中存在 `user:query:mobile` 和 `user:query:email` 权限记录
- **并且** 用户不具有这两个权限
- **那么** `GET /user/searchable-fields` 不应包含 `mobile` 和 `email` 字段

### 需求：登录日志 IP 字段权限

登录日志模块的 IP 字段必须在权限表中配置相应的权限记录。

#### 场景：安全管理员可见登录 IP

- **当** 权限表中存在 `login_log:query:login_ip` 权限记录
- **并且** 用户具有该权限
- **那么** `GET /login-log/searchable-fields` 应包含 `login_ip` 字段

#### 场景：普通用户不可见登录 IP

- **当** 权限表中存在 `login_log:query:login_ip` 权限记录
- **并且** 用户不具有该权限
- **那么** `GET /login-log/searchable-fields` 不应包含 `login_ip` 字段

### 需求：接口输出结构保持不变

`searchable-fields` 接口的响应结构必须保持不变，仅通过过滤字段列表实现权限控制。

#### 场景：输出结构不变

- **当** 调用 `GET /{module}/searchable-fields` 接口
- **那么** 响应结构应为：
  ```json
  {
    "module": "模块名",
    "display_name": "模块显示名",
    "searchable_fields": [
      {"name": "字段名", "display_name": "显示名", "type": "类型"}
    ]
  }
  ```
- **并且** 字段对象结构不包含 `permission` 属性
