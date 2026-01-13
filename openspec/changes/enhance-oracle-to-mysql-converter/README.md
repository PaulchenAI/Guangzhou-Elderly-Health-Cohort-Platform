# OpenSpec 变更提案创建完成

## 提案概述

**变更ID**: `enhance-oracle-to-mysql-converter`

**目的**: 增强 Oracle 到 MySQL 转换工具，解决三个关键问题：
1. 保留 COMMENT 注释信息
2. 支持 SQL 表名前缀
3. 集成自动化修复流程

## 提案状态

✅ **验证通过** - 已通过 `openspec-cn validate --strict` 严格验证

## 文件结构

```
openspec/changes/enhance-oracle-to-mysql-converter/
├── proposal.md          # 变更提案（为什么、变更内容、影响）
├── design.md            # 技术设计（架构决策、实现细节、风险评估）
├── tasks.md             # 实施任务清单（7个阶段，42个子任务）
└── specs/
    └── sql-import/
        └── spec.md      # 规范增量（3个新增需求，1个修改需求）
```

## 核心变更

### 1. COMMENT 转换功能

**问题**: Oracle 的表注释和列注释在转换时被完全忽略

**解决方案**:
- 第一遍扫描：收集所有 `COMMENT ON TABLE` 和 `COMMENT ON COLUMN` 语句
- 第二遍转换：在 CREATE TABLE 中注入列注释和表注释

**示例**:
```sql
-- Oracle 原始
COMMENT ON TABLE BS_AREA IS '院区表';
COMMENT ON COLUMN BS_AREA.mainid IS '主键ID';

-- MySQL 转换结果
CREATE TABLE BS_AREA (
  mainid VARCHAR(50) NOT NULL COMMENT '主键ID',
  ...
) ENGINE=InnoDB COMMENT='院区表';
```

### 2. SQL 表名前缀功能

**问题**: 无法为表名添加前缀以区分不同客户/项目的数据

**解决方案**:
- 新增 `--table-prefix` 参数
- 自动识别并替换 CREATE TABLE、INSERT INTO、DROP TABLE 中的表名
- 与文件名前缀 `--prefix` 参数独立

**示例**:
```bash
# 文件名: gzlry_BS_AREA.sql
# 表名: gzlry_BS_AREA
python tools/oracle_to_mysql.py convert BS_AREA.sql \
  --prefix gzlry_ \
  --table-prefix gzlry_ \
  --enable-comments
```

### 3. 自动化修复集成

**问题**: 需要手动执行两步操作（转换 + 修复），容易遗漏

**解决方案**:
- 新增 `--auto-fix` 参数
- 转换完成后自动调用 `sql-fix-tools/fix_sql_main.py`
- 生成统一的转换和修复报告

**工作流**:
```
Oracle SQL → oracle_to_mysql.py (转换) 
          → sql-fix-tools (修复) 
          → 最终 MySQL SQL
```

## 技术亮点

### 架构设计
- **混合方式处理 COMMENT**: 列注释内联 + 表注释追加
- **正则表达式替换表名**: 轻量级方案，避免引入 SQL 解析器重依赖
- **子进程集成修复工具**: 保持模块独立性，便于维护

### 性能优化
- 保持流式处理特性，支持超大文件（8960+ 行）
- COMMENT 收集内存占用 O(n)，可忽略（约 5KB）
- 双遍扫描开销小（10MB 文件约增加 0.5 秒）

### 向后兼容
- 所有新功能通过可选参数启用
- 默认行为与当前版本完全一致
- 不影响现有脚本和流程

## 实施计划

### 预估工时
- **基础架构**: 0.5 小时
- **COMMENT 转换**: 2 小时
- **表名前缀**: 1 小时
- **自动修复集成**: 1.5 小时
- **单元测试**: 2 小时
- **文档更新**: 1 小时
- **集成验证**: 1 小时

**总计**: 约 9 小时

### 任务依赖关系
```
基础准备 (1.1, 1.2)
   ↓
COMMENT 转换 (2.1 → 2.2 → 2.3 → 2.4)
   ↓
表名前缀 (3.1 → 3.2 → 3.3)
   ↓
自动修复 (4.1 → 4.2 → 4.3 → 4.4)
   ↓
单元测试 (5.1, 5.2, 5.3 并行)
   ↓
端到端测试 (5.4)
   ↓
文档更新 (6.1, 6.2, 6.3 并行)
   ↓
最终验证 (7.1, 7.2, 7.3)
```

## 规范增量

### 新增需求 (3个)

1. **Oracle COMMENT 转换为 MySQL 注释**
   - 6 个场景：收集表注释、收集列注释、注入列注释、注入表注释、处理特殊字符、默认行为

2. **SQL 语句中的表名前缀**
   - 7 个场景：CREATE TABLE、DROP TABLE、INSERT INTO、文件名前缀独立、只用文件名前缀、只用表名前缀、合法性验证

3. **自动化 SQL 修复集成**
   - 7 个场景：启用修复、修复成功、修复失败、跳过修复、路径定位、合并报告、批量转换修复

### 修改需求 (1个)

- **转换后文件保存**: 更新说明 `--prefix` 和 `--table-prefix` 的独立性

## 下一步行动

### 提案批准前
1. 与团队成员讨论技术设计
2. 确认需求优先级
3. 评估实施时间

### 提案批准后
1. 按照 `tasks.md` 顺序实施功能
2. 确保每个任务完成后更新清单
3. 完成后运行 `openspec-cn validate` 验证
4. 归档变更：`openspec-cn archive enhance-oracle-to-mysql-converter`

## 查看提案

```bash
# 查看完整提案
openspec-cn show enhance-oracle-to-mysql-converter

# 查看规范增量
openspec-cn show enhance-oracle-to-mysql-converter --json --deltas-only

# 验证提案
openspec-cn validate enhance-oracle-to-mysql-converter --strict
```

## 相关文档

- 提案文件: `openspec/changes/enhance-oracle-to-mysql-converter/proposal.md`
- 技术设计: `openspec/changes/enhance-oracle-to-mysql-converter/design.md`
- 任务清单: `openspec/changes/enhance-oracle-to-mysql-converter/tasks.md`
- 规范增量: `openspec/changes/enhance-oracle-to-mysql-converter/specs/sql-import/spec.md`

---

**创建时间**: 2026-01-13  
**状态**: ✅ 已验证，等待批准  
**优先级**: 高（解决实际业务痛点）
