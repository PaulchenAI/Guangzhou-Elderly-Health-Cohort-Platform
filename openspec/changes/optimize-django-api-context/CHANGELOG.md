# 变更日志

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
