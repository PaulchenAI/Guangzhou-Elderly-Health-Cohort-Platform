# zq-platform (芷青开发平台)

[English](./README.md) | 简体中文

<div align="center">

一个现代化的企业级后台管理系统，基于 Django + Vue3 + Element Plus 构建

[![Django](https://img.shields.io/badge/Django-5.2.7-green.svg)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-latest-blue.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

</div>

## 演示链接
[https://django-ninja.zq-platform.cn](https://django-ninja.zq-platform.cn/)

## 📖 项目简介

zq-platform 是一个功能完善的企业级后台管理系统解决方案，采用前后端分离架构。后端使用 Django 5.2 + Django Ninja 构建高性能 RESTful API，前端基于 Vue 3 + Vben Admin + Element Plus 打造现代化的管理界面。

### ✨ 核心特性

- 🎯 **完整的 RBAC 权限系统** - 用户、角色、权限、部门、岗位多维度权限控制
- 🔐 **JWT 认证机制** - 安全的 Token 认证，支持 Access Token 和 Refresh Token
- 📊 **系统监控** - 服务器监控、Redis 监控、数据库监控，实时掌握系统状态
- 📁 **文件管理** - 完善的文件上传、下载、预览功能
- 📝 **操作日志** - 详细的登录日志和操作审计
- 🗂️ **数据字典** - 灵活的字典管理，支持多级分类
- ⏰ **任务调度** - 基于 APScheduler 的定时任务管理
- 🔌 **WebSocket 支持** - 实时通信能力
- 🌐 **多数据库支持** - MySQL、PostgreSQL、SQL Server、SQLite
- 🎨 **现代化 UI** - 响应式设计，支持暗黑模式
- 📦 **Monorepo 架构** - 基于 pnpm workspace 的前端工程化方案

### 🆕 扩展功能

- 📋 **数据库表查询** - 配置化驱动的动态表查询，无需编写代码
- 🔄 **SQL 导入** - Oracle 到 MySQL 的 SQL 转换和批量导入，支持状态追踪
- 📊 **问卷数据集成** - 外部问卷 API 对接，支持灵活的导出选项

## 🏗️ 技术栈

### 后端技术

- **核心框架**: Django 5.2.7
- **API 框架**: Django Ninja 1.4.5 (高性能 API 框架)
- **认证**: PyJWT 2.8.0
- **异步任务**: Celery 5.4.0 + Django Celery Beat
- **任务调度**: APScheduler 3.10.4
- **缓存**: Redis + django-redis 6.0.0
- **WebSocket**: Django Channels 4.2
- **数据库驱动**: psycopg2-binary, pymysql, pyodbc
- **服务器**: Uvicorn 0.38.0 / Gunicorn 23.0.0
- **其他**: openpyxl, geoip2, psutil, cryptography

### 前端技术

- **核心框架**: Vue 3.x
- **构建工具**: Vite 5.x
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP 客户端**: Axios
- **样式**: Tailwind CSS
- **工具库**: VueUse, dayjs, lodash-es
- **代码规范**: ESLint, Prettier, Stylelint
- **包管理**: pnpm 10.14.0
- **Monorepo**: Turbo

## 📁 项目结构

```
zq-platform/
├── backend-django/          # Django 后端
│   ├── application/         # 项目配置
│   ├── core/               # 核心业务模块
│   │   ├── auth/           # 认证授权
│   │   ├── user/           # 用户管理
│   │   ├── role/           # 角色管理
│   │   ├── permission/     # 权限管理
│   │   ├── dept/           # 部门管理
│   │   ├── post/           # 岗位管理
│   │   ├── menu/           # 菜单管理
│   │   ├── dict/           # 字典管理
│   │   ├── login_log/      # 登录日志
│   │   ├── file_manager/   # 文件管理
│   │   ├── server_monitor/ # 服务器监控
│   │   ├── redis_monitor/  # Redis 监控
│   │   ├── redis_manager/  # Redis 管理
│   │   ├── database_monitor/ # 数据库监控
│   │   ├── database_manager/ # 数据库管理
│   │   ├── table_query/    # 动态表查询
│   │   └── survey/         # 问卷数据管理
│   ├── scheduler/          # 任务调度模块
│   ├── common/             # 公共模块
│   │   ├── fu_crud.py      # 通用 CRUD 操作
│   │   ├── fu_auth.py      # 认证授权
│   │   ├── fu_cache.py     # 缓存管理
│   │   ├── fu_pagination.py # 分页处理
│   │   └── fu_schema.py    # 公共数据结构
│   ├── env/                # 环境配置
│   ├── requirements.txt    # Python 依赖
│   └── manage.py          # Django 管理脚本
│
├── web/                    # Vue 前端 (Monorepo)
│   ├── apps/
│   │   └── web-ele/        # Element Plus 版本主应用
│   │       ├── src/
│   │       │   ├── api/    # API 接口
│   │       │   ├── views/  # 页面组件
│   │       │   ├── router/ # 路由配置
│   │       │   └── store/  # 状态管理
│   │       └── package.json
│   ├── packages/           # 共享包
│   │   ├── @core/          # 核心包
│   │   ├── effects/        # 副作用包
│   │   ├── hooks/          # Hooks
│   │   ├── icons/          # 图标
│   │   ├── locales/        # 国际化
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   ├── internal/           # 内部工具
│   └── package.json        # 根配置
│
├── openspec/               # OpenSpec 规范驱动开发
│   ├── project.md          # 项目约定
│   ├── AGENTS.md           # AI 助手说明
│   ├── specs/              # 功能规范
│   │   ├── database-table-query/
│   │   └── sql-import/
│   └── changes/            # 变更提案
│       └── archive/        # 已完成的变更
│
└── docs/                   # 文档
    ├── frontend-development-guide.md
    └── backend-api-development-guide.md
```

## 🚀 快速开始

### 环境要求

- **后端**
  - Python >= 3.10
  - MySQL >= 5.7 / PostgreSQL >= 12 / SQL Server / SQLite
  - Redis >= 5.0

- **前端**
  - Node.js >= 20.10.0
  - pnpm >= 9.12.0

### 后端安装

1. **克隆项目**
```bash
git clone https://github.com/jiangzhikj/zq-platform.git
cd zq-platform/backend-django
```

2. **创建虚拟环境**
```bash
# 方式一：使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 方式二：使用 conda（推荐）
conda create -n zqplat python=3.11 -y
conda activate zqplat
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
# 在 backend-django 目录下创建 .env 文件
vim .env
```

主要配置项：
```env
# JWT 密钥
JWT_ACCESS_SECRET_KEY=your-jwt-access-secret
JWT_REFRESH_SECRET_KEY=your-jwt-refresh-secret

# 数据库配置
DATABASE_TYPE=MYSQL  # MYSQL/POSTGRESQL/SQLSERVER/SQLITE3
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=password
DATABASE_NAME=zq_admin

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
```

5. **数据库迁移**
```bash
python manage.py makemigrations core scheduler
python manage.py migrate
```

6. **初始化数据**
```bash
python manage.py loaddata db_init.json
```

7. **启动服务**
```bash
# 开发环境
python manage.py runserver 0.0.0.0:8000
```

8. **启动任务调度器（可选）**
```bash
# 生产环境
python start_scheduler.py
```

### 前端安装

1. **进入前端目录**
```bash
cd zq-platform/web
```

2. **安装依赖**
```bash
pnpm install
```

3. **配置环境变量**
```bash
cd apps/web-ele
cp .env.development .env
# 编辑 .env 文件，配置后端 API 地址
```

4. **启动开发服务器**
```bash
# 在 web 根目录下
pnpm dev
```

5. **构建生产版本**
```bash
pnpm build:ele
```

## 📝 默认账号

初始化数据后，可使用以下账号登录：

- 账号: `superadmin`
- 密码: `123456` 或联系管理员

## 🔧 主要功能模块

### 系统管理
- **用户管理**: 用户的增删改查、密码重置、状态管理
- **角色管理**: 角色权限分配、数据权限控制
- **权限管理**: 接口权限、按钮权限细粒度控制
- **部门管理**: 树形部门结构管理
- **岗位管理**: 岗位信息维护
- **菜单管理**: 动态菜单配置、路由管理
- **字典管理**: 系统字典维护

### 系统监控
- **服务器监控**: CPU、内存、磁盘、网络实时监控
- **Redis 监控**: Redis 性能指标、键值管理
- **数据库监控**: 数据库连接、性能监控
- **登录日志**: 用户登录记录、IP 地理位置

### 任务调度
- **定时任务**: Cron 表达式配置
- **任务日志**: 执行历史、结果查看
- **任务管理**: 启动、停止、立即执行

### 文件管理
- **文件上传**: 支持多文件上传
- **文件预览**: 图片、文档在线预览
- **文件下载**: 批量下载功能

### 数据管理（扩展功能）

#### 数据库表查询
配置化驱动的动态表查询系统：
- **JSON 配置**: 通过配置定义查询规则，无需编写代码
- **动态查询 API**: 统一查询端点，支持分页、过滤、排序
- **SQL 注入防护**: 参数化查询和白名单验证
- **数据导出**: 支持 Excel/CSV 格式导出
- **查询日志**: 记录所有查询和导出操作用于审计

```bash
# 批量创建表查询配置
python manage.py batch_create_table_configs --prefix BS_ --all

# 初始化查询菜单
python manage.py init_table_query_menus
```

#### SQL 导入（Oracle 到 MySQL）
Oracle SQL 文件转换和导入系统：
- **语法转换**: Oracle 到 MySQL 兼容语法转换
- **批量导入**: 基于目录的批量文件导入
- **状态追踪**: 支持断点续导、失败重试
- **进度报告**: 详细的导入进度和统计信息

```bash
# 转换 Oracle SQL 文件到 MySQL
python manage.py convert_sql input.sql -o output/

# 导入转换后的文件
python manage.py import_sql converted/ --all --resume
```

#### 问卷数据集成
外部问卷 API 对接，用于问卷数据管理：
- **Schema 同步**: 自动从外部 API 同步问卷结构定义
- **数据导入**: 支持批量和增量导入，使用 JWT 认证
- **动态展示**: Schema 驱动的动态表格列和搜索表单
- **灵活导出**: 支持文案模式和数值模式导出
- **子表单支持**: 展开嵌套数据（如户外活动记录）导出
- **定时任务**: 通过 APScheduler 自动同步 Schema 和导入数据

```bash
# 从外部 API 同步问卷 Schema
python manage.py sync_survey_schemas

# 导入问卷数据（全量或增量）
python manage.py import_survey_data --incremental

# 初始化问卷管理菜单
python manage.py init_survey_menus
```

## 🔐 API 文档

后端启动后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## 🛠️ 开发指南

### 代码风格约定

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

### 后端模块化架构

每个业务模块（user、role、permission 等）遵循以下结构：
```
core/
└── [module]/
    ├── __init__.py
    ├── [module]_api.py      # API 接口定义（Django Ninja Router）
    ├── [module]_model.py    # 数据模型定义（Django Model）
    └── [module]_schema.py   # 数据校验和序列化（Pydantic Schema）
```

### 前端开发

1. **添加新页面**
   - 在 `src/views/` 创建页面组件
   - 在 `src/router/routes/modules/` 添加路由
   - 在 `src/api/` 添加接口定义

2. **组件开发规范**
   - 使用 Element Plus 组件
   - 优先使用 Tailwind CSS
   - 支持暗黑模式
   - 图标从 `@vben/icons` 导入

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
- Git Hooks: lefthook + commitlint

## 📋 OpenSpec 规范驱动开发

本项目使用 OpenSpec 进行规范驱动开发。所有重大功能和变更都通过结构化规范进行文档化。

### 目录结构
```
openspec/
├── project.md              # 项目约定和上下文
├── AGENTS.md               # AI 助手使用说明
├── specs/                  # 当前规范（真相来源）
│   └── [capability]/
│       ├── spec.md         # 需求和场景
│       └── design.md       # 技术模式
└── changes/                # 变更提案
    ├── [change-name]/
    │   ├── proposal.md     # 为什么、什么、影响
    │   ├── tasks.md        # 实施清单
    │   ├── design.md       # 技术决策（可选）
    │   └── specs/          # 增量规范变更
    └── archive/            # 已完成的变更
```

### 创建变更提案

当添加新功能或进行重大变更时：

1. **创建变更目录**: `openspec/changes/[change-id]/`
2. **编写 proposal.md**: 记录为什么、什么和影响
3. **创建规范增量**: 使用 `## 新增|修改|移除需求`
4. **验证**: `openspec-cn validate [change-id] --strict`

### CLI 命令

```bash
# 列出活动变更
openspec-cn list

# 列出规范
openspec-cn list --specs

# 显示变更或规范详情
openspec-cn show [item]

# 验证变更或规范
openspec-cn validate [item] --strict

# 归档已完成的变更
openspec-cn archive <change-id> --yes
```

详细说明请参阅 `openspec/AGENTS.md`。

## 📦 部署

1. **后端部署**
   - 使用 Gunicorn + Nginx
   - 配置 Supervisor 进程守护
   - 配置 SSL 证书

2. **前端部署**
   - 执行 `pnpm build` 构建
   - 将 `dist` 目录部署到 Nginx
   - 配置反向代理

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发流程
1. 检查现有规范: `openspec-cn list --specs`
2. 为重大变更创建变更提案
3. 在实施前获得提案批准
4. 遵循 `openspec/project.md` 中的代码约定
5. 完成任务后更新 tasks.md

## 🙏 致谢

- [Django](https://www.djangoproject.com/) - 强大的 Python Web 框架
- [Django Ninja](https://django-ninja.rest-framework.com/) - 快速的 Django REST 框架
- [Vue Vben Admin](https://github.com/vbenjs/vue-vben-admin) - 优秀的 Vue3 后台管理模板
- [Element Plus](https://element-plus.org/) - 基于 Vue 3 的组件库
- [OpenSpec](https://github.com/openspec-cn/openspec) - 规范驱动开发工具

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- Issue: [GitHub Issues](../../issues)
- Email: jiangzhikj@outlook.com

---

<div align="center">
  Made with ❤️ by ZQ Team
</div>
