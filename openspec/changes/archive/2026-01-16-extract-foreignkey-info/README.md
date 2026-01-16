# OpenSpec 变更提案：提取外键关联信息

## 概述

本提案旨在从 `docs/hospital/sql` 目录中的 Oracle SQL 文件提取外键约束信息，并以结构化 JSON 格式保存到 `docs/hospital/foreignkey` 目录。

## 提案状态

- **提案 ID**: `extract-foreignkey-info`
- **状态**: 待审核
- **验证结果**: ✅ 通过严格验证

## 背景

`docs/hospital/sql` 目录包含 954 个 Oracle SQL 文件，这些文件中包含了大量的外键约束信息。外键关系定义了表与表之间的关联关系，对于理解数据库结构、生成 ER 图、进行数据迁移分析等场景非常重要。

## 主要功能

### 1. 多策略 SQL 外键解析

系统采用**三层提取策略 + LLM 辅助**的架构，能够处理各种格式的 SQL 文件：

#### 策略 1：标准正则表达式（优先级最高）
- 适用于标准 Oracle SQL 格式
- 解析 `alter table ... add constraint ... foreign key` 语句
- 预计覆盖率：80-90% 的文件
- 速度最快，无额外成本

#### 策略 2：格式变体脚本库
- 针对已知的非标准格式维护脚本库
- 基于格式指纹自动匹配合适的脚本
- 预计覆盖率：额外 5-10% 的文件
- 可扩展，支持添加新格式

#### 策略 3：LLM 辅助脚本生成（兜底方案）
- 使用 Claude API 分析未知格式
- 自动生成定制化的提取脚本
- 预计覆盖率：剩余 5-10% 的文件
- 智能、灵活，处理复杂场景

**智能特性**：
- **自动格式识别**：计算格式指纹，自动选择最佳策略
- **置信度评估**：评估提取结果的可靠性
- **脚本缓存**：LLM 生成的脚本会被缓存，相同格式只调用一次 API
- **回退机制**：策略失败时自动尝试下一个策略

### 2. LLM 集成（Claude API）

**功能**：
- 分析未知格式的外键定义语句
- 生成 Python 提取脚本（带正则表达式或其他解析逻辑）
- 自动验证生成的脚本（语法检查 + 功能测试）
- 重试机制：最多尝试 3 次

**配置**：
```bash
# 通过环境变量
export ANTHROPIC_API_KEY="your-api-key"

# 或通过命令行参数
--anthropic-api-key your-api-key
```

**成本估算**：
- 假设 10% 文件需要 LLM（~100 文件）
- **使用关键字片段提取，每次调用平均 ~1000 tokens**（而非整个文件）
- 总成本：约 **$0.30**（使用 Claude Sonnet）

### 3. 大文件优化处理

**问题**：某些 SQL 文件可能非常大（>10MB），完整加载会导致内存溢出和 LLM Token 超限。

**解决方案**：关键字片段提取 + 流式处理

#### 关键字片段提取
```python
# 搜索外键相关关键字
keywords = [
    r'foreign\s+key',
    r'references\s+\w+',
    r'add\s+constraint.*foreign',
    r'constraint.*references'
]

# 提取包含关键字的行及上下文（前5行 + 当前行 + 后10行）
# 确保语句完整性（查找分号边界）
# 最多提取 5 个示例片段
```

#### 流式处理
- **大文件识别**：>1MB 的文件启用流式处理
- **逐行读取**：避免一次性加载整个文件到内存
- **分块应用**：对大文件分块应用提取脚本
- **内存控制**：确保内存占用 < 100MB

#### 性能优势
| 文件大小 | 传统方式 | 优化方式 |
|---------|---------|---------|
| 1MB | 加载全文 | 加载全文 |
| 5MB | 内存占用 5MB | 流式处理，内存 <50MB |
| 10MB | 内存占用 10MB | 流式处理，内存 <100MB |
| 50MB | **内存溢出** | 流式处理，内存 <100MB |

**LLM Token 优化**：
- 传统方式：发送整个 10MB 文件（约 40,000 tokens）→ **超出限制**
- 优化方式：只发送 5 个片段（约 1,000 tokens）→ **正常处理**

