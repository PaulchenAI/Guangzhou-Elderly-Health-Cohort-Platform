# 提案总结：数据库表查询管理系统

## ✅ 提案创建完成

OpenSpec 变更 ID: `add-database-table-query-manager`

验证状态: ✅ 通过 (`openspec-cn validate --strict`)

## 📋 提案文件清单

```
openspec/changes/add-database-table-query-manager/
├── README.md                                        # 提案总览（本文件）
├── proposal.md                                      # 提案说明（为什么、做什么、影响什么）
├── tasks.md                                         # 实施任务清单（7 阶段 32 个子任务）
├── design.md                                        # 技术设计文档（架构、安全、权衡）
├── config-examples.md                               # 配置示例（5 个真实表示例）
└── specs/
    └── database-table-query/
        └── spec.md                                  # 功能规范（9 个需求，40+ 场景）
```

## 🎯 核心目标

为 zq-platform 添加一个**通用的数据库表查询管理系统**，支持：

1. ✅ **配置化查询**：通过 JSON 配置定义表查询规则，无需编写代码
2. ✅ **统一 API**：提供通用查询接口，支持分页、过滤、排序
3. ✅ **前端界面**：友好的表切换、条件查询、数据展示、导出功能
4. ✅ **菜单集成**：自动生成表查询菜单项

## 📊 功能规范概览

### 新增需求统计
- **9 个核心需求**
- **40+ 个使用场景**
- **覆盖领域**：配置管理、动态查询、安全防护、数据导出、前端页面、菜单初始化、权限控制、审计日志

### 需求详细列表

| # | 需求 | 场景数 | 优先级 |
|---|------|--------|--------|
| 1 | 表查询配置管理 | 4 | P0 |
| 2 | 动态表查询 API | 6 | P0 |
| 3 | SQL 注入防护 | 4 | P0 |
| 4 | 数据导出功能 | 4 | P1 |
| 5 | 前端表查询页面 | 5 | P1 |
| 6 | 菜单初始化脚本 | 3 | P1 |
| 7 | 配置管理 API | 6 | P1 |
| 8 | 操作审计日志 | 4 | P2 |
| 9 | 权限控制 | 4 | P0 |

## 🏗️ 技术架构

### 后端架构（Django）

```
backend-django/
└── core/
    └── table_query/                      # 新增模块
        ├── __init__.py
        ├── table_query_model.py          # 配置存储模型
        ├── table_query_schema.py         # Pydantic 校验
        └── table_query_api.py            # 查询 API
            ├── GET  /api/table-query/configs/          # 获取配置列表
            ├── GET  /api/table-query/configs/{id}      # 获取配置详情
            ├── POST /api/table-query/configs/          # 创建配置
            ├── PUT  /api/table-query/configs/{id}      # 更新配置
            ├── DEL  /api/table-query/configs/{id}      # 删除配置
            ├── POST /api/table-query/query/            # 执行查询
            └── POST /api/table-query/export/           # 导出数据
```

### 前端架构（Vue 3）

```
web/apps/web-ele/src/
└── views/
    └── table-query/                      # 新增页面
        ├── index.vue                     # 主页面
        ├── components/
        │   ├── TableSelector.vue         # 表选择器
        │   ├── QueryForm.vue            # 动态查询表单
        │   ├── DataTable.vue            # 数据展示表格
        │   └── ExportButton.vue         # 导出按钮
        └── api/
            └── table-query.ts           # API 调用封装
```

### 数据库设计

```sql
-- 表查询配置表
CREATE TABLE table_query_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(100) NOT NULL,           -- 表名
    display_name VARCHAR(200) NOT NULL,         -- 显示名称
    description TEXT,                           -- 描述
    config_json JSON NOT NULL,                  -- 配置（字段、查询条件等）
    is_active BOOLEAN DEFAULT TRUE,             -- 是否激活
    created_by INT,                             -- 创建人
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_table_name (table_name)
);

-- 查询操作日志表
CREATE TABLE table_query_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,                       -- 用户ID
    table_name VARCHAR(100) NOT NULL,           -- 查询的表
    operation VARCHAR(20) NOT NULL,             -- 操作类型（query/export）
    filters JSON,                               -- 查询条件
    record_count INT,                           -- 返回/导出记录数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_table_name (table_name),
    INDEX idx_created_at (created_at)
);
```

## 🔒 安全设计

### 多层防护机制

