# 任务清单：联合查询前端界面

## 1. 基础设施搭建

### 1.1 创建页面结构
- [x] 创建 `views/join-query/` 目录结构
- [x] 创建主页面 `index.vue` 骨架
- [x] 创建 `data.ts` 工具函数文件
- **验证**：页面可正常访问，显示基本布局

### 1.2 添加 API 函数
- [x] 在 `api/core/table-query.ts` 添加联合查询相关 API
- [x] 添加类型定义（JoinPreviewResponse、JoinQueryParams 等）
- **验证**：API 函数可正确调用后端接口

### 1.3 配置路由
- [x] 添加 `/join-query` 路由配置（通过后端菜单系统）
- [x] 在导航菜单中添加入口（更新 `init_table_query_menus.py`）
- **验证**：通过菜单可导航到联合查询页面

## 2. 核心组件开发

### 2.1 主表选择器组件
- [x] 创建 `TableSelector.vue` 组件
- [x] 复用现有表配置列表逻辑
- [x] 支持搜索过滤
- **验证**：可显示表列表，支持选择和搜索

### 2.2 关联关系树组件
- [x] 创建 `RelationTree.vue` 组件
- [x] 实现树形数据转换（API 响应 → Tree 数据）
- [x] 实现关联深度设置（滑块 1-5）
- [x] 实现多选功能（勾选关联表）
- [x] 显示关联信息（外键 → 目标字段）
- **验证**：选择主表后正确显示关联关系树，可勾选关联表

### 2.3 列选择器组件
- [x] 创建 `ColumnSelector.vue` 组件（Drawer 抽屉）
- [x] 按表分组展示列
- [x] 支持单列选择/取消
- [x] 支持按表全选/取消
- [x] 记住用户偏好（localStorage）
- **验证**：可打开列选择器，选择/取消列后表格列正确更新

### 2.4 数据结果面板
- [x] 在 `index.vue` 集成数据结果展示区域
- [x] 集成 VxeGrid 表格
- [x] 实现动态列生成（根据 fieldInfo）
- [x] 实现分页功能
- [x] 实现过滤功能
- [x] 实现排序功能
- **验证**：执行查询后正确展示数据，分页/过滤/排序正常工作

## 3. 功能集成

### 3.1 主页面集成
- [x] 在 `index.vue` 集成所有组件
- [x] 实现组件间数据流
- [x] 实现加载状态管理
- **验证**：完整流程可正常工作

### 3.2 查询执行功能
- [x] 实现"执行查询"按钮
- [x] 构建查询参数（主表、关联表、深度、过滤、分页）
- [x] 处理查询结果
- [x] 错误处理和提示
- **验证**：点击查询按钮后正确获取并展示数据

### 3.3 导出功能
- [x] 实现"导出"下拉菜单（Excel/CSV）
- [x] 调用 join-export API
- [x] 处理文件下载
- **验证**：可成功导出联合查询结果

## 4. 配置保存功能

### 4.1 配置管理组件
- [x] 创建 `ConfigManager.vue` 组件
- [x] 实现保存配置功能（名称输入对话框）
- [x] 实现加载配置功能（下拉选择）
- [x] 实现删除配置功能
- [x] localStorage 存储实现
- **验证**：可保存、加载、删除联合查询配置

### 4.2 配置持久化
- [x] 实现配置序列化/反序列化（在 `data.ts`）
- [x] 处理配置版本兼容
- **验证**：刷新页面后配置仍然存在

## 5. 用户体验优化

### 5.1 加载状态
- [x] 关联关系加载骨架屏
- [x] 查询执行加载遮罩
- [x] 导出进度提示
- **验证**：各操作有明确的加载反馈

### 5.2 错误处理
- [x] API 错误提示
- [x] 空状态展示（无数据、无关联）
- [x] 关联深度过深警告（通过 Tooltip 提示）
- **验证**：错误情况有友好提示

