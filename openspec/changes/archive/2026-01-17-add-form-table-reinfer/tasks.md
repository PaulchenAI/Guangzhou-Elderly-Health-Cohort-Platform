## 1. 实施

### 1.1 Excel 读取功能
- [x] 1.1.1 新增 `_read_excel_metadata()` 方法，读取 Excel 文件
- [x] 1.1.2 解析 TABLENAME、FORMDES、NAMELABEL 三列
- [x] 1.1.3 处理表名大小写统一（转为大写）

### 1.2 上下文推断方法
- [x] 1.2.1 新增 `CONTEXT_PROMPT` 提示词模板，包含表单分类和名称
- [x] 1.2.2 新增 `infer_with_context()` 方法，支持传入业务上下文
- [x] 1.2.3 在提示词中注入 FORMDES 和 NAMELABEL 信息

### 1.3 批量重新推断
- [x] 1.3.1 新增 `reinfer_from_excel()` 方法
- [x] 1.3.2 遍历 Excel 每行数据
- [x] 1.3.3 查找对应的 `{TABLENAME}_meaning.json` 文件
- [x] 1.3.4 如果 JSON 存在，从中提取原始 SQL 文件路径
- [x] 1.3.5 读取原始 SQL 文件内容
- [x] 1.3.6 调用 `infer_with_context()` 重新推断
- [x] 1.3.7 如果 JSON 不存在，记录并跳过
- [x] 1.3.8 支持 `--skip-existing` 参数（跳过已重新推断的）
- [x] 1.3.9 支持并发处理

### 1.4 CLI 命令
- [x] 1.4.1 新增 `reinfer-from-excel` 子命令
- [x] 1.4.2 参数：`excel_file` - Excel 文件路径
- [x] 1.4.3 参数：`-o/--output` - 输出目录（默认 `docs/hospital/commentsql`）
- [x] 1.4.4 参数：`--sql-dir` - SQL 文件目录（默认 `docs/hospital/convertsql/create`）
- [x] 1.4.5 参数：`-c/--concurrency` - 并发数
- [x] 1.4.6 参数：`--skip-existing` - 跳过已存在的结果
- [x] 1.4.7 参数：`--dry-run` - 预览模式，只显示要处理的文件

### 1.5 进度与报告
- [x] 1.5.1 显示处理进度（已处理/总数）
- [x] 1.5.2 统计成功、失败、跳过的数量
- [x] 1.5.3 列出跳过的表（JSON 不存在）
- [x] 1.5.4 列出失败的表（推断错误）

## 2. 测试

- [x] 2.1 测试 Excel 读取功能
- [x] 2.2 测试单个表的上下文推断
- [x] 2.3 测试批量重新推断
- [x] 2.4 验证跳过逻辑（JSON 不存在时）
- [x] 2.5 对比重新推断前后的结果差异

## 3. 文档

- [x] 3.1 更新 CLI 帮助信息
- [x] 3.2 添加使用示例到 README
