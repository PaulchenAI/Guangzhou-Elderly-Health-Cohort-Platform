# 设计文档：数据库表查询管理系统

> **参考规范**：
> - 后端：`docs/backend-api-development-guide.md`
> - 前端：`docs/frontend-development-guide.md`

## 上下文

项目已经完成了从 Oracle 到 MySQL 的大量医院数据迁移（约 100+ 张表），这些表包含患者、医嘱、护理、工作流等各类业务数据。目前这些数据只是存储在数据库中，缺乏一个统一的查询和展示界面。

### 背景
- 已导入表：包括 WORKFLOW_REQUESTBASE（工作流）、WM_MATERIAL（物资）、BS_DEPARTMENT（部门）等
- 数据量：部分表数据量较大（GB 级别）
- 用户需求：业务人员需要快速查看和导出这些数据，但不希望为每个表开发独立页面

### 约束
- 后端必须使用 Django 5.x + Django Ninja 框架，遵循 `docs/backend-api-development-guide.md` 规范
- 前端使用 Vue 3 + Element Plus，遵循 `docs/frontend-development-guide.md` 规范
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
      "visible": true,
      "width": 100
    },
    {
      "name": "REQUESTNAME",
      "display_name": "请求名称",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 200
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

### 3. 后端架构方案

**决策**：遵循项目模块化架构，在 `core/` 下创建 `table_query` 模块

**目录结构**（符合 `docs/backend-api-development-guide.md` 规范）：

```
backend-django/
└── core/
    └── table_query/                      # 新增模块
        ├── __init__.py
        ├── table_query_model.py          # 数据模型（TableQueryConfig）
        ├── table_query_schema.py         # Pydantic Schema
        └── table_query_api.py            # API 接口（Django Ninja Router）
```

**路由注册**（在 `core/router.py` 中添加）：

```python
# core/router.py
from core.table_query.table_query_api import router as table_query_router

# 在现有路由后添加
core_router.add_router("", table_query_router, tags=["Core-TableQuery"])
```

**API 端点设计**：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/table-query/configs/ | 获取配置列表 |
| GET | /api/table-query/configs/{id} | 获取配置详情 |
| POST | /api/table-query/configs/ | 创建配置 |
| PUT | /api/table-query/configs/{id} | 更新配置 |
| DELETE | /api/table-query/configs/{id} | 删除配置 |
| POST | /api/table-query/query/ | 执行动态查询 |
| POST | /api/table-query/export/ | 导出数据 |

**动态查询实现**（使用 `connection.cursor()` + 参数化查询）：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Query API - 表查询管理接口
提供动态表查询、配置管理和数据导出功能
"""
from django.db import connection
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from common.fu_crud import create, delete
from common.fu_pagination import MyPagination
from common.fu_schema import response_success
from core.table_query.table_query_model import TableQueryConfig, TableQueryLog
from core.table_query.table_query_schema import (
    TableQueryConfigSchemaIn,
    TableQueryConfigSchemaOut,
    TableQueryIn,
    TableQueryResult,
)

router = Router()


@router.post("/table-query/query", response=TableQueryResult, summary="执行动态表查询")
def execute_query(request, data: TableQueryIn):
    """
    执行动态表查询，支持分页、过滤、排序
    
    安全措施：
    - 表名白名单验证
    - 字段白名单验证
    - 参数化查询防止 SQL 注入
    """
    config = get_object_or_404(TableQueryConfig, id=data.config_id, is_deleted=False)
    
    if not config.is_active:
        raise HttpError(400, "该表查询配置已禁用")
    
    # 验证表名和字段（白名单）
    table_name = validate_table_name(config.table_name)
    select_fields = validate_fields(data.fields or get_visible_fields(config), config)
    
    # 构建安全的 WHERE 子句
    where_clauses, params = build_where_clause(data.filters, config)
    
    # 构建查询 SQL
    sql = f"SELECT {', '.join(select_fields)} FROM {table_name}"
    if where_clauses:
        sql += f" WHERE {' AND '.join(where_clauses)}"
    
    # 验证排序字段
    order_by = validate_order_by(data.order_by or config.config_json.get('default_order_by'), config)
    sql += f" ORDER BY {order_by}"
    
    # 分页
    max_page_size = config.config_json.get('max_page_size', 100)
    page_size = min(data.page_size, max_page_size)
    offset = (data.page - 1) * page_size
    sql += " LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    
    # 执行查询
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # 记录查询日志
    TableQueryLog.objects.create(
        user_id=str(request.auth.id),
        table_name=table_name,
        operation="query",
        filters=data.filters or {},
        record_count=len(results),
        sys_creator=request.auth,
    )
    
    total = get_total_count(table_name, where_clauses, params[:-2])
    return {"items": results, "total": total}
```

### 4. 前端架构方案

**决策**：遵循项目前端架构，在 `views/` 下创建表查询页面

**目录结构**（符合 `docs/frontend-development-guide.md` 规范）：

```
web/apps/web-ele/src/
├── views/
│   └── table-query/                     # 新增页面
│       ├── index.vue                    # 主页面
│       ├── data.ts                      # 表单/表格配置（useColumns, useSearchFormSchema）
│       └── modules/
│           └── query-form.vue           # 动态查询表单组件
└── api/
    └── core/
        └── table-query.ts               # API 接口封装（与其他 core API 放一起）
```

**主页面实现**（使用项目标准组件）：

```vue
<!-- views/table-query/index.vue -->
<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { TableQueryConfig } from '#/api/core/table-query';

import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElCard, ElMenu, ElMenuItem, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  executeTableQueryApi,
  exportTableDataApi,
  getTableQueryConfigsApi,
} from '#/api/core/table-query';

import { buildColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'TableQuery' });

// 表配置列表
const configs = ref<TableQueryConfig[]>([]);
const selectedConfigId = ref<string>('');
const currentFilters = ref<Record<string, any>>({});

const selectedConfig = computed(() =>
  configs.value.find((c) => c.id === selectedConfigId.value),
);

// 动态生成列配置
const columns = computed(() => buildColumns(selectedConfig.value));

// 动态生成搜索表单
const searchFormSchema = computed(() =>
  useSearchFormSchema(selectedConfig.value),
);

// 使用 VxeTable 组件
const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: columns.value,
    proxyConfig: {
      ajax: {
        query: async ({ page }) => {
          if (!selectedConfigId.value) {
            return { items: [], total: 0 };
          }
          const result = await executeTableQueryApi({
            configId: selectedConfigId.value,
            page: page.currentPage,
            pageSize: page.pageSize,
            filters: currentFilters.value,
          });
          return { items: result.items, total: result.total };
        },
      },
    },
  },
  formOptions: {
    schema: searchFormSchema.value,
  },
});

// 切换表配置
function handleConfigChange(configId: string) {
  selectedConfigId.value = configId;
  currentFilters.value = {};
  gridApi.reload();
}

// 导出数据
async function handleExport(format: 'excel' | 'csv') {
  if (!selectedConfigId.value) {
    ElMessage.warning('请先选择数据表');
    return;
  }
  try {
    await exportTableDataApi({
      configId: selectedConfigId.value,
      filters: currentFilters.value,
      format,
    });
    ElMessage.success('导出成功');
  } catch {
    ElMessage.error('导出失败');
  }
}

// 加载配置列表
onMounted(async () => {
  const result = await getTableQueryConfigsApi();
  configs.value = result;
  if (result.length > 0) {
    selectedConfigId.value = result[0].id;
  }
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full gap-4">
      <!-- 表选择器 -->
      <div class="w-60 flex-shrink-0">
        <ElCard header="数据表">
          <ElMenu
            :default-active="selectedConfigId"
            @select="handleConfigChange"
          >
            <ElMenuItem
              v-for="config in configs"
              :key="config.id"
              :index="config.id"
            >
              {{ config.displayName }}
            </ElMenuItem>
          </ElMenu>
        </ElCard>
      </div>

      <!-- 数据表格 -->
      <div class="flex-1">
        <Grid />
      </div>
    </div>
  </Page>
</template>
```

**API 封装**：

```typescript
// api/core/table-query.ts
import { requestClient } from '#/api/request';

/**
 * 表查询相关类型定义
 */
export interface FieldConfig {
  name: string;
  displayName: string;
  type: 'string' | 'integer' | 'decimal' | 'date' | 'datetime' | 'boolean';
  searchable?: boolean;
  sortable?: boolean;
  visible?: boolean;
  width?: number;
}

export interface TableQueryConfig {
  id: string;
  tableName: string;
  displayName: string;
  description?: string;
  configJson: {
    fields: FieldConfig[];
    defaultPageSize: number;
    maxPageSize: number;
    defaultOrderBy: string;
    allowedOperations: string[];
  };
  isActive: boolean;
  sysCreateDatetime?: string;
}

export interface TableQueryParams {
  configId: string;
  page: number;
  pageSize: number;
  filters?: Record<string, any>;
  orderBy?: string;
}

export interface TableQueryResult {
  items: Record<string, any>[];
  total: number;
}

/**
 * 获取表查询配置列表
 */
export function getTableQueryConfigsApi() {
  return requestClient.get<TableQueryConfig[]>('/core/table-query/configs');
}

/**
 * 获取单个配置详情
 */
export function getTableQueryConfigApi(id: string) {
  return requestClient.get<TableQueryConfig>(`/core/table-query/configs/${id}`);
}

/**
 * 执行动态表查询
 */
export function executeTableQueryApi(params: TableQueryParams) {
  return requestClient.post<TableQueryResult>('/core/table-query/query', params);
}

/**
 * 导出表数据
 */
export function exportTableDataApi(
  params: TableQueryParams & { format: 'excel' | 'csv' },
) {
  return requestClient.post('/core/table-query/export', params, {
    responseType: 'blob',
  });
}
```

### 5. 数据库设计

**模型定义**（继承 `RootModel`）：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Query Model - 表查询模型
用于存储表查询配置和操作日志
"""
from django.db import models
from common.fu_model import RootModel


class TableQueryConfig(RootModel):
    """
    表查询配置模型 - 存储可查询表的配置信息
    
    配置内容（config_json）包含：
    - fields: 字段配置列表
    - default_page_size: 默认分页大小
    - max_page_size: 最大分页大小
    - default_order_by: 默认排序
    - allowed_operations: 允许的操作（query/export）
    """
    
    table_name = models.CharField(
        max_length=100, 
        unique=True,
        db_index=True,
        help_text="数据库表名"
    )
    display_name = models.CharField(
        max_length=200, 
        help_text="显示名称"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="表描述"
    )
    config_json = models.JSONField(
        default=dict, 
        help_text="配置内容（JSON格式）"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="是否激活"
    )
    
    class Meta:
        db_table = "table_query_config"
        verbose_name = "表查询配置"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-sys_create_datetime"]

    def __str__(self):
        return f"{self.display_name} ({self.table_name})"
    
    def get_visible_fields(self):
        """获取可见字段列表"""
        fields = self.config_json.get('fields', [])
        return [f['name'] for f in fields if f.get('visible', True)]
    
    def get_searchable_fields(self):
        """获取可搜索字段列表"""
        fields = self.config_json.get('fields', [])
        return [f['name'] for f in fields if f.get('searchable', False)]


class TableQueryLog(RootModel):
    """
    表查询日志模型 - 记录查询和导出操作
    用于安全审计和使用统计
    """
    
    OPERATION_CHOICES = [
        ("query", "查询"),
        ("export", "导出"),
    ]
    
    user_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="操作用户ID"
    )
    table_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="查询的表名"
    )
    operation = models.CharField(
        max_length=20, 
        choices=OPERATION_CHOICES,
        db_index=True,
        help_text="操作类型"
    )
    filters = models.JSONField(
        default=dict, 
        help_text="查询条件"
    )
    record_count = models.IntegerField(
        default=0, 
        help_text="返回/导出记录数"
    )
    
    class Meta:
        db_table = "table_query_log"
        verbose_name = "表查询日志"
        verbose_name_plural = verbose_name
        ordering = ["-sys_create_datetime"]
        indexes = [
            models.Index(fields=['user_id', 'table_name']),
            models.Index(fields=['operation', 'sys_create_datetime']),
        ]
