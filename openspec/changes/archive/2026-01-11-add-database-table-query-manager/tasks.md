# 实施任务清单

## 1. 后端模型与迁移

- [x] 1.1 创建 `core/table_query/` 模块目录结构
- [x] 1.2 实现 `table_query_model.py`（TableQueryConfig、TableQueryLog）
- [x] 1.3 生成并运行数据库迁移：`python manage.py makemigrations core --name table_query`

## 2. 后端 Schema 定义

- [x] 2.1 实现 `table_query_schema.py`
  - `TableQueryConfigSchemaIn` - 配置创建输入
  - `TableQueryConfigSchemaPatch` - 配置更新输入
  - `TableQueryConfigSchemaOut` - 配置输出
  - `TableQueryIn` - 查询请求输入
  - `FilterCondition` - 过滤条件
  - `ExportParams` - 导出参数

## 3. 后端 API 实现

- [x] 3.1 实现 `table_query_api.py`
  - `GET /table-query/configs` - 获取配置列表
  - `GET /table-query/configs/all` - 获取所有配置（不分页）
  - `GET /table-query/configs/{id}` - 获取配置详情
  - `POST /table-query/configs` - 创建配置
  - `PUT /table-query/configs/{id}` - 更新配置
  - `DELETE /table-query/configs/{id}` - 删除配置（软删除）
  - `POST /table-query/query` - 执行动态查询
  - `POST /table-query/export` - 导出数据（Excel/CSV）
  - `GET /table-query/logs` - 获取查询日志
- [x] 3.2 实现安全验证函数
  - `validate_identifier()` - 标识符格式验证
  - `validate_table_name()` - 表名白名单验证
  - `validate_fields()` - 字段白名单验证
  - `validate_order_by()` - 排序字段验证
  - `build_where_clause()` - 安全构建 WHERE 子句
- [x] 3.3 在 `core/router.py` 注册 table_query_router

## 4. 前端 API 封装

- [x] 4.1 创建 `api/core/table-query.ts`
  - `getAllTableQueryConfigsApi()` - 获取所有配置
  - `getTableQueryConfigListApi()` - 获取配置列表（分页）
  - `getTableQueryConfigApi(id)` - 获取配置详情
  - `createTableQueryConfigApi()` - 创建配置
  - `updateTableQueryConfigApi()` - 更新配置
  - `deleteTableQueryConfigApi()` - 删除配置
  - `executeTableQueryApi(params)` - 执行查询
  - `exportTableDataApi(params)` - 导出数据
  - `getTableQueryLogsApi()` - 获取查询日志

## 5. 前端页面开发

- [x] 5.1 创建 `views/table-query/index.vue` 主页面
  - 表选择器（侧边栏菜单）
  - 动态查询表单
  - 数据表格（使用 VxeTable）
  - 导出按钮（支持 Excel/CSV）
- [x] 5.2 创建 `views/table-query/data.ts`
  - `buildColumns()` - 动态生成表格列配置
  - `useSearchFormSchema()` - 动态生成查询表单 Schema
  - `getFieldDisplayNames()` - 获取字段显示名称映射
- [x] 5.3 路由配置（使用动态菜单，无需单独配置静态路由）

## 6. 菜单初始化

- [x] 6.1 创建 management command：`init_table_query_menus`
- [x] 6.2 创建 management command：`create_sample_table_configs` 用于创建示例配置

## 7. 集成与验收

- [x] 7.1 前后端联调
- [x] 7.2 权限配置（RBAC）
- [x] 7.3 功能验收测试

## 8. 实施过程中的额外修改

- [x] 8.1 添加 `quote_identifier()` 函数，使用反引号转义 MySQL 保留关键字
- [x] 8.2 修复 VxeTable 组件适配（使用项目 `useVbenVxeGrid` 适配器）
- [x] 8.3 修复配置 JSON 键名兼容性（同时支持 camelCase 和 snake_case）
- [x] 8.4 添加 `batch_create_table_configs` 管理命令批量创建表配置
- [x] 8.5 为 952 个数据库表创建了查询配置
