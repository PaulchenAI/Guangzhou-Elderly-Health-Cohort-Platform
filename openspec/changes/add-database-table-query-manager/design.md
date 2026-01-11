# 设计文档：数据库表查询管理系统

## 上下文

项目已经完成了从 Oracle 到 MySQL 的大量医院数据迁移（约 100+ 张表），这些表包含患者、医嘱、护理、工作流等各类业务数据。目前这些数据只是存储在数据库中，缺乏一个统一的查询和展示界面。

### 背景
- 已导入表：包括 WORKFLOW_REQUESTBASE（工作流）、WM_MATERIAL（物资）、BS_DEPARTMENT（部门）等
- 数据量：部分表数据量较大（GB 级别）
- 用户需求：业务人员需要快速查看和导出这些数据，但不希望为每个表开发独立页面

### 约束
- 必须使用 Django + Django Ninja 框架
- 前端使用 Vue 3 + Element Plus
- 需要支持 MySQL/PostgreSQL/SQL Server 多种数据库
- 必须防止 SQL 注入
- 大表查询需要分页和性能优化

### 利益相关者
- 业务人员：需要简单的数据查询界面
- 开发人员：需要可维护的配置化方案
- 系统管理员：需要权限控制和安全保障

## 目标 / 非目标

### 目标
- 通过 JSON 配置快速定义表查询规则，无需编写代码
- 提供统一的查询 API，支持分页、过滤、排序
- 前端提供友好的表切换和数据展示界面
- 自动生成菜单，降低配置成本
- 确保查询安全，防止 SQL 注入和非法访问
- 支持数据导出（Excel/CSV）

### 非目标
- 不支持复杂的多表 JOIN 查询（初期版本）
- 不提供数据编辑功能（只读查询）
- 不支持实时数据刷新（WebSocket）
- 不提供数据统计和图表功能（后续扩展）

## 决策

### 1. 配置存储方案

**决策**：使用数据库表存储配置（TableQueryConfig），配置内容使用 JSON 字段

**理由**：
- 支持动态加载和热更新
- 便于权限控制（基于数据库记录）
- 支持版本管理和审计
- 可通过 API 进行配置管理

**配置结构**：
```json
{
  "table_name": "WORKFLOW_REQUESTBASE",
  "display_name": "工作流请求",
  "description": "工作流系统请求基础数据",
  "fields": [
    {
      "name": "REQUESTID",
      "display_name": "请求ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true
    },
    {
      "name": "REQUESTNAME",
      "display_name": "请求名称",
      "type": "string",
      "searchable": true,
      "visible": true
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "REQUESTID DESC",
  "allowed_operations": ["query", "export"]
}
```

### 2. 查询安全方案

**决策**：使用参数化查询 + 白名单验证

**安全措施**：
- 表名白名单：只允许查询配置中定义的表
- 字段白名单：只允许查询配置中定义的字段
- 使用 Django ORM 的参数化查询，避免拼接 SQL
- 排序字段验证：检查排序字段是否在白名单中
- 过滤操作符白名单：只允许安全的操作符（=, !=, >, <, LIKE, IN, BETWEEN）

### 3. 动态查询实现方案

**决策**：使用 Django 的 `connection.cursor()` + 参数化查询

**理由**：
- Django ORM 难以动态映射未在 models.py 中定义的表
- 直接使用 cursor 更灵活，适合动态表查询
- 仍然使用参数化查询，保证安全性

**查询构建示例**：
```python
def build_query(config, filters, page, page_size, order_by):
    # 验证表名
    table_name = validate_table_name(config['table_name'])
    
    # 验证字段
    select_fields = [f['name'] for f in config['fields'] if f['visible']]
    select_fields = validate_fields(select_fields, config)
    
    # 构建 WHERE 子句
    where_clauses = []
    params = []
    for field, operator, value in filters:
        if not is_valid_filter(field, operator, config):
            raise ValidationError(f"Invalid filter: {field}")
        where_clauses.append(f"{field} {operator} %s")
        params.append(value)
    
    # 构建查询
    sql = f"SELECT {', '.join(select_fields)} FROM {table_name}"
    if where_clauses:
        sql += f" WHERE {' AND '.join(where_clauses)}"
    
    # 验证排序字段
    order_by = validate_order_by(order_by, config)
    sql += f" ORDER BY {order_by}"
    
    # 分页
    sql += " LIMIT %s OFFSET %s"
    params.extend([page_size, (page - 1) * page_size])
    
    return sql, params
```

