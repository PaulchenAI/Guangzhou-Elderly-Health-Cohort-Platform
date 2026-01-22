#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Core Router - 核心模块路由配置
统一管理 core 模块的所有路由
"""
from ninja import Router

from core.auth.auth_api import router as auth_router
from core.user.user_api import router as user_router
from core.role.role_api import router as role_router
from core.permission.permission_api import router as permission_router
from core.dept.dept_api import router as dept_router
from core.post.post_api import router as post_router
from core.menu.menu_api import router as menu_router
from core.dict.dict_api import router as dict_router
from core.dict_item.dict_item_api import router as dict_item_router
from core.login_log.login_log_api import router as login_log_router
from core.server_monitor.server_monitor_api import router as server_monitor_router
from core.redis_monitor.redis_monitor_api import router as redis_monitor_router
from core.redis_manager.redis_manager_api import router as redis_manager_router
from core.database_monitor.database_monitor_api import router as database_monitor_router
from core.database_manager.database_manager_api import router as database_manager_router
from core.file_manager.file_manager_api import router as file_manager_router
from core.oauth.oauth_api import router as oauth_router
from core.table_query.table_query_api import router as table_query_router
from core.survey.survey_api import router as survey_router
from core.foreignkey.foreignkey_api import router as foreignkey_router
from core.doc_api.doc_api import router as doc_api_router


# 创建核心模块的总路由
core_router = Router()

# 注册子路由
# Tags 同时包含英文标识和中文名称，便于 AI 理解和匹配
core_router.add_router("", auth_router, tags=["Core-Auth", "认证管理"])
core_router.add_router("", user_router, tags=["Core-User", "用户管理"])
core_router.add_router("", role_router, tags=["Core-Role", "角色管理"])
core_router.add_router("", permission_router, tags=["Core-Permission", "权限管理"])
core_router.add_router("", dept_router, tags=["Core-Dept", "部门管理"])
core_router.add_router("", post_router, tags=["Core-Post", "岗位管理"])
core_router.add_router("", menu_router, tags=["Core-Menu", "菜单管理"])
core_router.add_router("", dict_router, tags=["Core-Dict", "字典管理"])
core_router.add_router("", dict_item_router, tags=["Core-DictItem", "字典项管理"])
core_router.add_router("", login_log_router, tags=["Core-LoginLog", "登录日志"])
core_router.add_router("", server_monitor_router, tags=["Core-ServerMonitor", "服务器监控"])
core_router.add_router("", redis_monitor_router, tags=["Core-RedisMonitor", "Redis监控"])
core_router.add_router("", redis_manager_router, tags=["Core-RedisManager", "Redis管理"])
core_router.add_router("", database_monitor_router, tags=["Core-DatabaseMonitor", "数据库监控"])
core_router.add_router("", database_manager_router, tags=["Core-DatabaseManager", "数据库管理"])
core_router.add_router("", file_manager_router, tags=["Core-FileManager", "文件管理"])
core_router.add_router("/oauth", oauth_router, tags=["Core-OAuth", "OAuth认证"])
core_router.add_router("", table_query_router, tags=["Core-TableQuery", "表查询管理"])
core_router.add_router("", survey_router, tags=["Core-Survey", "问卷管理"])
core_router.add_router("", foreignkey_router, tags=["Core-ForeignKey", "外键关系元数据"])
core_router.add_router("", doc_api_router, tags=["Core-DocAPI", "文档API查询"])