### 5.3 帮助提示
- [x] 关联关系说明 Tooltip
- [x] 列选择器使用提示
- [ ] 首次使用引导（可选，暂不实现）
- **验证**：用户可理解各功能用途

## 6. 测试

### 6.1 单元测试
- [x] 树形数据转换函数测试（可选）- 手动验证通过
- [x] 列配置构建函数测试（可选）- 手动验证通过
- [x] 配置序列化测试（可选）- 手动验证通过

### 6.2 集成测试
- [x] 完整查询流程测试 - 手动验证通过
- [x] 配置保存/加载测试 - 手动验证通过

## 7. 实现过程中的额外修复

### 7.1 图标兼容性修复
- [x] `Delete` → `Trash2`（ConfigManager.vue）
- [x] `FolderOpened` → `FolderOpen`（ConfigManager.vue）
- [x] `QuestionFilled` → `CircleHelp`（RelationTree.vue）
- [x] `Setting` → `Settings`（index.vue）
- [x] `Plus` → `ElIconPlus`（ConfigManager.vue，使用 element-plus 图标）

### 7.2 渲染逻辑修复
- [x] 修复 Grid 组件渲染条件的循环依赖问题（`v-if="queryResult"` → `v-if="primaryTable"`）

### 7.3 中文显示支持
- [x] 后端 FieldInfo schema 添加 `field_comment` 字段
- [x] 后端 API 传递 `field_comment` 到响应
- [x] 后端 `_get_table_fields` 查询 `COLUMN_COMMENT`
- [x] 前端表头显示中文/英文双语格式
- [x] 前端搜索表单显示中文字段名
- [x] 关联关系树显示表的中文名称

### 7.4 健壮性改进
- [x] 后端添加 `check_table_exists` 函数
- [x] 关联解析时跳过不存在的表
- [x] SQL 构建时跳过不存在的表

## 实现文件清单

| 文件路径 | 说明 |
|---------|------|
| `web/apps/web-ele/src/views/join-query/index.vue` | 主页面 |
| `web/apps/web-ele/src/views/join-query/data.ts` | 工具函数 |
| `web/apps/web-ele/src/views/join-query/components/TableSelector.vue` | 主表选择器 |
| `web/apps/web-ele/src/views/join-query/components/RelationTree.vue` | 关联关系树 |
| `web/apps/web-ele/src/views/join-query/components/ColumnSelector.vue` | 列选择器 |
| `web/apps/web-ele/src/views/join-query/components/ConfigManager.vue` | 配置管理 |
| `web/apps/web-ele/src/api/core/table-query.ts` | API 函数（扩展） |
| `backend-django/core/management/commands/init_table_query_menus.py` | 菜单初始化（扩展） |

## 依赖关系

```
1.1 ──┬── 1.2 ──┬── 1.3
      │         │
      ▼         ▼
     2.1       2.2
      │         │
      └────┬────┘
           │
           ▼
     2.3 ─── 2.4
           │
           ▼
          3.1
           │
      ┌────┼────┐
      ▼    ▼    ▼
     3.2  3.3  4.1
      │         │
      └────┬────┘
           │
           ▼
          5.x
           │
           ▼
          6.x
```

## 预估工时

| 阶段 | 任务 | 工时（小时） | 状态 |
|------|------|-------------|------|
| 基础设施 | 1.1 - 1.3 | 2 | ✅ 完成 |
| 核心组件 | 2.1 - 2.4 | 8 | ✅ 完成 |
| 功能集成 | 3.1 - 3.3 | 4 | ✅ 完成 |
| 配置保存 | 4.1 - 4.2 | 3 | ✅ 完成 |
| 体验优化 | 5.1 - 5.3 | 3 | ✅ 完成 |
| 测试 | 6.1 - 6.2 | 2 | ✅ 手动验证通过 |
| 额外修复 | 7.1 - 7.4 | 3 | ✅ 完成 |
| **总计** | | **25** | ✅ 全部完成 |
