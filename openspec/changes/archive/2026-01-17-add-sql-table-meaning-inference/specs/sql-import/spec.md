## 新增需求

### 需求：SQL 表名和字段名中文含义推断

系统必须提供 SQL 表名和字段名中文含义推断功能，能够读取 SQL 文件并使用 LLM 推断表名和字段名的中文含义。

#### 场景：单文件推断

- **当** 用户指定单个 SQL 文件路径
- **那么** 读取该文件内容并发送给 LLM 进行解析和推断
- **并且** 输出结构化 JSON 结果到指定路径（默认 `docs/hospital/commentsql/表名_meaning.json`）

#### 场景：批量推断

- **当** 用户指定 SQL 文件目录
- **那么** 遍历目录下所有 `.sql` 文件
- **并且** 为每个文件推断表名和字段名的中文含义
- **并且** 生成汇总 JSON 文件 `all_meanings.json` 和单个文件的 JSON 文件

#### 场景：配置表名前缀参数

- **当** 用户使用 `--ignore-prefix` 参数指定前缀（如 `--ignore-prefix custom_`）
- **那么** 告知 LLM 忽略该前缀进行推断
- **当** 用户未指定前缀参数
- **那么** 使用默认前缀 `gzlry_`

#### 场景：使用 LLM 直接处理 SQL

- **当** 读取到 SQL 文件内容
- **那么** 将完整 SQL 内容发送给 LLM
- **并且** LLM 同时完成解析和推断
- **并且** 返回结构化 JSON 结果

#### 场景：JSON 格式验证

- **当** LLM 返回推断结果
- **那么** 使用 Pydantic 模型验证 JSON 格式
- **并且** 验证必填字段：table_name, table_meaning, fields
- **并且** 验证 confidence 在 0-1 之间
- **并且** 验证 fields 数组不为空

#### 场景：带上下文的重试机制

- **当** JSON 格式验证失败
- **那么** 将上一次的 LLM 响应和验证错误信息作为上下文
- **并且** 构建修正提示词，告知 LLM 具体的错误字段
- **并且** 重新调用 LLM 进行推断
- **并且** 最多重试 2 次（共 3 次尝试）

#### 场景：输出结构化结果

- **当** 推断完成且验证通过
- **那么** 输出 JSON 文件，包含：
  - file_path：源文件路径
  - table：表信息
    - table_name：表名（不含前缀）
    - original_comment：原始注释
    - inferred_meaning：推断的中文含义
    - confidence：置信度（0-1）
    - reasoning：推理过程
    - fields：字段列表
  - metadata：元数据（处理时间、LLM 模型、LLM 提供商）

#### 场景：CLI 单文件推断命令

- **当** 用户执行 `python -m AIagent.src.sql_import.sql_meaning_cli infer-file <file> [-o <output>] [--ignore-prefix <prefix>] [--prompt-template <template_file>]`
- **那么** 推断指定 SQL 文件的表名和字段名含义
- **并且** 保存结果到指定输出路径（默认 `docs/hospital/commentsql/表名_meaning.json`）
- **并且** 显示 JSON 格式验证结果和重试次数

#### 场景：CLI 批量推断命令

- **当** 用户执行 `python -m AIagent.src.sql_import.sql_meaning_cli infer-dir <directory> [-o <output_dir>] [--ignore-prefix <prefix>] [--prompt-template <template_file>] [--skip-existing] [--retry-failed]`
- **那么** 批量推断目录下所有 SQL 文件
- **并且** 保存结果到指定输出目录（默认 `docs/hospital/commentsql`）
- **并且** 生成汇总文件 `all_meanings.json`

#### 场景：跳过已存在结果

- **当** 用户使用 `--skip-existing` 参数
- **那么** 检查输出目录中是否已存在对应的 `_meaning.json` 文件
- **并且** 如果已存在则跳过该文件的推断
- **并且** 在日志中记录跳过的文件数量

#### 场景：错误日志记录

- **当** 批量处理过程中有文件推断失败
- **那么** 将失败的任务记录到 `error_log.json` 文件
- **并且** 记录失败的文件路径、错误信息、失败时间
- **并且** 在处理完成后显示成功、失败、跳过的文件数量

#### 场景：重试失败任务

- **当** 用户使用 `--retry-failed` 参数
- **那么** 从 `error_log.json` 读取之前失败的任务列表
- **并且** 只处理这些失败的文件
- **并且** 如果没有失败任务，显示提示信息

#### 场景：清除错误日志

- **当** 用户执行 `python -m AIagent.src.sql_import.sql_meaning_cli clear-errors [-o <output_dir>]`
- **那么** 删除指定目录下的 `error_log.json` 文件
- **并且** 显示清除结果

#### 场景：并发批量处理

- **当** 用户使用 `-c/--concurrency <N>` 参数
- **那么** 同时处理最多 N 个文件
- **并且** 使用信号量控制并发数量
- **并且** 所有任务完成后统一汇总结果
- **当** 用户未指定并发数
- **那么** 使用默认值 1（顺序处理）

#### 场景：自定义提示词模板

- **当** 用户提供自定义提示词模板文件
- **那么** 模板文件支持以下占位符：
  - `{sql_content}`：SQL 文件完整内容
  - `{ignore_prefix}`：要忽略的表名前缀
- **并且** 如果模板文件不存在，输出警告并使用默认模板

#### 场景：错误处理

- **当** SQL 文件不存在或无法读取
- **那么** 抛出 FileNotFoundError 并记录错误信息

- **当** LLM 调用失败
- **那么** 记录错误信息
- **并且** 在结果中标记为推断失败（包含 error 字段）

- **当** 所有重试都失败
- **那么** 返回包含 error 字段的结果
- **并且** 记录详细的错误日志
