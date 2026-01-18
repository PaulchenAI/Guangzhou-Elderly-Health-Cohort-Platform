## 新增需求

### 需求：Django 模型外键关系生成命令

系统必须提供 Django management command 来自动提取 Django 模型中的外键关系并导入到 `table_foreignkey_metadata` 表。

#### 场景：扫描 Django 模型并提取外键关系

- **当** 用户执行 `python manage.py generate_django_foreignkey_metadata`
- **那么** 系统扫描所有已注册的 Django 模型
- **并且** 提取所有 ForeignKey 字段的关系信息
- **并且** 提取所有 ManyToManyField 字段的关系信息（包括中间表）
- **并且** 将关系信息插入到 `table_foreignkey_metadata` 表

#### 场景：预览模式

- **当** 用户执行 `python manage.py generate_django_foreignkey_metadata --dry-run`
- **那么** 系统显示将要导入的外键关系列表
- **并且** 不执行实际的数据库插入操作

#### 场景：清空后导入

- **当** 用户执行 `python manage.py generate_django_foreignkey_metadata --truncate`
- **那么** 系统在导入前删除所有 `source_file` 为 `django_models` 的记录
- **并且** 执行新的导入操作

#### 场景：指定扫描的 app

- **当** 用户执行 `python manage.py generate_django_foreignkey_metadata --app-labels core,common`
- **那么** 系统仅扫描指定的 app 中的模型

#### 场景：排除指定的 app

- **当** 用户执行 `python manage.py generate_django_foreignkey_metadata --exclude-apps admin,auth,contenttypes,sessions`
- **那么** 系统排除指定的 app，扫描其余所有 app

#### 场景：外键关系数据格式

- **当** 系统提取 ForeignKey 关系
- **那么** 将以下信息插入 `table_foreignkey_metadata` 表：
  - `source_table`：源表名（Django 模型的 db_table）
  - `source_columns`：源字段列表（外键字段的 db_column 或字段名 + "_id"）
  - `target_table`：目标表名（关联模型的 db_table）
  - `target_columns`：目标字段列表（通常为 "id"）
  - `constraint_name`：约束名（格式：`fk_{source_table}_{field_name}`）
  - `on_delete`：删除规则（CASCADE/SET_NULL/PROTECT/DO_NOTHING）
  - `source_file`：来源标识（固定为 `django_models`）

#### 场景：ManyToMany 关系数据格式

- **当** 系统提取 ManyToManyField 关系
- **那么** 将中间表的两个外键关系分别插入 `table_foreignkey_metadata` 表
- **并且** `source_table` 为中间表名
- **并且** `source_file` 为 `django_models`

#### 场景：导入报告

- **当** 导入完成
- **那么** 系统输出以下统计信息：
  - 扫描的 app 数量
  - 扫描的模型数量
  - 提取的 ForeignKey 数量
  - 提取的 ManyToManyField 数量
  - 成功导入的记录数
  - 失败的记录数（如有）
