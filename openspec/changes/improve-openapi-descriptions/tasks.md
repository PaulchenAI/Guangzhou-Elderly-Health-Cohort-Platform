# 任务清单

## 1. 分析与规划

- [x] 1.1 统计所有缺少中文 summary 的 API 端点
- [x] 1.2 按模块分类，确定修改优先级
- [x] 1.3 制定 summary 命名规范文档

## 2. 核心模块修改（AIagent 常用）

- [x] 2.1 修改 `core/survey/survey_api.py`（问卷管理，11 个端点）
  - [x] 2.1.1 List Schemas → 获取问卷配置列表（分页）
  - [x] 2.1.2 List All Schemas → 获取所有问卷配置
  - [x] 2.1.3 Get Schema → 获取问卷配置详情
  - [x] 2.1.4 Get Schema By Type → 根据类型获取问卷配置
  - [x] 2.1.5 List Records → 获取问卷数据列表（分页）
  - [x] 2.1.6 Get Record → 获取问卷数据详情
  - [x] 2.1.7 Query Records → 查询问卷数据
  - [x] 2.1.8 Export Records → 导出问卷数据
  - [x] 2.1.9 List Import Logs → 获取导入日志列表
  - [x] 2.1.10 Get Import Log → 获取导入日志详情
  - [x] 2.1.11 Trigger Sync → 触发问卷数据同步

- [x] 2.2 修改 `core/table_query/table_query_api.py`（表查询管理，9 个端点）

## 3. 基础模块修改

- [x] 3.1 修改 `core/dict/dict_api.py`（字典管理，5 个端点）
  - [x] 3.1.1 Create Dict → 创建字典
  - [x] 3.1.2 Delete Dict → 删除字典
  - [x] 3.1.3 Update Dict → 更新字典
  - [x] 3.1.4 List Dict → 获取字典列表（分页）
  - [x] 3.1.5 List All Dict → 获取所有字典

- [x] 3.2 修改 `core/dict_item/dict_item_api.py`（字典项管理，6 个端点）

## 4. 其他模块修改

- [x] 4.1 修改 `core/database_manager/` 相关端点（已检查，无缺少 summary 的端点）
- [x] 4.2 修改 `core/database_monitor/` 相关端点
- [x] 4.3 修改 `core/redis_manager/` 相关端点
- [x] 4.4 修改 `core/redis_monitor/` 相关端点
- [x] 4.5 修改 `core/server_monitor/` 相关端点
- [x] 4.6 修改 `core/file_manager/` 相关端点
- [x] 4.7 修改 `scheduler/` 相关端点（已检查，无缺少 summary 的端点）

## 5. 验证测试

- [x] 5.1 验证所有 API 模块语法正确
- [x] 5.2 验证所有端点已添加中文 summary
- [x] 5.3 验证 Django 服务可正常启动
- [x] 5.4 验证 OpenAPI Schema 可正常生成

## 6. 文档更新

- [x] 6.1 更新 `docs/backend-api-development-guide.md`
  - [x] 6.1.1 在第 4 节 "API 开发规范" 后新增 "4.5 OpenAPI 描述规范" 小节
  - [x] 6.1.2 添加 summary 命名规范（动词 + 名词格式）
  - [x] 6.1.3 添加 description 结构化格式示例
  - [x] 6.1.4 添加动词标准化映射表（与 7.3 API 命名规范呼应）
  - [x] 6.1.5 更新 4.1 路由定义示例，确保包含 summary 参数
- [x] 6.2 在 design.md 中记录 API 描述约定（代替更新 project.md）

## 依赖关系

- 任务 2、3、4 可并行执行
- 任务 5 依赖任务 2、3、4 完成
- 任务 6 可与任务 5 并行

## 验收标准

- [x] 所有 API 端点 summary 为中文
- [x] OpenAPI 提案验证通过
- [x] Django 服务可正常启动
- [x] API 开发规范文档已更新

## 修改统计

| 模块 | 文件 | 添加 summary 数量 |
|------|------|------------------|
| 问卷管理 | survey_api.py | 11 |
| 表查询管理 | table_query_api.py | 9 |
| 字典管理 | dict_api.py | 5 |
| 字典项管理 | dict_item_api.py | 6 |
| 数据库监控 | database_monitor_api.py | 4 |
| 文件管理 | file_manager_api.py | 16 |
| 分块上传 | chunk_upload_api.py | 5 |
| Redis管理 | redis_manager_api.py | 10 |
| Redis监控 | redis_monitor_api.py | 4 |
| 服务器监控 | server_monitor_api.py | 13 |
| **总计** | | **83** |
