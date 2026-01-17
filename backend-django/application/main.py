# -*- coding: utf-8 -*-
# @Time    : 2022/5/9 23:15
# @Author  : 臧成龙
# @FileName: api.py
# @Software: PyCharm
from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja.main import NinjaAPI
from ninja.renderers import JSONRenderer
from ninja.responses import NinjaJSONEncoder

from common.fu_auth import BearerAuth, ApiKey
from core.router import core_router
from scheduler.router import scheduler_router


class MyJsonEncoder(NinjaJSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(o)


class MyJsonRenderer(JSONRenderer):
    encoder_class = MyJsonEncoder


# 使用本地静态文件的 Swagger UI
# 静态文件位置: static/swagger-ui/
# 模板文件位置: templates/ninja/swagger.html

# OpenAPI Tags 描述 - 帮助 AI 理解各模块功能和 API 之间的关系
# 注：Django Ninja 1.x 不直接支持 openapi_tags 参数，通过自定义 schema 添加
OPENAPI_TAGS = [
    {
        "name": "问卷管理",
        "description": "问卷数据管理模块。调用流程: GET /survey/schemas → POST /survey/query → POST /survey/export"
    },
    {
        "name": "表查询管理",
        "description": "动态表查询模块。调用流程: GET /table-query/configs → POST /table-query/query → POST /table-query/export"
    },
    {
        "name": "字典管理",
        "description": "系统字典数据管理，维护下拉选项、状态码等枚举数据。"
    },
    {
        "name": "字典项管理",
        "description": "字典项数据管理，管理字典下的具体选项值。通过 dict_id 关联字典。"
    },
    {
        "name": "文件管理",
        "description": "文件上传下载模块。分块上传顺序: POST /chunk/init → POST /chunk/upload(循环) → POST /chunk/merge"
    },
    {
        "name": "Redis管理",
        "description": "Redis 键值管理，提供 CRUD 操作。需指定 db_index(0-15)。"
    },
    {
        "name": "Redis监控",
        "description": "Redis 服务器监控，获取运行状态和性能指标。"
    },
    {
        "name": "数据库监控",
        "description": "数据库服务器监控，获取 MySQL 等数据库运行状态。"
    },
    {
        "name": "服务器监控",
        "description": "服务器硬件监控，获取 CPU、内存、磁盘、网络等系统信息。"
    },
]


class CustomNinjaAPI(NinjaAPI):
    """自定义 NinjaAPI，添加 OpenAPI tags description"""
    
    def get_openapi_schema(self, *args, **kwargs):
        schema = super().get_openapi_schema(*args, **kwargs)
        # 添加 tags description
        schema["tags"] = OPENAPI_TAGS
        return schema


api = CustomNinjaAPI(
    auth=[BearerAuth(), ApiKey()], 
    renderer=MyJsonRenderer(),
)


# @api.exception_handler(DjangoValidationError)
# def service_unavailable(request, exc):
#     return api.create_response(
#         request,
#         {"detail": exc.messages},
#         status=422,
#     )


api.add_router('/core', core_router)
api.add_router('/scheduler', scheduler_router)
