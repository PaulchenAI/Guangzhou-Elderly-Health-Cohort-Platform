# 设计文档：Django API 上下文优化

## 上下文

当前 Django API 智能体在初始化时通过 `get_api_summary_for_ai()` 加载所有 288 个 API 端点的完整描述到 LLM 上下文中。随着 API 数量增长，存在以下问题：

1. **上下文超限风险**：288 个端点的完整描述可能超过 8000 Token，接近 LLM 上下文窗口限制
2. **效率低下**：大部分 API 与用户意图无关，浪费上下文空间
3. **脚本无法复用**：生成的脚本没有持久化，相似意图需要重复生成

## 目标 / 非目标

### 目标
- 将 API 上下文控制在可配置的 Token 限制内（默认 4000 Token）
- 保持 API 选择的准确性
- 实现脚本持久化和 RAG 检索复用

### 非目标
- 不改变现有的 API 调用逻辑
- 不改变 OpenAPI Schema 的加载方式
- 不实现复杂的脚本版本管理

## 决策

### 决策 1：分层 API 摘要

**方案**：实现三层 API 摘要机制

```
第一层（紧凑）：Tag 统计
├── Core-Auth (5 个端点): 用户认证、登录、Token 管理
├── Core-User (12 个端点): 用户管理、查询、增删改
├── Survey (8 个端点): 问卷管理、数据查询
└── ... 共 15 个分类，288 个端点

第二层（Tag 详情）：指定 Tag 的端点列表
├── GET /api/core/user/list - 获取用户列表
├── GET /api/core/user/{id} - 获取用户详情
└── POST /api/core/user - 创建用户

第三层（端点详情）：完整的参数和响应描述
└── GET /api/core/user/list
    ├── 参数: page, pageSize, keyword, status
    └── 响应: {total, list: [{id, username, ...}]}
```

**理由**：
- 第一层约 500 Token，可快速定位相关 Tag
- 第二层按需加载，每个 Tag 约 200-500 Token
- 第三层仅在确定 API 后加载，避免浪费

### 决策 2：两阶段迭代 API 选择

**方案**：LLM 分两阶段迭代确认 API 选择

```
阶段 1：意图 → 选择相关 Tags（select_relevant_tags）
┌─────────────────────────────────────────────────────────────┐
│ 输入：用户意图 + 紧凑摘要（Tag 列表 + 端点数量）              │
│ LLM 任务：从 15 个 Tag 中选择 1-3 个最相关的分类             │
│ 输出：["Core-Auth", "Core-User"]                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
阶段 2：Tags → 获取详细 API 信息（get_detailed_api_summary）
┌─────────────────────────────────────────────────────────────┐
│ 加载选中 Tags 的完整端点列表（包含路径、方法、参数）           │
│                                                              │
│ Core-Auth API 端点列表（5 个端点）                           │
│ - POST /api/core/login                                       │
│   - operation_id: core_login                                 │
│   - 参数: username, password                                 │
│                                                              │
│ Core-User API 端点列表（12 个端点）                          │
│ - GET /api/core/user                                         │
│   - operation_id: core_user_list                             │
│   - 参数: page, pageSize, keyword                            │
│ - GET /api/core/user/{id}                                    │
│ - POST /api/core/user                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
阶段 3：详细信息 → 选择具体端点（plan_intent）
┌─────────────────────────────────────────────────────────────┐
│ LLM 基于详细 API 信息规划执行步骤                            │
│ 选择：POST /api/core/login → GET /api/core/user             │
│ ⚠️ LLM 只能选择上下文中明确列出的路径                        │
└─────────────────────────────────────────────────────────────┘
```

**实际效果**：
```
用户: "查询用户列表"

📂 阶段1: 分析意图，选择相关 API 分类...
   选中分类: Core-Auth, Core-User

📋 阶段2: 获取选中分类的详细 API 信息...
   已加载 2 个分类的详细端点信息

[计划] 目标: 查询用户列表
[计划]   步骤1: POST /api/core/login
[计划]   步骤2: GET /api/core/user  ← 正确路径！
```

**考虑的替代方案**：
- 一次性加载所有端点：Token 超限风险，且 LLM 容易幻觉编造路径
- 纯向量检索：可能遗漏语义相关但关键词不匹配的 API
- 只给紧凑摘要：LLM 没有看到具体路径，会自行编造（如 `/api/core/user/list`）

