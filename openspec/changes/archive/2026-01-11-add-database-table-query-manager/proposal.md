# 变更：添加数据库表查询管理系统

## 为什么

我们已经成功完成了从 Oracle 到 MySQL 的数据导入工作（docs/hospital/convertsql），导入了大量医院业务数据表。现在需要一个灵活的数据库表查询管理系统，让用户能够通过配置化的方式查询和展示这些导入的数据，而不需要为每个表单独编写代码。

这个系统将提供：
- 通过 JSON 配置定义表的查询条件和显示字段
- 统一的后端 API 支持分页查询
- 前端页面支持表单切换和数据展示
- 菜单系统自动初始化

## 变更内容

- 新增数据库表查询配置管理功能（JSON 配置）
- 新增通用查询 API，支持根据配置动态查询数据库表
- 新增前端表查询页面，支持多表切换和数据展示
- 新增菜单初始化脚本，自动生成表查询菜单

## 影响

- 受影响规范：新增 `database-table-query` 功能规范
- 受影响代码：
  - 后端：新增 `core/table_query/` 模块
    - `table_query_api.py` - API 接口（Django Ninja Router）
    - `table_query_model.py` - 数据模型（TableQueryConfig、TableQueryLog）
    - `table_query_schema.py` - Pydantic Schema
  - 前端：新增 `views/table-query/` 页面
    - `index.vue` - 主页面
    - `data.ts` - 表单/表格配置
    - `api/table-query/index.ts` - API 封装
  - 数据库：新增 `table_query_config`、`table_query_log` 表
  - 菜单：通过 management command 初始化表查询菜单

详见 `design.md` 技术设计文档。

