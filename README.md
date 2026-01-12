# zq-platform (ZhiQing Development Platform)

English | [简体中文](./README.zh-CN.md)

<div align="center">

A modern enterprise-level admin management system built with Django + Vue3 + Element Plus

[![Django](https://img.shields.io/badge/Django-5.2.7-green.svg)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-brightgreen.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-latest-blue.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

</div>

## Demo Link
[https://django-ninja.zq-platform.cn](https://django-ninja.zq-platform.cn/)

## 📖 Introduction

zq-platform is a comprehensive enterprise-level admin management system solution with a separated frontend and backend architecture. The backend uses Django 5.2 + Django Ninja to build high-performance RESTful APIs, while the frontend is based on Vue 3 + Vben Admin + Element Plus to create a modern management interface.

### ✨ Core Features

- 🎯 **Complete RBAC Permission System** - Multi-dimensional permission control for users, roles, permissions, departments, and positions
- 🔐 **JWT Authentication** - Secure token authentication with Access Token and Refresh Token support
- 📊 **System Monitoring** - Server monitoring, Redis monitoring, database monitoring for real-time system status
- 📁 **File Management** - Comprehensive file upload, download, and preview functionality
- 📝 **Operation Logs** - Detailed login logs and operation auditing
- 🗂️ **Data Dictionary** - Flexible dictionary management with multi-level classification support
- ⏰ **Task Scheduling** - APScheduler-based scheduled task management
- 🔌 **WebSocket Support** - Real-time communication capabilities
- 🌐 **Multi-Database Support** - MySQL, PostgreSQL, SQL Server, SQLite
- 🎨 **Modern UI** - Responsive design with dark mode support
- 📦 **Monorepo Architecture** - Frontend engineering solution based on pnpm workspace

### 🆕 Extended Features

- 📋 **Database Table Query** - Configuration-driven dynamic table querying without code changes
- 🔄 **SQL Import** - Oracle to MySQL SQL conversion and batch import with status tracking
- 📊 **Survey Integration** - External survey API integration for questionnaire data management with flexible export options

## 🏗️ Tech Stack

### Backend Technologies

- **Core Framework**: Django 5.2.7
- **API Framework**: Django Ninja 1.4.5 (High-performance API framework)
- **Authentication**: PyJWT 2.8.0
- **Async Tasks**: Celery 5.4.0 + Django Celery Beat
- **Task Scheduling**: APScheduler 3.10.4
- **Caching**: Redis + django-redis 6.0.0
- **WebSocket**: Django Channels 4.2
- **Database Drivers**: psycopg2-binary, pymysql, pyodbc
- **Server**: Uvicorn 0.38.0 / Gunicorn 23.0.0
- **Others**: openpyxl, geoip2, psutil, cryptography

### Frontend Technologies

- **Core Framework**: Vue 3.x
- **Build Tool**: Vite 5.x
- **UI Component Library**: Element Plus
- **State Management**: Pinia
- **Router**: Vue Router
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS
- **Utility Libraries**: VueUse, dayjs, lodash-es
- **Code Standards**: ESLint, Prettier, Stylelint
- **Package Manager**: pnpm 10.14.0
- **Monorepo**: Turbo

## 📁 Project Structure

```
zq-platform/
├── backend-django/          # Django Backend
│   ├── application/         # Project Configuration
│   ├── core/               # Core Business Modules
│   │   ├── auth/           # Authentication & Authorization
│   │   ├── user/           # User Management
│   │   ├── role/           # Role Management
│   │   ├── permission/     # Permission Management
│   │   ├── dept/           # Department Management
│   │   ├── post/           # Position Management
│   │   ├── menu/           # Menu Management
│   │   ├── dict/           # Dictionary Management
│   │   ├── login_log/      # Login Logs
│   │   ├── file_manager/   # File Management
│   │   ├── server_monitor/ # Server Monitoring
│   │   ├── redis_monitor/  # Redis Monitoring
│   │   ├── redis_manager/  # Redis Management
│   │   ├── database_monitor/ # Database Monitoring
│   │   ├── database_manager/ # Database Management
│   │   ├── table_query/    # Dynamic Table Query
│   │   └── survey/         # Survey Data Management
│   ├── scheduler/          # Task Scheduling Module
│   ├── common/             # Common Modules
│   │   ├── fu_crud.py      # Generic CRUD Operations
│   │   ├── fu_auth.py      # Auth & Authorization
│   │   ├── fu_cache.py     # Cache Management
│   │   ├── fu_pagination.py # Pagination Handler
│   │   └── fu_schema.py    # Common Data Structures
│   ├── env/                # Environment Configuration
│   ├── requirements.txt    # Python Dependencies
│   └── manage.py          # Django Management Script
│
├── web/                    # Vue Frontend (Monorepo)
│   ├── apps/
│   │   └── web-ele/        # Element Plus Main Application
│   │       ├── src/
│   │       │   ├── api/    # API Interfaces
│   │       │   ├── views/  # Page Components
│   │       │   ├── router/ # Router Configuration
│   │       │   └── store/  # State Management
│   │       └── package.json
│   ├── packages/           # Shared Packages
│   │   ├── @core/          # Core Packages
│   │   ├── effects/        # Effects Packages
│   │   ├── hooks/          # Hooks
│   │   ├── icons/          # Icons
│   │   ├── locales/        # Internationalization
│   │   ├── stores/         # State Management
│   │   └── utils/          # Utility Functions
│   ├── internal/           # Internal Tools
│   └── package.json        # Root Configuration
│
├── openspec/               # OpenSpec Specification-Driven Development
│   ├── project.md          # Project Conventions
│   ├── AGENTS.md           # AI Assistant Instructions
│   ├── specs/              # Feature Specifications
│   │   ├── database-table-query/
│   │   └── sql-import/
│   └── changes/            # Change Proposals
│       └── archive/        # Completed changes
│
└── docs/                   # Documentation
    ├── frontend-development-guide.md
    └── backend-api-development-guide.md
```

## 🚀 Quick Start

### Requirements

- **Backend**
  - Python >= 3.10
  - MySQL >= 5.7 / PostgreSQL >= 12 / SQL Server / SQLite
  - Redis >= 5.0

- **Frontend**
  - Node.js >= 20.10.0
  - pnpm >= 9.12.0

### Backend Installation

1. **Clone the Project**
```bash
git clone https://github.com/jiangzhikj/zq-platform.git
cd zq-platform/backend-django
```

2. **Create Virtual Environment**
```bash
# Option 1: Using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Option 2: Using conda (Recommended)
conda create -n zqplat python=3.11 -y
conda activate zqplat
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
```bash
# Create .env file in backend-django directory
vim .env
```

Main configuration items:
```env
# JWT Keys
JWT_ACCESS_SECRET_KEY=your-jwt-access-secret
JWT_REFRESH_SECRET_KEY=your-jwt-refresh-secret

# Database Configuration
DATABASE_TYPE=MYSQL  # MYSQL/POSTGRESQL/SQLSERVER/SQLITE3
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=password
DATABASE_NAME=zq_admin

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=2
```

5. **Database Migration**
```bash
python manage.py makemigrations core scheduler
python manage.py migrate
```

6. **Initialize Data**
```bash
python manage.py loaddata db_init.json
```

7. **Start Service**
```bash
# Development Environment
python manage.py runserver 0.0.0.0:8000
```

8. **Start Task Scheduler (Optional)**
```bash
# Production Environment
python start_scheduler.py
```

### Frontend Installation

1. **Navigate to Frontend Directory**
```bash
cd zq-platform/web
```

2. **Install Dependencies**
```bash
pnpm install
```

3. **Configure Environment Variables**
```bash
cd apps/web-ele
cp .env.development .env
# Edit the .env file to configure backend API address
```

4. **Start Development Server**
```bash
# In web root directory
pnpm dev
```

5. **Build for Production**
```bash
pnpm build:ele
```

## 📝 Default Account

After initializing data, you can login with the following account:

- Username: `superadmin`
- Password: `123456` or contact administrator

## 🔧 Main Functional Modules

### System Management
- **User Management**: CRUD operations for users, password reset, status management
- **Role Management**: Role permission assignment, data permission control
- **Permission Management**: Fine-grained API and button permission control
- **Department Management**: Tree-structured department management
- **Position Management**: Position information maintenance
- **Menu Management**: Dynamic menu configuration, route management
- **Dictionary Management**: System dictionary maintenance

### System Monitoring
- **Server Monitoring**: Real-time monitoring of CPU, memory, disk, network
- **Redis Monitoring**: Redis performance metrics, key-value management
- **Database Monitoring**: Database connection, performance monitoring
- **Login Logs**: User login records, IP geolocation

### Task Scheduling
- **Scheduled Tasks**: Cron expression configuration
- **Task Logs**: Execution history, result viewing
- **Task Management**: Start, stop, execute immediately

### File Management
- **File Upload**: Multi-file upload support
- **File Preview**: Online preview for images and documents
- **File Download**: Batch download functionality

### Data Management (Extended)

#### Database Table Query
Configuration-driven dynamic table querying system:
- **JSON Configuration**: Define query rules without code changes
- **Dynamic Query API**: Unified query endpoint with pagination, filtering, sorting
- **SQL Injection Protection**: Parameterized queries and whitelist validation
- **Data Export**: Export to Excel/CSV formats
- **Query Logging**: Audit all query and export operations

```bash
# Batch create table configurations
python manage.py batch_create_table_configs --prefix BS_ --all

# Initialize query menus
python manage.py init_table_query_menus
```

#### SQL Import (Oracle to MySQL)
Oracle SQL file conversion and import system:
- **Syntax Conversion**: Oracle to MySQL compatible syntax
- **Batch Import**: Directory-based batch file import
- **Status Tracking**: Resume interrupted imports, retry failed files
- **Progress Reporting**: Detailed import progress and statistics

```bash
# Convert Oracle SQL files to MySQL
python manage.py convert_sql input.sql -o output/

# Import converted files
python manage.py import_sql converted/ --all --resume
```

#### Survey Data Integration
External survey API integration for questionnaire data management:
- **Schema Sync**: Auto-sync questionnaire schema definitions from external API
- **Data Import**: Batch and incremental import with JWT authentication
- **Dynamic Display**: Schema-driven table columns and search forms
- **Flexible Export**: Export with label (text) or value (numeric) mode
- **Sub-form Support**: Expand nested data (e.g., outdoor activities) in exports
- **Scheduled Tasks**: Automatic schema sync and data import via APScheduler

```bash
# Sync questionnaire schemas from external API
python manage.py sync_survey_schemas

# Import questionnaire data (full or incremental)
python manage.py import_survey_data --incremental

# Initialize survey management menus
python manage.py init_survey_menus
```

## 🔐 API Documentation

After starting the backend, visit the following URLs to view API documentation:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## 🛠️ Development Guide

### Code Style Conventions

#### Backend (Python/Django)
- Follow PEP 8 coding standards
- Use UTF-8 encoding declaration: `# -*- coding: utf-8 -*-`
- Write comments and docstrings in Chinese
- Module files naming: `module_function.py` (e.g., `user_api.py`, `user_model.py`)
- Class names: PascalCase; Functions and variables: snake_case
- API endpoints: RESTful style with unified response format

#### Frontend (TypeScript/Vue)
- Use ESLint + Prettier for code formatting
- TypeScript for type-safe development
- Components use `<script setup>` syntax
- Prefer Tailwind CSS for styling
- Import icons from `@vben/icons`

### Backend Module Architecture

Each business module (user, role, permission, etc.) follows this structure:
```
core/
└── [module]/
    ├── __init__.py
    ├── [module]_api.py      # API Endpoints (Django Ninja Router)
    ├── [module]_model.py    # Data Models (Django Model)
    └── [module]_schema.py   # Data Validation (Pydantic Schema)
```

### Frontend Development

1. **Adding New Pages**
   - Create page components in `src/views/`
   - Add routes in `src/router/routes/modules/`
   - Add API definitions in `src/api/`

2. **Component Development Standards**
   - Use Element Plus components
   - Prefer Tailwind CSS
   - Support dark mode
   - Import icons from `@vben/icons`

### Testing Strategy

#### Frontend Testing
- **Unit Tests**: Vitest + Vue Test Utils + happy-dom
- **E2E Tests**: Playwright
- Test files: `*.spec.ts` or `*.test.ts`
- Commands: `pnpm test:unit` (unit), `pnpm test:e2e` (E2E)

#### Backend Testing
- Django TestCase for unit tests
- Django Ninja test client for API tests
- Test data fixtures: `db_init.json`

### Git Workflow

#### Branch Strategy
- `main`: Main branch, stable and releasable
- `feature/*`: Feature branches, created from main
- `fix/*`: Bug fix branches
- `release/*`: Release branches

#### Commit Conventions
- Use Conventional Commits specification
- Format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Use `pnpm commit` (czg) for interactive commits
- Git Hooks: lefthook + commitlint

## 📋 OpenSpec Specification-Driven Development

This project uses OpenSpec for specification-driven development. All major features and changes are documented through structured specifications.

### Directory Structure
```
openspec/
├── project.md              # Project conventions and context
├── AGENTS.md               # AI assistant instructions
├── specs/                  # Current specifications (source of truth)
│   └── [capability]/
│       ├── spec.md         # Requirements and scenarios
│       └── design.md       # Technical patterns
└── changes/                # Change proposals
    ├── [change-name]/
    │   ├── proposal.md     # Why, what, impact
    │   ├── tasks.md        # Implementation checklist
    │   ├── design.md       # Technical decisions (optional)
    │   └── specs/          # Incremental spec changes
    └── archive/            # Completed changes
```

### Creating a Change Proposal

When adding new features or making significant changes:

1. **Create change directory**: `openspec/changes/[change-id]/`
2. **Write proposal.md**: Document why, what, and impact
3. **Create spec deltas**: Use `## ADDED|MODIFIED|REMOVED Requirements`
4. **Validate**: `openspec-cn validate [change-id] --strict`

### CLI Commands

```bash
# List active changes
openspec-cn list

# List specifications
openspec-cn list --specs

# Show change or spec details
openspec-cn show [item]

# Validate change or spec
openspec-cn validate [item] --strict

# Archive completed change
openspec-cn archive <change-id> --yes
```

For detailed instructions, see `openspec/AGENTS.md`.

## 📦 Deployment

1. **Backend Deployment**
   - Use Gunicorn + Nginx
   - Configure Supervisor process daemon
   - Configure SSL certificates

2. **Frontend Deployment**
   - Execute `pnpm build` to build
   - Deploy `dist` directory to Nginx
   - Configure reverse proxy

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork this project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Process
1. Check existing specs: `openspec-cn list --specs`
2. Create change proposal for significant changes
3. Get proposal approved before implementation
4. Follow code conventions in `openspec/project.md`
5. Update tasks.md as you complete items

## 🙏 Acknowledgments

- [Django](https://www.djangoproject.com/) - Powerful Python web framework
- [Django Ninja](https://django-ninja.rest-framework.com/) - Fast Django REST framework
- [Vue Vben Admin](https://github.com/vbenjs/vue-vben-admin) - Excellent Vue3 admin template
- [Element Plus](https://element-plus.org/) - Vue 3 component library
- [OpenSpec](https://github.com/openspec-cn/openspec) - Specification-driven development

## 📞 Contact

For questions or suggestions, please contact us via:

- Issue: [GitHub Issues](../../issues)
- Email: jiangzhikj@outlook.com

---

<div align="center">
  Made with ❤️ by ZQ Team
</div>