```

### 6. 菜单生成方案

**决策**：使用 Django Management Command 生成菜单

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化表查询菜单命令
"""
# core/table_query/management/commands/init_table_query_menus.py
from django.core.management.base import BaseCommand
from core.menu.menu_model import Menu
from core.table_query.table_query_model import TableQueryConfig


class Command(BaseCommand):
    help = "初始化表查询菜单"

    def handle(self, *args, **options):
        # 创建父菜单
        parent_menu, created = Menu.objects.get_or_create(
            path="/table-query",
            defaults={
                "name": "TableQuery",
                "title": "数据查询",
                "type": "catalog",
                "component": "LAYOUT",
                "icon": "ant-design:database-outlined",
                "order": 100,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("创建父菜单：数据查询"))
        
        # 为每个配置创建子菜单
        configs = TableQueryConfig.objects.filter(is_active=True, is_deleted=False)
        created_count = 0
        
        for idx, config in enumerate(configs):
            menu, created = Menu.objects.update_or_create(
                path=f"/table-query/{config.id}",
                defaults={
                    "name": f"TableQuery_{config.table_name}",
                    "title": config.display_name,
                    "type": "menu",
                    "parent": parent_menu,
                    "component": "/table-query/index",
                    "order": idx,
                    "query": {"configId": str(config.id)},
                    "keepAlive": True,
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f"菜单初始化完成：共 {configs.count()} 个配置，新增 {created_count} 个菜单"
            )
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
- 删除 `core/table_query/` 模块
- 回滚数据库迁移：`python manage.py migrate table_query zero`
- 删除前端页面：`views/table-query/`
- 清理菜单配置

## 配置示例

### 字段类型说明

| 类型 | 说明 | 前端组件 |
|------|------|----------|
| string | 字符串 | el-input |
| integer | 整数 | el-input-number |
| decimal | 小数 | el-input-number |
| date | 日期 | el-date-picker |
| datetime | 日期时间 | el-date-picker |
| boolean | 布尔值 | el-switch |

### 示例：工作流请求表

```json
{
  "table_name": "WORKFLOW_REQUESTBASE",
  "display_name": "工作流请求",
  "description": "工作流系统请求基础数据表",
  "fields": [
    { "name": "REQUESTID", "display_name": "请求ID", "type": "integer", "searchable": true, "sortable": true, "visible": true, "width": 100 },
    { "name": "REQUESTNAME", "display_name": "请求名称", "type": "string", "searchable": true, "sortable": true, "visible": true, "width": 200 },
    { "name": "CREATER", "display_name": "创建人", "type": "string", "searchable": true, "visible": true, "width": 100 },
    { "name": "CREATEDATE", "display_name": "创建日期", "type": "datetime", "searchable": true, "sortable": true, "visible": true, "width": 150 },
    { "name": "STATUS", "display_name": "状态", "type": "string", "searchable": true, "sortable": true, "visible": true, "width": 100 }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "REQUESTID DESC",
  "allowed_operations": ["query", "export"]
}
```

### 示例：部门表

```json
{
  "table_name": "BS_DEPARTMENT",
  "display_name": "部门信息",
  "description": "医院部门基础信息表",
  "fields": [
    { "name": "ID", "display_name": "部门ID", "type": "integer", "searchable": true, "sortable": true, "visible": true },
    { "name": "DEPARTMENTNAME", "display_name": "部门名称", "type": "string", "searchable": true, "sortable": true, "visible": true },
    { "name": "DEPARTMENTMARK", "display_name": "部门编码", "type": "string", "searchable": true, "visible": true },
    { "name": "CANCELED", "display_name": "是否停用", "type": "boolean", "searchable": true, "sortable": true, "visible": true }
  ],
  "default_page_size": 50,
  "max_page_size": 200,
  "default_order_by": "ID ASC",
  "allowed_operations": ["query", "export"]
}
```

### 示例：物资表

```json
{
  "table_name": "WM_MATERIAL",
  "display_name": "物资信息",
  "description": "仓库物资管理表",
  "fields": [
    { "name": "ID", "display_name": "物资ID", "type": "integer", "searchable": true, "sortable": true, "visible": true },
    { "name": "MATERIAL_NAME", "display_name": "物资名称", "type": "string", "searchable": true, "sortable": true, "visible": true },
    { "name": "SPECIFICATION", "display_name": "规格", "type": "string", "searchable": true, "visible": true },
    { "name": "UNIT", "display_name": "单位", "type": "string", "visible": true },
    { "name": "PRICE", "display_name": "价格", "type": "decimal", "sortable": true, "visible": true },
    { "name": "CATEGORY", "display_name": "分类", "type": "string", "searchable": true, "sortable": true, "visible": true }
  ],
  "default_page_size": 30,
  "max_page_size": 100,
  "default_order_by": "ID DESC",
  "allowed_operations": ["query", "export"]
}
```

## 实施过程中的额外修改

### 1. MySQL 保留关键字处理

**问题**：部分表的字段名使用了 MySQL 保留关键字（如 `partition`、`explain`），导致 SQL 语法错误。

**解决方案**：添加 `quote_identifier()` 函数，对所有表名和字段名使用反引号转义：

```python
def quote_identifier(name: str) -> str:
    """使用反引号转义标识符（表名/字段名）"""
    name = name.replace('`', '')
    return f'`{name}`'
```

修改位置：`table_query_api.py` 中的所有 SQL 构建函数。

### 2. VxeTable 组件适配

**问题**：直接导入 `vxe-table` 的组件导致样式文件找不到的错误。

**解决方案**：使用项目已有的 `useVbenVxeGrid` 适配器，通过 `gridApi.setGridOptions({ columns })` 动态更新列配置。

### 3. 配置 JSON 键名兼容性

**问题**：配置 JSON 中的键名存在 `camelCase` 和 `snake_case` 不一致的问题。

**解决方案**：API 层同时支持两种格式：

```python
# 同时支持 camelCase 和 snake_case
order_by = config.config_json.get('defaultOrderBy') or config.config_json.get('default_order_by')
```

### 4. 批量配置创建工具

新增 `batch_create_table_configs` 管理命令，支持：
- `--list`：列出所有可配置的表
- `--prefix PREFIX`：按表名前缀过滤
- `--all`：处理所有表
- `--update`：更新现有配置

**实施结果**：为数据库中的 952 个表全部创建了查询配置。

## 待决问题

- [x] ~~是否需要支持数据导出审计？~~ 已实现 `TableQueryLog` 模型记录导出操作
- [ ] 是否需要支持查询结果缓存？缓存策略如何设计？
- [ ] 是否需要支持自定义查询（用户可以编写 SQL）？如何确保安全？
- [ ] 大表查询是否需要异步处理（Celery 任务）？
- [ ] 是否需要支持数据字段的国际化？
- [ ] 配置是否需要支持导入/导出功能（备份和迁移）？
