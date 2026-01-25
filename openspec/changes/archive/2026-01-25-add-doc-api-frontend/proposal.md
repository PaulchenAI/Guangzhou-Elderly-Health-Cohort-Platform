# 变更：添加文档 API 前端操作界面

## 为什么

后台已完成文档 API 接口（`backend-django/core/doc_api`），提供了 HIS 接口文档的查询、搜索、详情查看等功能。现在需要开发配套的前端操作界面，让用户能够直观地浏览和查询 HIS 系统的 API 文档信息。

## 变更内容

- 新增前端 API 调用模块 `web/apps/web-ele/src/api/core/doc-api.ts`
- 新增文档 API 浏览页面 `web/apps/web-ele/src/views/doc-api/`
  - 接口列表展示（分页、表格）
  - 多条件搜索功能（按名称、路径、方法、关键词搜索）
  - 接口详情抽屉/弹窗（展示完整的请求参数、响应定义、示例数据）
  - 文档摘要信息展示（标题、版本、接口统计）
- 配置路由和菜单

## 影响

- 受影响规范：`doc-api`（新增前端相关需求）
- 受影响代码：
  - `web/apps/web-ele/src/api/core/` - 新增 API 调用
  - `web/apps/web-ele/src/views/` - 新增视图页面
  - `web/apps/web-ele/src/router/` - 路由配置
  - 菜单配置（后端或前端配置）
