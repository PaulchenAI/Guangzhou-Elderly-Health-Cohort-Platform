# 任务清单：支持手动字段匹配的联合查询

## 1. 扩展 Schema

- [x] 1.1 在 `table_query_schema.py` 中创建 `ManualJoin` Schema
  - `source_field`: 源字段名（主表的字段，必填）
  - `target_table`: 目标表名（必填）
  - `target_field`: 目标字段名（必填）
  - `match_type`: 匹配类型（exact | fuzzy，默认 exact）

- [x] 1.2 在 `JoinQueryIn` Schema 中添加 `manual_joins` 字段
  - 类型：`Optional[List[ManualJoin]]`
  - 描述：手动字段匹配关联列表
  - 默认值：`None`

**验证**：Schema 验证通过，可以正确解析 `manual_joins` 参数

## 2. 扩展联合查询构建器

- [x] 2.1 修改 `JoinQueryBuilder.__init__`，接收 `manual_joins` 参数
  - 参数类型：`Optional[List[Dict[str, Any]]]`
  - 存储为实例变量

- [x] 2.2 实现 `_convert_manual_joins` 方法
  - 将手动关联转换为 `JoinRelation` 对象列表
  - 每个 `JoinRelation` 的 `join_depth` 固定为 1
  - 验证表名和字段名的存在性

- [x] 2.3 实现 `_merge_and_deduplicate` 方法
  - 合并外键关联和手动关联
  - 如果手动关联的目标表已在外键关联中存在，跳过手动关联
  - 返回去重后的关联列表

- [x] 2.4 修改 `build_from_clause` 方法
  - 支持手动关联的 JOIN 条件构建
  - 根据 `match_type` 构建精确匹配或模糊匹配条件
  - 精确匹配：`source_table.source_field = target_table.target_field`
  - 模糊匹配：`source_table.source_field LIKE CONCAT('%', target_table.target_field, '%')`

**验证**：单元测试验证手动关联 SQL 构建正确性，包括精确匹配和模糊匹配

## 3. 更新联合查询解析器

- [x] 3.1 修改 `JoinQueryParser.parse` 方法
  - 接收 `manual_joins` 参数
  - 调用 `_convert_manual_joins` 转换手动关联
  - 调用 `_merge_and_deduplicate` 合并关联

- [x] 3.2 更新 `execute_join_query` 函数（`join_query_utils.py`）
  - 接收 `manual_joins` 参数
  - 传递给 `JoinQueryParser` 和 `JoinSQLBuilder`

**验证**：单元测试验证解析器正确处理手动关联

## 4. 更新联合查询 API

- [x] 4.1 修改 `execute_join_query` API（`table_query_api.py`）
  - 从请求体中提取 `manual_joins` 参数
  - 传递给 `do_join_query` 函数

- [x] 4.2 验证手动关联参数的有效性
  - 检查表名是否存在（使用 `check_table_exists`）
  - 检查字段名是否存在（查询数据库表结构）
  - 检查手动关联表数量（最多5个）
  - 检查总关联表数量（外键关联 + 手动关联，最多10个）

- [x] 4.3 更新 API 文档和示例
  - 在 docstring 中说明 `manual_joins` 参数
  - 添加使用示例

**验证**：API 测试验证手动关联查询功能，包括成功和失败场景

## 5. 更新响应信息

- [x] 5.1 修改 `JoinTableInfo` Schema（如果需要）
  - 添加 `join_type` 字段，标识是外键关联还是手动关联
  - 或者保持现有结构，在 `join_details` 中区分

- [x] 5.2 更新 `join_info` 响应
  - 在 `join_details` 中标记手动关联
  - 确保响应信息准确反映关联方式

**验证**：响应中包含正确的关联信息

## 6. 处理边界情况

- [x] 6.1 检查手动关联的表是否已在外键关联中存在
  - 如果存在，跳过手动关联（外键关联优先）
  - 记录日志说明跳过原因

- [x] 6.2 验证手动关联的字段是否存在
  - 查询数据库表结构
  - 如果字段不存在，返回 400 错误

- [x] 6.3 处理手动关联与外键关联的冲突
  - 同一表只关联一次
  - 外键关联优先

- [x] 6.4 限制手动关联表数量
  - 最多5个手动关联表
  - 总关联表数（外键关联 + 手动关联）最多10个

**验证**：边界情况测试通过，错误信息清晰

## 7. 测试和文档

- [ ] 7.1 编写单元测试
  - 测试 `_convert_manual_joins` 方法
  - 测试 `_merge_and_deduplicate` 方法
  - 测试 `build_from_clause` 中的手动关联 JOIN 条件构建
  - 测试精确匹配和模糊匹配

- [ ] 7.2 编写集成测试
  - 测试问卷调查 + BS_OLDER 手动关联查询
  - 测试外键关联和手动关联同时使用
  - 测试手动关联的过滤和排序

- [ ] 7.3 测试边界情况
  - 表不存在
  - 字段不存在
  - 重复关联
  - 关联表数量超限

- [ ] 7.4 更新 API 文档
  - 说明 `manual_joins` 参数使用方法
  - 添加使用示例
  - 说明精确匹配和模糊匹配的区别
  - 说明性能注意事项

- [ ] 7.5 更新前端文档（如果需要）
  - 说明如何在联合查询页面使用手动关联功能

**验证**：所有测试通过，文档完整清晰

## 8. 前端手动关联支持

- [x] 8.1 扩展联合查询前端类型定义
- [x] 8.2 新增手动关联表单与字段选择器
- [x] 8.3 保存配置时包含手动关联
- [x] 8.4 通过 Web API 验证手动关联请求参数

**验证**：前端可提交 `manual_joins`，后端返回手动关联信息
