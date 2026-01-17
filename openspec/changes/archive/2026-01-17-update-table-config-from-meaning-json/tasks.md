# 任务清单

## 1. 实现 meaning.json 加载功能

- [x] 1.1 新增 `_load_meaning_files(meaning_dir)` 方法，扫描目录下所有 `*_meaning.json` 文件（忽略 `all_meanings.json`）
- [x] 1.2 解析 JSON 文件，构建 `{table_name: {table_meaning, fields: {field_name: field_meaning}}}` 结构
- [x] 1.3 处理文件读取错误，输出警告但不中断执行

## 2. 更新命令参数

- [x] 2.1 新增 `--meaning-dir` 参数，指定 meaning.json 文件目录
- [x] 2.2 默认值设为 `docs/hospital/commentsql`（如果存在）
- [x] 2.3 新增 `--table-prefix` 参数，配置数据库表名前缀（匹配时忽略）

## 3. 修改名称获取逻辑

- [x] 3.1 修改 `_generate_display_name()` 方法，增加 meaning.json 优先级
- [x] 3.2 修改 `_detect_table_structure()` 方法，字段 displayName 增加 meaning.json 优先级
- [x] 3.3 确保优先级顺序：COMMENT > meaning.json > config-file > 原名

## 4. 测试验证

- [x] 4.1 使用 `--list` 验证表名中文显示
- [x] 4.2 使用 `--update` 更新现有配置并验证字段中文名称
- [x] 4.3 验证无 meaning.json 时的降级行为（通过 `--table-prefix gzlry_` 成功匹配 953 个表）