**理由**：
- 阶段 1 缩小搜索范围，约 500 Token
- 阶段 2 提供精确的 API 路径信息，避免幻觉
- 整体 Token 控制在 2000-3000（紧凑概览 + 2-3 个 Tag 详情）
- 确保 LLM 只使用真实存在的 API 路径

### 决策 3：执行记录持久化结构（成功+失败全记录）

**方案**：按日期和意图哈希分类存储，**成功和失败都必须保存**

```
data/execution_history/
├── 2026/
│   └── 01/
│       └── 17/
│           ├── a1b2c3d4_查询用户列表_success.py
│           ├── a1b2c3d4_查询用户列表_success.json
│           ├── e5f6g7h8_查询问卷数据_failed.py
│           └── e5f6g7h8_查询问卷数据_failed.json
└── index/
    └── history.json  # 执行记录索引（用于快速检索）
```

**成功记录元数据**：
```json
{
  "id": "a1b2c3d4",
  "intent": "查询用户列表前10个",
  "status": "success",
  "apis_used": ["core_user_list"],
  "created_at": "2026-01-17T10:30:00",
  "execution_output": "返回 10 条记录",
  "script_path": "2026/01/17/a1b2c3d4_查询用户列表_success.py"
}
```

**失败记录元数据**：
```json
{
  "id": "e5f6g7h8",
  "intent": "查询问卷数据中的户外活动",
  "status": "failed",
  "apis_used": ["survey_query"],
  "created_at": "2026-01-17T11:00:00",
  "error_type": "parameter_error",
  "error_message": "缺少必需参数 table_name",
  "script_path": "2026/01/17/e5f6g7h8_查询问卷数据_failed.py"
}
```

**理由**：
- 成功记录便于直接复用
- 失败记录帮助 LLM 避免同样的错误
- 按状态分文件名便于快速识别

### 决策 4：强制优先检索历史指令

**方案**：每次新指令必须先检索历史，作为工作流第一步

```
用户意图 → [强制] 历史检索 → 分析检索结果 → 计划生成 → 脚本生成 → 执行 → 保存记录
                  │
                  ├── 找到相似成功记录 → 作为参考/直接复用
                  └── 找到相似失败记录 → 告知 LLM 避免同样错误
```

**理由**：
- 避免重复生成相同的脚本
- 从失败记录中学习，避免重复错误
- 提高脚本生成成功率

### 决策 5：相似度计算方式

**方案**：使用向量余弦相似度 + 多维度加权计算 + 意图归一化

#### 5.0 意图归一化（关键步骤）

**问题**：用户意图中可能包含数目、翻页等参数，如：
- "查询用户列表前10个"
- "查询用户列表前5个"  
- "查询第2页用户"
- "查询用户列表"

这些本质上是**同一个核心意图**，应该能相互匹配。

**方案**：在计算相似度前，先对意图进行归一化处理

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class NormalizedIntent:
    """归一化后的意图"""
    core_intent: str           # 核心意图（去除参数）
    original_intent: str       # 原始意图
    limit: Optional[int]       # 数目限制
    page: Optional[int]        # 页码
    page_size: Optional[int]   # 每页数量
    order_by: Optional[str]    # 排序字段
    order_desc: bool = False   # 是否倒序

def normalize_intent(intent: str) -> NormalizedIntent:
    """
    意图归一化：提取核心意图和参数信息
    
    示例：
    - "查询用户列表前10个" → core="查询用户列表", limit=10
    - "查询第2页用户" → core="查询用户", page=2
    - "查询用户列表按创建时间倒序" → core="查询用户列表", order_by="创建时间", order_desc=True
    """
    original = intent
    core = intent
    limit, page, page_size, order_by, order_desc = None, None, None, None, False
    
    # 提取数目参数
    patterns_limit = [
        (r'前(\d+)个', 1),
        (r'(\d+)条', 1),
        (r'limit\s*(\d+)', 1),
        (r'top\s*(\d+)', 1),
    ]
    for pattern, group in patterns_limit:
        match = re.search(pattern, core, re.IGNORECASE)
        if match:
            limit = int(match.group(group))
            core = re.sub(pattern, '', core, flags=re.IGNORECASE)
    
    # 提取翻页参数
    patterns_page = [
        (r'第(\d+)页', 1),
        (r'page\s*(\d+)', 1),
    ]
    for pattern, group in patterns_page:
        match = re.search(pattern, core, re.IGNORECASE)
        if match:
            page = int(match.group(group))
            core = re.sub(pattern, '', core, flags=re.IGNORECASE)
    
    # 提取排序参数
    order_match = re.search(r'按(.+?)(排序|倒序|升序|降序)', core)
    if order_match:
        order_by = order_match.group(1).strip()
        order_desc = '倒序' in order_match.group(0) or '降序' in order_match.group(0)
        core = re.sub(r'按.+?(排序|倒序|升序|降序)', '', core)
    
    # 清理多余空格
    core = re.sub(r'\s+', '', core).strip()
    
    return NormalizedIntent(
        core_intent=core,
        original_intent=original,
        limit=limit,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_desc=order_desc,
    )
