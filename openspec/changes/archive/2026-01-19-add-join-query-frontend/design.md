# 设计文档：联合查询前端界面

## 上下文

本设计基于已实现的联合查询后端 API，为用户提供可视化的多表联合查询界面。

### 相关后端 API

| API | 功能 |
|-----|------|
| `GET /api/core/table-query/join-preview/{table_name}` | 获取表的关联关系预览 |
| `POST /api/core/table-query/join-query` | 执行联合查询 |
| `POST /api/core/table-query/join-export` | 导出联合查询结果 |

### 现有前端结构

```
web/apps/web-ele/src/
├── views/table-query/
│   ├── index.vue          # 单表查询页面
│   └── data.ts            # 表格列构建工具
├── api/core/
│   └── table-query.ts     # 表查询 API
```

## 设计目标

1. **直观易用**：用户无需了解 SQL 即可执行多表联合查询
2. **性能优先**：处理大量字段时保持流畅
3. **复用现有组件**：最大化复用现有的表选择器、表格组件
4. **可扩展**：为未来功能（如查询模板、定时导出）预留空间

## 设计决策

### 决策 1：页面结构

**方案**：创建独立的联合查询页面 `join-query/index.vue`，通过导航菜单与单表查询并列。

**理由**：
- 联合查询功能相对独立，有自己的状态管理
- 避免在单表查询页面中增加过多复杂度
- 便于独立维护和测试

**结构**：
```
web/apps/web-ele/src/views/
├── table-query/
│   └── index.vue          # 单表查询
└── join-query/
    ├── index.vue          # 联合查询主页面
    ├── components/
    │   ├── TableSelector.vue      # 主表选择器
    │   ├── RelationTree.vue       # 关联关系树
    │   ├── ColumnSelector.vue     # 列选择器
    │   └── ConfigManager.vue      # 配置保存管理
    └── data.ts            # 工具函数
```

### 决策 2：关联关系展示

**方案**：使用 Element Plus 的 Tree 组件展示关联关系，支持多选。

**数据结构**：
```typescript
interface RelationTreeNode {
  id: string;           // 唯一标识：table_name
  label: string;        // 显示名称
  tableName: string;    // 表名
  depth: number;        // 关联深度
  joinInfo: {
    sourceTable: string;
    sourceColumns: string[];
    targetColumns: string[];
  };
  children?: RelationTreeNode[];
}
```

**交互**：
- 默认展开第一级关联
- 勾选节点即选择关联该表
- 显示关联路径：`主表.外键字段 → 关联表.目标字段`

### 决策 3：列管理方案

**方案**：使用抽屉（Drawer）组件展示列选择器，按表分组。

**功能**：
- 按表名分组展示所有列
- 支持全选/取消某个表的所有列
- 支持单独选择/取消特定列
- 记住用户的列选择偏好（存储在 localStorage）

**示例**：
```
┌─ 列选择器 ─────────────────────┐
│ ☑ gzlry_BS_STAFF (主表)       │
│   ☑ mainid                     │
│   ☑ NAME                       │
│   ☐ CREATETIME                 │
│                                │
│ ☐ gzlry_BS_BUILDINGS          │
│   ☐ buildingcode              │
│   ☐ buildingname              │
└────────────────────────────────┘
```

### 决策 4：配置保存方案

**方案**：前端使用 localStorage 存储，后续可扩展为后端存储。

**配置结构**：
```typescript
interface JoinQueryConfig {
  id: string;
  name: string;                    // 配置名称
  primaryTable: string;            // 主表名
  includeTables: string[];         // 选中的关联表
  maxDepth: number;                // 关联深度
  visibleColumns?: string[];       // 可见列（可选）
  createdAt: string;
  updatedAt: string;
}
```

**存储 Key**：`join_query_configs`

### 决策 5：性能优化

**列虚拟化**：
- 当列数超过 20 时，使用 VxeTable 的列虚拟滚动
- 默认只显示主表和第一级关联表的列

**数据加载**：
- 使用分页，默认每页 20 条
- 查询时显示加载状态
- 支持取消正在进行的查询

**防抖处理**：
- 搜索输入使用 300ms 防抖
- 关联表选择变化后延迟 500ms 自动刷新（或手动触发）

## 数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                        用户操作流程                               │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. 选择主表    │───▶│  2. 加载关联   │───▶│  3. 选择关联表  │
│  (表列表)       │    │  (join-preview) │    │  (树形选择)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  6. 导出数据    │◀───│  5. 展示结果   │◀───│  4. 执行查询    │
│  (join-export)  │    │  (VxeGrid)      │    │  (join-query)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## API 设计（前端）

### 新增 API 函数

```typescript
// web/apps/web-ele/src/api/core/table-query.ts

// 获取关联关系预览
export function getJoinPreviewApi(tableName: string, maxDepth?: number);

// 执行联合查询
export function executeJoinQueryApi(params: JoinQueryParams);

// 导出联合查询结果
export function exportJoinDataApi(params: JoinExportParams);
```

### 类型定义

```typescript
// 关联表信息
interface JoinTableInfo {
  tableName: string;
  joinDepth: number;
  sourceTable: string;
  sourceColumns: string[];
  targetColumns: string[];
}

// 关联关系预览响应
interface JoinPreviewResponse {
  primaryTable: string;
  joinTree: JoinTableInfo[];
  totalRelatedTables: number;
  maxDepth: number;
  hasCycle: boolean;
  allFields: FieldInfo[];
}

// 联合查询参数
interface JoinQueryParams {
  primaryTable: string;
  maxDepth?: number;
  includeTables?: string[];
  excludeTables?: string[];
  page?: number;
  pageSize?: number;
  filters?: FilterCondition[];
  orderBy?: string;
}

// 联合查询结果
interface JoinQueryResult {
  items: Record<string, any>[];
  total: number;
  page: number;
  pageSize: number;
  joinInfo: JoinInfo;
  fieldInfo: FieldInfo[];
}
```

