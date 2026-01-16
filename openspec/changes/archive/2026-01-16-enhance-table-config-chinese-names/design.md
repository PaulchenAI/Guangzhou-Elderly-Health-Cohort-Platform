## 上下文

当前 `batch_create_table_configs` 命令通过 `_generate_display_name` 方法生成表的中文显示名称，仅基于表名本身。字段的 `displayName` 直接使用字段名，没有中文名称。

数据库表通常包含 COMMENT 信息，这些注释通常包含中文名称。对于没有 COMMENT 的表，需要通过外部配置文件提供映射。

## 目标 / 非目标

### 目标
- 优先使用数据库表 COMMENT 作为表的中文名称
- 优先使用数据库字段 COMMENT 作为字段的中文显示名称
- 支持通过 JSON 配置文件提供表名和字段名的中文映射
- 保持向后兼容，配置文件不存在时使用现有逻辑

### 非目标
- 不修改数据库表结构
- 不强制要求配置文件存在
- 不修改现有配置的存储格式

## 决策

### 1. 获取数据库 COMMENT 的方式

**决策**：使用 MySQL 的 `INFORMATION_SCHEMA` 查询获取表和字段的注释

**理由**：
- `DESCRIBE` 命令不包含 COMMENT 信息
- `SHOW FULL COLUMNS` 包含 COMMENT，但需要逐表查询
- `INFORMATION_SCHEMA.COLUMNS` 和 `INFORMATION_SCHEMA.TABLES` 可以一次性获取所有信息，性能更好

**SQL 查询示例**：
```sql
-- 获取表注释
SELECT TABLE_COMMENT 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'table_name';

-- 获取字段注释
SELECT COLUMN_NAME, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'table_name';
```

### 2. 配置文件格式

**决策**：使用 JSON 格式，结构如下：

```json
{
  "tables": {
    "WORKFLOW_TASK": "工作流任务",
    "BS_DEPARTMENT": "基础数据-部门"
  },
  "fields": {
    "WORKFLOW_TASK": {
      "TASK_ID": "任务ID",
      "TASK_NAME": "任务名称",
      "STATUS": "状态"
    },
    "BS_DEPARTMENT": {
      "DEPT_ID": "部门ID",
      "DEPT_NAME": "部门名称"
    }
  }
}
```

**理由**：
- JSON 格式易于编辑和维护
- 支持表级和字段级映射
- 结构清晰，易于扩展

### 3. 优先级策略

**决策**：按以下优先级获取中文名称

1. **表名**：数据库表 COMMENT > JSON 配置文件 > 表名
2. **字段名**：数据库字段 COMMENT > JSON 配置文件 > 字段名

**理由**：
- 数据库 COMMENT 是最权威的来源
- 配置文件提供灵活性，适合没有 COMMENT 的情况
- 移除硬编码的前缀映射，简化逻辑，统一使用配置文件管理映射关系

### 4. 配置文件位置

**决策**：默认使用 `backend-django/core/management/commands/table_name_mapping.json`，支持通过 `--config-file` 参数指定

**理由**：
- 默认位置便于管理
- 支持自定义路径提供灵活性

## 风险 / 权衡

### 风险
1. **性能影响**：查询 `INFORMATION_SCHEMA` 可能比 `DESCRIBE` 稍慢
   - **缓解**：批量查询，减少数据库往返次数

2. **配置文件格式错误**：可能导致命令失败
   - **缓解**：添加异常处理，格式错误时降级到默认逻辑

3. **COMMENT 编码问题**：数据库 COMMENT 可能包含特殊字符
   - **缓解**：确保使用 UTF-8 编码处理

### 权衡
- **简单性 vs 功能**：选择支持多种数据源，增加了一些复杂度，但提供了更好的灵活性
- **性能 vs 准确性**：使用 `INFORMATION_SCHEMA` 查询可能稍慢，但能获取完整的 COMMENT 信息

## 迁移计划

1. **向后兼容**：现有命令参数和行为保持不变
2. **渐进式采用**：配置文件是可选的，不强制使用
3. **数据迁移**：对于已存在的配置，可以通过 `--update` 参数重新生成，获取新的中文名称

## 待决问题

- 是否需要支持配置文件的热重载？
  - **决定**：不需要，配置文件在命令启动时读取一次即可
