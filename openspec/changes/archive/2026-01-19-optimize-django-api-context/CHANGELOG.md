# 变更日志

## 2026-01-19

### 修复
- **修复验证阶段 LLM 修正错误**
  - 问题：LLM 在修正阶段使用错误的操作符（`=` 而不是 `eq`）、错误的配置名、中文字段名
  - 根本原因：LLM 提示词缺少操作符格式说明和配置名保留指导
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- **修复无效 HTTP 方法导致的崩溃**
  - 问题：LLM 生成 `NONE` 等无效 HTTP 方法，导致 `'AsyncClient' object has no attribute 'none'` 错误
  - 修复：在 `validate_steps` 中添加 HTTP 方法有效性检查，跳过无效方法
  - 影响文件：`AIagent/src/django_api/script_generator.py`

- **修复路径参数未传递问题**
  - 问题：URL 中的路径变量（如 `{name}`）未被替换，导致请求 URL 包含未解析的变量
  - 修复：在 `call_api_by_path` 调用中添加 `path_params` 参数传递
  - 影响文件：`AIagent/src/django_api/script_generator.py`

### 功能增强
- **添加操作符格式说明**
  - 在 LLM 提示词中明确支持的操作符：`eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`, `between`
  - 明确禁止的符号：`=`, `==`, `!=`, `>`, `<`

- **实现配置名保留机制**
  - 在 `field_help_section` 中使用醒目格式强调已验证的配置名
  - 添加提示："🔴 关键: config_name 必须保持为..."

- **完善字段名映射表**
  - 提供字段名（英文）与显示名（中文）的 Markdown 表格
  - 添加说明："过滤条件必须使用字段名（左列），不能使用中文名"

- **空结果处理优化**
  - 查询返回 0 条数据时，也获取配置的可用字段信息
  - 避免 LLM 在第二次修正时因缺少信息而乱改配置

### 技术细节

#### 1. 操作符格式说明
```python
# 在 get_base_context() 中添加
"""
- **⚠️ 操作符必须使用**: `eq`(等于), `ne`(不等于), `gt`(大于), `gte`(大于等于), 
                        `lt`(小于), `lte`(小于等于), `like`(模糊匹配), 
                        `in`(包含), `between`(范围)
- **❌ 不要使用**: `=`, `==`, `!=`, `>`, `<` 等符号
"""
```

#### 2. 配置名保留提示
```python
field_help_section += f"""
## ✅ 配置 '{config_name}' 已验证存在！请保持使用。

**🔴 关键**: `config_name` 必须保持为 `"{config_name}"`，不要更改为其他配置名！
"""
```

#### 3. 无效 HTTP 方法检测
```python
VALID_HTTP_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}

if method not in VALID_HTTP_METHODS:
    # 跳过无效方法
    validation_results.append({
        'step': step_num,
        'status': 'skipped',
        'message': f'跳过无效 HTTP 方法: {method}'
    })
    continue
```

#### 4. 路径参数传递
```python
response = await client.call_api_by_path(
    method=method,
    path=path,
    query_params=query_params,
    body=body,
    path_params=params.get('path_params', {})  # 新增
)
```

### 测试验证
- ✅ "表数据查询 中的 老人档案 中 老人姓名 为 王丽珍 的记录" 查询成功
- ✅ 配置名 "老人档案" 正确保留
- ✅ 字段名 "oldername" 正确使用（而不是中文 "老人姓名"）
- ✅ 操作符 "eq" 正确使用（而不是 "=" 或 "=="）
- ✅ 查询返回数据：`{"oldername": "王丽珍", ...}`

---

## 2026-01-18

### 修复
- **修复 `ScriptGenerator` 初始化参数错误**
  - 问题：`cli.py` 中调用 `ScriptGenerator.__init__()` 时传入了不支持的参数 `save_history` 和 `output_format`
  - 修复：移除这些不支持的参数，修复 `generate()` 方法调用时的不支持参数，修复 `format_output()` 方法不存在的调用
  - 影响文件：`AIagent/src/django_api/cli.py`

### 功能增强
- **自动迭代修正默认启用**
  - 修改 `--auto-fix` 参数定义，使用 `action='store_const', const=True, default=True` 确保默认启用
  - 更新帮助信息和示例，说明默认启用
  - 更新提示信息，说明可通过 `--no-auto-fix` 禁用
  - 影响文件：`AIagent/src/django_api/cli.py`

- **执行历史自动保存集成**
  - 在 `cmd_generate` 函数中添加执行历史保存逻辑
  - 提取执行结果中的 API 列表、状态、错误信息
  - 创建 `ExecutionRecord` 并调用 `storage.save_execution()` 保存
  - 添加异常处理，确保保存失败不影响主流程
  - 默认启用，可通过 `--no-save` 禁用
  - 影响文件：`AIagent/src/django_api/cli.py`

### 技术细节

#### 1. 修复参数错误
```python
# 修复前
generator = ScriptGenerator(
    api_client=client,
    debug_mode=args.debug,
    auto_fix=auto_fix_enabled,
    max_iterations=args.max_iter if hasattr(args, 'max_iter') else 10,
    save_history=not no_save,  # ❌ 不支持
    output_format=output_format,  # ❌ 不支持
)

# 修复后
generator = ScriptGenerator(
    api_client=client,
    debug_mode=args.debug,
    auto_fix=auto_fix_enabled,
    max_iterations=args.max_iter if hasattr(args, 'max_iter') else 10,
)
```

#### 2. 自动迭代修正默认启用
```python
# 修改前
parser_generate.add_argument('--auto-fix', action='store_true', help='...')

# 修改后
parser_generate.add_argument('--auto-fix', action='store_const', const=True, default=True, help='执行失败时自动迭代修正（默认启用）')
```

#### 3. 执行历史自动保存
```python
# 在 cmd_generate 中添加
if not no_save:
    try:
        normalized = normalize_intent(intent)
        apis_used = extract_apis_from_plan(result.get('execution_plan', {}))
        status = determine_status(result)
        record = ExecutionRecord(...)
        storage = ExecutionHistoryStorage()
        storage.save_execution(record)
    except Exception as save_error:
        # 保存失败不影响主流程
        pass
```

### 测试验证
- ✅ 修复后命令可以正常执行
- ✅ `--auto-fix` 默认启用，无需显式指定
- ✅ 执行历史自动保存到 `data/execution_history/YYYY/MM/DD/` 目录
- ✅ 成功和失败的记录都能正确保存
