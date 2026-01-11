# 实施任务

## 1. 开发 SQL 转换工具

- [x] 1.1 创建 `tools/oracle_to_mysql.py` 转换脚本
- [x] 1.2 实现 Oracle 数据类型到 MySQL 的映射
- [x] 1.3 实现 `CREATE TABLE` 语句转换（移除 tablespace、storage 等）
- [x] 1.4 只保留表结构和数据（CREATE TABLE 和 INSERT 语句）
- [x] 1.5 转换后的文件保存到 `docs/hospital/convertsql/`
- [x] 1.6 移除 PL/SQL 特有命令（prompt、set feedback 等）
- [x] 1.7 支持添加文件名前缀

## 2. Django 管理命令

- [x] 2.1 创建 `python manage.py import_oracle_sql` 命令
- [x] 2.2 读取转换后的 MySQL SQL 文件
- [x] 2.3 支持指定目录或单个文件导入
- [x] 2.4 支持 `--dry-run` 预览模式
- [x] 2.5 添加错误处理和进度显示

## 3. 测试与验证

- [x] 3.1 测试单个文件转换
- [x] 3.2 测试转换后文件只包含表结构和数据
- [x] 3.3 测试导入功能

