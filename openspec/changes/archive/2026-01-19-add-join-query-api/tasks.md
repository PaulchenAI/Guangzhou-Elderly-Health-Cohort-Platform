# 外键联合查询 API 实施任务

## 1. 后端核心实现

- [x] 1.1 创建联合查询 Schema 定义
  - 定义 `JoinQueryIn`、`JoinQueryResult`、`JoinPreviewOut` 等数据结构
  - 文件：`backend-django/core/table_query/table_query_schema.py`

- [x] 1.2 实现关联关系解析器
  - 从 `table_foreignkey_metadata` 递归解析关联关系
  - 支持深度限制和循环检测
  - 文件：`backend-django/core/table_query/join_query_utils.py`

- [x] 1.3 实现 SQL 构建器
  - 动态构建 SELECT 字段列表（带表名前缀）
  - 动态构建 LEFT JOIN 子句
  - 支持 WHERE、ORDER BY、LIMIT
  - 文件：`backend-django/core/table_query/join_query_utils.py`

- [x] 1.4 实现联合查询 API 端点
  - `POST /table-query/join-query` - 执行联合查询
  - `GET /table-query/join-preview/{table_name}` - 预览关联关系
  - 文件：`backend-django/core/table_query/table_query_api.py`

- [x] 1.5 实现联合查询导出功能
  - `POST /table-query/join-export` - 导出联合查询结果
  - 支持 Excel/CSV 格式
  - 文件：`backend-django/core/table_query/table_query_api.py`

## 2. 安全与验证

- [x] 2.1 实现字段白名单验证
  - 验证过滤和排序字段是否在允许的字段列表中
  - 支持带表名前缀的字段名验证

- [x] 2.2 实现 SQL 注入防护
  - 表名和字段名白名单验证
  - 使用参数化查询处理值

## 3. 测试

- [x] 3.1 编写单元测试
  - 关联关系解析测试
  - SQL 构建测试
  - 循环引用检测测试
  - 文件：`backend-django/core/table_query/tests/test_join_query.py`

- [x] 3.2 编写 API 集成测试
  - 联合查询 API 测试（1级、2级、3级关联）
  - 关联预览 API 测试
  - 过滤、排序、分页功能测试
  - 测试结果：16 项测试全部通过

## 4. 文档

- [x] 4.1 更新 API 文档
  - 添加联合查询 API 说明
  - 添加使用示例

## 依赖关系

```
1.1 → 1.2 → 1.3 → 1.4 → 1.5
          ↘
           2.1 → 2.2
                  ↘
                   3.1 → 3.2 → 4.1
```

## 验证标准

- [x] 能够根据主表自动解析外键关联关系
- [x] 支持多级关联查询（最多 5 级）
- [x] 主表数据完整，关联数据可为空
- [x] 字段名冲突自动添加表名前缀
- [x] 分页功能正常工作
- [x] 过滤和排序功能正常工作
- [x] 导出功能正常工作
- [x] 无 SQL 注入风险
