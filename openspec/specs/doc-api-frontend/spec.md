# doc-api-frontend Specification

## Purpose
TBD - created by archiving change add-doc-api-frontend. Update Purpose after archive.
## 需求
### 需求：文档 API 浏览页面

系统必须提供前端页面，允许用户浏览和查询 HIS API 文档信息。

#### 场景：访问文档 API 页面

- **当** 用户访问 `/doc-api` 路由
- **那么** 系统必须展示文档 API 浏览页面
- **并且** 页面必须包含：
  - 文档摘要信息卡片
  - 搜索表单
  - 接口列表表格

#### 场景：展示文档摘要信息

- **当** 页面加载完成
- **那么** 系统必须调用 `GET /api/core/doc-api/summary` 获取摘要
- **并且** 必须展示以下信息：
  - 文档标题
  - 文档版本
  - 接口总数
  - 各 HTTP 方法的接口数量统计

#### 场景：展示接口列表

- **当** 页面加载完成
- **那么** 系统必须调用 `GET /api/core/doc-api/endpoints` 获取接口列表
- **并且** 表格必须展示以下列：
  - operation_id（操作 ID）
  - name（接口名称）
  - method（HTTP 方法，带颜色标识）
  - path（接口路径）
  - summary（接口摘要）
- **并且** 必须支持分页（默认每页 20 条）

---

### 需求：接口搜索功能

系统必须提供接口搜索功能，支持多条件组合搜索。

#### 场景：按名称搜索

- **当** 用户在搜索表单中输入接口名称
- **并且** 点击搜索按钮
- **那么** 系统必须调用 `POST /api/core/doc-api/endpoints/search`
- **并且** 必须展示名称匹配的接口列表

#### 场景：按 HTTP 方法筛选

- **当** 用户在搜索表单中选择 HTTP 方法（GET/POST/PUT/DELETE）
- **并且** 点击搜索按钮
- **那么** 系统必须返回指定方法的接口列表

#### 场景：按关键词搜索

- **当** 用户在搜索表单中输入关键词
- **并且** 点击搜索按钮
- **那么** 系统必须在名称、路径、摘要中搜索匹配的接口

#### 场景：重置搜索条件

- **当** 用户点击重置按钮
- **那么** 系统必须清空所有搜索条件
- **并且** 必须重新加载完整的接口列表

---

### 需求：接口详情查看

系统必须提供接口详情查看功能，展示接口的完整定义信息。

#### 场景：打开接口详情

- **当** 用户点击接口列表中的某一行
- **那么** 系统必须调用 `GET /api/core/doc-api/endpoints/{operation_id}`
- **并且** 必须在抽屉组件中展示接口详情

#### 场景：展示接口详情内容

- **当** 接口详情加载完成
- **那么** 详情抽屉必须展示以下信息：
  - 基本信息：operation_id、name、method、path、summary、description
  - 请求参数：parameters 列表
  - 请求体：request_body 结构（如有）
  - 响应定义：responses 各状态码的结构
  - 请求示例：request_example（JSON 格式化展示）
  - 响应示例：response_example（JSON 格式化展示）

#### 场景：关闭接口详情

- **当** 用户点击抽屉关闭按钮或遮罩层
- **那么** 系统必须关闭详情抽屉
- **并且** 用户必须返回接口列表视图

---

### 需求：HTTP 方法颜色标识

系统必须为不同的 HTTP 方法提供不同的颜色标识，提高可读性。

#### 场景：显示 HTTP 方法标签

- **当** 展示接口列表或详情中的 HTTP 方法
- **那么** 系统必须使用以下颜色约定：
  - GET：绿色（success）
  - POST：蓝色（primary）
  - PUT：橙色（warning）
  - DELETE：红色（danger）
  - PATCH：紫色
  - 其他：灰色（default）

---

### 需求：加载状态和错误处理

系统必须正确处理加载状态和错误情况，提供良好的用户体验。

#### 场景：数据加载中

- **当** 系统正在请求接口数据
- **那么** 必须展示加载动画（loading）
- **并且** 禁止用户重复提交请求

#### 场景：数据加载失败

- **当** 接口请求失败
- **那么** 系统必须展示错误提示消息
- **并且** 必须提供重试按钮或刷新选项

#### 场景：无数据状态

- **当** 接口列表为空或搜索无结果
- **那么** 系统必须展示空状态提示（Empty）
- **并且** 提示用户调整搜索条件或刷新

---

### 需求：前端 API 调用模块

系统必须提供 TypeScript API 调用模块，封装后端接口调用。

#### 场景：API 模块结构

- **当** 创建 API 调用模块
- **那么** 必须位于 `web/apps/web-ele/src/api/core/doc-api.ts`
- **并且** 必须导出以下函数：
  - `getDocEndpointsApi(page, pageSize)` - 获取接口列表
  - `searchDocEndpointsApi(params)` - 搜索接口
  - `getDocEndpointDetailApi(operationId)` - 获取接口详情
  - `getDocSummaryApi()` - 获取文档摘要

#### 场景：TypeScript 类型定义

- **当** 定义 API 类型
- **那么** 必须包含以下接口定义：
  - `DocEndpoint` - 接口基本信息
  - `DocEndpointDetail` - 接口详情信息
  - `DocEndpointSearchParams` - 搜索参数
  - `DocEndpointListResponse` - 列表响应
  - `DocSummary` - 文档摘要信息