```

**归一化示例**：

| 原始意图 | 核心意图 | 提取参数 |
|---------|---------|---------|
| "查询用户列表前10个" | "查询用户列表" | limit=10 |
| "查询用户列表前5个" | "查询用户列表" | limit=5 |
| "查询第2页用户" | "查询用户" | page=2 |
| "查询用户列表" | "查询用户列表" | (无) |
| "查询用户按时间倒序" | "查询用户" | order_by="时间", order_desc=True |

**理由**：
- 核心意图相同的查询应该能相互匹配
- 提取的参数用于脚本复用时的参数替换
- 避免因数目不同导致无法匹配历史脚本

#### 5.1 向量化方案

```python
# 使用 Embedding 模型将 **归一化后的核心意图** 转换为向量
# 推荐模型：text-embedding-ada-002 / text-embedding-3-small / 阿里云百炼

def embed_intent(intent: str, apis_used: List[str]) -> Vector:
    """
    向量化内容包括：
    1. 归一化后的核心意图（主要权重）
    2. 使用的 API 列表（辅助权重）
    3. 关键实体（表名、字段名等）
    """
    # 先归一化
    normalized = normalize_intent(intent)
    text = f"意图: {normalized.core_intent}\nAPI: {', '.join(apis_used)}"
    return embedding_model.encode(text)
```

#### 5.2 相似度计算

```python
# 余弦相似度计算
def cosine_similarity(vec_a: Vector, vec_b: Vector) -> float:
    """
    cos(θ) = (A · B) / (||A|| × ||B||)
    返回值范围: [-1, 1]，归一化到 [0, 1]
    """
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    similarity = dot_product / (norm_a * norm_b)
    return (similarity + 1) / 2  # 归一化到 [0, 1]
```

#### 5.3 多维度加权（可选增强）

```python
def compute_weighted_similarity(
    query_intent: str,
    history_record: HistoryRecord,
    weights: dict = {"semantic": 0.7, "api": 0.2, "keyword": 0.1}
) -> float:
    """
    综合相似度 = 语义相似度 × 0.7 + API重合度 × 0.2 + 关键词匹配 × 0.1
    """
    # 1. 语义相似度（向量余弦）
    semantic_sim = cosine_similarity(
        embed(query_intent), 
        embed(history_record.intent)
    )
    
    # 2. API 重合度（Jaccard 系数）
    query_apis = extract_potential_apis(query_intent)
    history_apis = set(history_record.apis_used)
    api_sim = len(query_apis & history_apis) / len(query_apis | history_apis) if history_apis else 0
    
    # 3. 关键词匹配（可选）
    keyword_sim = keyword_overlap(query_intent, history_record.intent)
    
    return (
        weights["semantic"] * semantic_sim +
        weights["api"] * api_sim +
        weights["keyword"] * keyword_sim
    )
```

### 决策 6：检索结果分层处理策略

**方案**：根据相似度分数将检索结果分为三个层级，采用不同的处理策略

#### 6.1 分层定义

| 层级 | 相似度范围 | 处理策略 | 配置项 |
|------|-----------|---------|--------|
| **精确匹配层** | ≥ 0.95 | 直接复用脚本，跳过生成 | `HISTORY_EXACT_THRESHOLD` |
| **高度相似层** | 0.80 - 0.95 | 作为主要参考，LLM 基于此修改 | `HISTORY_HIGH_THRESHOLD` |
| **一般相似层** | 0.60 - 0.80 | 作为辅助参考，仅提供思路 | `HISTORY_LOW_THRESHOLD` |
| **不相关** | < 0.60 | 不使用，从头生成 | - |

#### 6.2 分层处理流程

```
用户意图: "查询用户列表前10个"
                ↓
        [向量相似度检索]
                ↓
