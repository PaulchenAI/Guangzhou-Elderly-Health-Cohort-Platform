# 设计文档：OpenAPI 描述规范化

## 上下文

### 背景
- backend-django 使用 Django Ninja 框架，原生支持 OpenAPI 3.0
- 当前 269 个 API 端点中，约 191 个（71%）有中文 summary，78 个（29%）为英文
- AIagent 的意图匹配依赖 summary 和 description 进行语义搜索
- 英文 summary 如 "Create Dict" 无法被中文意图 "创建字典" 准确匹配

### 约束
- 必须保持 API 功能不变
- 必须遵循现有代码风格（中文注释、UTF-8 编码）
- 应尽量减少对现有代码的修改范围

### 利益相关者
- AIagent 开发者：需要准确的 API 语义描述
- 后端开发者：需要清晰的 API 开发规范
- 前端开发者：需要可读的 API 文档

## 目标 / 非目标

### 目标
- 所有 API 端点使用中文 summary
- 建立统一的 OpenAPI 描述规范
- 提升 AI 意图理解准确率

### 非目标
- 不修改 API 功能逻辑
- 不修改 API 路径或参数
- 不重构代码结构

## 决策

### 决策 1：Summary 命名规范

**选择**：动词 + 名词 格式

**规范**：
```python
# 格式：[动词][对象名词]（[补充说明]）
summary="创建字典"
summary="获取字典列表（分页）"
summary="删除字典"
summary="更新字典"
summary="批量删除字典"
```

**动词标准化**：
| 操作类型 | 推荐动词 | 示例 |
|---------|---------|------|
| 创建 | 创建 | 创建用户 |
| 读取单个 | 获取 | 获取用户详情 |
| 读取列表 | 获取 | 获取用户列表（分页） |
| 读取全部 | 获取所有 | 获取所有用户 |
| 更新 | 更新 | 更新用户 |
| 部分更新 | 部分更新 | 部分更新用户 |
| 删除 | 删除 | 删除用户 |
| 批量删除 | 批量删除 | 批量删除用户 |
| 搜索 | 搜索 | 搜索用户 |
| 导出 | 导出 | 导出用户数据 |
| 导入 | 导入 | 导入用户数据 |

### 决策 2：Description 规范

**选择**：结构化描述格式

**规范**：
```python
description="""
获取字典列表（分页）

查询参数:
- page: 页码（默认 1）
- page_size: 每页数量（默认 10）
- name: 字典名称（模糊查询）
- code: 字典编码（精确匹配）

返回:
- items: 字典列表
- total: 总数
"""
```

### 决策 3：Tags 规范

**选择**：保持现有英文 Tag 命名（暂不修改）

**原因**：
- 现有 `backend-api-development-guide.md` 使用 `tags=["Core-User"]` 格式
- 部分模块已使用中文 tags（如 "问卷管理"），存在不一致
- Tags 主要用于 Swagger UI 分组，对 AI 意图匹配影响较小
- 修改 tags 需要同时更新路由注册代码和开发规范文档

**后续优化**：
可作为单独变更提案处理，统一 tags 命名规范：
| 当前 Tag | 建议 Tag |
|---------|-----------|
| Core-Dict | 字典管理 |
| Core-User | 用户管理 |
| Core-Role | 角色管理 |
| Core-Auth | 认证授权 |
| ... | ... |

## 实施策略

### 批量修改方案

1. **识别需要修改的文件**：
   ```bash
   grep -r "@router" backend-django/core --include="*_api.py" | grep -v "summary="
   ```

2. **按模块逐个修改**：
   - 优先修改 AIagent 常用的模块（survey、table_query）
   - 然后修改基础模块（dict、dict_item）
   - 最后修改其他模块

3. **验证修改**：
   - 启动服务检查 OpenAPI Schema
   - 使用 AIagent CLI 测试意图匹配

## 风险 / 权衡

### 风险 1：修改范围大
- **风险**：涉及多个模块，可能引入错误
- **缓解**：逐模块修改，每次修改后验证

### 风险 2：中英文混用
- **风险**：部分开发者习惯英文命名
- **缓解**：在开发规范中明确要求中文 summary

## 待决问题

1. ~~**是否需要修改 Tags？**~~（已决定）
   - 本次变更不修改 Tags
   - 可作为后续独立变更处理

2. **是否需要添加 examples？**
   - OpenAPI 支持 request/response examples
   - 建议：作为后续优化，本次不涉及

3. **是否需要同步更新前端 API 类型定义？**
   - 前端使用 `docs/frontend-development-guide.md` 中的 API 命名规范
   - summary 修改不影响前端代码，无需同步更新

### 决策 4：增强 AI 理解能力

**问题**：简短的 summary 无法让 AI 理解复杂 API 的用法和 API 之间的关系

**解决方案**：

#### 4.1 OpenAPI Tags Description（模块级说明）

Django Ninja 1.x 不直接支持 `openapi_tags` 参数，需要通过自定义 `NinjaAPI` 子类实现。

在 `application/main.py` 中：

```python
# OpenAPI Tags 描述
OPENAPI_TAGS = [
    {
        "name": "文件管理",
        "description": "文件上传下载模块。分块上传顺序: POST /chunk/init → POST /chunk/upload(循环) → POST /chunk/merge"
    },
    # ...
]

class CustomNinjaAPI(NinjaAPI):
    """自定义 NinjaAPI，添加 OpenAPI tags description"""
    
    def get_openapi_schema(self, *args, **kwargs):
        schema = super().get_openapi_schema(*args, **kwargs)
        schema["tags"] = OPENAPI_TAGS
        return schema

api = CustomNinjaAPI(auth=[BearerAuth(), ApiKey()], renderer=MyJsonRenderer())
```

#### 4.2 增强 Docstring 结构（单个 API）

对于复杂 API，docstring 应包含：
- **调用顺序**：标明前置条件和后续操作
- **请求参数**：详细的参数说明
- **返回值**：字段含义说明
- **使用示例**：典型调用场景

```python
def init_chunk_upload(request, data: InitChunkUploadSchemaIn):
    """
    初始化分块上传（大文件上传第一步）
    
    **调用顺序**: 本接口 → /chunk/upload（循环） → /chunk/merge
    
    请求参数:
    - filename: 文件名
    - total_size: 文件总大小（字节）
    - chunk_size: 分块大小（建议 5MB）
    
    返回值:
    - upload_id: 上传会话ID（后续接口需要）
    - total_chunks: 总分块数
    - file_exists: 是否已存在（秒传）
    
    **使用示例**:
    1. 前端计算文件 MD5
    2. 调用本接口获取 upload_id
    3. 如果 file_exists=true，跳过上传
    """
```

#### 4.3 关键字和同义词

在 description 中包含业务相关的同义词，帮助 AI 匹配意图：
- "问卷数据" / "问卷记录" / "调查数据"
- "分块上传" / "大文件上传" / "断点续传"

**已实施**：
- `application/main.py` 添加了 `openapi_tags` 模块级描述
- `chunk_upload_api.py` 增强了分块上传相关 API 的 docstring
- `survey_api.py` 增强了问卷查询相关 API 的 docstring
