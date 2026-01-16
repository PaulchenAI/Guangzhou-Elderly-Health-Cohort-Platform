## 1. 实施

- [x] 1.1 修改 `_detect_table_structure` 方法，从数据库获取表和字段的 COMMENT
- [x] 1.2 修改 `_generate_display_name` 方法，优先使用表 COMMENT，其次使用配置文件，最后使用表名
- [x] 1.3 实现从 JSON 配置文件读取表名和字段名映射的功能
- [x] 1.4 修改字段配置生成逻辑，使用字段 COMMENT 或配置文件中的映射作为 `displayName`
- [x] 1.5 添加 `--config-file` 参数，允许指定外部配置文件路径
- [x] 1.6 更新命令帮助文档和使用示例

## 2. 移除前缀映射

- [x] 2.1 删除 `TABLE_PREFIX_NAMES` 常量定义
- [x] 2.2 从 `_generate_display_name` 方法中移除前缀映射逻辑
- [x] 2.3 更新规范文档，移除前缀映射优先级
- [x] 2.4 更新设计文档，移除前缀映射说明

## 3. 验证

- [x] 3.1 测试从数据库 COMMENT 获取表名和字段名
  - ✅ `_get_table_comment()` 方法使用 INFORMATION_SCHEMA.TABLES 查询表 COMMENT
  - ✅ `_detect_table_structure()` 方法使用 INFORMATION_SCHEMA.COLUMNS 查询字段 COMMENT
  - ✅ 使用参数化查询防止 SQL 注入
  - ✅ 正确处理空值和异常情况

- [x] 3.2 测试从 JSON 配置文件读取映射
  - ✅ `_load_name_mapping()` 方法支持默认路径和自定义路径
  - ✅ 使用 UTF-8 编码读取配置文件
  - ✅ 正确解析 JSON 格式

- [x] 3.3 测试优先级：COMMENT > 配置文件 > 表名
  - ✅ 表名优先级：`_generate_display_name()` 方法正确实现（第342-355行）
  - ✅ 字段名优先级：`_detect_table_structure()` 方法正确实现（第252-259行）
  - ✅ 优先级逻辑清晰，按顺序检查

- [x] 3.4 测试配置文件不存在或格式错误时的降级处理
  - ✅ 配置文件不存在时返回 None，不影响主流程（第305-307行）
  - ✅ JSON 格式错误时捕获异常并显示警告，返回 None（第313-317行）
  - ✅ 其他异常时捕获并显示警告，返回 None（第318-322行）
  - ✅ name_mapping 为 None 时代码安全处理（第350行、第256行）