### 4. 策略缓存系统

**目录结构**：
```
docs/hospital/foreignkey/generated_strategies/
├── a1b2c3d4.py          # LLM 生成的提取脚本
├── e5f6g7h8.py
├── metadata.json        # 格式指纹和脚本映射
└── test_cases.json      # 测试用例
```

**缓存优势**：
- 避免重复调用 LLM API
- 降低成本和提取时间
- 支持团队共享（可提交到 Git）
- 累积格式知识库

### 5. 外键元数据提取

提取完整的外键信息：
- 约束名称、源表、源字段、目标表、目标字段、删除规则
- 支持单字段外键、复合字段外键、自引用外键
- 记录使用的提取策略和格式指纹

### 6. JSON 存储格式
提供两种存储模式：

#### 按表存储模式（默认）
每个表生成单独的 JSON 文件：
- 文件名：`{表名}_foreignkeys.json`
- 示例：`BS_DEPARTMENT_foreignkeys.json`
- 包含提取策略信息

#### 统一存储模式
所有外键信息保存到一个文件：
- 文件名：`all_foreignkeys.json`
- 包含元数据和统计信息
- 包含策略使用统计

### 7. CLI 命令

#### 单文件提取
```bash
python -m AIagent.sql_import extract-foreignkey \
  docs/hospital/sql/BS_DEPARTMENT.sql \
  -o docs/hospital/foreignkey/
```

#### 批量提取（按表存储）
```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --mode per-table
```

#### 批量提取（统一存储）
```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --mode unified
```

#### 启用 LLM 辅助提取
```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --enable-llm \
  --anthropic-api-key $ANTHROPIC_API_KEY
```

#### 查看策略统计
```bash
python -m AIagent.sql_import foreignkey-stats
```

#### 查看详细进度和策略使用
```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --enable-llm \
  --verbose \
  --show-strategies
```

## JSON 格式示例

### 按表存储格式（含策略信息）

**自引用外键示例** (`BS_DEPARTMENT_foreignkeys.json`)：
```json
{
    "table_name": "BS_DEPARTMENT",
    "source_file": "BS_DEPARTMENT.sql",
    "extraction_strategy": "standard_regex",
    "foreign_keys": [
        {
            "constraint_name": "FK_DEPAR_R11_DEPAR",
            "source_table": "BS_DEPARTMENT",
            "source_columns": ["PARENTID"],
            "target_table": "BS_DEPARTMENT",
            "target_columns": ["MAINID"],
            "on_delete": null
        }
    ],
    "extracted_at": "2026-01-16T10:30:00Z"
}
```

**多外键 + LLM 生成策略示例** (`BSE_SERVICE_PACKAGE_DETAIL_foreignkeys.json`)：
```json
{
    "table_name": "BSE_SERVICE_PACKAGE_DETAIL",
    "source_file": "BSE_SERVICE_PACKAGE_DETAIL.sql",
    "extraction_strategy": "llm_generated",
    "strategy_fingerprint": "a1b2c3d4",
    "foreign_keys": [
        {
            "constraint_name": "FK_BSE_SERVICE_PACKAGE_DETAIL1",
            "source_table": "BSE_SERVICE_PACKAGE_DETAIL",
            "source_columns": ["BASE_SERVICE_PACKAGE_ID"],
            "target_table": "BSE_SERVICE_PACKAGE",
            "target_columns": ["MAINID"],
            "on_delete": "cascade"
        },
        {
            "constraint_name": "FK_BSE_SERVICE_PACKAGE_DETAIL2",
            "source_table": "BSE_SERVICE_PACKAGE_DETAIL",
            "source_columns": ["SERVICE_ID"],
            "target_table": "BS_SER_MAINFILE",
            "target_columns": ["MAINID"],
            "on_delete": "cascade"
        }
    ],
    "extracted_at": "2026-01-16T10:30:00Z"
}
```

### 统一存储格式（含策略统计）

