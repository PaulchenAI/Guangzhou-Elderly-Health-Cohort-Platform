# 变更：对接外部问卷调查 API 并导入数据

## 为什么

需要对接外部问卷调查系统（`http://106.52.105.202:13000`），获取问卷结构定义并导入历史问卷数据到本地数据库，以便在本地系统中查询和管理问卷数据。

## 变更内容

1. **问卷 Schema 获取与解析**
   - 调用外部 API `/api/survey-types` 获取所有问卷类型列表
   - 调用 `/api/survey-schema/{survey_type}` 获取每个问卷的详细字段定义
   - 解析 Schema 生成本地数据库模型

2. **本地数据库模型生成**
   - 根据问卷 Schema 动态生成 Django Model
   - 支持的问卷类型包括：
     - Fried 衰弱评估
     - Rockwood 临床衰弱量表
     - GPM 疼痛量表
     - NRS 疼痛评估
     - PSQI 睡眠质量评估
     - HAMD 抑郁评估
     - 等其他问卷类型

3. **数据导入功能**
   - 调用外部 API `/api/search` 查询问卷数据（需要 JWT 认证）
   - 支持按问卷类型、时间范围、患者姓名等条件查询
   - 批量导入数据到本地数据库
   - 支持增量导入（避免重复数据）
   - **支持手动命令 + 定时任务两种触发方式**

4. **管理命令**
   - `sync_survey_schemas` - 同步问卷 Schema 并生成/更新模型
   - `import_survey_data` - 从外部 API 导入问卷数据
   - `init_survey_menus` - 初始化问卷管理菜单

5. **定时任务**
   - 使用框架自带的 APScheduler 模块
   - 支持定时同步 Schema
   - 支持定时增量导入问卷数据

6. **前端管理页面**
   - 统一的问卷数据查询页面（参考 `table-query/index.vue` 实现）
   - 左侧问卷类型选择器
   - 右侧动态表格展示问卷数据
   - 支持搜索、分页、导出功能

## 配置说明

外部 API 认证信息配置在 `/mnt/f/work/zq-platform/backend-django/.env` 文件中：

```env
# 问卷调查 API 配置
SURVEY_API_URL=http://106.52.105.202:13000
SURVEY_API_ADMIN=<管理员账号>
SURVEY_API_PASSWORD=<管理员密码>
```

## 影响

- 受影响规范：新增 `survey-integration` 功能
- 受影响代码：
  - `backend-django/core/survey/` - 新增问卷模块
  - `backend-django/core/management/commands/` - 新增管理命令
  - `backend-django/scheduler/module/` - 新增定时任务函数
  - `web/apps/web-ele/src/views/survey/` - 新增前端页面
  - `web/apps/web-ele/src/api/core/survey.ts` - 新增前端 API

