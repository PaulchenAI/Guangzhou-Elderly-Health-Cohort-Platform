# SQL 表名和字段名中文含义推断 - 技术设计

## 上下文

需要实现 SQL 表名和字段名中文含义推断功能。该功能需要：
- 读取 SQL 文件内容
- 使用 LLM 直接解析并推断表名和字段名的中文含义
- 支持批量处理
- 输出结构化 JSON 结果

## 目标 / 非目标

### 目标
- 简单直接的实现，代码量少
- 支持单文件和批量处理
- 输出结构化 JSON，包含置信度和推理过程
- JSON 格式验证，确保输出正确
- 支持重试机制，提高成功率

### 非目标
- 不使用复杂的多智能体工作流（已简化）
- 不实现新的 LLM 提供商（使用现有 LLM 工厂）
- 不实现复杂的缓存机制（可后续优化）

## 决策

### 决策 1：简化架构 - 直接使用 LLM 处理原始 SQL

**理由**：
- 代码更简单（~300行 vs ~500行多智能体版本）
- LLM 天然理解 SQL 语法，不需要复杂的正则解析
- 减少中间处理环节，降低出错概率
- 推断结果更丰富（LLM 能看到完整上下文）

**考虑的替代方案**：
- 多智能体架构（SQLParserAgent + MeaningInferenceAgent + ResultWriterAgent）：过于复杂，正则解析容易出错
- 独立工具：无法利用已有的 LLM 基础设施

### 决策 2：使用 Pydantic 模型验证 JSON 格式

**理由**：
- 确保 LLM 输出符合预期格式
- 提供详细的验证错误信息
- 支持自动重试修正

**考虑的替代方案**：
- 手动验证：代码冗余，容易遗漏
- JSON Schema：不如 Pydantic 集成度高

### 决策 3：带上下文的重试机制

**理由**：
- LLM 输出格式可能不稳定
- 将上次的错误信息作为上下文，让 LLM 针对性修正
- 提高成功率，减少手动干预

**考虑的替代方案**：
- 简单重试：效果不如带上下文重试
- 不重试：成功率较低

### 决策 4：使用 AIagent LLM 工厂

**理由**：
- 统一管理 LLM 配置
- 支持多提供商（Anthropic、OpenAI、Local 等）
- 复用现有基础设施

### 决策 5：输出格式使用 JSON

**理由**：
- JSON 格式结构化、易解析
- 支持嵌套数据结构（表、字段、元数据）
- 便于后续处理和集成

### 决策 6：表名前缀忽略使用参数配置

**理由**：
- 提高灵活性，支持不同的前缀模式
- 默认值设为 `gzlry_` 以兼容当前场景

### 决策 7：支持自定义提示词模板

**理由**：
- 允许用户根据特定领域定制提示词
- 提高推断准确性和针对性

### 决策 8：默认输出到 docs/hospital/commentsql

**理由**：
- 与源文件目录结构对应
- 便于管理和查找推断结果

### 决策 9：错误日志记录与重试失败任务

**理由**：
- 批量处理时需要跟踪失败的任务
- 支持只重试失败的任务，避免重复处理成功的文件
- 错误日志使用 JSON 格式，便于解析和处理

**实现方式**：
- 失败任务记录到 `error_log.json`
- 支持 `--retry-failed` 参数只处理失败任务
- 支持 `clear-errors` 命令清除错误日志

### 决策 10：跳过已存在结果

**理由**：
- 增量处理，避免重复推断已完成的文件
- 提高批量处理效率
- 支持中断后继续处理

**实现方式**：
- 支持 `--skip-existing` 参数
- 检查输出目录中是否已存在对应的 `_meaning.json` 文件

### 决策 11：支持并发处理

**理由**：
- 大幅提升批量处理速度
- 充分利用 LLM API 的并发能力
- 用户可根据 API 限制调整并发数

**实现方式**：
- 使用 `asyncio.Semaphore` 控制并发数量
- 使用 `asyncio.gather` 并行执行任务
- 支持 `-c/--concurrency` 参数，默认为 1（顺序处理）
- 建议值：3-5（根据 API 速率限制调整）

## 风险 / 权衡

### 风险 1：LLM API 调用成本
**缓解措施**：
- 批量处理时可以控制并发
- 优先使用已有注释，减少推断量

### 风险 2：LLM 输出格式不稳定
**缓解措施**：
- Pydantic 模型验证
- 带上下文的重试机制（最多 3 次）
- 详细的错误日志

### 风险 3：推断准确性
**缓解措施**：
- 输出置信度，标记低置信度结果
- 保留推理过程，便于人工审核

## 架构设计

### 简化架构
```
SQL 文件 → SQLMeaningInferencer → LLM（解析+推断）→ JSON 验证 → 输出文件
                                        ↓
                                  验证失败？
                                        ↓
                                  带上下文重试
```

### 核心类

#### SQLMeaningInferencer
- 读取 SQL 文件内容
- 构建 LLM 提示词
- 调用 LLM 进行推断
- 验证 JSON 格式（Pydantic）
- 重试机制（带上下文）
- 写入结果文件
- 错误日志记录（`_save_error_log()`）
- 获取失败任务列表（`_get_failed_files()`）
- 清除错误日志（`clear_error_log()`）
- 跳过已存在结果（`skip_existing` 参数）

#### JSON 验证模型
```python
class MeaningInfo(BaseModel):
    meaning: str
    confidence: float  # 0-1
    reasoning: str

class FieldInfo(BaseModel):
    name: str
    type: str
    comment: Optional[str]
    meaning: str
    confidence: float
    reasoning: str

class LLMOutputSchema(BaseModel):
    table_name: str
    table_comment: Optional[str]
    table_meaning: MeaningInfo
    fields: List[FieldInfo]
```

### 数据流

1. **输入**：SQL 文件路径或目录
2. **读取**：读取 SQL 文件内容
3. **推断**：发送给 LLM，获取结构化结果
4. **验证**：使用 Pydantic 验证 JSON 格式
5. **重试**：验证失败时带上下文重试
6. **输出**：生成 JSON 文件

## 文件结构

```
AIagent/src/sql_import/
├── sql_meaning_llm.py    # 核心推断器（~300行）
├── sql_meaning_cli.py    # CLI 命令行工具（~90行）
└── __init__.py           # 模块导出
```

## 已决策问题

- [x] **输出格式**：使用 JSON 格式
- [x] **前缀忽略**：使用参数配置，默认 `gzlry_`
- [x] **自定义提示词模板**：支持通过文件指定
- [x] **架构选择**：简化为单一类，不使用多智能体
- [x] **JSON 验证**：使用 Pydantic 模型
- [x] **重试机制**：带上下文重试，最多 3 次
- [x] **默认输出目录**：`docs/hospital/commentsql`
- [x] **错误日志记录**：失败任务记录到 `error_log.json`
- [x] **跳过已存在结果**：支持 `--skip-existing` 参数
- [x] **重试失败任务**：支持 `--retry-failed` 参数
- [x] **并发批量处理**：支持 `-c/--concurrency` 参数

## 待决问题

（无）
