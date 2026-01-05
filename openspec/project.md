# 项目上下文

## 目的

zq-platform（芷青开发平台）是一个功能完善的企业级后台管理系统解决方案，采用前后端分离架构。项目旨在提供一套开箱即用的后台管理系统模板，帮助开发者快速构建企业级应用。

### 核心功能
- **RBAC 权限系统**：用户、角色、权限、部门、岗位多维度权限控制
- **JWT 认证机制**：支持 Access Token 和 Refresh Token 双令牌认证
- **系统监控**：服务器、Redis、数据库实时监控
- **文件管理**：文件上传、下载、预览功能
- **操作日志**：登录日志和操作审计
- **数据字典**：灵活的字典管理
- **任务调度**：基于 APScheduler 的定时任务管理
- **WebSocket**：实时通信能力

## 技术栈

### 后端技术
- **核心框架**: Django 5.2.7
- **API 框架**: Django Ninja 1.4.5（高性能 RESTful API）
- **认证**: PyJWT 2.8.0
- **异步任务**: Celery 5.4.0 + Django Celery Beat
- **任务调度**: APScheduler 3.10.4
- **缓存**: Redis + django-redis 6.0.0
- **WebSocket**: Django Channels 4.2
- **数据库**: MySQL / PostgreSQL / SQL Server / SQLite（多数据库支持）
- **服务器**: Uvicorn 0.38.0 / Gunicorn 23.0.0

### 前端技术
- **核心框架**: Vue 3.x
- **构建工具**: Vite 5.x
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP 客户端**: Axios
- **样式**: Tailwind CSS
- **代码规范**: ESLint, Prettier, Stylelint
- **包管理**: pnpm 10.14.0
- **Monorepo**: Turbo

## 项目约定

### 代码风格

#### 后端（Python/Django）
- 遵循 PEP 8 代码规范
- 文件头使用 UTF-8 编码声明：`# -*- coding: utf-8 -*-`
- 使用中文编写注释和文档字符串
- 模块文件使用 `模块名_功能.py` 命名，如 `user_api.py`、`user_model.py`
- 类名使用 PascalCase，函数和变量使用 snake_case
- API 接口使用 RESTful 风格，统一返回格式

#### 前端（TypeScript/Vue）
- 使用 ESLint + Prettier 进行代码格式化
- 使用 TypeScript 进行类型安全开发
- 组件使用 `<script setup>` 语法
- 优先使用 Tailwind CSS 进行样式开发
- 图标统一从 `@vben/icons` 导入

### 架构模式

#### 后端模块化架构
每个业务模块（如 user、role、permission）包含以下文件：
```
core/
└── [module]/
    ├── __init__.py
    ├── [module]_api.py      # API 接口定义（Django Ninja Router）
    ├── [module]_model.py    # 数据模型定义（Django Model）
    └── [module]_schema.py   # 数据校验和序列化（Pydantic Schema）
```

公共功能位于 `common/` 目录：
- `fu_crud.py`: 通用 CRUD 操作
- `fu_auth.py`: 认证授权
- `fu_cache.py`: 缓存管理
- `fu_pagination.py`: 分页处理
- `fu_schema.py`: 公共数据结构

#### 前端 Monorepo 架构
```
web/
├── apps/
│   └── web-ele/           # Element Plus 版本主应用
├── packages/              # 共享包
│   ├── @core/            # 核心功能包
│   ├── effects/          # 副作用处理
│   ├── hooks/            # 组合式函数
│   ├── icons/            # 图标库
│   ├── locales/          # 国际化
│   ├── stores/           # 状态管理
│   └── utils/            # 工具函数
└── internal/             # 内部构建工具
```

### 测试策略

#### 前端测试
- **单元测试**: Vitest + Vue Test Utils + happy-dom
- **E2E 测试**: Playwright
- 测试文件与源文件同目录，命名为 `*.spec.ts` 或 `*.test.ts`
- 运行命令：`pnpm test:unit`（单元测试）、`pnpm test:e2e`（E2E 测试）

#### 后端测试
- 使用 Django TestCase 进行单元测试
- API 测试使用 Django Ninja 的测试客户端
- 测试数据使用 fixtures：`db_init.json`

### Git 工作流

#### 分支策略
- `main`: 主分支，保持稳定可发布状态
- `feature/*`: 功能分支，从 main 创建
- `fix/*`: 修复分支
- `release/*`: 发布分支

#### 提交约定
- 使用 Conventional Commits 规范
- 提交信息格式：`<type>(<scope>): <description>`
- 类型包括：`feat`、`fix`、`docs`、`style`、`refactor`、`test`、`chore`
- 使用 `pnpm commit`（czg）进行交互式提交

#### Git Hooks
- 使用 lefthook 管理 Git hooks
- commitlint 校验提交信息格式

## 领域上下文

### 核心领域模型
- **User（用户）**: 系统用户，包含基本信息、认证信息、状态
- **Role（角色）**: 权限角色，关联权限集合
- **Permission（权限）**: 接口权限、按钮权限
- **Dept（部门）**: 组织架构，树形结构
- **Post（岗位）**: 岗位信息
- **Menu（菜单）**: 系统菜单，支持动态路由

### 支撑领域
- **Dict（字典）**: 系统字典，支持多级分类
- **LoginLog（登录日志）**: 用户登录记录
- **FileManager（文件管理）**: 文件上传、存储、管理

### 技术领域
- **ServerMonitor（服务器监控）**: CPU、内存、磁盘、网络监控
- **RedisMonitor（Redis 监控）**: Redis 性能指标
- **DatabaseMonitor（数据库监控）**: 数据库连接和性能
- **Scheduler（任务调度）**: 定时任务管理

## 重要约束

### 环境要求
- **Python**: >= 3.10
- **Node.js**: >= 20.10.0
- **pnpm**: >= 9.12.0
- **数据库**: MySQL >= 5.7 / PostgreSQL >= 12 / SQL Server / SQLite
- **Redis**: >= 5.0

### 安全约束
- 生产环境必须配置 `DJANGO_SECRET_KEY`
- 生产环境必须配置 `JWT_ACCESS_SECRET_KEY` 和 `JWT_REFRESH_SECRET_KEY`
- 生产环境启用 HTTPS、HSTS、安全 Cookie
- 接口权限验证通过 JWT + RBAC 实现

### 性能约束
- 使用 Redis 缓存热点数据
- 数据库查询使用 `select_related` 和 `prefetch_related` 优化
- 前端使用 Turbo 进行构建优化

## 外部依赖

### 第三方服务
- **阿里云短信服务**: 短信验证码发送
- **GeoIP2**: IP 地理位置解析
- **Azure AD**: OAuth 认证（可选）

### 存储服务（可配置）
- **本地存储**: 默认，文件存储到 `media/` 目录
- **阿里云 OSS**: 对象存储
- **MinIO**: 私有化对象存储
- **Azure Blob**: Azure 存储服务

### API 文档
- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
