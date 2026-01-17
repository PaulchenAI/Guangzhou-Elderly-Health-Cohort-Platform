# 设计文档：外键关系元数据 API

## 上下文

### 背景
- 已有 `table_foreignkey_metadata` 表存储了 535 个外键关系
- 表结构包含：源表名、源字段、目标表名、目标字段、约束名、删除规则等
- 该表是通过 Django raw SQL 创建的，不是 Django Model
- 需要提供 RESTful API 支持 AI 查询表之间的关联关系

### 约束
- 数据表已存在，使用 `managed = False` 映射现有表
- API 需要支持 AI 友好的按表名查询（模糊匹配）
- 遵循项目的 API 开发规范

## 目标 / 非目标

### 目标
- 提供完整的外键关系查询 API
- 支持 AI 通过表名查询关联关系
- 提供统计信息接口

### 非目标
- 不提供外键关系的增删改操作（数据来源于导入）
- 不验证外键数据完整性

## 决策

### 决策 1：Model 设计

**选择**：使用 `managed = False` 映射现有表

```python
class ForeignKeyMetadata(models.Model):
    """外键关系元数据模型（映射现有表）"""
    id = models.AutoField(primary_key=True)
    source_table = models.CharField(max_length=128)
    source_columns = models.JSONField()
    target_table = models.CharField(max_length=128)
    target_columns = models.JSONField()
    constraint_name = models.CharField(max_length=128, null=True)
    on_delete = models.CharField(max_length=20, null=True)
    source_file = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'table_foreignkey_metadata'
```

**理由**：
- 表已通过 raw SQL 创建并有数据
- `managed = False` 避免 Django 迁移干扰现有表
- 使用 Django ORM 简化查询

### 决策 2：API 设计

**选择**：遵循项目 API 规范，提供 AI 友好的端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/foreignkey/metadata` | GET | 外键列表（分页） |
| `/foreignkey/metadata/all` | GET | 所有外键（不分页） |
| `/foreignkey/metadata/{id}` | GET | 单个外键详情 |
| `/foreignkey/by-source/{table_name}` | GET | 按源表查询（模糊匹配） |
| `/foreignkey/by-target/{table_name}` | GET | 按目标表查询（模糊匹配） |
| `/foreignkey/relations/{table_name}` | GET | 表的所有关联（出+入） |
| `/foreignkey/stats` | GET | 统计信息 |

### 决策 3：AI 友好设计

**选择**：表名查询支持精确匹配和模糊匹配

```python
def get_by_source_table(request, table_name: str):
    """
    查询逻辑:
    1. 优先精确匹配 source_table
    2. 如果无结果，尝试模糊匹配（包含关键字）
    3. 支持带前缀和不带前缀的表名
    """
    # 尝试精确匹配
    results = ForeignKeyMetadata.objects.filter(source_table=table_name)
    if results.exists():
        return list(results)
    
    # 尝试带前缀匹配
    results = ForeignKeyMetadata.objects.filter(source_table__iendswith=table_name)
    if results.exists():
        return list(results)
    
    # 模糊匹配
    results = ForeignKeyMetadata.objects.filter(source_table__icontains=table_name)
    return list(results)
```

**理由**：
- AI 提取的表名可能不带前缀
- 用户可能只记得表名的一部分
- 提高 API 的容错性

## 响应示例

### 按源表查询
```json
{
  "table_name": "gzlry_BS_STAFF",
  "outgoing_relations": [
    {
      "id": 1,
      "source_table": "gzlry_BS_STAFF",
      "source_columns": ["DEPT_ID"],
      "target_table": "gzlry_BS_DEPARTMENT",
      "target_columns": ["ID"],
      "constraint_name": "gzlry_FK_STAFF_DEPT",
      "on_delete": "SET NULL"
    }
  ],
  "count": 1
}
```

### 表关联关系
```json
{
  "table_name": "gzlry_BS_DEPARTMENT",
  "outgoing": [
    {
      "target_table": "gzlry_BS_ORGANIZATION",
      "columns": "ORG_ID -> ID"
    }
  ],
  "incoming": [
    {
      "source_table": "gzlry_BS_STAFF",
      "columns": "DEPT_ID -> ID"
    },
    {
      "source_table": "gzlry_BS_DEPARTMENT",
      "columns": "PARENT_ID -> ID"
    }
  ],
  "outgoing_count": 1,
  "incoming_count": 2
}
```

### 统计信息
```json
{
  "total_foreignkeys": 535,
  "tables_with_foreignkeys": 281,
  "unique_source_tables": 281,
  "unique_target_tables": 156
}
```

## 文件结构

```
backend-django/core/foreignkey/
├── __init__.py
├── foreignkey_api.py      # API 接口定义
├── foreignkey_model.py    # 数据模型
└── foreignkey_schema.py   # Schema 定义
```
