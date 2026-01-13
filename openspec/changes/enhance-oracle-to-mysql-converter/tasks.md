# 实施任务清单

## 1. 基础架构准备

- [x] 1.1 在 `OracleToMySQLConverter` 类中添加 COMMENT 存储字典
  - 添加 `self.table_comments = {}`
  - 添加 `self.column_comments = {}`

- [x] 1.2 添加命令行参数支持
  - 在 `convert` 子命令添加 `--table-prefix` 参数
  - 在 `convert` 子命令添加 `--enable-comments` 参数（启用 COMMENT 转换）
  - 在 `convert-all` 子命令添加 `--table-prefix` 参数
  - 在 `convert-all` 子命令添加 `--enable-comments` 参数
  - 在 `convert-all` 子命令添加 `--auto-fix` 参数

## 2. COMMENT 转换功能实现

- [x] 2.1 实现 COMMENT 收集方法 `_collect_comments()`
  - 使用正则表达式匹配 `COMMENT ON TABLE ... IS '...';`
  - 使用正则表达式匹配 `COMMENT ON COLUMN ... IS '...';`
  - 处理单引号转义（`'` → `''`）
  - 测试边界情况：空注释、多行注释、特殊字符

- [x] 2.2 实现列注释注入方法 `_inject_column_comments()`
  - 解析 CREATE TABLE 语句，识别列定义
  - 在列定义后添加 `COMMENT '...'`
  - 保持列定义的其他属性（NOT NULL、DEFAULT 等）
  - 测试各种数据类型和约束组合

- [x] 2.3 实现表注释注入方法 `_inject_table_comment()`
  - 在 ENGINE 子句前插入 `COMMENT='...'`
  - 处理没有 ENGINE 子句的情况
  - 测试不同的表选项组合

- [x] 2.4 修改 `_convert_create_table()` 方法
  - 集成 COMMENT 注入逻辑
  - 确保注入后 SQL 语法正确
  - 添加日志记录注释转换情况

## 3. DDL/DML 分离功能实现

- [x] 3.1 实现分离逻辑 `convert_file_with_split()`
  - 解析并分类 DDL 和 DML 语句
  - 创建 create/ 和 insert/ 子目录
  - 分别保存到不同文件

- [x] 3.2 实现流式写入优化
  - 避免在内存中累积所有语句
  - 边解析边写入到对应文件
  - 测试大文件（BS_OLDER.sql）的内存占用

- [x] 3.3 实现空表处理
  - 检测没有 INSERT 语句的表
  - 只创建 DDL 文件
  - 在日志中标记"无数据"

- [x] 3.4 实现文件命名规则
  - DDL 文件：`表名.sql`
  - DML 文件：`表名_data.sql`
  - 测试各种表名（带下划线、数字等）

- [x] 3.5 集成到批量转换
  - 修改 `convert_directory()` 支持分离模式
  - 创建统一的子目录结构
  - 更新进度显示（显示 DDL 和 DML 文件路径）

## 4. 表名前缀功能实现

- [x] 4.1 实现表名前缀方法 `add_table_prefix()`
  - 处理 `CREATE TABLE table_name`
  - 处理 `DROP TABLE IF EXISTS table_name`
  - 处理 `INSERT INTO table_name`
  - 使用正则表达式精确匹配表名（避免误匹配）

- [x] 4.2 集成表名前缀到转换流程
  - 在 `_convert_create_table()` 中应用前缀
  - 在 `_convert_insert()` 中应用前缀
  - 确保 DROP TABLE 语句也包含前缀

- [x] 4.3 添加表名前缀验证
  - 记录警告日志（如果前缀包含特殊字符）
  - 测试各种前缀格式（字母、数字、下划线、短横线等）

## 5. 自动修复集成实现

- [x] 5.1 实现自动修复调用方法 `auto_fix_sql_files()`
  - 定位 `sql-fix-tools/fix_sql_main.py` 路径
  - 使用 `subprocess.run()` 调用修复脚本
  - 捕获 stdout 和 stderr
  - 处理返回码（成功/失败）

- [x] 5.2 实现分离模式下的修复
  - 分别修复 create/ 和 insert/ 目录
  - 传递正确的目录参数给修复工具
  - 合并两次修复的报告

- [x] 5.3 修改 `sql-fix-tools/fix_sql_main.py` 支持参数化调用
  - 添加 `--target-dir` 参数（指定要修复的目录）
  - 添加 `--quiet` 参数（减少输出，适合自动化调用）
  - 确保脚本可以被其他工具调用

- [x] 5.4 集成自动修复到 `convert_directory()`
  - 在所有文件转换完成后调用修复工具
  - 打印修复工具的输出
  - 处理修复失败的情况（记录警告，但不中断流程）

- [x] 5.5 生成合并报告
  - 统计转换阶段的成功/失败文件数
  - 统计修复阶段的修复项数量（分别统计 DDL 和 DML）
  - 计算总耗时
  - 格式化输出报告

## 6. 单元测试

- [x] 6.1 COMMENT 转换测试
  - 测试表注释收集和注入
  - 测试列注释收集和注入
  - 测试特殊字符转义
  - 测试没有 COMMENT 的情况

