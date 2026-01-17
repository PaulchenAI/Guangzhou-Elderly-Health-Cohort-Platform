# 设计文档：外键关系元数据导入

## 上下文

### 背景
- 已有 955 个 JSON 文件存储了从 Oracle SQL 提取的外键信息
- 281 个表包含外键，共 535 个外键约束关系
- JSON 中的表名无前缀，数据库表名有 `gzlry_` 前缀
- 需要将这些关系信息存储到数据库中，便于查询

### 约束
- 只存储元数据，不创建实际的外键约束
- 表名需要统一添加前缀

## 目标 / 非目标

### 目标
- 创建元数据表存储外键关系信息
- 自动化批量导入
- 正确处理表名前缀

### 非目标
- 不在数据库表上创建实际的外键约束（`ALTER TABLE ADD CONSTRAINT`）
- 不验证外键数据完整性

## 决策

### 决策 1：元数据表结构

**选择**：创建独立的元数据表存储外键关系

```sql
CREATE TABLE IF NOT EXISTS table_foreignkey_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(128) NOT NULL COMMENT '源表名（带前缀）',
    source_columns JSON NOT NULL COMMENT '源字段列表',
    target_table VARCHAR(128) NOT NULL COMMENT '目标表名（带前缀）',
    target_columns JSON NOT NULL COMMENT '目标字段列表',
    constraint_name VARCHAR(128) COMMENT '约束名（带前缀）',
    on_delete VARCHAR(20) COMMENT '删除规则：cascade/set_null/restrict/no_action',
    source_file VARCHAR(255) COMMENT '来源 JSON 文件名',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source_table (source_table),
    INDEX idx_target_table (target_table)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='外键关系元数据表';
```

### 决策 2：表名前缀处理

**选择**：在导入时统一添加前缀

```python
def add_prefix(name: str, prefix: str) -> str:
    return f"{prefix}{name}"

# 示例：
# source_table: "BS_DEPARTMENT" -> "gzlry_BS_DEPARTMENT"
# target_table: "BS_DEPARTMENT" -> "gzlry_BS_DEPARTMENT"  
# constraint_name: "FK_STAFF_DEPT" -> "gzlry_FK_STAFF_DEPT"
```

### 决策 3：数据格式

**选择**：字段列表使用 JSON 格式存储

**理由**：
- 支持复合外键（多个字段）
- 便于查询和展示
- MySQL 5.7+ 原生支持 JSON 类型

## 导入流程

```
1. 读取 JSON 文件目录下所有 *_foreignkeys.json 文件
2. 解析每个文件的 foreign_keys 数组
3. 跳过 foreign_keys 为空的文件
4. 对每个外键关系：
   - 添加表名前缀
   - 添加约束名前缀
   - 插入到 table_foreignkey_metadata 表
5. 输出统计报告
```

## 使用方法

```bash
# 进入 backend-django 目录并激活虚拟环境
cd backend-django
source venv/bin/activate

# 预览模式
python manage.py import_foreignkey_metadata --dry-run

# 导入外键元数据
python manage.py import_foreignkey_metadata

# 指定表名前缀
python manage.py import_foreignkey_metadata --prefix custom_

# 清空后重新导入
python manage.py import_foreignkey_metadata --truncate
```

## 查询示例

```sql
-- 查询某个表的所有外键关系（作为源表）
SELECT * FROM table_foreignkey_metadata 
WHERE source_table = 'gzlry_BS_STAFF';

-- 查询某个表被哪些表引用（作为目标表）
SELECT * FROM table_foreignkey_metadata 
WHERE target_table = 'gzlry_BS_DEPARTMENT';

-- 统计外键数量
SELECT COUNT(*) as total_fks FROM table_foreignkey_metadata;
```
