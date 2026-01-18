## 1. 规范与设计

- [x] 1.1 定义字段描述的标准格式规范
- [x] 1.2 整理所有需要增强描述的 ForeignKey 字段列表

## 2. 实施 - Management Command

- [x] 2.1 创建 `enhance_field_descriptions.py` management command
- [x] 2.2 实现 Django 模型扫描逻辑（遍历所有 ForeignKey 和 ManyToManyField）
- [x] 2.3 实现字段描述生成逻辑（根据关联关系生成描述）
- [x] 2.4 实现 `--dry-run` 预览模式
- [x] 2.5 实现 `--output` 输出到文件功能

## 3. 实施 - 更新现有字段描述

- [x] 3.1 更新 `core/user/user_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.2 更新 `core/user/user_schema.py` 中的关联字段 description
- [x] 3.3 更新 `core/post/post_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.4 更新 `core/permission/permission_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.5 更新 `core/menu/menu_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.6 更新 `core/dept/dept_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.7 更新 `core/dict_item/dict_item_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.8 更新 `core/file_manager/file_manager_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.9 更新 `common/fu_model.py` 基类中的 ForeignKey 字段 help_text
- [x] 3.10 更新 `core/role/role_model.py` 中的 ManyToManyField 字段 help_text

## 4. 验证

- [x] 4.1 运行 `enhance_field_descriptions --dry-run` 验证扫描结果
- [x] 4.2 验证所有 44 个关联字段已增强（需要更新: 0, 已增强: 44）
- [x] 4.3 Management command 功能正常运行
