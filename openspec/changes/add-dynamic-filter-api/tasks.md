# 实施任务清单

## 1. 基础设施

- [x] 1.1 在 `common/fu_schema.py` 中添加 `ALLOWED_OPERATORS` 常量和 `FilterCondition` Schema
- [x] 1.2 在 `common/fu_crud.py` 中添加 `dynamic_query` 通用查询函数
- [x] 1.3 添加通用的操作符验证函数，返回清晰的错误提示

## 2. 用户模块 (user)

- [x] 2.1 在 `user_schema.py` 中定义 `UserSearchableFields` 和 `UserQueryIn` Schema
- [x] 2.2 在 `user_api.py` 中添加 `POST /user/query` 动态查询接口
- [x] 2.3 在 `user_api.py` 中添加 `GET /user/searchable-fields` 可搜索字段接口

## 3. 角色模块 (role)

- [x] 3.1 在 `role_schema.py` 中定义 `RoleSearchableFields` 和 `RoleQueryIn` Schema
- [x] 3.2 在 `role_api.py` 中添加 `POST /role/query` 动态查询接口
- [x] 3.3 在 `role_api.py` 中添加 `GET /role/searchable-fields` 可搜索字段接口

## 4. 部门模块 (dept)

- [x] 4.1 在 `dept_schema.py` 中定义 `DeptSearchableFields` 和 `DeptQueryIn` Schema
- [x] 4.2 在 `dept_api.py` 中添加 `POST /dept/query` 动态查询接口
- [x] 4.3 在 `dept_api.py` 中添加 `GET /dept/searchable-fields` 可搜索字段接口

## 5. 岗位模块 (post)

- [x] 5.1 在 `post_schema.py` 中定义 `PostSearchableFields` 和 `PostQueryIn` Schema
- [x] 5.2 在 `post_api.py` 中添加 `POST /post/query` 动态查询接口
- [x] 5.3 在 `post_api.py` 中添加 `GET /post/searchable-fields` 可搜索字段接口

## 6. 字典模块 (dict)

- [x] 6.1 在 `dict_schema.py` 中定义 `DictSearchableFields` 和 `DictQueryIn` Schema
- [x] 6.2 在 `dict_api.py` 中添加 `POST /dict/query` 动态查询接口
- [x] 6.3 在 `dict_api.py` 中添加 `GET /dict/searchable-fields` 可搜索字段接口

## 7. 字典项模块 (dict_item)

- [x] 7.1 在 `dict_item_schema.py` 中定义 `DictItemSearchableFields` 和 `DictItemQueryIn` Schema
- [x] 7.2 在 `dict_item_api.py` 中添加 `POST /dict-item/query` 动态查询接口
- [x] 7.3 在 `dict_item_api.py` 中添加 `GET /dict-item/searchable-fields` 可搜索字段接口

## 8. 菜单模块 (menu)

- [x] 8.1 在 `menu_schema.py` 中定义 `MenuSearchableFields` 和 `MenuQueryIn` Schema
- [x] 8.2 在 `menu_api.py` 中添加 `POST /menu/query` 动态查询接口
- [x] 8.3 在 `menu_api.py` 中添加 `GET /menu/searchable-fields` 可搜索字段接口

## 9. 权限模块 (permission)

- [x] 9.1 在 `permission_schema.py` 中定义 `PermissionSearchableFields` 和 `PermissionQueryIn` Schema
- [x] 9.2 在 `permission_api.py` 中添加 `POST /permission/query` 动态查询接口
- [x] 9.3 在 `permission_api.py` 中添加 `GET /permission/searchable-fields` 可搜索字段接口

## 10. 登录日志模块 (login_log)

- [x] 10.1 在 `login_log_schema.py` 中定义 `LoginLogSearchableFields` 和 `LoginLogQueryIn` Schema
- [x] 10.2 在 `login_log_api.py` 中添加 `POST /login-log/query` 动态查询接口
- [x] 10.3 在 `login_log_api.py` 中添加 `GET /login-log/searchable-fields` 可搜索字段接口

## 11. 文件管理模块 (file_manager)

- [x] 11.1 在 `file_manager_schema.py` 中定义 `FileManagerSearchableFields` 和 `FileManagerQueryIn` Schema
- [x] 11.2 在 `file_manager_api.py` 中添加 `POST /file/query` 动态查询接口
- [x] 11.3 在 `file_manager_api.py` 中添加 `GET /file/searchable-fields` 可搜索字段接口

## 12. 验证和文档

- [x] 12.1 Django 项目检查通过 (`python manage.py check`)
- [x] 12.2 更新 `docs/backend-api-development-guide.md` 添加动态查询接口开发指南
- [x] 12.3 更新 API 文档（OpenAPI/Swagger）- 由 Django Ninja 自动生成
- [x] 12.4 端到端测试验证所有新增接口
