# 任务清单

## 1. 模型定义

- [x] 1.1 创建 `core/foreignkey/__init__.py`
- [x] 1.2 创建 `foreignkey_model.py`，使用 `managed = False` 映射现有 `table_foreignkey_metadata` 表

## 2. Schema 定义

- [x] 2.1 创建 `foreignkey_schema.py`，定义：
  - `ForeignKeyMetadataSchemaOut`：输出 Schema
  - `ForeignKeyMetadataFilters`：过滤器 Schema
  - `ForeignKeyRelationsOut`：表关联关系输出
  - `ForeignKeyStatsOut`：统计信息输出

## 3. API 实现

- [x] 3.1 创建 `foreignkey_api.py`，实现以下端点：
  - `GET /foreignkey/metadata` - 获取外键关系列表（分页）
  - `GET /foreignkey/metadata/all` - 获取所有外键关系
  - `GET /foreignkey/metadata/{id}` - 获取单个外键详情
  - `GET /foreignkey/by-source/{table_name}` - 按源表查询（AI 友好）
  - `GET /foreignkey/by-target/{table_name}` - 按目标表查询（AI 友好）
  - `GET /foreignkey/relations/{table_name}` - 获取表所有关联
  - `GET /foreignkey/stats` - 获取统计信息

## 4. 路由注册

- [x] 4.1 在 `core/router.py` 中注册外键 API 路由

## 5. 验证

- [x] 5.1 启动服务器测试 API 可访问
- [x] 5.2 验证 OpenAPI 文档生成正确
