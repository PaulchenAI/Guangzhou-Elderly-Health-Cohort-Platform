# 数据库表查询管理系统提案

## 概述

本提案旨在为 zq-platform 添加一个通用的数据库表查询管理系统，允许用户通过配置化的方式查询和展示已导入的医院数据表，无需为每个表单独编写代码。

## 背景

项目已成功完成从 Oracle 到 MySQL 的数据迁移（docs/hospital/convertsql），导入了 100+ 张医院业务表，包括工作流、物资管理、护理记录等各类数据。目前这些数据缺乏统一的查询和展示界面。

## 核心功能

1. **JSON 配置管理**：通过 JSON 配置定义表的查询条件和显示字段
2. **通用查询 API**：支持分页、过滤、排序的动态查询接口
3. **前端查询页面**：支持多表切换、条件查询、数据展示、导出功能
4. **菜单自动初始化**：一键生成表查询菜单项

## 技术方案

### 后端架构
- **框架**：Django + Django Ninja
- **数据库**：MySQL（支持 PostgreSQL/SQL Server）
- **安全**：参数化查询 + 白名单验证 + SQL 注入防护
- **性能**：强制分页 + 查询限制 + 索引建议

### 前端架构
- **框架**：Vue 3 + Element Plus
- **特点**：动态表单生成 + 响应式表格 + 数据导出

### 核心模块
```
backend-django/core/table_query/
├── table_query_model.py    # 数据模型
├── table_query_schema.py   # Pydantic Schema
└── table_query_api.py      # API 接口

web/apps/web-ele/src/views/table-query/
├── TableQueryView.vue      # 主页面
├── TableSelector.vue       # 表选择器
├── QueryForm.vue          # 查询表单
└── DataTable.vue          # 数据表格
```

## 安全设计

- ✅ 表名白名单验证
- ✅ 字段名白名单验证
- ✅ 参数化查询（防 SQL 注入）
- ✅ 操作符白名单限制
- ✅ 权限验证（RBAC 集成）
- ✅ 操作审计日志

## 使用示例

### 配置示例
```json
{
  "table_name": "WORKFLOW_REQUESTBASE",
  "display_name": "工作流请求",
  "fields": [
    {
      "name": "REQUESTID",
      "display_name": "请求ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100
}
```

### 菜单初始化
```bash
python manage.py init_table_query_menus
```

## 文件清单

- ✅ `proposal.md` - 提案说明
- ✅ `tasks.md` - 实施任务清单（7 大阶段，30+ 子任务）
- ✅ `design.md` - 技术设计文档（架构、安全、性能）
- ✅ `specs/database-table-query/spec.md` - 功能规范（8 个需求，40+ 场景）
- ✅ `config-examples.md` - 配置示例（5 个真实表示例）

## 实施计划

| 阶段 | 时间 | 内容 |
|------|------|------|
| 阶段 1 | 第 1-2 周 | 数据库设计、后端 API、前端基础页面 |
| 阶段 2 | 第 3 周 | 配置管理、数据导出、菜单集成 |
| 阶段 3 | 第 4 周 | 测试、优化、文档 |
| 阶段 4 | 第 5 周 | 部署、反馈、改进 |

## 验证状态

✅ **OpenSpec 验证通过**（`openspec-cn validate --strict`）

```bash
openspec-cn validate add-database-table-query-manager --strict
# 输出：变更 'add-database-table-query-manager' 验证通过
```

## 下一步行动

1. **获得批准**：等待项目负责人审核和批准
2. **开始实施**：按照 `tasks.md` 清单逐步实施
3. **持续反馈**：在实施过程中收集反馈并调整

## 相关文档

- [提案说明](./proposal.md)
- [实施任务](./tasks.md)
- [技术设计](./design.md)
- [功能规范](./specs/database-table-query/spec.md)
- [配置示例](./config-examples.md)

## 联系方式

如有问题或建议，请联系项目团队。

