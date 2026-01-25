# 任务清单

## 1. 前端 API 层

- [x] 1.1 创建 `web/apps/web-ele/src/api/core/doc-api.ts`
  - 定义 TypeScript 类型接口（DocEndpoint, DocEndpointDetail, DocSummary 等）
  - 实现 `getDocEndpointsApi` - 获取接口列表（分页）
  - 实现 `searchDocEndpointsApi` - 搜索接口
  - 实现 `getDocEndpointDetailApi` - 获取接口详情
  - 实现 `getDocSummaryApi` - 获取文档摘要

## 2. 前端视图组件

- [x] 2.1 创建 `web/apps/web-ele/src/views/doc-api/index.vue`
  - 主页面布局：顶部摘要卡片 + 搜索表单 + 数据表格
  - 文档摘要展示（标题、版本、接口数量、各方法统计）
  - 搜索表单：名称、路径、方法（下拉）、关键词
  - 接口列表表格（VxeGrid）：operation_id、名称、方法、路径、摘要
  - 分页功能

- [x] 2.2 创建 `web/apps/web-ele/src/views/doc-api/components/EndpointDetail.vue`
  - 接口详情抽屉组件
  - 基本信息区：operation_id、名称、方法（带颜色标签）、路径
  - 请求参数展示：parameters 列表、requestBody 结构
  - 响应定义展示：responses 状态码及结构
  - 示例数据展示：request_example、response_example（JSON 格式化）
  - 额外信息：request_fields、response_fields、location

## 3. 路由与菜单配置

- [x] 3.1 添加前端路由配置
  - 路由路径：`/doc-api`
  - 组件：`doc-api/index.vue`
  - 菜单名称：HIS 接口文档

- [x] 3.2 配置菜单项
  - 创建管理命令：`init_doc_api_menus.py`
  - 图标：`ant-design:api-outlined`
  - 路径：`/doc-api`

## 4. 验证与优化

- [x] 4.1 功能验证
  - 接口列表分页（VxeGrid proxyConfig）
  - 搜索功能（多条件组合搜索）
  - 详情展示（抽屉组件）
  - 加载状态和错误处理（loading、error、empty 状态）

- [x] 4.2 UI/UX 优化
  - 响应式布局适配（flex 布局）
  - 暗色模式适配（dark: 类名）
  - 加载态和空状态处理（ElSkeleton、ElEmpty）