### 4. 前端架构方案

**决策**：使用单页面 + 动态组件

**组件结构**：
```
TableQueryView.vue (主页面)
├── TableSelector.vue (表选择器)
├── QueryForm.vue (查询表单 - 动态生成)
├── DataTable.vue (数据表格)
└── ExportButton.vue (导出按钮)
```

**特点**：
- 根据配置动态生成查询表单
- 使用 Element Plus Table 组件
- 支持前端分页和后端分页
- 响应式设计，支持移动端

### 5. 菜单生成方案

**决策**：使用 Django Management Command 生成菜单

**实现**：
```python
# 命令：python manage.py init_table_query_menus
class Command(BaseCommand):
    def handle(self, *args, **options):
        # 读取所有表查询配置
        configs = TableQueryConfig.objects.filter(is_active=True)
        
        # 创建父菜单
        parent_menu = Menu.objects.get_or_create(
            name="数据查询",
            path="/table-query",
            component="TableQueryView"
        )
        
        # 为每个配置创建子菜单
        for config in configs:
            Menu.objects.get_or_create(
                name=config.display_name,
                path=f"/table-query/{config.id}",
                parent=parent_menu,
                component="TableQueryView"
            )
```

### 考虑的替代方案

#### 替代方案 1：使用 Django Admin
- **优点**：快速实现，内置功能丰富
- **缺点**：定制化程度低，UI 不符合项目风格
- **结论**：不采用，自研更灵活

#### 替代方案 2：配置文件存储（YAML/JSON 文件）
- **优点**：版本控制友好，部署简单
- **缺点**：不支持动态更新，难以做权限控制
- **结论**：不采用，数据库存储更适合动态场景

#### 替代方案 3：为每个表生成独立的 API 和页面
- **优点**：性能最优，定制化最强
- **缺点**：开发成本高，维护困难
- **结论**：不采用，配置化方案更合适

## 风险 / 权衡

### 风险 1：大表查询性能问题
- **风险**：部分表数据量达到 GB 级别，查询可能很慢
- **缓解措施**：
  - 强制分页，限制单次查询数量
  - 在配置中设置 `max_page_size` 上限
  - 建议用户在数据库中为常用查询字段创建索引
  - 考虑添加查询缓存（Redis）

### 风险 2：SQL 注入风险
- **风险**：动态构建 SQL 可能引入注入漏洞
- **缓解措施**：
  - 使用参数化查询
  - 严格的白名单验证
  - 代码审计和安全测试
  - 限制用户输入的长度和格式

### 风险 3：配置错误导致系统问题
- **风险**：错误的配置可能导致查询失败或暴露敏感数据
- **缓解措施**：
  - 配置验证（JSON Schema）
  - 配置导入前预检查
  - 敏感字段标记（如密码字段自动脱敏）
  - 配置审计日志

### 权衡 1：灵活性 vs 安全性
- **权衡**：为了安全性，限制了查询的灵活性（如不支持复杂 JOIN）
- **接受理由**：初期版本优先保证安全，后续可通过配置扩展支持更复杂查询

### 权衡 2：性能 vs 通用性
- **权衡**：通用查询方案性能不如专门优化的查询
- **接受理由**：对于查看历史数据的场景，查询性能要求不高

## 迁移计划

### 阶段 1：基础功能开发（第 1-2 周）
1. 创建数据模型和迁移
2. 实现基础查询 API
3. 开发前端基础页面

### 阶段 2：功能完善（第 3 周）
1. 添加配置管理功能
2. 实现数据导出
3. 菜单初始化脚本

### 阶段 3：测试与优化（第 4 周）
1. 安全测试
2. 性能优化
3. 文档编写

### 阶段 4：部署与反馈（第 5 周）
1. 部署到测试环境
2. 为已导入表创建配置
3. 用户培训和反馈收集

### 回滚计划
- 删除 `table_query` 模块
- 回滚数据库迁移
- 删除前端页面和路由
- 清理菜单配置

## 待决问题

- [ ] 是否需要支持数据导出审计（记录谁导出了哪些数据）？
- [ ] 是否需要支持查询结果缓存？缓存策略如何设计？
- [ ] 是否需要支持自定义查询（用户可以编写 SQL）？如何确保安全？
- [ ] 大表查询是否需要异步处理（Celery 任务）？
- [ ] 是否需要支持数据字段的国际化？
- [ ] 配置是否需要支持导入/导出功能（备份和迁移）？

