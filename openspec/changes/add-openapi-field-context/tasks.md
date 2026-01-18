## 1. 规范与设计

- [x] 1.1 定义字段描述的标准格式规范
- [x] 1.2 整理所有需要增强描述的 ForeignKey 字段列表

## 2. 实施 - Management Command

- [x] 2.1 创建 `enhance_field_descriptions.py` management command
- [x] 2.2 实现 Django 模型扫描逻辑（遍历所有 ForeignKey 和 ManyToManyField）
- [x] 2.3 实现字段描述生成逻辑（根据关联关系生成描述）
- [x] 2.4 实现 `--dry-run` 预览模式
- [x] 2.5 实现 `--output` 输出到文件功能

## 3. 实施 - 更新 Model 字段描述

- [x] 3.1 更新 `core/user/user_model.py` 中的 ForeignKey/M2M 字段 help_text
- [x] 3.2 更新 `core/post/post_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.3 更新 `core/permission/permission_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.4 更新 `core/menu/menu_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.5 更新 `core/dept/dept_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.6 更新 `core/dict_item/dict_item_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.7 更新 `core/file_manager/file_manager_model.py` 中的 ForeignKey 字段 help_text
- [x] 3.8 更新 `core/role/role_model.py` 中的 ManyToManyField 字段 help_text
- [x] 3.9 更新 `common/fu_model.py` 基类中的 ForeignKey 字段 help_text

## 4. 实施 - 更新 Schema 字段描述

- [x] 4.1 更新 `core/user/user_schema.py` 中的关联字段 description
- [x] 4.2 更新 `core/post/post_schema.py` 中的关联字段 description
- [x] 4.3 更新 `core/dept/dept_schema.py` 中的关联字段 description
- [x] 4.4 更新 `core/menu/menu_schema.py` 中的关联字段 description
- [x] 4.5 更新 `core/permission/permission_schema.py` 中的关联字段 description
- [x] 4.6 更新 `core/role/role_schema.py` 中的关联字段 description
- [x] 4.7 更新 `core/dict_item/dict_item_schema.py` 中的关联字段 description
- [x] 4.8 更新 `core/file_manager/file_manager_schema.py` 中的关联字段 description
- [x] 4.9 更新 `core/login_log/login_log_schema.py` 中的关联字段 description

## 5. 验证

- [x] 5.1 运行 `enhance_field_descriptions --dry-run` 验证 Model 字段描述
- [x] 5.2 验证所有 44 个关联字段已增强（Model 层）
- [x] 5.3 验证 Schema 层关联字段描述已添加
- [x] 5.4 Management command 功能正常运行