**all_foreignkeys.json**：
```json
{
    "metadata": {
        "extracted_at": "2026-01-16T10:30:00Z",
        "total_files": 954,
        "total_foreignkeys": 256,
        "tables_with_foreignkeys": 128,
        "strategy_stats": {
            "standard_regex": 780,
            "variant_script": 98,
            "llm_generated": 76
        },
        "llm_api_calls": 15,
        "estimated_cost_usd": 0.45
    },
    "foreignkeys": [
        {
            "constraint_name": "FK_DEPAR_R11_DEPAR",
            "source_table": "BS_DEPARTMENT",
            "source_columns": ["PARENTID"],
            "target_table": "BS_DEPARTMENT",
            "target_columns": ["MAINID"],
            "on_delete": null,
            "source_file": "BS_DEPARTMENT.sql",
            "extraction_strategy": "standard_regex"
        },
        ...
    ]
}
```

## 技术亮点

1. **多策略架构**：渐进式策略选择，从快速简单到智能复杂
2. **LLM 辅助**：Claude API 提供强大的格式分析和代码生成能力
3. **大文件优化**：关键字片段提取 + 流式处理，支持处理 >50MB 的文件
4. **智能缓存**：格式指纹识别 + 脚本缓存，避免重复分析
5. **自动验证**：生成的脚本经过严格验证（语法 + 功能）
6. **成本控制**：优先使用正则表达式，LLM 作为兜底方案，片段提取降低 Token 成本
7. **内存安全**：流式处理确保内存占用 < 100MB，避免溢出
8. **双存储模式**：灵活支持单表分析和全局分析
9. **Pydantic 验证**：确保数据结构的类型安全和完整性
10. **全面监控**：记录每个文件的提取策略、文件大小、处理时间

## 实施任务

详见 [`tasks.md`](./tasks.md)，包含以下阶段：
1. 核心功能实施（解析器、提取器、多策略）
2. LLM 集成实施（Claude API、脚本生成、验证）
3. 策略缓存系统
4. CLI 命令实施
5. 数据格式与存储
6. 测试与验证
7. 文档与输出

## 文件结构

```
openspec/changes/extract-foreignkey-info/
├── README.md             # 提案完整说明（本文件）
├── proposal.md           # 提案概述（为什么、变更内容、影响）
├── tasks.md              # 实施任务清单（46 项）
├── design.md             # 技术设计文档（架构决策、数据结构、LLM 集成）
└── specs/
    └── sql-import/
        └── spec.md       # 规范增量（7 个新增需求）
```

## 统计信息

- **总文件数**: 5 个核心文档 + 1 个 README
- **任务数量**: 51 项实施任务（分 7 个阶段）
- **需求数量**: 8 个新增需求
- **场景数量**: 60+ 个详细场景
- **目标 SQL 文件**: 954 个 Oracle SQL 文件
- **文件大小范围**: 1KB - 50MB+
- **预计覆盖率**: 
  - 标准正则：80-90%
  - 格式变体：5-10%
  - LLM 生成：5-10%
  - 总计：95-100%
- **内存占用**: < 100MB（流式处理）
- **LLM 成本**: 约 $0.30（使用片段提取）

## 验证结果

```bash
$ openspec-cn validate extract-foreignkey-info --strict
变更 'extract-foreignkey-info' 验证通过
```

## 下一步

1. **审核提案**：团队审核提案内容和技术方案
2. **批准后实施**：按照 `tasks.md` 逐项实施功能
3. **测试验证**：使用样本文件测试，然后批量提取所有 954 个文件
4. **归档变更**：实施完成后，将变更归档并更新 `specs/sql-import/spec.md`

## 参考文档

- OpenSpec 使用指南：`openspec/AGENTS.md`
- SQL Import 规范：`openspec/specs/sql-import/spec.md`
- 项目约定：`openspec/project.md`

## 示例文件

- `.example_BS_DEPARTMENT_foreignkeys.json` - 自引用外键示例
- `.example_BSE_SERVICE_PACKAGE_DETAIL_foreignkeys.json` - 多外键示例

---

**创建时间**: 2026-01-16  
**创建者**: AI Assistant  
**变更 ID**: extract-foreignkey-info
