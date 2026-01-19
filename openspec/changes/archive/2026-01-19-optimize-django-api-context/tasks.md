# 任务清单

## 1. API 上下文优化

- [x] 1.1 实现分层 API 摘要生成器
  - 添加 `get_api_summary_compact()` 方法，仅返回 Tag 统计
  - 添加 `get_tag_endpoints_summary(tag)` 方法，返回指定 Tag 的端点摘要
  - 添加 `get_endpoint_detail(operation_id)` 方法，返回完整端点详情

- [x] 1.2 添加上下文 Token 估算
  - 实现 `estimate_token_count(text)` 方法
  - 在 `get_api_summary_for_ai()` 中添加 Token 限制参数
  - 超过阈值时自动切换到紧凑模式

- [x] 1.3 优化 LLM 交互流程
  - 修改 `get_system_prompt()` 支持分层上下文
  - 实现两阶段 API 选择：先选 Tag，再选端点
  - 添加配置项 `DJANGO_API_CONTEXT_TOKEN_LIMIT`

- [x] 1.4 更新配置和文档
  - 在 `config/settings.yaml` 添加上下文优化配置
  - 更新 README.md 说明新的配置项

## 2. 历史指令记录与持久化

- [x] 2.1 实现执行记录存储模块
  - 创建 `execution_history.py` 模块
  - 定义执行记录模型（意图、API、状态、结果/错误、时间戳）
  - 实现 `save_execution()` 方法，**成功和失败都必须保存**

- [x] 2.2 定义执行记录数据结构
  - `status`: success / failed / error
  - `intent`: 用户原始指令
  - `normalized_intent`: 归一化后的核心意图
  - `intent_params`: 提取的参数（limit、page 等）
  - `apis_used`: 调用的 API 列表
  - `script_content`: 生成的脚本内容
  - `execution_output`: 执行输出
  - `error_message`: 错误信息（失败时）
  - `error_type`: 错误类型分类
  - `created_at`: 创建时间

- [x] 2.3 配置存储目录
  - 添加环境变量 `DJANGO_API_HISTORY_DIR`
  - 默认目录 `data/execution_history/`
  - 按日期分目录存储

- [x] 2.4 集成到脚本生成器
  - 在 `ScriptGenerator` 执行后自动保存记录
  - **成功时**：保存脚本和执行结果
  - **失败时**：保存错误信息和失败原因
  - 支持通过 CLI 参数禁用保存 `--no-save`

- [x] 2.5 **在 CLI 中集成自动保存功能**（2026-01-18 补充）
  - 在 `cmd_generate` 函数中添加执行历史保存逻辑
  - 提取执行结果中的 API 列表、状态、错误信息
  - 创建 `ExecutionRecord` 并调用 `storage.save_execution()` 保存
  - 保存失败不影响主流程执行
  - 修复 `ScriptGenerator.__init__()` 的参数错误（移除不支持的 `save_history` 和 `output_format` 参数）

## 3. 历史指令 RAG 检索（强制优先）

- [x] 3.1 **实现意图归一化**（关键功能）
  - 创建 `normalize_intent()` 函数
  - 提取核心意图（去除数目、翻页、排序等参数）
  - 提取参数信息：limit、page、pageSize、orderBy、orderDesc
  - 示例："查询用户列表前10个" → core="查询用户列表", limit=10

- [x] 3.2 实现历史指令向量索引
  - 创建 `HistoryIndexer` 类
  - 使用**归一化后的核心意图**生成向量
  - 向量内容包括：核心意图、API 列表、执行状态
  - 支持增量更新索引

- [x] 3.3 实现相似度计算模块
  - 实现向量余弦相似度计算 `cosine_similarity()`
  - 实现多维度加权相似度 `compute_weighted_similarity()`
    - 语义相似度权重 0.7（基于核心意图）
    - API 重合度权重 0.2（Jaccard 系数）
    - 关键词匹配权重 0.1
  - 支持通过配置调整权重

- [x] 3.4 实现检索结果分层
  - 创建 `HistoryRetriever` 类
  - 实现三层分类逻辑：
    - 🟢 精确匹配层（≥0.95）：直接复用
    - 🟡 高度相似层（0.80-0.95）：主要参考
    - 🟠 一般相似层（0.60-0.80）：辅助参考
  - 分层阈值可配置

- [x] 3.5 **实现参数自动替换**
  - 创建 `substitute_params()` 函数
  - 复用脚本时替换数目参数（limit）
  - 复用脚本时替换翻页参数（page、pageSize）
  - 复用脚本时替换排序参数（orderBy）
  - 示例：历史 limit=5，当前"前10个"→ 替换为 limit=10

- [x] 3.6 实现分层上下文构建
  - 创建 `build_history_context()` 方法
  - 精确匹配：提示直接复用脚本 + 参数替换
  - 高度相似成功记录：作为参考模板
  - 高度相似失败记录：提取错误原因告知 LLM
  - 一般相似：仅作为思路参考

- [x] 3.7 **强制优先检索**（关键功能）
  - 在生成新脚本前**必须**先检索历史指令
  - 返回分层的检索结果
  - 精确匹配时跳过脚本生成，直接复用 + 参数替换
  - 失败记录：提供错误信息，避免重复同样的错误

- [x] 3.8 集成到脚本生成流程
  - 修改 `ScriptGenerator` 工作流，添加历史检索节点作为**第一步**
  - 分层检索结果作为 LLM 上下文的一部分
  - 添加配置项：
    - `HISTORY_EXACT_THRESHOLD` = 0.95
    - `HISTORY_HIGH_THRESHOLD` = 0.80
    - `HISTORY_LOW_THRESHOLD` = 0.60

