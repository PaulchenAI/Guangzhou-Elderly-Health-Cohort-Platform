# 变更：新增 Django 模型外键关系生成脚本

## 为什么

当前系统中的 `table_foreignkey_metadata` 表存储了从 Oracle SQL 文件中提取的外键关系元数据（535 条记录）。但是，Django 后端项目 (`backend-django`) 中定义的模型（如 User、Role、Dept、Menu、Permission 等）也包含大量的 ForeignKey 和 ManyToManyField 关系，这些关系目前没有被导入到 `table_foreignkey_metadata` 表中。

AI 在生成 SQL 查询时需要了解表之间的关联关系，但目前只能查询到外部导入的外键元数据，无法获取 Django 内置模型的关联关系，导致 AI 无法正确生成涉及 Django 模型的 JOIN 查询。

## 变更内容

- 新增 Django management command `generate_django_foreignkey_metadata`
- 自动扫描 Django 项目中所有已注册的模型
- 提取 ForeignKey 和 ManyToManyField 关系
- 将提取的关系信息导入到 `table_foreignkey_metadata` 表
- 支持以下选项：
  - `--dry-run`：预览模式，不执行实际导入
  - `--truncate`：导入前清空 Django 相关的记录
  - `--app-labels`：指定要扫描的 app（默认扫描所有）
  - `--exclude-apps`：排除指定的 app
  - `--verbose`：显示详细进度

## 影响

- 受影响规范：`foreignkey-api`
- 受影响代码：
  - `backend-django/core/management/commands/generate_django_foreignkey_metadata.py`（新增）
