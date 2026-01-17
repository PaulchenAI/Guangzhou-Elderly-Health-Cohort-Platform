# 变更：为外键关系元数据添加后台 API

## 为什么

已有的外键关系元数据导入功能通过 Django management command 将 535 个外键关系导入到了 `table_foreignkey_metadata` 表中。但目前缺少后台 API 接口来查询这些外键关系，AI 和前端无法通过 API 获取表之间的关联关系。

关键需求：
1. AI 需要通过 API 查询某个表的所有外键关系（出向引用）
2. AI 需要通过 API 查询某个表被哪些表引用（入向引用）
3. 支持按表名模糊匹配查询（AI 友好）
4. 提供统计信息（总外键数、有外键的表数等）

## 变更内容

- 新增外键关系元数据 API 模块 `core/foreignkey/`
  - `foreignkey_api.py` - API 接口定义
  - `foreignkey_model.py` - 数据模型（映射现有表）
  - `foreignkey_schema.py` - Schema 定义
- 新增 API 端点：
  - `GET /foreignkey/metadata` - 获取外键关系列表（分页）
  - `GET /foreignkey/metadata/all` - 获取所有外键关系
  - `GET /foreignkey/metadata/{id}` - 获取单个外键关系详情
  - `GET /foreignkey/by-source/{table_name}` - 按源表名查询外键（支持模糊匹配）
  - `GET /foreignkey/by-target/{table_name}` - 按目标表名查询被引用关系（支持模糊匹配）
  - `GET /foreignkey/relations/{table_name}` - 获取表的所有关联关系（出向+入向）
  - `GET /foreignkey/stats` - 获取外键统计信息

## 影响

- 受影响规范：foreignkey-api（新增）
- 受影响代码：
  - `backend-django/core/foreignkey/` - 新增模块
  - `backend-django/core/router.py` - 注册新路由