┌─────────────────────────────────────────────────────────────────┐
│                     检索结果分层                                  │
├─────────────────────────────────────────────────────────────────┤
│ 🟢 精确匹配层 (≥0.95)                                            │
│    └── "查询用户列表前5个" (成功, 0.97)                           │
│        → 动作: 直接复用脚本，仅修改参数 (10→5)                     │
├─────────────────────────────────────────────────────────────────┤
│ 🟡 高度相似层 (0.80-0.95)                                        │
│    ├── "获取所有用户信息" (成功, 0.88)                            │
│    │   → 动作: 作为主要参考模板                                   │
│    └── "查询用户详情失败" (失败, 0.82)                            │
│        → 动作: 提取错误原因，告知 LLM 避免                        │
├─────────────────────────────────────────────────────────────────┤
│ 🟠 一般相似层 (0.60-0.80)                                        │
│    └── "查询部门列表" (成功, 0.65)                                │
│        → 动作: 仅作为思路参考，不直接使用代码                      │
├─────────────────────────────────────────────────────────────────┤
│ ⚪ 不相关 (<0.60)                                                │
│    └── 忽略，不加入上下文                                         │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.3 LLM 上下文构建

```python
def build_history_context(
    query: str,
    search_results: List[SearchResult]
) -> str:
    """根据分层结果构建 LLM 上下文"""
    
    context_parts = []
    
    # 精确匹配：直接复用提示
    exact_matches = [r for r in search_results if r.score >= 0.95]
    if exact_matches:
        best = exact_matches[0]
        if best.status == "success":
            context_parts.append(f"""
## 🟢 发现精确匹配的历史成功记录（相似度 {best.score:.2f}）
历史意图: {best.intent}
可直接复用以下脚本，仅需调整参数:
```python
{best.script_content}
```
""")
    
    # 高度相似：主要参考
    high_similar = [r for r in search_results if 0.80 <= r.score < 0.95]
    if high_similar:
        context_parts.append("## 🟡 高度相似的历史记录（可作为主要参考）")
        for r in high_similar[:3]:  # 最多3个
            if r.status == "success":
                context_parts.append(f"""
### 成功案例 (相似度 {r.score:.2f})
- 历史意图: {r.intent}
- 使用的 API: {r.apis_used}
- 参考脚本片段: {r.script_content[:500]}...
""")
            else:
                context_parts.append(f"""
### ⚠️ 失败案例 (相似度 {r.score:.2f}) - 请避免同样的错误
- 历史意图: {r.intent}
- 错误类型: {r.error_type}
- 错误原因: {r.error_message}
""")
    
    # 一般相似：辅助参考
    low_similar = [r for r in search_results if 0.60 <= r.score < 0.80]
    if low_similar and not exact_matches and not high_similar:
        context_parts.append("## 🟠 相关的历史记录（仅供参考思路）")
        for r in low_similar[:2]:  # 最多2个
            context_parts.append(f"- {r.intent} ({r.status}, 相似度 {r.score:.2f})")
    
    return "\n".join(context_parts)
```

#### 6.4 配置项

```yaml
# config/settings.yaml
history_retrieval:
  # 检索数量
  top_k: 10
  
  # 分层阈值
  exact_threshold: 0.95      # 精确匹配阈值（直接复用）
  high_threshold: 0.80       # 高度相似阈值（主要参考）
  low_threshold: 0.60        # 一般相似阈值（辅助参考）
  
  # 上下文限制
  max_exact_results: 1       # 精确匹配最多返回数
  max_high_results: 3        # 高度相似最多返回数
  max_low_results: 2         # 一般相似最多返回数
  
  # 权重配置（多维度加权）
  weights:
    semantic: 0.7            # 语义相似度权重
    api: 0.2                 # API 重合度权重
    keyword: 0.1             # 关键词匹配权重
```

### 决策 7：查询结果默认翻页

**方案**：当用户意图没有明确数目时，自动添加默认翻页参数

#### 7.1 数目检测规则

```python
def has_explicit_count(intent: str) -> bool:
    """检测意图是否包含明确数目"""
    patterns = [
        r'前\d+个',        # 前10个
        r'第\d+页',        # 第2页
        r'\d+条',          # 100条
        r'全部',           # 全部
        r'所有',           # 所有
        r'top\s*\d+',      # top 10
        r'limit\s*\d+',    # limit 100
    ]
    return any(re.search(p, intent, re.IGNORECASE) for p in patterns)
```

#### 7.2 默认翻页注入

```python
def inject_pagination(params: dict, intent: str) -> dict:
    """注入默认翻页参数"""
    if not has_explicit_count(intent):
        params.setdefault('page', DEFAULT_PAGE)        # 默认 1
        params.setdefault('pageSize', DEFAULT_PAGE_SIZE)  # 默认 10
    return params
```

