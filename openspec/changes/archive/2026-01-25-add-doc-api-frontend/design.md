# 设计文档

## 上下文

后台已完成 doc_api 模块，提供以下 API：

```
GET  /api/core/doc-api/endpoints              - 获取接口列表（分页）
POST /api/core/doc-api/endpoints/search       - 搜索接口
GET  /api/core/doc-api/endpoints/{operation_id} - 获取接口详情
GET  /api/core/doc-api/summary                - 获取文档摘要
```

前端需要提供一个直观的操作界面，与现有的 `join-query`、`table-query` 等页面保持一致的 UI 风格。

## 目标 / 非目标

**目标：**
- 提供用户友好的 HIS API 文档浏览界面
- 支持多条件搜索和分页浏览
- 详情展示请求/响应结构和示例数据
- 与项目现有 UI 风格保持一致

**非目标：**
- 不实现 API 在线调试/测试功能
- 不实现文档编辑功能
- 不实现 OpenAPI 规范验证功能

## 决策

### 1. 页面布局

采用与 `join-query` 类似的卡片式布局：
- 顶部：文档摘要卡片（标题、版本、接口统计、HTTP方法分布）
- 中部：搜索表单（行内布局，支持名称、路径、方法、关键词搜索）
- 底部：接口列表表格（VxeGrid，支持分页）

**理由**：保持项目 UI 一致性，用户熟悉的操作体验

### 2. 详情展示方式

采用抽屉（Drawer）组件从右侧滑出展示详情：
- 优点：不离开列表页面，方便快速切换查看不同接口
- 宽度：50% 或固定 800px

**考虑的替代方案**：
- 弹窗（Dialog）：信息密度高时可能不够展示
- 跳转详情页：用户体验不够流畅
- 行内展开：表格行数据量大时不适合

### 3. HTTP 方法颜色标识

| 方法 | 颜色 |
|------|------|
| GET | 绿色（success） |
| POST | 蓝色（primary） |
| PUT | 橙色（warning） |
| DELETE | 红色（danger） |
| PATCH | 紫色 |

**理由**：业界通用的颜色约定，与 Swagger UI 一致

### 4. JSON 数据展示

使用 `<pre>` + 语法高亮或 JSON 格式化组件展示：
- request_example
- response_example
- parameters
- request_body
- responses

**理由**：结构化数据需要良好的可读性

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|----------|
| 接口详情数据量大，渲染慢 | 使用虚拟滚动或折叠展示 |
| 搜索条件多，表单过长 | 采用行内紧凑布局，可考虑高级搜索折叠 |
| 暗色模式 JSON 显示 | 确保语法高亮支持暗色主题 |

## 文件结构

```
web/apps/web-ele/src/
├── api/core/
│   └── doc-api.ts              # API 调用
└── views/doc-api/
    ├── index.vue               # 主页面
    └── components/
        └── EndpointDetail.vue  # 详情抽屉组件
```

## 待决问题

- 是否需要缓存接口列表数据？（暂不实现，按需考虑）
- 是否需要接口收藏/标记功能？（暂不实现，作为后续增强）
