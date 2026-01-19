# 实施任务清单

## 1. 基础设施

- [ ] 1.1 在 `common/fu_crud.py` 中添加 `filter_searchable_fields_by_permission` 函数
- [ ] 1.2 在 `common/fu_crud.py` 中添加 `validate_query_field_permissions` 函数
- [ ] 1.3 修改 `get_searchable_fields_response` 函数支持权限过滤
- [ ] 1.4 在 `common/fu_schema.py` 中更新 `SearchableFieldInfo` Schema 添加 `permission` 字段

## 2. 用户模块 (user)

- [ ] 2.1 为 `USER_SEARCHABLE_FIELDS` 中的敏感字段添加权限配置
- [ ] 2.2 修改 `query_user` 接口传入用户权限并验证
- [ ] 2.3 修改 `get_user_searchable_fields` 接口传入用户权限进行过滤

## 3. 登录日志模块 (login_log)

- [ ] 3.1 为 `LOGIN_LOG_SEARCHABLE_FIELDS` 中的 IP 字段添加权限配置
- [ ] 3.2 修改 `query_login_log` 接口传入用户权限并验证
- [ ] 3.3 修改 `get_login_log_searchable_fields` 接口传入用户权限进行过滤

## 4. 其他模块适配

- [ ] 4.1 修改 role 模块接口支持权限传递
- [ ] 4.2 修改 dept 模块接口支持权限传递
- [ ] 4.3 修改 post 模块接口支持权限传递
- [ ] 4.4 修改 dict 模块接口支持权限传递
- [ ] 4.5 修改 dict_item 模块接口支持权限传递
- [ ] 4.6 修改 menu 模块接口支持权限传递
- [ ] 4.7 修改 permission 模块接口支持权限传递
- [ ] 4.8 修改 file_manager 模块接口支持权限传递

## 5. 权限数据初始化

- [ ] 5.1 在权限表中添加 `user:view_sensitive` 权限记录
- [ ] 5.2 在权限表中添加 `login_log:view_ip` 权限记录
- [ ] 5.3 为管理员角色分配新增权限

## 6. 验证和文档

- [ ] 6.1 编写单元测试验证权限过滤逻辑
- [ ] 6.2 编写集成测试验证端到端权限控制
- [ ] 6.3 更新 `docs/backend-api-development-guide.md` 添加字段权限说明