#### 7.3 配置项

```yaml
# config/settings.yaml
pagination:
  default_page: 1
  default_page_size: 10
  # 按 Tag 配置不同默认值（可选）
  tag_overrides:
    Survey: 20      # 问卷数据默认返回 20 条
    Core-User: 10   # 用户数据默认返回 10 条
```

#### 7.4 返回结果翻页信息

```python
@dataclass
class PaginationInfo:
    """翻页信息"""
    page: int           # 当前页码
    page_size: int      # 每页数量
    total: int          # 总记录数
    total_pages: int    # 总页数
    has_more: bool      # 是否有下一页
    
    def to_summary(self) -> str:
        """生成用户友好的翻页摘要"""
        remaining = self.total - (self.page * self.page_size)
        remaining = max(0, remaining)
        
        summary = f"当前返回第 {self.page} 页，共 {self.page_size} 条。"
        summary += f"总计 {self.total} 条记录"
        
        if self.has_more:
            summary += f"，还有 {remaining} 条未显示。"
            summary += "可输入'下一页'或'查询第N页'继续查看。"
        else:
            summary += "，已全部显示。"
        
        return summary
```

#### 7.5 输出格式示例

```
📊 查询结果
├── 数据: [10 条用户记录]
│   ├── {"id": 1, "username": "admin", ...}
│   ├── {"id": 2, "username": "user1", ...}
│   └── ... (共 10 条)
│
└── 📄 翻页信息
    ├── 当前页: 1 / 16
    ├── 每页数量: 10
    ├── 总记录数: 156
    └── 💡 还有 146 条未显示，可输入"下一页"继续查看
```

**理由**：
- 避免一次性返回大量数据导致超时或内存溢出
- 提供合理的默认值，用户可按需调整
- 保持用户明确指定数目时的行为不变
- 清晰告知用户数据分页状态，便于继续查询

### 决策 8：输出格式支持

**方案**：支持文本格式（默认）和 JSON 格式两种输出

#### 8.1 文本格式（默认）

```
📊 查询结果
├── 数据: [10 条用户记录]
│   ├── {"id": 1, "username": "admin", ...}
│   └── ... (共 10 条)
│
└── 📄 翻页信息
    ├── 当前页: 1 / 16
    ├── 总记录数: 156
    └── 💡 还有 146 条未显示，可输入"下一页"继续查看
```

#### 8.2 JSON 格式

```json
{
  "success": true,
  "data": [
    {"id": 1, "username": "admin", "email": "admin@example.com"},
    {"id": 2, "username": "user1", "email": "user1@example.com"}
  ],
  "pagination": {
    "page": 1,
    "pageSize": 10,
    "total": 156,
    "totalPages": 16,
    "hasMore": true
  },
  "meta": {
    "intent": "查询用户列表",
    "api": "core_user_list",
    "duration": "0.23s",
    "timestamp": "2026-01-18T10:30:00Z"
  }
}
```

#### 8.3 CLI 参数

```bash
# 默认文本格式
python -m AIagent.src.django_api generate "查询用户列表"

# JSON 格式输出
python -m AIagent.src.django_api generate "查询用户列表" --json
python -m AIagent.src.django_api generate "查询用户列表" --output json

# 配置默认格式
export DJANGO_API_OUTPUT_FORMAT=json
```

#### 8.4 输出格式实现

```python
from enum import Enum
from dataclasses import dataclass, asdict
import json

class OutputFormat(Enum):
    TEXT = "text"
    JSON = "json"

@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: list
    pagination: PaginationInfo
    meta: dict
    
    def to_text(self) -> str:
        """转换为文本格式"""
        lines = ["📊 查询结果"]
        lines.append(f"├── 数据: [{len(self.data)} 条记录]")
        for item in self.data[:3]:
            lines.append(f"│   ├── {json.dumps(item, ensure_ascii=False)[:80]}...")
        if len(self.data) > 3:
            lines.append(f"│   └── ... (共 {len(self.data)} 条)")
        lines.append("│")
        lines.append(f"└── 📄 {self.pagination.to_summary()}")
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """转换为 JSON 格式"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)
    
    def output(self, format: OutputFormat = OutputFormat.TEXT) -> str:
        """按指定格式输出"""
        if format == OutputFormat.JSON:
            return self.to_json()
        return self.to_text()
```

**理由**：
- 文本格式便于人工阅读和交互
- JSON 格式便于程序化处理、管道操作和集成
- 支持环境变量配置默认格式，适应不同使用场景