## 组件设计

### 主页面布局

```vue
<!-- join-query/index.vue -->
<template>
  <Page auto-content-height>
    <div class="flex h-full gap-4">
      <!-- 左侧：主表选择 -->
      <div class="w-60 flex-shrink-0">
        <TableSelector 
          v-model="primaryTable"
          @change="handlePrimaryTableChange"
        />
      </div>
      
      <!-- 中间：关联配置 -->
      <div class="w-72 flex-shrink-0">
        <RelationTree
          v-if="primaryTable"
          :relations="relations"
          v-model:selected="selectedTables"
          v-model:depth="maxDepth"
          :loading="loadingRelations"
        />
      </div>
      
      <!-- 右侧：数据展示 -->
      <div class="flex flex-1 flex-col overflow-hidden">
        <ResultPanel
          :loading="loadingData"
          :result="queryResult"
          :visible-columns="visibleColumns"
          @query="handleQuery"
          @export="handleExport"
          @column-change="handleColumnChange"
        />
      </div>
    </div>
  </Page>
</template>
```

### 关联关系树组件

```vue
<!-- components/RelationTree.vue -->
<template>
  <ElCard shadow="never" class="h-full">
    <template #header>
      <div class="flex items-center justify-between">
        <span>关联配置</span>
        <ElTooltip content="勾选要关联的表">
          <QuestionFilled class="text-gray-400" />
        </ElTooltip>
      </div>
    </template>
    
    <!-- 关联深度设置 -->
    <div class="mb-4">
      <span class="text-sm text-gray-500">关联深度：</span>
      <ElSlider v-model="depth" :min="1" :max="5" :step="1" />
    </div>
    
    <!-- 关联关系树 -->
    <ElTree
      :data="treeData"
      show-checkbox
      node-key="id"
      :default-expanded-keys="defaultExpanded"
      :props="treeProps"
      @check="handleCheck"
    >
      <template #default="{ node, data }">
        <div class="flex items-center gap-2">
          <span>{{ data.label }}</span>
          <ElTag v-if="data.depth" size="small" type="info">
            {{ data.depth }}级
          </ElTag>
        </div>
      </template>
    </ElTree>
  </ElCard>
</template>
```

## 路由配置

```typescript
// 新增路由
{
  path: '/join-query',
  name: 'JoinQuery',
  component: () => import('#/views/join-query/index.vue'),
  meta: {
    title: '联合查询',
    icon: 'mdi:table-multiple',
  },
}
```

## 测试策略

### 单元测试
- 关联关系树数据转换
- 列选择器状态管理
- 配置序列化/反序列化

### 集成测试
- 选择主表 → 加载关联 → 选择关联表 → 执行查询 完整流程
- 列显示/隐藏功能
- 配置保存/加载功能

### E2E 测试
- 完整的用户操作流程
- 导出功能验证

## 实现过程中的额外决策

### 决策 6：图标库兼容性

**问题**：`@vben/icons` 库导出的图标名称与 Element Plus 不一致，导致多个组件报错。

**解决方案**：
- 检查 `web/packages/icons/src/lucide.ts` 获取正确的图标名称
- 映射关系：
  - `Delete` → `Trash2`
  - `FolderOpened` → `FolderOpen`
  - `QuestionFilled` → `CircleHelp`
  - `Setting` → `Settings`
  - `Plus` → 使用 `element-plus/icons-vue` 的 `Plus as ElIconPlus`

### 决策 7：Grid 组件渲染时机

**问题**：Grid 组件使用 `v-if="queryResult"` 条件渲染，但 `gridApi.query()` 需要 Grid 已挂载才能执行，形成循环依赖。

**解决方案**：将条件改为 `v-if="primaryTable"`，确保选择主表后 Grid 即可渲染，避免循环依赖。

### 决策 8：字段中文名称显示

**问题**：用户要求表头和搜索表单显示字段的中文名称。

**解决方案**：
1. 后端修改：
   - `FieldInfo` schema 添加 `field_comment` 字段
   - `_get_table_fields` 从 `INFORMATION_SCHEMA.COLUMNS` 查询 `COLUMN_COMMENT`
   - API 响应传递 `field_comment`
2. 前端修改：
   - 表头显示格式：`中文名/英文名 (表名)`
   - 搜索表单优先显示 `field_comment`

### 决策 9：关联表中文名称显示

**问题**：关联关系树只显示表名（英文），用户要求显示中文名称。

**解决方案**：
- 创建 `tableDisplayNames` 计算属性，从 `configs`（表配置列表）构建 `Map<table_name, display_name>`
- 传递给 `RelationTree` 组件
- `buildRelationTree` 函数使用 `tableDisplayNames.get(table_name)` 获取显示名称

### 决策 10：不存在表的处理

**问题**：外键元数据可能引用数据库中不存在的表，导致 SQL 执行失败。

**解决方案**：
- 添加 `check_table_exists` 函数检查表是否存在
- 关联解析时跳过不存在的表
- SQL 构建时跳过不存在的表
- 前端不会看到这些表，避免用户困惑
