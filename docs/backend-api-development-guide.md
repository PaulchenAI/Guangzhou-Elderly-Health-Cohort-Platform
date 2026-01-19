# ZQ-Platform 后端 API 接口开发规范

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术栈](#2-技术栈)
- [3. 项目结构](#3-项目结构)
- [4. API 开发规范](#4-api-开发规范)
- [5. 模型开发](#5-模型开发)
- [6. Schema 定义](#6-schema-定义)
- [7. CRUD 操作](#7-crud-操作)
- [8. 认证与权限](#8-认证与权限)
- [9. 分页与过滤](#9-分页与过滤)
- [10. 错误处理](#10-错误处理)
- [11. 数据验证](#11-数据验证)
- [12. 缓存策略](#12-缓存策略)
- [13. 日志规范](#13-日志规范)
- [14. 代码风格](#14-代码风格)

---

## 1. 项目概述

ZQ-Platform 后端项目基于 Django 5.x + Django Ninja 框架开发，提供 RESTful API 服务。

### 1.1 环境要求

- **Python**: >= 3.10
- **Django**: 5.2.x
- **Django Ninja**: 1.4.x
- **数据库**: PostgreSQL / MySQL / SQLite

### 1.2 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
python manage.py migrate

# 启动开发服务器
python manage.py runserver

# 启动 ASGI 服务器（支持 WebSocket）
uvicorn application.asgi:application --reload --host 0.0.0.0 --port 8000

# 生产环境启动
gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker

# 创建超级用户
python manage.py createsuperuser
```

---

## 2. 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Django | 5.2.x | Web 框架 |
| Django Ninja | 1.4.x | API 框架（类似 FastAPI） |
| Pydantic | 2.x | 数据验证 |
| PyJWT | 2.8.x | JWT 认证 |
| Celery | 5.4.x | 异步任务 |
| Redis | - | 缓存与消息队列 |
| Channels | 4.2.x | WebSocket 支持 |
| PostgreSQL/MySQL | - | 数据库 |

---

## 3. 项目结构

### 3.1 整体结构

```
backend-django/
├── application/              # 项目配置
│   ├── settings.py          # Django 配置
│   ├── urls.py              # URL 路由
│   ├── main.py              # Ninja API 入口
│   ├── asgi.py              # ASGI 应用
│   └── celery.py            # Celery 配置
├── core/                     # 核心业务模块
│   ├── auth/                # 认证模块
│   ├── user/                # 用户管理
│   ├── role/                # 角色管理
│   ├── permission/          # 权限管理
│   ├── dept/                # 部门管理
│   ├── menu/                # 菜单管理
│   └── router.py            # 核心路由聚合
├── common/                   # 公共组件
│   ├── fu_auth.py           # 认证工具
│   ├── fu_crud.py           # CRUD 工具
│   ├── fu_model.py          # 基础模型
│   ├── fu_schema.py         # 基础 Schema
│   ├── fu_pagination.py     # 分页工具
│   ├── fu_cache.py          # 缓存工具
│   ├── middleware.py        # 中间件
│   └── utils/               # 工具函数
├── scheduler/               # 定时任务模块
├── env/                     # 环境配置
├── logs/                    # 日志目录
├── media/                   # 媒体文件
├── static/                  # 静态文件
└── requirements.txt         # 依赖列表
```

### 3.2 模块结构

每个业务模块遵循统一的目录结构：

```
module_name/
├── __init__.py
├── module_api.py           # API 接口定义
├── module_model.py         # 数据模型
├── module_schema.py        # 请求/响应 Schema
└── module_service.py       # 业务逻辑（可选）
```

---

## 4. API 开发规范

### 4.1 路由定义

使用 Django Ninja Router 定义 API 路由：

```python
# module_api.py
from ninja import Router

router = Router()


@router.post("/user", response=UserSchemaOut, summary="创建用户")
def create_user(request, data: UserSchemaIn):
    """
    创建新用户
    
    详细描述接口的功能和注意事项
    """
    # 实现逻辑
    pass


@router.get("/user/{user_id}", response=UserSchemaOut, summary="获取用户详情")
def get_user(request, user_id: str):
    """获取单个用户的详细信息"""
    pass
```

### 4.2 路由注册

在 `router.py` 中聚合子路由：

```python
# core/router.py
from ninja import Router

from core.user.user_api import router as user_router
from core.role.role_api import router as role_router

# 创建核心模块的总路由
core_router = Router()

# 注册子路由
core_router.add_router("", user_router, tags=["Core-User"])
core_router.add_router("", role_router, tags=["Core-Role"])
```

在 `main.py` 中注册到 API：

```python
# application/main.py
from ninja import NinjaAPI
from common.fu_auth import BearerAuth, ApiKey
from core.router import core_router

api = NinjaAPI(auth=[BearerAuth(), ApiKey()])

api.add_router('/core', core_router)
```

### 4.3 HTTP 方法规范

| HTTP 方法 | 用途 | 路径示例 |
|-----------|------|----------|
| `GET` | 获取资源（单个或列表） | `/user`, `/user/{id}` |
| `POST` | 创建资源 | `/user` |
| `PUT` | 完全替换资源 | `/user/{id}` |
| `PATCH` | 部分更新资源 | `/user/{id}` |
| `DELETE` | 删除资源 | `/user/{id}` |

### 4.4 路径命名规范

```python
# 资源列表
@router.get("/user")                    # 获取用户列表
@router.get("/user/all")                # 获取所有用户（不分页）

# 单个资源
@router.get("/user/{user_id}")          # 获取用户详情
@router.put("/user/{user_id}")          # 更新用户
@router.delete("/user/{user_id}")       # 删除用户

# 资源操作
@router.post("/user/{user_id}/reset_password")  # 重置密码

# 批量操作
@router.delete("/user/batch/delete")    # 批量删除
@router.post("/user/batch/update-status")  # 批量更新状态

# 关联资源
@router.get("/user/by/dept/{dept_id}")  # 根据部门获取用户
@router.get("/role/users/by/role_id")   # 获取角色下的用户

# 搜索
@router.get("/user/search")             # 搜索用户

# AI 友好的按名称/编码查询（支持模糊匹配）
@router.get("/user/by-name/{name}")       # 按姓名查询用户
@router.get("/user/by-username/{username}")  # 按登录名查询用户
@router.get("/role/by-name/{name}")       # 按角色名称查询
@router.get("/role/by-code/{code}")       # 按角色编码查询
@router.get("/dept/by-name/{name}")       # 按部门名称查询
@router.get("/dept/by-code/{code}")       # 按部门编码查询
@router.get("/post/by-name/{name}")       # 按岗位名称查询
@router.get("/post/by-code/{code}")       # 按岗位编码查询
@router.get("/dict/by-name/{name}")       # 按字典名称查询
@router.get("/dict/by-code/{code}")       # 按字典编码查询
@router.get("/survey/schemas/by-name/{name}")  # 按问卷名称查询配置
@router.get("/table-query/configs/by-name/{name}")  # 按表查询配置名称查询
```

### 4.5 OpenAPI 描述规范

所有 API 端点必须提供中文 summary 和规范化的 description，以支持 AI 意图理解和文档生成。

#### 4.5.1 Summary 命名规范

**格式**：`动词 + 名词（补充说明）`

```python
# 正确示例
@router.get("/user", response=List[UserSchemaOut], summary="获取用户列表（分页）")
@router.post("/user", response=UserSchemaOut, summary="创建用户")
@router.get("/user/{user_id}", response=UserSchemaDetail, summary="获取用户详情")
@router.put("/user/{user_id}", response=UserSchemaOut, summary="更新用户")
@router.delete("/user/{user_id}", response=UserSchemaOut, summary="删除用户")

# 错误示例
@router.get("/user")  # 缺少 summary，Django Ninja 自动生成英文
@router.get("/user", summary="List User")  # 英文 summary
```

**动词标准化映射表**：

| HTTP 方法 | 操作类型 | 标准动词 | 示例 |
|-----------|---------|---------|------|
| POST | 创建 | 创建 | 创建用户 |
| GET | 读取单个 | 获取 | 获取用户详情 |
| GET | 读取列表 | 获取 | 获取用户列表（分页） |
| GET | 读取全部 | 获取所有 | 获取所有用户 |
| PUT | 完全更新 | 更新 | 更新用户 |
| PATCH | 部分更新 | 部分更新 | 部分更新用户 |
| DELETE | 删除 | 删除 | 删除用户 |
| DELETE | 批量删除 | 批量删除 | 批量删除用户 |
| POST | 搜索 | 搜索 | 搜索用户 |
| POST | 导出 | 导出 | 导出用户数据 |
| POST | 导入 | 导入 | 导入用户数据 |
| POST | 同步 | 触发同步 | 触发数据同步 |

#### 4.5.2 Description 规范

使用函数 docstring 作为 description，Django Ninja 会自动将其作为 OpenAPI 的 description：

```python
@router.get("/user", response=List[UserSchemaOut], summary="获取用户列表（分页）")
@paginate(MyPagination)
def list_user(request, filters: UserFilters = Query(...)):
    """
    获取用户列表（分页）
    
    查询参数:
    - page: 页码（默认 1）
    - pageSize: 每页数量（默认 10）
    - name: 用户名（模糊查询）
    - user_status: 用户状态（0-禁用，1-正常，2-锁定）
    
    返回:
    - items: 用户列表
    - total: 总数
    """
    query_set = retrieve(request, User, filters)
    return query_set
```

#### 4.5.3 AI 友好的描述

为了支持 AI 意图理解，description 应包含：
- 业务语义描述（使用自然语言）
- 常用同义词（如 "数据"、"记录" 等）

```python
# 良好示例 - 包含业务语义
description="""
获取问卷数据列表（分页）

用于查询已填写的问卷记录，支持按问卷类型、患者姓名、日期范围筛选。
"""

# 避免 - 缺乏业务语义
description="获取问卷数据列表"
```

#### 4.5.4 支持名称参数的 API description 编写规范

当 API 同时支持 ID 和名称参数时，description 应明确说明：

```python
@router.post("/survey/query", response=SurveyQueryResult, summary="查询问卷数据")
def query_records(request, data: SurveyQueryIn):
    """
    动态查询问卷数据（根据 Schema 配置）
    
    支持两种方式指定问卷类型：
    1. schema_id: 问卷配置 ID（精确匹配）
    2. survey_name: 问卷名称（支持模糊匹配，如"户外活动"可匹配"户外活动记录表"）
    
    参数优先级：schema_id > survey_name
    
    AI 调用建议：优先使用 survey_name 参数，传入用户提到的问卷名称即可。
    
    请求体:
    - schema_id: Schema 配置 ID（可选，优先级高于 survey_name）
    - survey_name: 问卷名称（可选，支持模糊匹配，AI 推荐使用）
    - page: 页码（默认 1）
    ...
    """
```

### 4.6 AI 友好的按名称查询 API 设计模式

为了使 AI/LLM 能够通过自然语言提取的名称直接调用 API，系统提供按名称查询的 API 端点。

#### 4.6.1 设计原则

1. **路径格式**：使用 `/resource/by-name/{name}` 或 `/resource/by-code/{code}` 形式
2. **模糊匹配**：支持精确匹配和模糊匹配（使用 `__icontains`）
3. **匹配优先级**：优先返回精确匹配的结果，其次返回模糊匹配的第一个结果
4. **错误处理**：无匹配时返回 404 错误，包含清晰的错误信息

#### 4.6.2 实现模板

```python
@router.get("/resource/by-name/{name}", response=ResourceSchemaOut, summary="按名称查询资源")
def get_resource_by_name(request, name: str):
    """
    按资源名称查询资源（支持模糊匹配）
    
    路径参数:
    - name: 资源名称（支持模糊匹配）
    
    查询逻辑:
    1. 优先返回名称完全匹配的资源
    2. 如果没有完全匹配，返回名称包含关键字的第一个资源
    3. 如果都没有匹配，返回 404 错误
    
    AI 调用建议: 直接传入用户提到的资源名称，无需获取 ID。
    
    示例:
    - /resource/by-name/系统管理员 → 精确匹配
    - /resource/by-name/管理员 → 模糊匹配到"系统管理员"
    """
    # 优先精确匹配
    resource = Resource.objects.filter(name=name, is_deleted=False).first()
    if resource:
        return resource
    
    # 模糊匹配
    resource = Resource.objects.filter(name__icontains=name, is_deleted=False).first()
    if resource:
        return resource
    
    raise HttpError(404, f"未找到名称匹配 '{name}' 的资源")
```

#### 4.6.3 请求体中支持名称参数

对于 POST 请求，当原接口需要 ID 参数时，可添加名称参数作为替代：

```python
class QueryIn(Schema):
    """查询请求"""
    config_id: Optional[str] = Field(
        None, 
        description="配置 ID（精确匹配，优先级高于 config_name）"
    )
    config_name: Optional[str] = Field(
        None, 
        description="配置名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
    # ... 其他字段

def _resolve_config_by_name(config_name: str) -> Config:
    """根据名称解析配置"""
    # 优先精确匹配
    config = Config.objects.filter(name=config_name, is_deleted=False).first()
    if config:
        return config
    
    # 模糊匹配
    config = Config.objects.filter(name__icontains=config_name, is_deleted=False).first()
    if config:
        return config
    
    raise HttpError(400, f"未找到名称匹配 '{config_name}' 的配置")

@router.post("/query", response=QueryResult)
def execute_query(request, data: QueryIn):
    # 获取配置（优先使用 config_id，其次使用 config_name）
    if data.config_id:
        config = get_object_or_404(Config, id=data.config_id, is_deleted=False)
    elif data.config_name:
        config = _resolve_config_by_name(data.config_name)
    else:
        raise HttpError(400, "必须提供 config_id 或 config_name 参数")
    # ... 继续处理
```

#### 4.6.4 已实现的按名称查询 API

| 模块 | 端点 | 说明 |
|------|------|------|
| 用户 | `/user/by-name/{name}` | 按姓名查询用户 |
| 用户 | `/user/by-username/{username}` | 按登录名查询用户 |
| 角色 | `/role/by-name/{name}` | 按角色名称查询 |
| 角色 | `/role/by-code/{code}` | 按角色编码查询 |
| 部门 | `/dept/by-name/{name}` | 按部门名称查询 |
| 部门 | `/dept/by-code/{code}` | 按部门编码查询 |
| 岗位 | `/post/by-name/{name}` | 按岗位名称查询 |
| 岗位 | `/post/by-code/{code}` | 按岗位编码查询 |
| 字典 | `/dict/by-name/{name}` | 按字典名称查询 |
| 字典 | `/dict/by-code/{code}` | 按字典编码查询 |
| 问卷 | `/survey/schemas/by-name/{name}` | 按问卷名称查询配置 |
| 表查询 | `/table-query/configs/by-name/{name}` | 按配置名称查询 |

---

## 5. 模型开发

### 5.1 基础模型

所有模型继承自 `RootModel`，提供统一的基础字段：

```python
# common/fu_model.py
import uuid
from django.db import models


class RootModel(models.Model):
    """
    核心模型基类 - 提供统一的基础字段
    """
    
    # 主键（使用 UUID）
    id = models.CharField(
        primary_key=True,
        max_length=36,
        default=uuid.uuid4,
        help_text="主键ID",
        editable=False,
    )
    
    # 创建信息
    sys_creator = models.ForeignKey(
        to='core.User',
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        help_text="创建人，关联 User 模型/表 core_user.id",
        related_name="%(app_label)s_%(class)s_created",
        db_index=True,
    )
    
    sys_create_datetime = models.DateTimeField(
        auto_now_add=True,
        help_text="创建时间",
        db_index=True,
    )
    
    # 修改信息
    sys_modifier = models.ForeignKey(
        to='core.User',
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        help_text="修改人，关联 User 模型/表 core_user.id",
        related_name="%(app_label)s_%(class)s_modified",
    )
    
    sys_update_datetime = models.DateTimeField(
        auto_now=True,
        help_text="更新时间",
        db_index=True,
    )
    
    # 软删除标识
    is_deleted = models.BooleanField(
        default=False,
        help_text="是否删除（软删除标识）",
        db_index=True,
    )
    
    # 排序字段
    sort = models.IntegerField(
        default=0,
        help_text="排序（数字越大越靠前）",
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = ['is_deleted', '-sort', '-sys_create_datetime']
    
    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'sys_update_datetime'])
    
    def restore(self):
        """恢复软删除"""
        self.is_deleted = False
        self.save(update_fields=['is_deleted', 'sys_update_datetime'])
```

### 5.2 业务模型示例

```python
# core/user/user_model.py
from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.hashers import make_password, check_password
from common.fu_model import RootModel


class User(RootModel):
    """
    用户模型 - 系统用户管理
    """
    
    # 用户类型选择
    USER_TYPE_CHOICES = [
        (0, '系统用户'),
        (1, '普通用户'),
        (2, '外部用户'),
    ]
    
    # 用户状态选择
    STATUS_CHOICES = [
        (0, '禁用'),
        (1, '正常'),
        (2, '锁定'),
    ]
    
    # 用户名
    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="用户名",
        error_messages={
            'unique': "该用户名已存在。",
        },
    )
    
    # 密码
    password = models.CharField(
        max_length=128,
        help_text="密码（加密存储）",
    )
    
    # 邮箱
    email = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        help_text="邮箱地址",
        validators=[EmailValidator(message="请输入有效的邮箱地址")],
        db_index=True,
    )
    
    # 手机号
    mobile = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        help_text="手机号码",
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的11位手机号码',
            )
        ],
        db_index=True,
    )
    
    # 用户类型
    user_type = models.IntegerField(
        choices=USER_TYPE_CHOICES,
        default=1,
        help_text="用户类型",
        db_index=True,
    )
    
    # 用户状态
    user_status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=1,
        help_text="用户状态",
        db_index=True,
    )
    
    # 关联的角色
    core_roles = models.ManyToManyField(
        to="core.Role",
        db_constraint=False,
        blank=True,
        help_text="关联的角色，多对多关联 Role 模型/表 core_role，中间表 core_user_core_roles",
        related_name="core_users",
    )
    
    # 关联的部门
    dept = models.ForeignKey(
        to="core.Dept",
        on_delete=models.SET_NULL,
        db_constraint=False,
        null=True,
        blank=True,
        help_text="所属部门，关联 Dept 模型/表 core_dept.id",
        related_name="core_users",
    )
    
    class Meta:
        db_table = "core_user"
        ordering = ("-sys_create_datetime",)
        verbose_name = "用户"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user_status', 'user_type']),
            models.Index(fields=['dept', 'user_status']),
        ]
    
    def __str__(self):
        return f"{self.name or self.username}"
    
    # 辅助方法
    def get_user_type_display_name(self):
        """获取用户类型的显示名称"""
        type_map = dict(self.USER_TYPE_CHOICES)
        return type_map.get(self.user_type, 'UNKNOWN')
    
    def set_password(self, raw_password):
        """设置密码（加密）"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """验证密码"""
        return check_password(raw_password, self.password)
    
    def can_delete(self):
        """判断用户是否可以删除"""
        return self.user_type != 0 and not self.is_superuser
```

### 5.3 字段规范

| 字段类型 | 使用场景 | 示例 |
|----------|----------|------|
| `CharField` | 短文本（有长度限制） | 用户名、手机号 |
| `TextField` | 长文本 | 描述、备注 |
| `IntegerField` | 整数（状态、类型） | 用户状态、用户类型 |
| `BooleanField` | 布尔值 | 是否激活、是否删除 |
| `DateTimeField` | 日期时间 | 创建时间、更新时间 |
| `DateField` | 日期 | 生日 |
| `ForeignKey` | 外键关联 | 部门、上级 |
| `ManyToManyField` | 多对多关联 | 角色、岗位 |
| `EmailField` | 邮箱 | email |
| `GenericIPAddressField` | IP 地址 | 登录 IP |

### 5.4 关联字段描述规范（AI 友好）

为了让 AI 能够从 OpenAPI Schema 中直接理解表之间的关联关系，所有 `ForeignKey` 和 `ManyToManyField` 字段的 `help_text` 必须包含**模型名**和**表名**的上下文信息。

#### 5.4.1 描述格式

| 字段类型 | 格式 | 示例 |
|----------|------|------|
| ForeignKey | `{业务含义}，关联 {模型名} 模型/表 {表名}.{字段}` | `所属部门，关联 Dept 模型/表 core_dept.id` |
| 自引用 ForeignKey | `{业务含义}，自引用 {模型名} 模型/表 {表名}.{字段}` | `直属上级，自引用 User 模型/表 core_user.id` |
| ManyToManyField | `{业务含义}，多对多关联 {模型名} 模型/表 {表名}，中间表 {中间表名}` | `关联的角色，多对多关联 Role 模型/表 core_role，中间表 core_user_core_roles` |

#### 5.4.2 示例代码

```python
# ForeignKey 字段
dept = models.ForeignKey(
    to="core.Dept",
    on_delete=models.SET_NULL,
    db_constraint=False,
    null=True,
    blank=True,
    help_text="所属部门，关联 Dept 模型/表 core_dept.id",  # ✅ 包含模型名和表名
    related_name="core_users",
)

# 自引用 ForeignKey 字段
manager = models.ForeignKey(
    to="self",
    on_delete=models.SET_NULL,
    db_constraint=False,
    null=True,
    blank=True,
    related_name="subordinates",
    help_text="直属上级，自引用 User 模型/表 core_user.id",  # ✅ 自引用说明
)

# ManyToManyField 字段
core_roles = models.ManyToManyField(
    to="core.Role",
    db_constraint=False,
    blank=True,
    help_text="关联的角色，多对多关联 Role 模型/表 core_role，中间表 core_user_core_roles",  # ✅ 包含中间表
    related_name="core_users",
)
```

#### 5.4.3 为什么需要这种格式

1. **AI 理解跨表关联**：AI 可以通过描述中的模型名（如 `Dept`）在 OpenAPI Schema 中找到对应的 Schema 定义（如 `DeptSchemaOut`）
2. **支持 SQL 生成**：AI 可以通过表名（如 `core_dept`）直接生成正确的 JOIN 语句
3. **保持人类可读性**：业务含义在前，技术细节在后，不影响开发者阅读

#### 5.4.4 辅助工具

项目提供了 Django management command 来自动生成字段描述建议：

```bash
# 预览模式（显示所有建议）
python manage.py enhance_field_descriptions --dry-run

# 输出到 JSON 文件
python manage.py enhance_field_descriptions --output suggestions.json

# 仅扫描指定 app
python manage.py enhance_field_descriptions --app-labels core

# JSON 格式输出
python manage.py enhance_field_descriptions --format json
```

---

## 6. Schema 定义

### 6.1 输入 Schema (In)

用于接收请求数据，支持数据验证：

```python
# user_schema.py
from typing import Optional, List
from ninja import ModelSchema, Field, Schema
from pydantic import field_validator

from common.fu_model import exclude_fields
from core.user.user_model import User


class UserSchemaIn(ModelSchema):
    """用户输入模式"""
    dept_id: Optional[str] = Field(None, alias="dept_id", description="所属部门ID（关联 Dept 模型/表 core_dept.id）")
    manager_id: Optional[str] = Field(None, alias="manager_id", description="直属上级ID（自引用 User 模型/表 core_user.id）")
    post: List[str] = Field(default=[], description="岗位ID列表（关联 Post 模型/表 core_post.id）")
    core_roles: List[str] = Field(default=[], description="角色ID列表（关联 Role 模型/表 core_role.id）")
    
    @field_validator('username', check_fields=False)
    @classmethod
    def validate_username(cls, v):
        """验证用户名"""
        if not v:
            raise ValueError('用户名不能为空')
        if len(v) < 3:
            raise ValueError('用户名长度不能少于3个字符')
        if len(v) > 150:
            raise ValueError('用户名长度不能超过150个字符')
        return v
    
    @field_validator('mobile', check_fields=False)
    @classmethod
    def validate_mobile(cls, v):
        """验证手机号"""
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        if v and len(v) != 11:
            raise ValueError('手机号必须为11位')
        return v
    
    class Config:
        model = User
        model_exclude = (
            "password",
            "is_superuser",
            "post",
            "core_roles",
            "dept",
            *exclude_fields,
        )
```

### 6.2 部分更新 Schema (Patch)

用于 PATCH 请求，所有字段可选：

```python
class UserSchemaPatch(Schema):
    """用户部分更新模式（PATCH）"""
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[int] = None
    user_type: Optional[int] = None
    user_status: Optional[int] = None
    dept_id: Optional[str] = Field(None, description="所属部门ID（关联 Dept 模型/表 core_dept.id）")
    post: Optional[List[str]] = Field(None, description="岗位ID列表（关联 Post 模型/表 core_post.id）")
    core_roles: Optional[List[str]] = Field(None, description="角色ID列表（关联 Role 模型/表 core_role.id）")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """验证用户名（PATCH 模式）"""
        if v is not None:
            if not v:
                raise ValueError('用户名不能为空')
            if len(v) < 3:
                raise ValueError('用户名长度不能少于3个字符')
        return v
```

### 6.3 输出 Schema (Out)

用于返回响应数据：

```python
class UserSchemaOut(ModelSchema):
    """用户输出模式"""
    dept_id: Optional[str] = Field(None, alias="dept_id")
    dept_name: Optional[str] = Field(None, alias="dept.name")
    manager_name: Optional[str] = Field(None, alias="manager.name")
    user_type_display: Optional[str] = None
    user_status_display: Optional[str] = None
    role_names: Optional[List[str]] = None
    post_names: Optional[List[str]] = None
    
    class Config:
        model = User
        model_exclude = ("password", )
    
    @staticmethod
    def resolve_user_type_display(obj):
        """解析用户类型显示名称"""
        return obj.get_user_type_display_name()
    
    @staticmethod
    def resolve_role_names(obj):
        """解析角色名称列表"""
        return obj.get_role_names()
```

### 6.4 详情 Schema (Detail)

扩展输出 Schema，包含更多信息：

```python
class UserSchemaDetail(UserSchemaOut):
    """用户详情输出模式（包含更多信息）"""
    role_ids: Optional[List[str]] = None
    post_ids: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    
    @staticmethod
    def resolve_role_ids(obj):
        """解析角色ID列表"""
        return [str(role.id) for role in obj.core_roles.all()]
    
    @staticmethod
    def resolve_permissions(obj):
        """解析用户权限列表"""
        permissions = obj.get_all_permissions()
        return [perm.code for perm in permissions]
```

### 6.5 简化 Schema (Simple)

用于选择器等场景：

```python
class UserSchemaSimple(Schema):
    """用户简单输出（用于选择器）"""
    id: str
    name: Optional[str]
    username: str
    avatar: Optional[str]
    dept_name: Optional[str] = Field(None, alias="dept.name")
```

### 6.6 操作 Schema

批量操作等专用 Schema：

```python
class UserSchemaBatchDeleteIn(Schema):
    """批量删除用户输入"""
    ids: List[str] = Field(..., description="要删除的用户ID列表")


class UserSchemaBatchDeleteOut(Schema):
    """批量删除用户输出"""
    count: int = Field(..., description="删除的记录数")
    failed_ids: List[str] = Field(default=[], description="删除失败的ID列表")


class UserBatchUpdateStatusIn(Schema):
    """批量更新用户状态输入"""
    ids: List[str] = Field(..., description="用户ID列表")
    user_status: int = Field(..., description="用户状态：0-禁用，1-正常，2-锁定")
```

### 6.7 过滤器 Schema

用于列表查询过滤：

```python
from ninja import FilterSchema, Field
from common.fu_schema import FuFilters


class UserFilters(FuFilters):
    """用户过滤器"""
    name: Optional[str] = Field(None, q="name__icontains", alias="name")
    username: Optional[str] = Field(None, q="username__icontains", alias="username")
    user_status: Optional[int] = Field(None, q="user_status", alias="user_status")
    user_type: Optional[int] = Field(None, q="user_type", alias="user_type")
    dept_id: Optional[list] = Field(None, q="dept_id__in", alias="dept_ids[]")
    mobile: Optional[str] = Field(None, q="mobile__icontains", alias="mobile")
```

### 6.8 关联字段 description 规范（AI 友好）

Schema 中的关联字段（如 `dept_id`、`manager_id`）必须在 `description` 中包含关联关系信息，让 AI 能够理解字段的关联目标。

#### 6.8.1 描述格式

| 字段类型 | 格式 | 示例 |
|----------|------|------|
| ForeignKey ID | `{业务含义}（关联 {模型名} 模型/表 {表名}.{字段}）` | `所属部门ID（关联 Dept 模型/表 core_dept.id）` |
| 自引用 ID | `{业务含义}（自引用 {模型名} 模型/表 {表名}.{字段}）` | `直属上级ID（自引用 User 模型/表 core_user.id）` |
| ID 列表 | `{业务含义}（关联 {模型名} 模型/表 {表名}.id）` | `角色ID列表（关联 Role 模型/表 core_role.id）` |

#### 6.8.2 示例代码

```python
class UserSchemaIn(ModelSchema):
    """用户输入模式"""
    # ForeignKey 关联字段
    dept_id: Optional[str] = Field(
        None, 
        alias="dept_id", 
        description="所属部门ID（关联 Dept 模型/表 core_dept.id）"
    )
    
    # 自引用字段
    manager_id: Optional[str] = Field(
        None, 
        alias="manager_id", 
        description="直属上级ID（自引用 User 模型/表 core_user.id）"
    )
    
    # ManyToMany ID 列表
    post: List[str] = Field(
        default=[], 
        description="岗位ID列表（关联 Post 模型/表 core_post.id）"
    )
    
    core_roles: List[str] = Field(
        default=[], 
        description="角色ID列表（关联 Role 模型/表 core_role.id）"
    )
```

#### 6.8.3 Model 与 Schema 描述对照

| 位置 | 属性 | 格式 |
|------|------|------|
| Model (ForeignKey) | `help_text` | `{含义}，关联 {模型} 模型/表 {表}.{字段}` |
| Schema (ID 字段) | `description` | `{含义}（关联 {模型} 模型/表 {表}.{字段}）` |

**关键差异**：
- Model 使用中文逗号 `，` 分隔
- Schema 使用中文括号 `（）` 包裹关联信息

---

## 7. CRUD 操作

### 7.1 通用 CRUD 函数

项目提供了通用的 CRUD 函数：

```python
# common/fu_crud.py
from django.db.models import Model, QuerySet
from django.shortcuts import get_object_or_404
from ninja import Schema


def create(request, data: dict | Schema, model: Type[Model]) -> QuerySet:
    """创建记录"""
    user_info = request.auth
    if not isinstance(data, dict):
        data = data.dict()
    data["sys_creator_id"] = user_info.id
    query_set = model.objects.create(**data)
    return query_set


def delete(id: str, model: Type[Model]) -> Type[Model]:
    """删除记录"""
    instance = get_object_or_404(model, id=id)
    instance.delete()
    return instance


def batch_delete(ids: list[str], model: Type[Model]) -> int:
    """批量删除"""
    count = model.objects.filter(id__in=ids).delete()[0]
    return count


def update(request, id: str, data: dict | Schema, model: Type[Model]) -> Type[Model]:
    """更新记录"""
    if not isinstance(data, dict):
        data = data.dict(exclude_none=True)
    instance = get_object_or_404(model, id=id)
    for attr, value in data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance


def retrieve(request, model: Type[Model], filters: FuFilters = None) -> QuerySet:
    """查询记录列表"""
    query_set = model.objects.all()
    if filters is not None:
        query_set = filters.filter(query_set)
    return query_set
```

### 7.2 API 实现示例

```python
# user_api.py
from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate

from common.fu_crud import create, retrieve, delete
from common.fu_pagination import MyPagination

router = Router()


@router.post("/user", response=UserSchemaOut, summary="创建用户")
def create_user(request, data: UserSchemaIn):
    """创建新用户"""
    # 1. 唯一性检查
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"用户名已存在: {data.username}")
    
    if data.email and User.objects.filter(email=data.email).exists():
        raise HttpError(400, f"邮箱已存在: {data.email}")
    
    # 2. 准备数据
    data_dic = data.dict()
    data_dic["password"] = make_password(DEFAULT_PASSWORD)
    
    # 3. 提取多对多关系字段
    post_ids = data_dic.pop("post", [])
    role_ids = data_dic.pop("core_roles", [])
    
    # 4. 创建记录
    user = create(request, data_dic, User)
    
    # 5. 设置多对多关系
    if post_ids:
        user.post.set(post_ids)
    if role_ids:
        user.core_roles.set(role_ids)
    
    return user


@router.delete("/user/{user_id}", response=UserSchemaOut, summary="删除用户")
def delete_user(request, user_id: str):
    """删除用户"""
    user = get_object_or_404(User, id=user_id)
    
    # 业务规则检查
    if user.id == request.auth.id:
        raise HttpError(400, "不能删除自己")
    
    if not user.can_delete():
        raise HttpError(400, "系统用户或超级管理员不能删除")
    
    instance = delete(user_id, User)
    return instance


@router.put("/user/{user_id}", response=UserSchemaOut, summary="更新用户（完全替换）")
def update_user(request, user_id: str, data: UserSchemaIn):
    """更新用户（PUT - 完全替换）"""
    user = get_object_or_404(User, id=user_id)
    
    # 唯一性检查（排除自身）
    if User.objects.filter(username=data.username).exclude(id=user_id).exists():
        raise HttpError(400, f"用户名已存在: {data.username}")
    
    # 更新字段
    for attr, value in data.dict().items():
        if attr == "core_roles":
            user.core_roles.set(value)
        elif attr == "post":
            user.post.set(value)
        elif attr == "password":
            continue  # 跳过密码
        else:
            if value is not None:
                setattr(user, attr, value)
    
    user.save()
    return user


@router.patch("/user/{user_id}", response=UserSchemaOut, summary="部分更新用户")
def patch_user(request, user_id: str, data: UserSchemaPatch):
    """部分更新用户（PATCH - 只更新提供的字段）"""
    user = get_object_or_404(User, id=user_id)
    
    # 只更新提供的字段
    update_data = data.dict(exclude_unset=True)
    
    for attr, value in update_data.items():
        if attr == "core_roles":
            user.core_roles.set(value)
        elif attr == "post":
            user.post.set(value)
        else:
            setattr(user, attr, value)
    
    user.save()
    return user


@router.get("/user", response=List[UserSchemaOut], summary="获取用户列表（分页）")
@paginate(MyPagination)
def list_user(request, filters: UserFilters = Query(...)):
    """获取用户列表"""
    query_set = retrieve(request, User, filters)
    # 优化查询
    query_set = query_set.select_related('dept', 'manager').prefetch_related('post', 'core_roles')
    return query_set


@router.get("/user/{user_id}", response=UserSchemaDetail, summary="获取用户详情")
def get_user(request, user_id: str):
    """获取用户详情"""
    user = get_object_or_404(
        User.objects.select_related('dept', 'manager').prefetch_related('post', 'core_roles'),
        id=user_id
    )
    return user
```

---

## 8. 认证与权限

### 8.1 JWT 认证

项目使用 JWT 进行认证：

```python
# common/fu_auth.py
from ninja.security import HttpBearer
from ninja.errors import HttpError
import jwt


class BearerAuth(HttpBearer):
    """Bearer Token 认证"""
    
    def authenticate(self, request, token):
        try:
            # 1. 验证 token
            payload = verify_token(token, token_type="access")
            if not payload:
                raise HttpError(401, "令牌无效或已过期")
            
            # 2. 获取用户
            user_id = payload.get('id')
            user = User.objects.get(id=user_id)
            
            # 3. 检查用户状态
            if not user.is_active:
                raise HttpError(403, "用户账户已被禁用")
            
            # 4. 超级管理员直接通过
            if user.is_superuser:
                return user
            
            # 5. 权限校验
            has_permission = self._check_permission(user, request.path, request.method)
            if has_permission:
                return user
            else:
                raise HttpError(403, "无访问权限")
        
        except HttpError:
            raise
        except Exception as e:
            raise HttpError(401, "认证失败")


def create_token(data: dict):
    """创建 access token 和 refresh token"""
    access_token_expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expire = datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token_data = {
        **data,
        "exp": access_token_expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    
    refresh_token_data = {
        "id": data.get("id"),
        "exp": refresh_token_expire,
        "type": "refresh",
    }
    
    access_token = jwt.encode(access_token_data, settings.JWT_ACCESS_SECRET_KEY, algorithm="HS256")
    refresh_token = jwt.encode(refresh_token_data, settings.JWT_REFRESH_SECRET_KEY, algorithm="HS256")
    
    return access_token, refresh_token, timegm(access_token_expire.utctimetuple())
```

### 8.2 免认证接口

某些接口不需要认证：

```python
@router.post("/login", response=LoginOut, auth=None, summary="用户登录")
def login(request, data: LoginIn):
    """用户登录接口（免认证）"""
    pass
```

### 8.3 权限校验

基于 RBAC 模型进行权限控制：

```python
def _check_permission(self, user, path: str, method: str) -> bool:
    """检查用户是否有权限访问指定的 API"""
    # 标准化路径（将 UUID 替换为 :id）
    normalized_path = normalize_api_path(path)
    
    # 获取 HTTP 方法对应的数字
    method_code = HTTP_METHOD_MAP.get(method)  # GET=0, POST=1, PUT=2, DELETE=3, PATCH=4
    
    # 获取用户所有角色的权限
    role_ids = list(user.core_roles.filter(status=True).values_list('id', flat=True))
    
    # 查询权限
    has_permission = Permission.objects.filter(
        roles__id__in=role_ids,
        api_path=normalized_path,
        http_method__in=[method_code, 5],  # 5 表示 ALL
        is_active=True,
    ).exists()
    
    return has_permission
```

---

## 9. 分页与过滤

### 9.1 自定义分页

```python
# common/fu_pagination.py
from ninja import Schema, Field
from ninja.pagination import PaginationBase


class MyPagination(PaginationBase):
    class Input(Schema):
        pageSize: int = Field(10, gt=0)
        page: int = Field(1, gt=-1)

    class Output(Schema):
        items: List[Any]
        total: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        offset = pagination.pageSize * (pagination.page - 1)
        limit = pagination.pageSize
        return {
            "page": offset,
            "limit": limit,
            "items": queryset[offset: offset + limit],
            "total": self._items_count(queryset),
        }
```

### 9.2 使用分页

```python
from ninja.pagination import paginate
from common.fu_pagination import MyPagination


@router.get("/user", response=List[UserSchemaOut])
@paginate(MyPagination)
def list_user(request, filters: UserFilters = Query(...)):
    query_set = retrieve(request, User, filters)
    return query_set
```

### 9.3 过滤器

```python
from ninja import FilterSchema, Field


class FuFilters(FilterSchema):
    """基础过滤器"""
    creator_id: str = Field(None, alias="creator_id")


class UserFilters(FuFilters):
    """用户过滤器"""
    name: Optional[str] = Field(None, q="name__icontains", alias="name")
    username: Optional[str] = Field(None, q="username__icontains", alias="username")
    user_status: Optional[int] = Field(None, q="user_status", alias="user_status")
    dept_id: Optional[list] = Field(None, q="dept_id__in", alias="dept_ids[]")
```

### 9.4 动态查询接口

动态查询接口允许客户端（特别是 AI Agent）灵活地构造查询条件，支持多种操作符。

#### 9.4.1 支持的操作符

| 操作符 | 说明 | 示例值 | SQL 映射 |
|--------|------|--------|----------|
| `eq` | 等于 | `"张三"` | `= '张三'` |
| `ne` | 不等于 | `"张三"` | `!= '张三'` |
| `gt` | 大于 | `18` | `> 18` |
| `gte` | 大于等于 | `18` | `>= 18` |
| `lt` | 小于 | `65` | `< 65` |
| `lte` | 小于等于 | `65` | `<= 65` |
| `like` | 模糊匹配 | `"张"` | `LIKE '%张%'` |
| `in` | 包含 | `[1, 2, 3]` | `IN (1, 2, 3)` |
| `between` | 范围 | `["2024-01-01", "2024-12-31"]` | `BETWEEN` |

#### 9.4.2 通用 Schema 定义

```python
# common/fu_schema.py

# 允许的操作符
ALLOWED_OPERATORS = {
    "eq": "等于",
    "ne": "不等于",
    "gt": "大于",
    "gte": "大于等于",
    "lt": "小于",
    "lte": "小于等于",
    "like": "模糊匹配",
    "in": "包含",
    "between": "范围",
}


class FilterCondition(Schema):
    """通用过滤条件"""
    field: str = Field(..., description="字段名")
    operator: str = Field("eq", description="操作符")
    value: Any = Field(..., description="过滤值")


class DynamicQueryIn(Schema):
    """通用动态查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段")
```

#### 9.4.3 可搜索字段定义

每个模块需要定义可搜索字段列表：

```python
# user_schema.py

USER_SEARCHABLE_FIELDS = [
    {"name": "id", "display_name": "用户ID", "type": "string"},
    {"name": "name", "display_name": "姓名", "type": "string"},
    {"name": "username", "display_name": "用户名", "type": "string"},
    {"name": "email", "display_name": "邮箱", "type": "string"},
    {"name": "user_status", "display_name": "用户状态", "type": "integer"},
    {"name": "sys_create_datetime", "display_name": "创建时间", "type": "datetime"},
]


class UserQueryIn(Schema):
    """用户动态查询请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=1000, description="每页数量")
    filters: Optional[List[FilterCondition]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段")
```

#### 9.4.4 动态查询 API 实现

```python
# user_api.py
from common.fu_crud import dynamic_query, get_searchable_fields_response
from common.fu_schema import DynamicQueryResult, SearchableFieldsResult


@router.post("/user/query", response=DynamicQueryResult, summary="动态查询用户")
def query_user(request, data: UserQueryIn):
    """
    动态查询用户数据
    
    支持灵活的过滤条件和操作符选择。
    """
    base_queryset = User.objects.filter(is_deleted=False).select_related('dept')
    
    items, total = dynamic_query(
        model=User,
        filters=data.filters,
        searchable_fields=USER_SEARCHABLE_FIELDS,
        page=data.page,
        page_size=data.page_size,
        order_by=data.order_by or "-sys_create_datetime",
        base_queryset=base_queryset
    )
    
    result_items = [UserSchemaOut.from_orm(item) for item in items]
    
    return DynamicQueryResult(
        items=result_items,
        total=total,
        page=data.page,
        page_size=data.page_size
    )


@router.get("/user/searchable-fields", response=SearchableFieldsResult, summary="获取可搜索字段")
def get_user_searchable_fields(request):
    """获取用户模块的可搜索字段列表"""
    return get_searchable_fields_response(
        module="user",
        display_name="用户管理",
        searchable_fields=USER_SEARCHABLE_FIELDS
    )
```

#### 9.4.5 请求示例

```json
// POST /api/core/user/query
{
  "page": 1,
  "page_size": 10,
  "filters": [
    {"field": "name", "operator": "like", "value": "张"},
    {"field": "user_status", "operator": "eq", "value": 1},
    {"field": "sys_create_datetime", "operator": "gte", "value": "2024-01-01"}
  ],
  "order_by": "-sys_create_datetime"
}
```

#### 9.4.6 响应格式

```json
{
  "items": [
    {"id": "xxx", "name": "张三", ...}
  ],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

#### 9.4.7 错误处理

当使用不支持的操作符时，会返回清晰的错误提示：

```json
{
  "detail": "不支持的操作符: ==。支持的操作符: eq(等于), ne(不等于), gt(大于), gte(大于等于), lt(小于), lte(小于等于), like(模糊匹配), in(包含), between(范围)"
}
```

#### 9.4.8 AI Agent 调用建议

1. **先获取可搜索字段**：调用 `GET /{module}/searchable-fields` 获取可用的过滤字段
2. **构造查询条件**：根据返回的字段信息构造 `filters` 数组
3. **使用正确的操作符**：字符串字段用 `like`，数值字段用 `eq/gt/lt`，日期字段用 `between`

#### 9.4.9 字段级权限控制

动态查询接口支持字段级权限控制，可以限制敏感字段的访问。

##### 权限控制逻辑

- **权限表中存在字段权限记录，且用户没有该权限** → 字段被隐藏，不可查询
- **权限表中不存在字段权限记录** → 字段对所有人可见
- **用户拥有该权限** → 字段可见可查询

##### 权限编码规范

```
{module}:query:{field_name}
```

示例：
| 权限编码 | 说明 | 保护字段 |
|---------|------|---------|
| `user:query:mobile` | 用户模块查询手机号 | user.mobile |
| `user:query:email` | 用户模块查询邮箱 | user.email |
| `login_log:query:login_ip` | 登录日志查询IP | login_log.login_ip |

##### 行为说明

1. **searchable-fields 接口**：返回的字段列表会根据当前用户权限自动过滤，只显示用户有权访问的字段。

2. **query 接口**：如果用户尝试查询无权限访问的字段，将返回 403 错误：
   ```json
   {
     "detail": "无权限查询字段: mobile。需要权限: user:query:mobile"
   }
   ```

##### 初始化字段权限

使用 management command 初始化默认的字段级权限：

```bash
# 查看将要创建的权限
python manage.py init_field_permissions --list

# 创建字段级权限（会自动分配给管理员角色）
python manage.py init_field_permissions

# 删除字段级权限
python manage.py init_field_permissions --remove
```

##### 添加新的字段权限

要为新字段添加权限控制，有两种方式：

**方式 1：通过权限管理界面**

在前端权限管理页面创建新权限，编码格式为 `{module}:query:{field_name}`。

**方式 2：修改 command 配置**

编辑 `core/management/commands/init_field_permissions.py` 中的 `FIELD_PERMISSIONS` 列表：

```python
FIELD_PERMISSIONS = [
    {
        'name': '查询用户手机号',
        'code': 'user:query:mobile',
        'menu_keyword': '用户',
        'permission_type': 2,  # 数据权限
        'description': '允许在用户动态查询中使用手机号字段',
    },
    # 添加新的字段权限...
]
```

##### 缓存说明

字段权限映射会被缓存 1 小时（`cache:field_permission:{module}`），权限变更后可调用 `invalidate_field_permission_cache(module)` 清除缓存。

---

## 10. 错误处理

### 10.1 HTTP 错误码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| `200` | 成功 | 正常响应 |
| `400` | 错误请求 | 参数验证失败、业务规则违反 |
| `401` | 未授权 | 认证失败、Token 无效 |
| `403` | 禁止访问 | 无权限、账户被禁用 |
| `404` | 未找到 | 资源不存在 |
| `422` | 验证错误 | 数据格式错误 |
| `429` | 请求过多 | 频率限制 |
| `500` | 服务器错误 | 内部错误 |

### 10.2 抛出错误

```python
from ninja.errors import HttpError


@router.post("/user", response=UserSchemaOut)
def create_user(request, data: UserSchemaIn):
    # 业务规则检查
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"用户名已存在: {data.username}")
    
    # 权限检查
    if not request.auth.is_superuser:
        raise HttpError(403, "只有管理员可以创建用户")
    
    # ...
```

### 10.3 标准响应格式

成功响应：

```python
def response_success(data='success'):
    return {"detail": data}
```

错误响应（Django Ninja 自动处理）：

```json
{
  "detail": "错误描述信息"
}
```

---

## 11. 数据验证

### 11.1 Pydantic 验证器

```python
from pydantic import field_validator


class UserSchemaIn(Schema):
    username: str
    mobile: Optional[str] = None
    
    @field_validator('username', check_fields=False)
    @classmethod
    def validate_username(cls, v):
        if not v:
            raise ValueError('用户名不能为空')
        if len(v) < 3:
            raise ValueError('用户名长度不能少于3个字符')
        return v
    
    @field_validator('mobile', check_fields=False)
    @classmethod
    def validate_mobile(cls, v):
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        if v and len(v) != 11:
            raise ValueError('手机号必须为11位')
        return v
```

### 11.2 模型级验证

```python
from django.core.validators import EmailValidator, RegexValidator


class User(models.Model):
    email = models.EmailField(
        validators=[EmailValidator(message="请输入有效的邮箱地址")],
    )
    
    mobile = models.CharField(
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的11位手机号码',
            )
        ],
    )
```

### 11.3 业务逻辑验证

```python
@router.post("/user")
def create_user(request, data: UserSchemaIn):
    # 唯一性验证
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"用户名已存在: {data.username}")
    
    # 关联验证
    if data.dept_id:
        if not Dept.objects.filter(id=data.dept_id).exists():
            raise HttpError(400, "部门不存在")
    
    # 业务规则验证
    if data.user_type == 0 and not request.auth.is_superuser:
        raise HttpError(403, "只有超级管理员可以创建系统用户")
```

---

## 12. 缓存策略

### 12.1 Django 缓存配置

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f'{REDIS_URL}/{REDIS_DB}',
        "TIMEOUT": None,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    },
}
```

### 12.2 缓存使用示例

```python
from django.core.cache import cache


class PermissionCacheManager:
    """权限缓存管理器"""
    
    USER_PERM_KEY = "user_permission:{user_id}:{path}:{method}"
    CACHE_TIMEOUT = 300  # 5分钟
    
    @classmethod
    def get_user_permission(cls, user_id, path, method):
        """获取缓存的权限结果"""
        cache_key = cls.USER_PERM_KEY.format(
            user_id=user_id, path=path, method=method
        )
        return cache.get(cache_key)
    
    @classmethod
    def set_user_permission(cls, user_id, path, method, has_permission):
        """缓存权限结果"""
        cache_key = cls.USER_PERM_KEY.format(
            user_id=user_id, path=path, method=method
        )
        cache.set(cache_key, has_permission, cls.CACHE_TIMEOUT)
    
    @classmethod
    def invalidate_user_permissions(cls, user_id):
        """清除用户的权限缓存"""
        # 使用模式匹配删除
        pattern = f"user_permission:{user_id}:*"
        cache.delete_pattern(pattern)
```

---

## 13. 日志规范

### 13.1 日志配置

```python
# settings.py
import logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s][%(name)s.%(funcName)s():%(lineno)d] [%(levelname)s] %(message)s"
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/server.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/error.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 3,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "error", "file"],
            "level": "INFO",
        },
    },
}
```

### 13.2 日志使用

```python
import logging

logger = logging.getLogger(__name__)


@router.post("/login", auth=None)
def login(request, data: LoginIn):
    try:
        user = authenticate_user(data.username, data.password)
        logger.info(f"用户登录成功: {user.username} from {get_request_ip(request)}")
        return create_token_response(user)
    except ValueError as e:
        logger.warning(f"登录失败: {data.username} - {str(e)}")
        raise HttpError(401, str(e))
    except Exception as e:
        logger.error(f"登录异常: {str(e)}", exc_info=True)
        raise HttpError(500, "内部服务器错误")
```

### 13.3 日志级别

| 级别 | 使用场景 |
|------|----------|
| `DEBUG` | 调试信息（开发环境） |
| `INFO` | 一般操作信息（用户登录、数据创建等） |
| `WARNING` | 警告信息（登录失败、权限拒绝等） |
| `ERROR` | 错误信息（异常、业务错误等） |
| `CRITICAL` | 严重错误（系统级故障） |

---

## 14. 代码风格

### 14.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `user_api.py` |
| 类名 | PascalCase | `UserSchemaOut` |
| 函数名 | snake_case | `create_user` |
| 变量名 | snake_case | `user_info` |
| 常量 | UPPER_SNAKE_CASE | `DEFAULT_PASSWORD` |
| 模型字段 | snake_case | `user_status` |

### 14.2 文档字符串

```python
def create_user(request, data: UserSchemaIn):
    """
    创建新用户
    
    改进点：
    - 检查用户名、邮箱、手机号的唯一性
    - 使用默认密码
    - 分离多对多关系的处理
    
    参数:
        request: Django request 对象
        data: 用户创建数据
    
    返回:
        创建的用户对象
    
    异常:
        HttpError(400): 用户名/邮箱/手机号已存在
    """
    pass
```

### 14.3 代码组织

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User API - 用户管理接口
提供用户的 CRUD 操作和高级功能
"""

# 1. 标准库导入
from typing import List
from datetime import datetime

# 2. Django 相关导入
from django.shortcuts import get_object_or_404
from django.db.models import Q

# 3. 第三方库导入
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate

# 4. 项目内部导入
from common.fu_crud import create, retrieve, delete
from common.fu_pagination import MyPagination
from core.user.user_model import User
from core.user.user_schema import UserSchemaOut, UserSchemaIn

# 5. 路由定义
router = Router()

# 6. API 接口实现
@router.post("/user", response=UserSchemaOut, summary="创建用户")
def create_user(request, data: UserSchemaIn):
    pass
```

### 14.4 查询优化

```python
# 使用 select_related 优化外键查询
users = User.objects.select_related('dept', 'manager')

# 使用 prefetch_related 优化多对多查询
users = User.objects.prefetch_related('post', 'core_roles')

# 组合使用
users = User.objects.select_related('dept', 'manager').prefetch_related('post', 'core_roles')

# 使用 only 限制字段
users = User.objects.only('id', 'username', 'name')

# 使用 defer 排除字段
users = User.objects.defer('password', 'bio')

# 使用 annotate 添加统计字段
from django.db.models import Count
roles = Role.objects.annotate(user_count=Count('core_users', distinct=True))
```

---

## 附录

### A. API 文档

项目自动生成 Swagger/OpenAPI 文档：

- **开发环境**: `http://localhost:8000/api/docs`
- **生产环境**: 根据配置访问

### B. 常用工具函数

```python
# 获取请求IP
from common.utils.request_util import get_request_ip
ip = get_request_ip(request)

# 成功响应
from common.fu_schema import response_success
return response_success("操作成功")

# 获取或返回None
from common.fu_crud import get_or_none
user = get_or_none(User, id=user_id)
```

### C. 相关文档

- [Django 官方文档](https://docs.djangoproject.com/)
- [Django Ninja 文档](https://django-ninja.dev/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [PyJWT 文档](https://pyjwt.readthedocs.io/)

