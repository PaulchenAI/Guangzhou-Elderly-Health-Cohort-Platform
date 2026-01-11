# 变更：添加 SQL 脚本语法错误自动修复功能

## 为什么

当前 `import_oracle_sql` 命令在导入转换后的 MySQL SQL 文件时，会遇到语法错误导致导入失败。从实际运行的错误日志可以看到：

```
[1/141] 处理: gzlry_PM_SER_MAJOR.sql (232B)
  导入失败: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near 'describe VARCHAR(4000),\n  dptid    VARCHAR(50)\n)\nENGINE=InnoDB DEFAULT CHARSET=u' at line 5")
```

**核心问题**：
1. **MySQL 保留字未处理**：`describe` 是 MySQL 保留字，需要用反引号包裹
2. **转换不完整**：Oracle 转 MySQL 的转换工具可能遗漏了部分语法兼容性问题
3. **人工修复低效**：141 个文件，手动修复耗时且容易出错

**业务影响**：
- 数据导入流程中断，需要人工介入
- 批量导入效率低下
- 可能造成数据导入不完整

## 变更内容

在 `import_oracle_sql` 命令中添加**自动修复 SQL 语法错误**的功能：

1. **MySQL 保留字自动处理**
   - 检测 SQL 语句中的 MySQL 保留字（列名、表名）
   - 自动添加反引号包裹（如 `describe` → `` `describe` ``）

2. **常见语法错误修复**
   - 自动修复日期格式问题
   - 自动修复字符串转义问题
   - 自动修复数据类型兼容性问题

3. **修复选项控制**
   - 添加 `--auto-fix` 参数：启用自动修复功能
   - 添加 `--save-fixed` 参数：将修复后的 SQL 保存到新文件
   - 添加 `--fix-report` 参数：生成修复报告，记录所有修复的内容

4. **增强错误提示**
   - 当检测到可自动修复的错误时，提示用户使用 `--auto-fix` 参数
   - 显示具体的修复建议

## 影响

- 受影响规范：`sql-import`
- 受影响代码：
  - `backend-django/core/management/commands/import_oracle_sql.py`
- 兼容性：**向后兼容**，不影响现有功能，通过可选参数启用

