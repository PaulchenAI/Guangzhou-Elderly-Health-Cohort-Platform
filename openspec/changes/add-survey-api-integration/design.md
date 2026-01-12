# 技术设计文档

## 上下文

需要对接外部问卷调查系统 API（`http://106.52.105.202:13000`），该系统提供：
- 问卷 Schema 定义接口
- 问卷数据查询接口（需要 JWT 认证）

目标是将外部系统的问卷数据导入到本地 Django 系统中进行管理和查询。

**认证配置**：外部 API 的账号密码配置在 `.env` 文件中：
- `SURVEY_API_URL` - API 地址
- `SURVEY_API_ADMIN` - 管理员账号
- `SURVEY_API_PASSWORD` - 管理员密码

## 目标 / 非目标

### 目标
- 自动同步外部系统的问卷 Schema 定义
- 根据 Schema 生成本地数据存储结构
- 支持批量和增量数据导入
- 支持手动命令和定时任务两种触发方式
- 提供本地数据查询能力
- 提供统一的前端管理页面

### 非目标
- 不实现双向同步（只从外部导入，不推送到外部）
- 不修改外部系统的数据

## 决策

### 决策 1：数据存储方案 - 使用 JSON 字段存储问卷数据

**选择**：使用统一的 `SurveyRecord` 模型 + JSON 字段存储问卷数据

**理由**：
- 外部系统有 20+ 种问卷类型，每种字段不同
- 动态创建表会增加数据库管理复杂度
- JSON 字段支持灵活查询（MySQL 5.7+ / PostgreSQL）
- 便于后续扩展新问卷类型

**考虑的替代方案**：
1. 为每种问卷创建独立表 - 维护成本高，需要动态迁移
2. EAV（实体-属性-值）模式 - 查询性能差，数据完整性难保证

### 决策 2：Schema 存储 - 本地缓存 + 定期同步

**选择**：将外部 Schema 缓存到本地 `SurveySchemaConfig` 表

**理由**：
- 减少对外部 API 的依赖
- 支持离线查询和验证
- 便于追踪 Schema 变更历史

### 决策 3：数据去重 - 基于 surveyId

**选择**：使用外部系统的 `surveyId` 作为唯一标识

**理由**：
- 外部系统已保证 `surveyId` 唯一性
- 支持增量导入时的去重判断
- 便于数据溯源

### 决策 4：JWT 认证 - Token 缓存 + 自动刷新

**选择**：客户端内部缓存 JWT Token，过期前自动刷新

**理由**：
- 减少不必要的认证请求
- 外部 API 的 `/api/search` 等数据接口需要 JWT 认证
- Token 过期时自动重新获取，无需人工干预

### 决策 5：数据导入触发方式 - 手动命令 + 定时任务

**选择**：支持两种触发方式
1. 手动命令：`python manage.py import_survey_data`
2. 定时任务：使用框架自带的 APScheduler 模块

**理由**：
- 手动命令适合初次导入和调试
- 定时任务适合日常增量同步
- APScheduler 已集成在项目中，无需引入新依赖

### 决策 6：前端页面设计 - 参考 table-query 实现

**选择**：创建统一的问卷数据查询页面，参考 `table-query/index.vue` 实现

**理由**：
- 保持 UI 风格一致性
- 复用已验证的交互模式
- 左侧选择器 + 右侧动态表格的布局适合多类型数据展示

## 数据模型设计

```python
# 问卷 Schema 配置
class SurveySchemaConfig(RootModel):
    survey_type = CharField(unique=True)  # 问卷类型标识
    survey_name = CharField()              # 问卷名称
    description = TextField()              # 问卷描述
    schema_json = JSONField()              # Schema 定义（字段、评分规则等）
    guide_url = CharField()                # 使用指南链接
    last_synced_at = DateTimeField()       # 最后同步时间
    is_active = BooleanField(default=True) # 是否激活

# 问卷数据记录
class SurveyRecord(RootModel):
    survey_type = CharField(db_index=True)     # 问卷类型
    survey_id = CharField(unique=True)          # 外部系统问卷ID
    patient_name = CharField(db_index=True)     # 患者姓名
    patient_info = JSONField()                  # 患者基本信息
    survey_data = JSONField()                   # 问卷答案数据
    scores = JSONField()                        # 评分结果
    record_time = DateTimeField(db_index=True)  # 记录时间
    recorder_info = JSONField()                 # 记录者信息
    external_created_at = DateTimeField()       # 外部系统创建时间

# 问卷导入日志
class SurveyImportLog(RootModel):
    batch_id = CharField(db_index=True)         # 批次ID
    survey_type = CharField(db_index=True)      # 问卷类型
    total_count = IntegerField()                # 总数量
    success_count = IntegerField()              # 成功数量
    skip_count = IntegerField()                 # 跳过数量（已存在）
    fail_count = IntegerField()                 # 失败数量
    error_details = JSONField()                 # 错误详情
    start_time = DateTimeField()                # 开始时间
    end_time = DateTimeField()                  # 结束时间
    trigger_type = CharField()                  # 触发类型：manual/scheduled
```

