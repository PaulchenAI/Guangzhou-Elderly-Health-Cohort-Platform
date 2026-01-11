# 实施任务清单

## 1. 后端模型与迁移

- [ ] 1.1 创建 `core/table_query/` 模块目录结构
- [ ] 1.2 实现 `table_query_model.py`（TableQueryConfig、TableQueryLog）
- [ ] 1.3 生成并运行数据库迁移：`python manage.py makemigrations table_query`

## 2. 后端 Schema 定义

- [ ] 2.1 实现 `table_query_schema.py`
  - `TableQueryConfigSchemaIn` - 配置创建输入
  - `TableQueryConfigSchemaPatch` - 配置更新输入
  - `TableQueryConfigSchemaOut` - 配置输出
  - `TableQueryIn` - 查询请求输入
  - `TableQueryFilters` - 过滤条件
  - `ExportParams` - 导出参数

## 3. 后端 API 实现

- [ ] 3.1 实现 `table_query_api.py`
  - `GET /configs/` - 获取配置列表
  - `GET /configs/{id}` - 获取配置详情
  - `POST /configs/` - 创建配置
  - `PUT /configs/{id}` - 更新配置
  - `DELETE /configs/{id}` - 删除配置（软删除）
  - `POST /query/` - 执行动态查询
  - `POST /export/` - 导出数据（Excel/CSV）
- [ ] 3.2 实现安全验证函数
  - `validate_table_name()` - 表名白名单验证
  - `validate_fields()` - 字段白名单验证
  - `validate_order_by()` - 排序字段验证
  - `build_where_clause()` - 安全构建 WHERE 子句
- [ ] 3.3 在 `core/router.py` 注册 table_query_router

## 4. 前端 API 封装

- [ ] 4.1 创建 `api/table-query/index.ts`
  - `getTableQueryConfigs()` - 获取配置列表
  - `getTableQueryConfig(id)` - 获取配置详情
  - `executeTableQuery(params)` - 执行查询
  - `exportTableData(params)` - 导出数据

## 5. 前端页面开发

- [ ] 5.1 创建 `views/table-query/index.vue` 主页面
  - 表选择器（侧边栏菜单）
  - 动态查询表单
  - 数据表格（使用 VxeTable）
  - 导出按钮
- [ ] 5.2 创建 `views/table-query/data.ts`
  - 动态生成表格列配置
  - 动态生成查询表单 Schema
- [ ] 5.3 配置路由 `router/routes/modules/table-query.ts`

## 6. 菜单初始化

- [ ] 6.1 创建 management command：`init_table_query_menus`
- [ ] 6.2 为已导入的医院表创建初始配置

## 7. 集成与验收

- [ ] 7.1 前后端联调
- [ ] 7.2 权限配置（RBAC）
- [ ] 7.3 功能验收测试