## 4. 查询结果默认翻页

- [x] 4.1 实现翻页参数检测
  - 分析用户意图是否包含明确数目（如"前10个"、"全部"）
  - 检测 API 端点是否支持分页参数（page、pageSize）

- [x] 4.2 自动添加默认翻页参数
  - 当用户意图没有明确数目时，自动添加翻页参数
  - 默认值：`page=1`，`pageSize=10`
  - 在脚本生成时注入翻页参数

- [x] 4.3 配置翻页默认值
  - 添加配置项 `DJANGO_API_DEFAULT_PAGE_SIZE`（默认 10）
  - 添加配置项 `DJANGO_API_DEFAULT_PAGE`（默认 1）
  - 支持按 API Tag 配置不同默认值

- [x] 4.4 实现返回结果翻页信息
  - 创建 `PaginationInfo` 数据结构
  - 从 API 响应中提取翻页信息（page、pageSize、total）
  - 计算总页数和是否有下一页

- [x] 4.5 生成翻页摘要提示
  - 实现 `to_summary()` 方法生成用户友好的翻页说明
  - 显示当前页码、总记录数、剩余记录数
  - 有下一页时提示用户可继续查询

## 5. 输出格式支持

- [x] 5.1 实现输出格式枚举
  - 创建 `OutputFormat` 枚举（TEXT、JSON）
  - 添加 CLI 参数 `--json` 和 `--output`

- [x] 5.2 实现 QueryResult 数据结构
  - 包含 success、data、pagination、meta 字段
  - 实现 `to_text()` 方法（友好文本格式）
  - 实现 `to_json()` 方法（结构化 JSON 格式）

- [x] 5.3 JSON 输出格式
  - data: 查询结果数组
  - pagination: 翻页信息对象（page、pageSize、total、totalPages、hasMore）
  - meta: 元信息（intent、api、duration、timestamp）

- [x] 5.4 配置默认输出格式
  - 添加环境变量 `DJANGO_API_OUTPUT_FORMAT`（默认 text）
  - 支持 text 和 json 两种格式

## 6. 测试与验证

- [x] 6.1 添加单元测试
  - 测试意图归一化（核心意图提取、参数提取）
  - 测试参数自动替换
  - 测试分层摘要生成
  - 测试执行记录保存（成功+失败）
  - 测试历史指令检索（核心意图匹配）
  - 测试默认翻页参数注入
  - 测试翻页信息提取
  - 测试 JSON 输出格式

- [x] 6.2 集成测试
  - 测试大规模 API（>200 端点）的上下文优化效果
  - 测试相似指令复用流程（含参数替换）
  - 测试失败记录的错误避免效果
  - 测试无数目查询的翻页行为
  - 测试不同输出格式切换
  - 测试"查询用户前10个"能匹配到"查询用户前5个"的历史

## 7. 用户体验优化（2026-01-18 补充）

- [x] 7.1 自动迭代修正默认启用
  - 修改 `--auto-fix` 参数定义，使用 `action='store_const', const=True, default=True`
  - 更新帮助信息和示例，说明默认启用
  - 更新提示信息，说明可通过 `--no-auto-fix` 禁用

- [x] 7.2 修复参数错误
  - 修复 `ScriptGenerator.__init__()` 调用时传入不支持的参数错误
  - 移除 `save_history` 和 `output_format` 参数
  - 修复 `generate()` 方法调用时的不支持参数
  - 修复 `format_output()` 方法不存在的调用

- [x] 7.3 执行历史自动保存集成
  - 在 `cli.py` 中导入执行历史相关模块
  - 在 `cmd_generate` 中添加保存逻辑（生成完成后）
  - 提取执行计划中的 API 列表
  - 根据执行结果确定状态（success/failed）
  - 创建并保存 `ExecutionRecord`
  - 添加异常处理，确保保存失败不影响主流程

## 8. 验证阶段智能修正（2026-01-19 补充）

- [x] 8.1 添加操作符格式说明
  - 在 `get_base_context()` 的 LLM 提示词中添加操作符说明
  - 明确支持的操作符：`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`, `between`
  - 明确禁止的符号：`=`, `==`, `!=`, `>`, `<` 等
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- [x] 8.2 实现配置名保留机制
  - 在 `field_help_section` 中添加配置名保留提示
  - 使用醒目格式（`✅`、`🔴`）强调已验证的配置名
  - 明确告知 LLM "不要更改为其他配置名"
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- [x] 8.3 完善字段名映射表
  - 在修正提示词中提供字段名与中文显示名的对照表
  - 使用 Markdown 表格格式，便于 LLM 理解
  - 在表格下方添加说明："过滤条件必须使用字段名（左列）"
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- [x] 8.4 添加无效 HTTP 方法检测
  - 定义有效 HTTP 方法集合：`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`
  - 在 `validate_steps` 中检测无效方法
  - 无效方法的步骤直接跳过，不调用 API
  - 记录跳过原因到验证结果
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- [x] 8.5 修复路径参数传递
  - 在 `call_api_by_path` 调用中添加 `path_params` 参数
  - 从步骤的 `params.path_params` 中获取路径参数
  - 支持 URL 中的变量替换（如 `/api/user/{id}` → `/api/user/123`）
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- [x] 8.6 空结果处理时保留配置信息
  - 当查询返回 0 条数据时，也获取配置的可用字段信息
  - 避免 LLM 在第二次修正时因缺少字段信息而乱改配置名
  - 添加提示："查询返回 0 条数据可能是数据库中没有匹配的记录，这是正常的"
  - 影响文件：`AIagent/src/django_api/script_generator.py`
