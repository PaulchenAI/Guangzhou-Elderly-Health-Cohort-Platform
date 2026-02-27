# zq-platform 智擎开发平台

<div align="center">

基于 **Django + Vue3 + Element Plus + LLM/RAG** 的现代化企业级后台管理与智能开发平台

[![Django](https://img.shields.io/badge/Django-5.2.7-green.svg)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-latest-blue.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

</div>

---

## � 项目简介

**zq-platform（智擎开发平台）** 是一套前后端分离的企业级后台管理与智能开发解决方案：

- 后端基于 **Django 5.2 + Django Ninja** 提供高性能 RESTful API 与任务调度能力  
- 前端基于 **Vue3 + Vite + Element Plus + Vben Admin** 提供现代化中后台界面  
- 内置 **权限系统、任务调度、日志审计、文件管理、数据库/Redis 监控** 等通用能力  
- 扩展支持 **Oracle→MySQL SQL 导入、动态表查询、问卷集成** 等业务场景  
- 集成 **LLM + 向量数据库（Chroma）**，支持 RAG 检索增强和智能 Agent 能力（在 docs 与 backend-django/.env 中已预置配置）

目标是让你可以在此基础上快速搭建自有后台管理系统，并按需接入 AI / RAG 能力。

线上示例：  
`https://django-ninja.zq-platform.cn/`

---

## 🧠 技术栈

### 前端（Frontend）

- 框架：Vue 3.x
- 构建工具：Vite 5.x
- UI 组件库：Element Plus
- 状态管理：Pinia
- 路由：Vue Router
- HTTP 客户端：Axios
- 样式：Tailwind CSS
- 工程化：pnpm Workspace + Turbo Monorepo

### 后端（Backend）

- Web 框架：Django 5.2.7
- API 框架：Django Ninja 1.4.5
- 身份认证：PyJWT（Access Token / Refresh Token）
- 任务队列：Celery 5.4.0 + django-celery-beat
- 定时任务：APScheduler 3.10.4
- 缓存与会话：Redis + django-redis
- WebSocket：Django Channels 4.2
- 数据库：MySQL / PostgreSQL / SQL Server / SQLite
- 驱动：psycopg2-binary、pymysql、pyodbc
- 部署：Gunicorn / Uvicorn + Nginx

### LLM 与向量检索（Intelligent / RAG）

- LLM：兼容 OpenAI API 的模型（默认配置为通义千问 Qwen，经由 DashScope 兼容模式）  
- 向量库：Chroma DB（`VECTOR_DB_TYPE=chromadb`）  
- 能力：  
  - 支持将文档切片后写入向量库  
  - 通过 RAG 检索增强调用 LLM  
  - 在后端提供统一的 API 封装（配置见 `backend-django/.env` 与 `docs/backend-api-development-guide.md`）

### 部署（Deployment）

- 推荐：Docker + Nginx + Gunicorn/Uvicorn  
- 也支持传统物理机 / 虚拟机部署（参见 README 与 openspec 文档）

---

## 🏗 系统架构

整体架构包括四个层面：

- **前端应用层**：Vue3 + Vite + Element Plus 构建的多应用 Monorepo（apps/web-ele 等）  
- **后端服务层**：Django + Django Ninja 提供 API、鉴权、任务调度、WebSocket 等能力  
- **基础设施层**：MySQL/PG/SQL Server、Redis、Chroma、对象存储/文件系统  
- **智能能力层**：LLM（Qwen/OpenAI API 等）+ RAG 检索增强，封装为统一服务接口

架构示意图（可根据实际情况补充图片文件）：  
![architecture](./docs/architecture.png)

---

## ✨ 核心亮点

- 🔐 **完整 RBAC 权限系统**  
  用户 / 角色 / 权限 / 部门 / 岗位多维度控制，支持菜单、按钮、接口粒度授权。

- 🧱 **通用后台能力开箱即用**  
  登录日志、操作日志、字典管理、文件管理、任务调度、数据监控等常用模块均已内置。

- 🗃 **Oracle→MySQL SQL 导入与动态表查询**  
  - 提供 SQL 转换与批量导入能力，支持断点续导、失败重试、自动修复保留字等  
  - 通过 JSON 配置驱动的动态表查询，支持分页、过滤、排序、导出、查询日志审计。

- 🧠 **LLM + RAG 能力集成**  
  - 支持将业务文档嵌入到 Chroma 向量库中  
  - 通过 RAG 检索增强调用 LLM，实现「带业务知识」的对话与辅助决策  
  - 配置式切换 LLM 提供商（OpenAI 兼容协议）。

- 🌐 **多数据库支持与监控**  
  MySQL / PostgreSQL / SQL Server / SQLite 统一接入，提供连接监控、库表管理、数据查询 API。

- 📦 **Monorepo 工程化**  
  前端采用 pnpm Workspace + Turbo，便于大型团队协作与代码复用。

---

## 🎥 Demo

- 在线演示地址（后台管理）：  
  `https://django-ninja.zq-platform.cn/`

- API 文档：  
  - Swagger UI：`http://localhost:8000/api/docs`  
  - ReDoc：`http://localhost:8000/api/redoc`

你也可以结合自己环境录制 GIF 或视频，放在本节中：

```markdown
![demo](./docs/demo.gif)
```

---

## 📂 项目结构

项目采用前后端分离 + Monorepo 结构：

```bash
zq-platform/
├── backend-django/          # 后端（Django + Django Ninja）
│   ├── application/         # 项目配置（settings/urls/asgi 等）
│   ├── core/                # 核心业务模块
│   │   ├── auth/            # 认证与授权
│   │   ├── user/            # 用户管理
│   │   ├── role/            # 角色管理
│   │   ├── permission/      # 权限管理
│   │   ├── dept/            # 部门管理
│   │   ├── post/            # 岗位管理
│   │   ├── menu/            # 菜单与路由
│   │   ├── dict/            # 数据字典
│   │   ├── login_log/       # 登录日志
│   │   ├── file_manager/    # 文件管理
│   │   ├── server_monitor/  # 服务器监控
│   │   ├── redis_monitor/   # Redis 监控
│   │   ├── redis_manager/   # Redis 管理
│   │   ├── database_monitor/# 数据库监控
│   │   ├── database_manager/# 数据库管理
│   │   ├── table_query/     # 动态表查询
│   │   └── survey/          # 问卷数据管理
│   ├── scheduler/           # APScheduler 任务调度
│   ├── common/              # 通用工具（CRUD、缓存、分页、Schema 等）
│   ├── env/                 # 环境配置（dev/prd 等）
│   ├── requirements.txt     # Python 依赖
│   └── manage.py            # Django 管理脚本
│
├── web/                     # 前端（Vue3 Monorepo）
│   ├── apps/
│   │   └── web-ele/         # 主应用（Element Plus 后台）
│   ├── packages/            # 共享包（hooks/icons/locales/utils 等）
│   ├── internal/            # 内部工具
│   └── package.json         # 前端根配置
│
├── openspec/                # OpenSpec 规范驱动开发
│   ├── project.md
│   ├── AGENTS.md
│   ├── specs/               # 规范（如 database-table-query、sql-import）
│   └── changes/             # 变更提案与归档
│
└── docs/                    # 文档（前端开发指南、后端 API 指南等）
```

---

## ⚙️ 本地运行方式

以下步骤假设你已经安装了：

- Python ≥ 3.10  
- Node.js ≥ 20.10.0  
- pnpm ≥ 9.12.0  
- MySQL（或其他支持的数据库）  
- Redis（建议本地启动一个实例）

### 1. 克隆项目

```bash
git clone https://github.com/jiangzhikj/zq-platform.git
cd zq-platform
```

### 2. 启动后端（backend-django）

```bash
cd backend-django

# 创建并激活虚拟环境（任选一种方式）
python -m venv venv
source venv/bin/activate      # Mac/Linux
# 或在 Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

配置后端环境变量（简化示例，详情可参考 backend-django/README.md）：

```bash
cp .env.example .env  # 如果仓库提供示例文件，可先复制
vim .env              # 或用你习惯的编辑器修改
```

核心配置项示例：

```env
# JWT 密钥
JWT_ACCESS_SECRET_KEY=your-jwt-access-secret
JWT_REFRESH_SECRET_KEY=your-jwt-refresh-secret

# 数据库配置
DATABASE_TYPE=MYSQL
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
DATABASE_USER=fuadmin
DATABASE_PASSWORD=fuadmin
DATABASE_NAME=fu_admin_pro

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
```

初始化数据库：

```bash
python manage.py makemigrations core scheduler
python manage.py migrate

# 可选：导入初始数据（包含默认账号、菜单等）
python manage.py loaddata db_init.json
```

运行开发服务器：

```bash
python manage.py runserver 0.0.0.0:8000
```

此时可访问：

- 后端 API 文档：`http://localhost:8000/api/docs`

### 3. 启动前端（web）

在项目根目录的另一个终端中：

```bash
cd zq-platform/web

# 安装依赖（使用 pnpm）
pnpm install
```

配置前端环境变量：

```bash
cd apps/web-ele
cp .env.development .env
# 编辑 .env，将后端地址改成你本地的服务，例如：
# VITE_GLOB_API_URL=http://localhost:8000/api
```

返回 web 根目录，启动开发服务器：

```bash
cd ../..
pnpm dev
```

默认访问地址类似：`http://localhost:5777`（以实际输出为准）。

### 4. 默认登录账号

当你执行了 `python manage.py loaddata db_init.json` 之后，可以使用默认账号登录前端：

- 用户名：`superadmin`  
- 密码：`123456`（如有变更以后端实际配置为准）

---

## 🔧 进阶能力与常用命令（节选）

只列出与本 README 提到能力强相关的几条，更多可参考 `backend-django/README.md` 与 `docs`：

- 导入 Oracle 转换后的 SQL（可选）：

```bash
# 导入表结构（DDL）
python manage.py import_oracle_sql ../docs/hospital/convertsql/create --all --batch-id ddl_batch --auto-fix --continue-on-error

# 导入数据（DML）
python manage.py import_oracle_sql ../docs/hospital/convertsql/insert --all --batch-id dml_batch --auto-fix --continue-on-error
```

- 批量创建表查询配置：

```bash
python manage.py batch_create_table_configs --list
python manage.py batch_create_table_configs --prefix BS --update
```

- 问卷 Schema 同步与数据导入（依赖外部问卷 API）：

```bash
python manage.py sync_survey_schemas
python manage.py import_survey_data
```

---

## 📦 部署提示（简要）

完整部署方案请参考项目文档与 openspec 规范，这里只给出最简要版本：

1. **后端**
   - 使用 Gunicorn/Uvicorn 运行 Django 应用
   - 通过 Nginx 做反向代理与静态文件托管
   - 配置系统服务（systemd/Supervisor）保证进程守护

2. **前端**
   - 在 `web` 目录执行 `pnpm build:ele`
   - 将生成的 `dist` 目录部署到 Nginx 静态站点
   - 配置反向代理，将 `/api` 转发到后端服务

---



