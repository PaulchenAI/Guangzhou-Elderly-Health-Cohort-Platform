## 上下文

当前 AI Agent 在处理 Django API 时，依赖 OpenAPI Schema 来理解 API 结构和数据模型。然而，OpenAPI Schema 中的字段描述仅包含业务含义（如"所属部门"），缺少关联关系的技术细节（如"关联 core_dept.id"）。

这导致 AI 在以下场景中表现不佳：
1. 跨表查询：无法正确生成 JOIN 语句
2. 数据关联：无法理解字段之间的引用关系
3. 级联操作：无法预测删除/更新操作的影响

## 目标 / 非目标

### 目标
- 让 AI 能够从 OpenAPI Schema 中直接理解表之间的关联关系
- 提供标准化的字段描述格式，便于 AI 解析
- 提供自动化工具生成字段描述建议

### 非目标
- 不修改现有的外键关系元数据 API（已有 `foreignkey-api` 规范）
- 不改变 Django Model 的实际关联关系
- 不自动修改代码（仅生成建议）

## 决策

### 决策 1：字段描述格式

**选择**：使用结构化的描述格式 `{业务含义}，关联 {目标表}.{目标字段}`

**理由**：
- 保留原有的业务含义描述，不影响人类阅读
- 添加明确的关联关系信息，便于 AI 解析
- 使用中文逗号分隔，与现有描述风格一致

**示例**：
```python
# Model 字段
dept = models.ForeignKey(
    to="core.Dept",
    help_text="所属部门，关联 core_dept.id",
)

# Schema 字段
dept_id: Optional[str] = Field(None, description="所属部门ID（关联 core_dept.id）")
```

### 决策 2：Management Command 设计

**选择**：创建独立的 `enhance_field_descriptions` 命令，仅生成建议，不自动修改代码

**理由**：
- 字段描述涉及业务语义，需要人工审核
- 避免自动修改代码带来的风险
- 便于增量更新和版本控制

**命令参数**：
```bash
python manage.py enhance_field_descriptions [options]

Options:
  --dry-run           预览模式，仅显示建议
  --output FILE       输出建议到文件
  --app-labels APPS   指定要扫描的 app（逗号分隔）
  --exclude-apps APPS 排除指定的 app（逗号分隔）
  --format FORMAT     输出格式：text/json（默认 text）
```

### 决策 3：描述增强的优先级

**选择**：优先增强以下类型的字段：
1. ForeignKey 字段（最重要，直接影响 JOIN 查询）
2. ManyToManyField 字段（次要，通过中间表关联）
3. 自引用字段（如 parent、manager）

**理由**：
- ForeignKey 是最常见的关联类型
- 优先处理核心业务模块（core/*）
- 自引用字段需要特殊说明（如"自引用 core_dept.id"）

## 风险 / 权衡

### 风险 1：描述过长影响可读性
- **缓解**：保持描述简洁，仅添加必要的关联信息

### 风险 2：描述与实际关联不一致
- **缓解**：使用 management command 自动生成，确保一致性

### 风险 3：AI 解析格式变化
- **缓解**：使用标准化格式，并在 AI 提示词中说明格式规范

## 迁移计划

1. **阶段 1**：创建 management command，生成建议
2. **阶段 2**：人工审核建议，更新核心模块（core/*）的字段描述
3. **阶段 3**：更新其他模块的字段描述
4. **阶段 4**：更新 AI Agent 的提示词，说明新的描述格式

## 待决问题

- [ ] 是否需要在 OpenAPI Schema 中添加专门的 `x-relation` 扩展字段？
- [ ] 是否需要更新 AI Agent 的 API 摘要生成逻辑？
