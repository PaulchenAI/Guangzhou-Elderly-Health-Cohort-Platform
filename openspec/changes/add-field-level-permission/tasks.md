# 实施任务清单

## 1. 基础设施

- [ ] 1.1 在 `common/fu_crud.py` 中添加 `get_field_permissions` 函数（查询权限表）
- [ ] 1.2 在 `common/fu_crud.py` 中添加 `filter_searchable_fields_by_permission` 函数
- [ ] 1.3 在 `common/fu_crud.py` 中添加 `validate_query_field_permissions` 函数
- [ ] 1.4 添加字段权限缓存逻辑

## 2. 模块适配

- [ ] 2.1 修改 user 模块的 `get_user_searchable_fields` 和 `query_user` 接口
- [ ] 2.2 修改 role 模块的动态查询接口
- [ ] 2.3 修改 dept 模块的动态查询接口
- [ ] 2.4 修改 post 模块的动态查询接口
- [ ] 2.5 修改 dict 模块的动态查询接口
- [ ] 2.6 修改 dict_item 模块的动态查询接口
- [ ] 2.7 修改 menu 模块的动态查询接口
- [ ] 2.8 修改 permission 模块的动态查询接口
- [ ] 2.9 修改 login_log 模块的动态查询接口
- [ ] 2.10 修改 file_manager 模块的动态查询接口

## 3. 权限数据初始化

- [ ] 3.1 创建迁移脚本添加 `user:query:mobile` 权限记录
- [ ] 3.2 创建迁移脚本添加 `user:query:email` 权限记录
- [ ] 3.3 创建迁移脚本添加 `login_log:query:login_ip` 权限记录
- [ ] 3.4 为管理员角色分配新增权限

## 4. 验证和文档

- [ ] 4.1 编写单元测试验证权限过滤逻辑
- [ ] 4.2 编写集成测试验证端到端权限控制
- [ ] 4.3 更新 `docs/backend-api-development-guide.md` 添加字段权限说明