## API 客户端设计

```python
class SurveyAPIClient:
    """问卷调查 API 客户端（含 JWT 认证）"""
    
    def __init__(self):
        self.base_url = settings.SURVEY_API_URL
        self.admin = settings.SURVEY_API_ADMIN
        self.password = settings.SURVEY_API_PASSWORD
        self._token = None
        self._token_expires_at = None
    
    def _get_token(self) -> str:
        """获取或刷新 JWT Token"""
        if self._token and self._token_expires_at > datetime.now():
            return self._token
        # 调用 /api/auth/token 获取新 Token
        response = requests.post(f"{self.base_url}/api/auth/token", json={
            "username": self.admin,
            "password": self.password
        })
        self._token = response.json()["access_token"]
        self._token_expires_at = datetime.now() + timedelta(hours=23)  # 假设24小时有效
        return self._token
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送认证请求"""
        headers = {"Authorization": f"Bearer {self._get_token()}"}
        response = requests.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def get_survey_types(self) -> List[SurveyTypeInfo]:
        """获取所有问卷类型"""
        return self._request("GET", "/api/survey-types")
    
    def get_survey_schema(self, survey_type: str) -> SurveySchema:
        """获取问卷 Schema"""
        return self._request("GET", f"/api/survey-schema/{survey_type}")
    
    def search_surveys(self, params: SearchRequest) -> SearchResult:
        """搜索问卷数据（需要 JWT 认证）"""
        return self._request("POST", "/api/search", json=params)
```

## 定时任务设计

```python
# scheduler/module/survey_tasks.py

def sync_survey_schemas_task(**kwargs):
    """
    定时同步问卷 Schema
    建议调度：每天凌晨执行一次
    Cron 表达式：0 2 * * *
    """
    from core.survey.survey_service import SurveyService
    service = SurveyService()
    result = service.sync_schemas()
    return f"同步完成：新增 {result['created']}，更新 {result['updated']}"

def import_survey_data_task(**kwargs):
    """
    定时增量导入问卷数据
    建议调度：每小时执行一次
    Cron 表达式：0 * * * *
    """
    from core.survey.survey_service import SurveyService
    service = SurveyService()
    result = service.import_data(incremental=True)
    return f"导入完成：成功 {result['success']}，跳过 {result['skipped']}，失败 {result['failed']}"
```

## 前端页面设计

参考 `table-query/index.vue` 实现统一的问卷数据查询页面：

```
/survey/index.vue
├── 左侧：问卷类型选择器（ElMenu）
│   ├── 搜索框
│   └── 问卷类型列表（从 SurveySchemaConfig 获取）
└── 右侧：数据展示区
    ├── 表头信息（问卷名称、描述）
    ├── 搜索表单（根据 Schema 动态生成）
    ├── 数据表格（VxeGrid，列根据 Schema 动态生成）
    └── 导出按钮（Excel/CSV）
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 外部 API 不可用 | 使用本地缓存的 Schema；导入失败时记录日志并支持重试 |
| JWT Token 过期 | 客户端内部自动刷新 Token |
| Schema 变更 | 同步时检测变更并记录；支持数据迁移 |
| 大量数据导入性能 | 使用批量插入；支持分页导入；显示进度 |
| 网络超时 | 设置合理的超时时间（30秒）；支持断点续传 |
| 认证信息泄露 | 敏感配置存储在 `.env` 文件中，不提交到版本控制 |

## 迁移计划

1. 创建新模型并执行迁移
2. 配置 `.env` 文件中的 API 认证信息
3. 运行 `sync_survey_schemas` 同步 Schema
4. 运行 `import_survey_data` 导入历史数据
5. 验证数据完整性
6. 运行 `init_survey_menus` 初始化菜单
7. 配置定时任务（通过 API 或管理命令创建 SchedulerJob 记录）

## 已确定事项

1. ✅ **JWT 认证**：需要使用 JWT 验证才能访问数据库查询接口（`/api/search`）
2. ✅ **数据导入触发方式**：支持手动命令 + 定时任务（使用框架自带的 APScheduler 模块）
3. ✅ **前端管理页面**：需要统一的问卷数据查询页面，参考 `table-query/index.vue` 实现

## 待决问题

1. 定时任务的默认调度频率？（建议：Schema 同步每天一次，数据导入每小时一次）
2. 是否需要前端页面展示导入日志？