### 决策 9：验证阶段智能修正

**方案**：在验证阶段提供详细的修正指导，帮助 LLM 正确修复错误

#### 9.1 问题背景

验证阶段常见的 LLM 错误：
1. **操作符格式错误**：LLM 使用 `=`, `==`, `!=` 而不是 `eq`, `ne`, `like`
2. **配置名乱改**：LLM 在修正时错误地更换配置名称
3. **中文字段名**：LLM 使用中文显示名而不是英文字段名
4. **无效 HTTP 方法**：LLM 生成 `NONE` 等无效方法
5. **路径参数丢失**：`path_params` 未正确传递导致 URL 变量未替换

#### 9.2 操作符格式说明

```python
# 在 LLM 提示词中添加操作符说明
OPERATOR_GUIDE = """
### 通用表查询
- **POST /api/core/table-query/query** - 执行动态表查询
  - filters 格式: [{"field": "字段名", "operator": "操作符", "value": "值"}]
  - **⚠️ 操作符必须使用**: `eq`(等于), `ne`(不等于), `gt`(大于), `gte`(大于等于), 
                          `lt`(小于), `lte`(小于等于), `like`(模糊匹配), 
                          `in`(包含), `between`(范围)
  - **❌ 不要使用**: `=`, `==`, `!=`, `>`, `<` 等符号
"""
```

#### 9.3 配置名保留机制

```python
# 在字段帮助信息中强调保留配置名
def build_field_help_section(config_name: str, fields: List[Tuple[str, str]]) -> str:
    """构建字段帮助信息，强调保留配置名"""
    section = f"""
## ✅ 配置 '{config_name}' 已验证存在！请保持使用。

**🔴 关键**: `config_name` 必须保持为 `"{config_name}"`，不要更改为其他配置名！

### 该配置的可用过滤字段：

| 字段名（使用这个） | 中文名（仅供参考） |
|---|---|
"""
    for fname, flabel in fields:
        section += f"| `{fname}` | {flabel} |\n"
    
    section += """
**⚠️ 重要**:
1. 过滤条件必须使用 **字段名**（左列），不能使用中文名！
2. **操作符必须使用**: `eq`(等于), `ne`(不等于), `like`(模糊)，**不要用** `=`, `==`, `!=`
"""
    return section
```

#### 9.4 无效 HTTP 方法检测

```python
# 验证阶段跳过无效方法
VALID_HTTP_METHODS = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}

async def validate_steps(steps: List[dict], ...):
    for step in steps:
        method = step.get('api', {}).get('method', 'GET').upper()
        
        if method not in VALID_HTTP_METHODS:
            # 跳过无效方法，不调用 API
            validation_results.append({
                'step': step_num,
                'status': 'skipped',
                'message': f'跳过无效 HTTP 方法: {method}'
            })
            continue
```

#### 9.5 路径参数传递

```python
# 正确传递 path_params
response = await client.call_api_by_path(
    method=method,
    path=path,
    query_params=query_params,
    body=body,
    path_params=params.get('path_params', {})  # 添加路径参数
)
```

**理由**：
- 明确的操作符说明减少 LLM 猜测
- 强调配置名保留避免无意义的修改尝试
- 字段映射表帮助 LLM 正确选择字段名
- 提前检测无效方法避免运行时崩溃
- 正确传递路径参数支持带变量的 URL

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|----------|
| 两阶段选择增加延迟 | 对简单意图可跳过第一阶段，直接向量检索 |
| 执行记录存储占用磁盘 | 添加自动清理策略（保留最近 30 天） |
| 历史脚本可能过时 | 检索时检查 API 版本兼容性 |
| 失败记录可能误导 | 失败原因要明确分类，只避免相同类型的错误 |
| 默认翻页可能不满足需求 | 用户可通过明确数目覆盖，或调整配置 |
| LLM 修正时乱改配置名 | 在修正提示词中强调保留已验证的配置名 |
| 操作符格式不统一 | 在提示词中明确支持的操作符列表 |

## 迁移计划

1. **阶段 1**：实现分层摘要，保持向后兼容（默认使用完整摘要）
2. **阶段 2**：实现脚本持久化，默认启用
3. **阶段 3**：实现脚本 RAG 检索，默认禁用（需手动启用）

## 待决问题

- [ ] 脚本自动清理的保留天数（建议 30 天）
- [ ] 脚本复用的相似度阈值（建议 0.85）
- [ ] 是否需要支持脚本版本管理