- [x] 6.2 DDL/DML 分离测试
  - 测试文件正确分离到 create/ 和 insert/ 目录
  - 测试文件命名规则（DDL 和 DML）
  - 测试空表处理（只生成 DDL 文件）
  - 测试大表数据分离（BS_OLDER.sql）
  - 测试流式处理的内存占用

- [x] 6.3 表名前缀测试
  - 测试 CREATE TABLE 前缀添加
  - 测试 INSERT INTO 前缀添加
  - 测试 DROP TABLE 前缀添加
  - 测试文件名前缀与表名前缀的独立性

- [x] 6.4 自动修复集成测试
  - 测试修复工具调用成功
  - 测试修复工具调用失败
  - 测试修复工具不存在的情况
  - 测试批量转换时的修复流程
  - 测试分离模式下的分别修复

- [x] 6.5 功能组合测试
  - 测试 COMMENT + 表名前缀
  - 测试 DDL/DML 分离 + 表名前缀
  - 测试 DDL/DML 分离 + COMMENT
  - 测试所有功能组合

- [x] 6.6 端到端测试
  - 使用实际的 Oracle SQL 文件测试（BS_AREA.sql）
  - 验证转换后的 SQL 可以成功导入 MySQL
  - 验证 COMMENT 正确显示在数据库中
  - 验证表名前缀正确应用
  - 验证分阶段导入流程（先导入 create/，再导入 insert/）

## 7. 文档更新

- [x] 7.1 更新 `tools/oracle_to_mysql.py` 的 docstring
  - 添加 `--split-ddl-dml` 参数说明
  - 添加 `--table-prefix` 参数说明
  - 添加 `--enable-comments` 参数说明
  - 添加 `--auto-fix` 参数说明
  - 添加使用示例

- [x] 7.2 更新 `tools/sql-fix-tools/README.md`
  - 说明自动化集成功能
  - 说明分离模式下的修复流程
  - 添加 `--target-dir` 参数说明
  - 更新工作流程图

- [x] 7.3 创建使用指南文档
  - 创建 `tools/oracle_to_mysql_guide.md`
  - 包含常见用例和示例
  - 包含 DDL/DML 分离的最佳实践
  - 包含分阶段导入指南
  - 包含故障排查指南

- [x] 7.4 创建分阶段导入脚本
  - 创建 `tools/import_ddl_dml.sh`
  - 支持先导入 create/，再导入 insert/
  - 支持事务控制和错误处理
  - 添加使用说明

## 8. 集成测试与验证

- [x] 8.1 在测试环境验证完整流程
  - 转换 `docs/hospital/sql/` 目录下的所有文件
  - 启用 COMMENT 转换
  - 启用 DDL/DML 分离
  - 使用表名前缀（例如 `test_`）
  - 启用自动修复
  - 导入到测试数据库并验证

- [x] 8.2 验证分阶段导入
  - 先导入 create/ 目录（创建所有表结构）
  - 验证表结构正确创建
  - 再导入 insert/ 目录（插入所有数据）
  - 验证数据正确导入
  - 测试重复导入数据（清空数据后重新导入 insert/）

- [x] 8.3 性能测试
  - 测试大文件（如 BS_OLDER.sql）的转换时间
  - 确保 COMMENT 收集不影响流式处理性能
  - 确保 DDL/DML 分离不增加内存占用
  - 确保内存占用在合理范围内

- [x] 8.4 向后兼容性验证
  - 测试不使用新参数的默认行为
  - 确保现有脚本和流程不受影响
  - 验证单文件转换仍然正常工作

## 验证清单

每个任务完成后，确认以下检查项：

- [x] 代码符合 PEP 8 规范
- [x] 添加了必要的注释和 docstring
- [x] 通过单元测试
- [x] 更新了相关文档
- [x] 在测试环境验证功能正常
- [x] 不引入向后不兼容的变更

## 依赖关系

```
1.1, 1.2 (基础准备)
   ↓
2.1 → 2.2 → 2.3 → 2.4 (COMMENT 转换)
   ↓
3.1 → 3.2 → 3.3 → 3.4 → 3.5 (DDL/DML 分离)
   ↓
4.1 → 4.2 → 4.3 (表名前缀)
   ↓
5.1 → 5.2 → 5.3 → 5.4 → 5.5 (自动修复)
   ↓
6.1, 6.2, 6.3, 6.4 (单元测试，可并行)
   ↓
6.5 (功能组合测试)
   ↓
6.6 (端到端测试)
   ↓
7.1, 7.2, 7.3, 7.4 (文档更新，可并行)
   ↓
8.1, 8.2, 8.3, 8.4 (最终验证)
```

## 预估工时

- 基础架构准备：0.5 小时
- COMMENT 转换功能：2 小时
- DDL/DML 分离功能：2.5 小时
- 表名前缀功能：1 小时
- 自动修复集成：2 小时
- 单元测试：3 小时
- 文档更新：1.5 小时
- 集成测试与验证：1.5 小时

**总计**：约 14 小时
