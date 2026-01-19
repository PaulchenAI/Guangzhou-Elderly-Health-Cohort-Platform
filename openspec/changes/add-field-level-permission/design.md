# 设计文档：动态查询接口字段级权限控制

## 上下文

### 背景

动态查询接口（`POST /{module}/query` 和 `GET /{module}/searchable-fields`）已在 10 个核心模块中实现。当前所有用户看到相同的可搜索字段列表，不受权限控制。

### 约束

- 必须与现有 RBAC 权限系统集成
- 必须保持向后兼容（无权限配置的字段行为不变）
- 权限验证不应显著影响查询性能
- 字段权限应与菜单/按钮权限使用相同的权限编码体系

### 利益相关者

- AI Agent：需要知道当前用户可用的查询字段
- 安全团队：需要控制敏感数据的访问
- 前端开发者：需要根据权限动态显示查询条件

## 目标 / 非目标

### 目标

1. 为可搜索字段添加权限配置能力
2. `searchable-fields` 接口根据用户权限返回可用字段
3. `query` 接口验证用户是否有权限使用查询中的字段
4. 提供清晰的错误提示，告知缺少的权限

### 非目标

1. 不实现行级数据权限（如只能查看本部门数据）
2. 不实现字段值脱敏（如手机号部分隐藏）
3. 不修改现有的菜单/按钮权限系统

## 决策

### 决策 1：权限配置方式

**选择**：在字段配置中添加可选的 `permission` 属性。

**实现**：
```python
USER_SEARCHABLE_FIELDS = [
    {"name": "id", "display_name": "用户ID", "type": "string"},  # 无权限要求
    {"name": "mobile", "display_name": "手机号", "type": "string", "permission": "user:view_sensitive"},
    {"name": "email", "display_name": "邮箱", "type": "string", "permission": "user:view_sensitive"},
]
```

**理由**：
- 配置简单，与现有结构兼容
- 单个权限编码，复用现有权限体系
- `permission: None` 或缺省表示无需权限

### 决策 2：权限验证位置

**选择**：在两个位置进行验证。

1. **`searchable-fields` 接口**：过滤返回的字段列表
2. **`query` 接口**：验证查询条件中的字段权限

**实现**：
```python
# fu_crud.py
def filter_searchable_fields_by_permission(
    searchable_fields: List[Dict],
    user_permissions: Set[str]
) -> List[Dict]:
    """根据用户权限过滤可搜索字段"""
    return [
        field for field in searchable_fields
        if field.get('permission') is None or field['permission'] in user_permissions
    ]

def validate_query_field_permissions(
    filters: List[FilterCondition],
    searchable_fields: List[Dict],
    user_permissions: Set[str]
) -> None:
    """验证查询字段权限，无权限时抛出 HttpError"""
    ...
```

**理由**：
- 双重验证确保安全性
- `searchable-fields` 过滤后，AI Agent 不会构造无权限的查询
- `query` 验证是最后一道防线

### 决策 3：权限获取方式

**选择**：通过 `request.auth` 获取当前用户，调用 `user.get_all_permission_codes()` 获取权限集合。

**理由**：
- 复用现有的用户权限获取逻辑
- 权限已被缓存，性能可控

### 决策 4：敏感字段权限编码

**选择**：为每个模块定义统一的敏感字段权限编码。

| 模块 | 权限编码 | 保护字段 |
|------|---------|---------|
| user | `user:view_sensitive` | mobile, email |
| login_log | `login_log:view_ip` | login_ip |

**理由**：
- 权限粒度适中，不过于细碎
- 便于在角色管理中配置

### 考虑的替代方案

1. **字段级独立权限**
   - 例如：`user:view_mobile`, `user:view_email`
   - 优点：粒度更细
   - 缺点：权限数量爆炸，管理复杂
   - 结论：不采用

2. **角色白名单**
   - 例如：`{"name": "mobile", "allowed_roles": ["admin", "hr"]}`
   - 优点：直观
   - 缺点：与现有权限系统不一致
   - 结论：不采用

## 风险 / 权衡

### 风险 1：性能影响

**风险**：每次查询都需要获取用户权限。

**缓解措施**：
- 用户权限已有缓存机制
- 权限验证是简单的集合查找，O(1) 复杂度

### 风险 2：配置遗漏

**风险**：新增字段忘记配置权限。

**缓解措施**：
- 默认无需权限，不影响功能
- 敏感字段需在代码审查时检查权限配置

## 迁移计划

### 阶段 1：基础设施（0.5 天）
1. 修改 `fu_crud.py` 添加权限过滤和验证函数
2. 修改 Schema 支持 `permission` 属性

### 阶段 2：核心模块适配（0.5 天）
1. 为 `user` 模块的敏感字段添加权限
2. 为 `login_log` 模块的 IP 字段添加权限
3. 修改各模块 API 传入用户权限

### 阶段 3：权限初始化（0.5 天）
1. 在权限表中添加新的权限记录
2. 为管理员角色分配敏感字段权限

### 回滚计划

- 移除字段的 `permission` 属性即可回滚
- 权限过滤函数检测到无 `permission` 属性时跳过验证

## 待决问题

1. **是否需要审计日志？**
   - 记录用户尝试访问无权限字段的行为
   - 建议：作为后续增强

2. **是否需要在 OpenAPI 文档中体现字段权限？**
   - 建议：不在 OpenAPI 中体现，通过 `searchable-fields` 接口动态获取
