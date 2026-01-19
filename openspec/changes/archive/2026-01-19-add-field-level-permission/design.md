# 设计文档：动态查询接口字段级权限控制

## 上下文

### 背景

动态查询接口（`POST /{module}/query` 和 `GET /{module}/searchable-fields`）已在 10 个核心模块中实现。当前所有用户看到相同的可搜索字段列表，不受权限控制。

### 约束

- 必须与现有 RBAC 权限系统集成
- **字段配置结构保持不变**，不添加 `permission` 属性
- **通过查询系统权限表判断字段访问权限**
- `searchable-fields` 接口输出结构保持不变
- 权限验证不应显著影响查询性能

### 利益相关者

- AI Agent：需要知道当前用户可用的查询字段
- 安全团队：需要控制敏感数据的访问
- 前端开发者：需要根据权限动态显示查询条件

## 目标 / 非目标

### 目标

1. 通过系统权限表控制字段访问，不修改字段配置结构
2. `searchable-fields` 接口根据用户权限返回可用字段
3. `query` 接口验证用户是否有权限使用查询中的字段
4. 提供清晰的错误提示，告知缺少的权限

### 非目标

1. 不实现行级数据权限（如只能查看本部门数据）
2. 不实现字段值脱敏（如手机号部分隐藏）
3. 不修改现有的菜单/按钮权限系统
4. 不修改可搜索字段配置结构

## 决策

### 决策 1：权限控制方式

**选择**：通过系统权限表中的权限编码，使用约定的命名规范来控制字段访问。

**权限编码命名规范**：
```
{module}:query:{field_name}
```

**示例**：
| 权限编码 | 说明 | 保护字段 |
|---------|------|---------|
| `user:query:mobile` | 用户模块查询手机号 | user.mobile |
| `user:query:email` | 用户模块查询邮箱 | user.email |
| `login_log:query:login_ip` | 登录日志查询IP | login_log.login_ip |

**逻辑**：
- 如果权限表中**存在**该字段的权限记录，且用户**没有**该权限 → 隐藏字段
- 如果权限表中**不存在**该字段的权限记录 → 字段对所有人可见
- 如果用户**拥有**该权限 → 字段可见

**理由**：
- 字段配置无需修改，保持简洁
- 权限由系统管理员在权限管理界面配置
- 新增敏感字段只需在权限表添加记录，无需改代码

### 决策 2：权限验证实现

**选择**：在 `fu_crud.py` 中添加权限检查函数，查询权限表判断字段访问权限。

**实现**：
```python
# fu_crud.py

def get_field_permissions(module: str) -> Dict[str, str]:
    """
    获取模块的字段权限映射
    
    从权限表查询以 '{module}:query:' 开头的权限，
    返回 {field_name: permission_code} 映射
    """
    from core.permission.permission_model import Permission
    
    prefix = f"{module}:query:"
    permissions = Permission.objects.filter(
        code__startswith=prefix,
        is_active=True
    ).values_list('code', flat=True)
    
    # 提取字段名：user:query:mobile -> mobile
    return {
        code.split(':')[-1]: code
        for code in permissions
    }


def filter_searchable_fields_by_permission(
    searchable_fields: List[Dict],
    module: str,
    user_permissions: Set[str]
) -> List[Dict]:
    """根据用户权限过滤可搜索字段"""
    field_permissions = get_field_permissions(module)
    
    result = []
    for field in searchable_fields:
        field_name = field['name']
        required_permission = field_permissions.get(field_name)
        
        # 无权限要求，或用户拥有权限
        if required_permission is None or required_permission in user_permissions:
            result.append(field)
    
    return result
```

**理由**：
- 权限配置集中在权限表，便于管理
- 查询结果可以缓存，避免频繁查库
- 与现有权限管理界面集成

### 决策 3：缓存策略

**选择**：缓存模块的字段权限映射，权限变更时清除缓存。

**实现**：
```python
from django.core.cache import cache

FIELD_PERMISSION_CACHE_KEY = "field_permission:{module}"
FIELD_PERMISSION_CACHE_TIMEOUT = 3600  # 1小时

def get_field_permissions(module: str) -> Dict[str, str]:
    cache_key = FIELD_PERMISSION_CACHE_KEY.format(module=module)
    result = cache.get(cache_key)
    
    if result is None:
        # 查询数据库...
        cache.set(cache_key, result, FIELD_PERMISSION_CACHE_TIMEOUT)
    
    return result
```

**理由**：
- 减少数据库查询
- 权限变更不频繁，1 小时缓存可接受

### 决策 4：输出结构不变

**选择**：`searchable-fields` 接口的响应结构保持不变。

**当前输出**：
```json
{
  "module": "user",
  "display_name": "用户管理",
  "searchable_fields": [
    {"name": "id", "display_name": "用户ID", "type": "string"},
    {"name": "name", "display_name": "姓名", "type": "string"}
  ]
}
```

**变更后输出**（结构相同，仅字段列表根据权限过滤）：
```json
{
  "module": "user",
  "display_name": "用户管理",
  "searchable_fields": [
    {"name": "id", "display_name": "用户ID", "type": "string"},
    {"name": "name", "display_name": "姓名", "type": "string"}
    // mobile, email 被过滤（无权限）
  ]
}
```

## 风险 / 权衡

### 风险 1：性能影响

**风险**：每次请求都需要查询权限表。

**缓解措施**：
- 字段权限映射缓存 1 小时
- 用户权限已有缓存机制
- 权限验证是简单的集合查找，O(1) 复杂度

### 风险 2：权限配置遗漏

**风险**：忘记在权限表中添加敏感字段的权限记录。

**缓解措施**：
- 默认无权限记录 = 字段对所有人可见（安全设计：显式限制）
- 提供权限初始化脚本
- 在部署文档中说明需要配置的权限

## 迁移计划

### 阶段 1：基础设施（0.5 天）
1. 在 `fu_crud.py` 中添加 `get_field_permissions` 函数
2. 添加 `filter_searchable_fields_by_permission` 函数
3. 添加 `validate_query_field_permissions` 函数
4. 添加缓存逻辑

### 阶段 2：模块适配（0.5 天）
1. 修改各模块的 `searchable-fields` 接口，传入模块名和用户权限
2. 修改各模块的 `query` 接口，验证字段权限

### 阶段 3：权限初始化（0.5 天）
1. 创建迁移脚本，在权限表中添加敏感字段的权限记录
2. 为管理员角色分配新权限

### 回滚计划

- 删除权限表中的字段权限记录即可回滚
- 函数检测到无权限记录时，所有字段可见

## 待决问题

1. **是否需要审计日志？**
   - 记录用户尝试访问无权限字段的行为
   - 建议：作为后续增强

2. **权限管理界面是否需要调整？**
   - 当前权限管理可直接添加字段权限
   - 建议：无需调整，使用现有功能
