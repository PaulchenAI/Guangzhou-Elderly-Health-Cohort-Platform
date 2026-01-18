## 新增需求

### 需求：ForeignKey 字段描述规范

所有 ForeignKey 字段的 `help_text` 必须包含关联关系信息，便于 AI 理解表之间的关联。

#### 场景：标准 ForeignKey 字段描述

- **当** 定义 ForeignKey 字段
- **那么** `help_text` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}，关联 {模型名} 模型/表 {目标表db_table}.{目标字段}`
- **例如** `help_text="所属部门，关联 Dept 模型/表 core_dept.id"`

#### 场景：自引用 ForeignKey 字段描述

- **当** 定义自引用 ForeignKey 字段（如 parent、manager）
- **那么** `help_text` 必须说明是自引用关系
- **并且** 格式为 `{业务含义}，自引用 {模型名} 模型/表 {当前表db_table}.{目标字段}`
- **例如** `help_text="上级部门，自引用 Dept 模型/表 core_dept.id"`

#### 场景：可空 ForeignKey 字段描述

- **当** 定义可空的 ForeignKey 字段（null=True）
- **那么** `help_text` 应说明可空情况
- **例如** `help_text="所属部门（可空），关联 Dept 模型/表 core_dept.id"`

---

### 需求：Schema 关联字段描述规范

所有 Schema 中的关联字段（如 `dept_id`、`manager_id`）的 `description` 必须包含关联关系信息。

#### 场景：Schema 关联字段描述格式

- **当** 定义 Schema 中的关联字段
- **那么** `description` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}（关联 {模型名} 模型/表 {目标表db_table}.{目标字段}）`
- **例如** `description="所属部门ID（关联 Dept 模型/表 core_dept.id）"`

#### 场景：Schema 自引用字段描述格式

- **当** 定义 Schema 中的自引用字段
- **那么** `description` 必须说明是自引用关系
- **并且** 格式为 `{业务含义}（自引用 {模型名} 模型/表 {当前表db_table}.{目标字段}）`
- **例如** `description="上级部门ID（自引用 Dept 模型/表 core_dept.id）"`

---

### 需求：字段描述增强工具

系统必须提供 Django management command 来自动生成字段描述增强建议。

#### 场景：扫描并生成描述建议

- **当** 用户执行 `python manage.py enhance_field_descriptions`
- **那么** 系统扫描所有已注册的 Django 模型
- **并且** 识别所有 ForeignKey 和 ManyToManyField 字段
- **并且** 生成符合规范的字段描述建议
- **并且** 输出当前描述与建议描述的对比

#### 场景：预览模式

- **当** 用户执行 `python manage.py enhance_field_descriptions --dry-run`
- **那么** 系统仅显示建议，不做任何修改
- **并且** 输出需要更新的字段列表

#### 场景：输出到文件

- **当** 用户执行 `python manage.py enhance_field_descriptions --output suggestions.json`
- **那么** 系统将建议输出到指定文件
- **并且** 文件格式为 JSON，包含模型名、字段名、当前描述、建议描述

#### 场景：指定扫描范围

- **当** 用户执行 `python manage.py enhance_field_descriptions --app-labels core`
- **那么** 系统仅扫描指定 app 中的模型

#### 场景：排除指定 app

- **当** 用户执行 `python manage.py enhance_field_descriptions --exclude-apps admin,auth,contenttypes,sessions`
- **那么** 系统排除 Django 内置 app，扫描其余所有 app

#### 场景：JSON 输出格式

- **当** 用户指定 `--format json`
- **那么** 输出格式为：
```json
{
  "suggestions": [
    {
      "model": "core.User",
      "field": "dept",
      "field_type": "ForeignKey",
      "current_help_text": "所属部门",
      "suggested_help_text": "所属部门，关联 Dept 模型/表 core_dept.id",
      "target_model": "core.Dept",
      "target_table": "core_dept",
      "target_field": "id"
    }
  ],
  "summary": {
    "total_models": 20,
    "total_fields": 15,
    "fields_needing_update": 10
  }
}
```

---

### 需求：ManyToManyField 字段描述规范

ManyToManyField 字段的 `help_text` 必须说明关联的目标表和中间表信息。

#### 场景：标准 ManyToMany 字段描述

- **当** 定义 ManyToManyField 字段
- **那么** `help_text` 必须包含业务含义、模型名和关联关系
- **并且** 格式为 `{业务含义}，多对多关联 {模型名} 模型/表 {目标表db_table}，中间表 {中间表db_table}`
- **例如** `help_text="关联的角色，多对多关联 Role 模型/表 core_role，中间表 core_user_core_roles"`

#### 场景：自定义中间表的 ManyToMany 字段描述

- **当** 定义使用 `through` 参数的 ManyToManyField 字段
- **那么** `help_text` 必须说明自定义中间表
- **例如** `help_text="关联的权限，多对多关联 Permission 模型/表 core_permission，中间表 core_role_permissions"`