```
用户请求
    │
    ├─► 1. JWT 认证
    │       └─► 验证用户身份
    │
    ├─► 2. 权限验证（RBAC）
    │       └─► 检查表查询权限
    │
    ├─► 3. 表名白名单
    │       └─► 只允许配置的表
    │
    ├─► 4. 字段白名单
    │       └─► 只允许配置的字段
    │
    ├─► 5. 操作符白名单
    │       └─► 只允许安全的操作符
    │
    ├─► 6. 参数化查询
    │       └─► 防止 SQL 注入
    │
    └─► 7. 审计日志
            └─► 记录所有操作
```

## 📅 实施计划

### 时间线（5 周）

```
第 1-2 周：基础功能开发
    ├─ Week 1
    │   ├─ Day 1-2: 数据库设计与模型创建
    │   ├─ Day 3-4: 后端查询 API 实现
    │   └─ Day 5: 安全验证逻辑
    └─ Week 2
        ├─ Day 1-3: 前端页面开发
        └─ Day 4-5: 前后端联调

第 3 周：功能完善
    ├─ 配置管理功能
    ├─ 数据导出功能
    └─ 菜单初始化脚本

第 4 周：测试与优化
    ├─ 单元测试
    ├─ 安全测试
    └─ 性能优化

第 5 周：部署与反馈
    ├─ 部署到测试环境
    ├─ 创建示例配置
    └─ 用户培训
```

## 📝 配置示例

### 工作流请求表配置

```json
{
  "table_name": "WORKFLOW_REQUESTBASE",
  "display_name": "工作流请求",
  "description": "工作流系统请求基础数据表",
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
      "sortable": true,
      "visible": true
    },
    {
      "name": "CREATEDATE",
      "display_name": "创建日期",
      "type": "datetime",
      "searchable": true,
      "sortable": true,
      "visible": true
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "REQUESTID DESC",
  "allowed_operations": ["query", "export"]
}
```

更多配置示例请参见 [config-examples.md](./config-examples.md)

## 🚀 快速开始

### 1. 验证提案

```bash
cd /mnt/f/work/zq-platform
openspec-cn validate add-database-table-query-manager --strict
```

### 2. 查看提案详情

```bash
openspec-cn show add-database-table-query-manager
```

### 3. 开始实施

```bash
# 查看任务清单
cat openspec/changes/add-database-table-query-manager/tasks.md
```

## 📚 文档导航

| 文档 | 描述 | 适用人员 |
|------|------|----------|
| [proposal.md](./proposal.md) | 提案说明（为什么、做什么、影响） | 所有人 |
| [design.md](./design.md) | 技术设计（架构、安全、权衡） | 开发者 |
| [tasks.md](./tasks.md) | 实施任务清单（32 个子任务） | 开发者 |
| [spec.md](./specs/database-table-query/spec.md) | 功能规范（9 个需求，40+ 场景） | 开发者、测试 |
| [config-examples.md](./config-examples.md) | 配置示例（5 个真实表） | 配置管理员 |

## ✨ 亮点特性

1. **零代码配置**：通过 JSON 配置快速添加新表查询，无需修改代码
2. **安全第一**：7 层安全防护，防止 SQL 注入和非法访问
3. **性能优化**：强制分页、查询限制、索引建议
4. **用户友好**：动态表单生成、友好的错误提示、数据导出
5. **易于维护**：统一的代码结构、完整的文档、详细的日志

## 🎉 验证结果

```bash
$ openspec-cn validate add-database-table-query-manager --strict
✅ 变更 'add-database-table-query-manager' 验证通过
```

**统计数据：**
- ✅ 9 个需求定义
- ✅ 40+ 个场景覆盖
- ✅ 0 个验证错误
- ✅ 100% 规范符合度

## 📞 下一步行动

### 待批准

- [ ] 项目负责人审核提案
- [ ] 技术负责人审核设计方案
- [ ] 安全团队审核安全方案

### 待实施

- [ ] 按照 tasks.md 逐步实施
- [ ] 在实施过程中更新任务状态
- [ ] 收集反馈并持续改进

### 待归档

- [ ] 实施完成后归档提案
- [ ] 更新项目规范文档
- [ ] 总结经验教训

## 📊 度量指标

### 预期收益

- **开发效率提升**：新增表查询从 2 天 → 5 分钟
- **代码减少**：避免为每个表编写重复代码（估计减少 10,000+ 行）
- **维护成本降低**：配置化方案更易维护和扩展
- **用户体验提升**：统一的查询界面，降低学习成本

### 风险评估

- **性能风险**：中等（通过强制分页和限制缓解）
- **安全风险**：低（7 层防护机制）
- **复杂度风险**：低（清晰的架构设计）
- **维护风险**：低（完整的文档和测试）

---

**创建时间**：2026-01-11  
**创建者**：AI Assistant  
**OpenSpec 版本**：中文版  
**项目**：zq-platform  

如有问题或建议，请联系项目团队。

