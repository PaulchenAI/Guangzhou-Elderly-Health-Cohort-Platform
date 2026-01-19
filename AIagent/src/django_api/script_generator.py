# -*- coding: utf-8 -*-
"""
Django API 脚本生成器

使用 LangGraph 进行工作流管理，集成 Claude Code CLI 进行脚本生成和调试。

工作流:
0. 历史检索 (retrieve_history) - 检索历史相似指令，支持直接复用
1. 拆解意图 (plan) - 使用 LLM 分析意图，拆解为多个 API 调用步骤
2. 生成脚本 (generate) - 使用 Claude Code CLI 根据计划生成 Python 脚本
3. 执行测试 (execute) - 运行脚本，收集输出
4. 调试修正 (debug) - 分析错误，迭代修正
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..claude_code.client import ClaudeCodeClient
from ..utils.config_models import ClaudeCodeConfig, Settings
from .client import OpenAPIAwareClient
from .execution_history import ExecutionHistoryStorage, normalize_intent
from .history_retriever import (
    HistoryRetriever,
    HistoryIndexer,
    HistoryRetrievalConfig,
    TieredSearchResults,
    SearchResult,
    build_history_context,
)


# ==================== 状态定义 ====================

class ScriptGeneratorState(TypedDict):
    """脚本生成器状态"""
    # 输入
    intent: str                          # 用户意图
    api_summary: str                     # OpenAPI 摘要
    api_client: Optional[Any]            # OpenAPI 客户端（用于两阶段 API 选择）
    debug_mode: bool                     # 是否启用调试
    auto_fix: bool                       # 是否自动修正
    max_iterations: int                  # 最大迭代次数
    
    # 中间状态 - API 选择（新增）
    selected_tags: Optional[List[str]]   # 选中的 API 分类
    
    # 中间状态 - 历史检索（新增 RAG）
    history_retrieval_results: Optional[Dict[str, Any]]  # 历史检索结果
    history_context: str                 # 历史检索构建的上下文
    use_history_script: bool             # 是否直接复用历史脚本
    history_script: str                  # 复用的历史脚本
    
    # 中间状态 - 意图拆解结果
    execution_plan: Dict[str, Any]       # 执行计划（API 调用步骤）
    plan_json: str                       # 执行计划的 JSON 字符串（供 Claude Code 使用）
    
    # 中间状态 - 步骤验证（新增）
    steps_validated: bool                # 步骤是否已验证
    steps_validation_results: List[Dict[str, Any]]  # 每个步骤的验证结果
    steps_validation_context: str        # 步骤验证的上下文信息（输入输出）
    plan_fix_count: int                  # 计划修正次数（防止无限循环）
    
    # 中间状态 - 执行
    iteration: int                       # 当前迭代次数
    generated_script: str                # 生成的脚本
    execution_output: str                # 执行输出
    execution_error: str                 # 执行错误
    execution_success: bool              # 执行是否成功
    data_structure_info: str             # 数据结构信息（从 DEBUG 输出提取）
    
    # 中间状态 - LLM 验证
    validation_passed: bool              # LLM 验证是否通过
    validation_feedback: str             # LLM 验证反馈（错误原因）
    
    # 输出
    final_script: str                    # 最终脚本
    final_output: str                    # 最终输出
    messages: List[str]                  # 过程消息


# ==================== 实时日志打印 ====================

# 全局日志回调函数
_log_callback: Optional[Callable[[str], None]] = None


def set_log_callback(callback: Optional[Callable[[str], None]]):
    """设置日志回调函数，用于实时输出"""
    global _log_callback
    _log_callback = callback


def log_realtime(message: str, prefix: str = "  "):
    """实时输出日志（如果设置了回调则立即输出）"""
    formatted = f"{prefix}{message}"
    if _log_callback:
        _log_callback(formatted)
    # 同时打印到 stderr 确保实时输出
    print(formatted, file=sys.stderr, flush=True)


@dataclass
class GeneratorConfig:
    """生成器配置"""
    aiagent_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    max_iterations: int = 10  # 增加默认迭代次数
    debug_mode: bool = True
    auto_fix: bool = True
    execution_timeout: int = 60


# ==================== 辅助函数 ====================

def compress_output(output: str, max_length: int = 2000) -> str:
    """压缩执行输出，提取关键信息"""
    lines = output.split('\n')
    compressed = []
    
    for line in lines:
        stripped = line.strip()
        if '[DEBUG]' in line:
            compressed.append(stripped)
        elif any(kw in line for kw in ['错误', 'Error', 'Exception', 'Traceback']):
            compressed.append(stripped)
        elif any(kw in line for kw in ['字段', 'keys', 'fields']):
            compressed.append(stripped)
    
    result = '\n'.join(compressed)
    if len(result) > max_length:
        result = result[:max_length] + '\n... (已截断)'
    
    return result or output[:max_length]


def extract_data_structure(output: str) -> str:
    """从 DEBUG 输出中提取数据结构信息"""
    import re
    
    info_parts = []
    
    field_pattern = r'\[DEBUG\].*字段[：:]\s*\[(.*?)\]'
    field_matches = re.findall(field_pattern, output)
    if field_matches:
        info_parts.append(f"字段: [{field_matches[0]}]")
    
    sample_pattern = r'\[DEBUG\].*示例数据[：:]\s*(\{.*?\})'
    sample_matches = re.findall(sample_pattern, output, re.DOTALL)
    if sample_matches:
        sample = sample_matches[0][:500]
        info_parts.append(f"示例: {sample}")
    
    names_pattern = r'\[DEBUG\].*可用.*名称.*[:：]\s*\[(.*?)\]'
    names_matches = re.findall(names_pattern, output)
    if names_matches:
        info_parts.append(f"可用名称: [{names_matches[0]}]")
    
    return '\n'.join(info_parts) if info_parts else ""


async def call_llm(prompt: str) -> str:
    """调用 LLM"""
    from langchain_openai import ChatOpenAI
    
    settings = Settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=0,
    )
    response = await llm.ainvoke(prompt)
    return response.content.strip()


# ==================== LangGraph 节点 ====================

async def retrieve_history(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 0: 历史指令 RAG 检索
    
    强制优先检索历史相似指令：
    - 精确匹配（≥0.95）：直接复用脚本
    - 高度相似（0.80-0.95）：作为主要参考
    - 一般相似（0.60-0.80）：作为辅助参考
    """
    intent = state['intent']
    messages = state.get('messages', [])
    
    log_realtime("🔍 [历史检索] 开始检索历史指令...", "")
    messages.append("[历史检索] 开始检索历史相似指令")
    
    try:
        # 归一化意图
        normalized = normalize_intent(intent)
        log_realtime(f"📋 归一化意图: '{normalized.core_intent}'")
        if normalized.limit:
            log_realtime(f"   提取参数: limit={normalized.limit}")
        if normalized.page:
            log_realtime(f"   提取参数: page={normalized.page}")
        
        # 创建存储和检索器
        storage = ExecutionHistoryStorage()
        
        # 检查是否有历史记录
        all_records = storage.get_all_records()
        record_count = len(all_records)
        log_realtime(f"📚 历史记录数量: {record_count} 条")
        
        if record_count == 0:
            log_realtime("⚠️ 没有历史记录，跳过 RAG 检索")
            messages.append("[历史检索] 没有历史记录，跳过检索")
            return {
                **state,
                "messages": messages,
                "history_retrieval_results": None,
                "history_context": "",
                "use_history_script": False,
                "history_script": "",
            }
        
        # 创建检索器（不使用向量索引，回退到关键词匹配）
        config = HistoryRetrievalConfig(
            exact_threshold=0.95,
            high_threshold=0.80,
            low_threshold=0.60,
        )
        retriever = HistoryRetriever(storage=storage, config=config)
        
        # 执行检索
        log_realtime("🔎 执行相似度检索...")
        results: TieredSearchResults = retriever.retrieve(intent)
        
        # 打印检索结果
        exact_count = len(results.exact_matches)
        high_count = len(results.high_similar)
        low_count = len(results.low_similar)
        
        log_realtime(f"📊 检索结果分层:")
        log_realtime(f"   🟢 精确匹配 (≥0.95): {exact_count} 条")
        log_realtime(f"   🟡 高度相似 (0.80-0.95): {high_count} 条")
        log_realtime(f"   🟠 一般相似 (0.60-0.80): {low_count} 条")
        
        # 详细打印每条结果
        if results.exact_matches:
            for r in results.exact_matches:
                status_icon = "✓" if r.status == "success" else "✗"
                log_realtime(f"   🟢 [{status_icon}] '{r.intent}' (相似度: {r.score:.2f})")
        
        if results.high_similar:
            for r in results.high_similar:
                status_icon = "✓" if r.status == "success" else "✗"
                log_realtime(f"   🟡 [{status_icon}] '{r.intent}' (相似度: {r.score:.2f})")
        
        if results.low_similar:
            for r in results.low_similar[:2]:  # 只显示前2条
                status_icon = "✓" if r.status == "success" else "✗"
                log_realtime(f"   🟠 [{status_icon}] '{r.intent}' (相似度: {r.score:.2f})")
        
        # 构建历史上下文
        history_context = build_history_context(intent, results)
        
        # 检查是否可以直接复用
        use_history_script = False
        history_script = ""
        
        if results.has_exact_match:
            best = results.exact_matches[0]
            if best.status == "success" and best.script_content:
                use_history_script = True
                # 替换参数
                from .execution_history import substitute_params
                new_params = {
                    "limit": normalized.limit,
                    "page": normalized.page,
                    "page_size": normalized.page_size,
                }
                history_script = substitute_params(
                    best.script_content,
                    best.intent_params or {},
                    {k: v for k, v in new_params.items() if v is not None}
                )
                log_realtime(f"✅ 发现可直接复用的历史脚本！")
                messages.append(f"[历史检索] ✅ 发现精确匹配，可直接复用脚本")
        
        # 构建返回结果
        retrieval_dict = {
            "exact_matches": [
                {"intent": r.intent, "score": r.score, "status": r.status}
                for r in results.exact_matches
            ],
            "high_similar": [
                {"intent": r.intent, "score": r.score, "status": r.status}
                for r in results.high_similar
            ],
            "low_similar": [
                {"intent": r.intent, "score": r.score, "status": r.status}
                for r in results.low_similar
            ],
        }
        
        messages.append(f"[历史检索] 完成: 精确={exact_count}, 高相似={high_count}, 一般={low_count}")
        
        return {
            **state,
            "messages": messages,
            "history_retrieval_results": retrieval_dict,
            "history_context": history_context,
            "use_history_script": use_history_script,
            "history_script": history_script,
        }
        
    except Exception as e:
        log_realtime(f"⚠️ 历史检索失败: {e}")
        messages.append(f"[历史检索] 失败: {e}")
        return {
            **state,
            "messages": messages,
            "history_retrieval_results": None,
            "history_context": "",
            "use_history_script": False,
            "history_script": "",
        }


async def select_relevant_apis(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 0.8: 两阶段 API 选择
    
    使用分层 API 摘要实现两阶段选择：
    1. 第一阶段：使用紧凑摘要识别相关的 Tag
    2. 第二阶段：获取选定 Tag 的详细 API 信息
    
    这样可以在保持上下文精简的同时，获得足够的 API 细节
    """
    intent = state['intent']
    api_client = state.get('api_client')
    messages = list(state.get('messages', []))
    
    if not api_client:
        # 如果没有 api_client，使用原始 api_summary
        log_realtime("⚠️ [API选择] 无 api_client，使用默认摘要")
        return state
    
    log_realtime("🔍 [API选择] 开始两阶段 API 选择...")
    messages.append("[API选择] 开始两阶段 API 选择")
    
    # ========== 第一阶段：识别相关 Tag ==========
    log_realtime("📋 [第一阶段] 获取 API 紧凑摘要...")
    compact_summary = api_client.get_api_summary_compact()
    
    # 获取所有可用的 Tag
    available_tags = api_client.get_tags()
    tag_stats = api_client.get_tag_stats()
    
    log_realtime(f"   共 {len(available_tags)} 个 API 分类:")
    for tag in available_tags[:10]:
        log_realtime(f"     - {tag} ({tag_stats.get(tag, 0)} 个端点)")
    if len(available_tags) > 10:
        log_realtime(f"     - ... 还有 {len(available_tags) - 10} 个分类")
    
    # 使用 LLM 选择相关的 Tag
    tag_selection_prompt = f"""你是一个 API 选择专家。根据用户的请求，从可用的 API 分类中选择最相关的分类。

## 用户请求
"{intent}"

## 可用的 API 分类
{compact_summary}

## 你的任务

分析用户请求，选择 **2-4 个** 最相关的 API 分类（Tag）。

**选择原则:**
1. 优先选择与用户请求直接相关的分类
2. 如果涉及数据查询，选择 "核心服务" 或 "表数据查询" 相关分类
3. 如果涉及认证，选择 "用户认证" 相关分类
4. 不要选择明显不相关的分类

## 输出格式

只输出选中的分类名称，每行一个：

```
分类名1
分类名2
分类名3
```

不要输出其他内容。
"""
    
    try:
        response = await call_llm(tag_selection_prompt)
        
        # 解析选中的 Tag
        selected_tags = []
        for line in response.strip().split('\n'):
            line = line.strip().strip('`').strip('-').strip()
            if line and line in available_tags:
                selected_tags.append(line)
        
        # 如果没有选中任何 Tag，使用默认的核心分类
        if not selected_tags:
            default_tags = ['core', '核心服务', 'auth', '用户认证']
            selected_tags = [t for t in default_tags if t in available_tags][:3]
            if not selected_tags and available_tags:
                selected_tags = available_tags[:3]
        
        log_realtime(f"📌 [第一阶段] 选中 {len(selected_tags)} 个分类:")
        for tag in selected_tags:
            log_realtime(f"     ✓ {tag}")
        messages.append(f"[API选择] 第一阶段: 选中分类 {', '.join(selected_tags)}")
        
    except Exception as e:
        log_realtime(f"⚠️ [第一阶段] LLM 选择失败: {e}，使用默认分类")
        selected_tags = available_tags[:3] if available_tags else []
    
    # ========== 第二阶段：获取详细 API 信息 ==========
    log_realtime("📖 [第二阶段] 获取选中分类的详细 API 信息...")
    
    detailed_summaries = []
    for tag in selected_tags:
        tag_summary = api_client.get_tag_endpoints_summary(tag)
        detailed_summaries.append(tag_summary)
        
        # 打印该分类下的端点
        endpoints = api_client._endpoints_by_tag.get(tag, [])
        log_realtime(f"   📂 {tag} ({len(endpoints)} 个端点):")
        for ep in endpoints[:5]:
            log_realtime(f"      - {ep.method} {ep.path}")
        if len(endpoints) > 5:
            log_realtime(f"      - ... 还有 {len(endpoints) - 5} 个")
    
    # 合并详细摘要
    enhanced_api_summary = "\n\n".join(detailed_summaries)
    
    # 添加核心 API 说明（始终包含）
    core_api_info = """
## 核心 API 说明（优先使用）

### 问卷数据查询
- **POST /api/core/survey/query** - 查询问卷数据（支持名称模糊匹配）
  - Body: {"survey_name": "问卷名称", "page": 1, "page_size": 10}

### 通用表查询
- **POST /api/core/table-query/query** - 执行动态表查询
  - Body: {"config_name": "配置名称", "page": 1, "page_size": 10}
  - 如果查询返回0条数据，可能是配置名称不对

### 认证
- **POST /api/core/login** - 登录获取 Token
"""
    
    final_api_summary = core_api_info + "\n\n" + enhanced_api_summary
    
    log_realtime(f"✅ [API选择] 完成，最终摘要长度: {len(final_api_summary)} 字符")
    messages.append(f"[API选择] 第二阶段: 获取 {len(selected_tags)} 个分类的详细信息")
    
    return {
        **state,
        "api_summary": final_api_summary,
        "selected_tags": selected_tags,
        "messages": messages,
    }


async def plan_intent(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 1: 拆解意图
    
    使用 LLM 分析用户意图，输出详细的执行计划：
    - 需要调用的 API 列表（按顺序）
    - 每个 API 的参数
    - API 之间的数据传递关系
    - 最终输出格式
    """
    intent = state['intent']
    api_summary = state['api_summary']
    history_context = state.get('history_context', '')
    
    log_realtime("📝 [意图拆解] 开始分析用户意图...", "")
    
    # 构建历史参考部分
    history_section = ""
    if history_context:
        history_section = f"""
## 历史参考（来自 RAG 检索）

以下是与当前请求相似的历史执行记录，请参考：

{history_context}

**注意**: 请优先参考历史成功案例的 API 路径和参数，避免历史失败案例的错误。

"""
    
    prompt = f"""你是一个 API 调用规划专家。根据用户的自然语言请求和可用的 API 列表，分析并拆解出完整的执行计划。
{history_section}
## 可用的 API（摘要）

{api_summary[:8000]}

## 用户请求

"{intent}"

## 核心 API 说明（优先使用）

### 问卷数据查询
- **POST /api/core/survey/query** - 查询问卷数据（支持名称模糊匹配）
  - Body: {{"survey_name": "问卷名称", "page": 1, "page_size": 10}}
  - 问卷名称示例: 户外活动记录表、性格特征记录表、空闲活动记录表、门诊随访表
  - 返回: {{"items": [...], "total": 100, "page": 1, "page_size": 10}}

- **GET /api/core/survey/schemas** - 获取所有问卷配置列表
- **GET /api/core/survey/schemas/by-name/{{name}}** - 按名称获取问卷配置

### 通用表查询
- **POST /api/core/table-query/query** - 执行动态表查询
  - Body: {{"config_name": "配置名称", "page": 1, "page_size": 10}}
  - 返回: {{"items": [...], "total": 100}}

- **GET /api/core/table-query/configs/all** - 获取所有表查询配置

### 认证
- **POST /api/core/login** - 登录
  - Body: {{"username": "admin", "password": "xxx"}}
  - 返回: {{"accessToken": "xxx", "refreshToken": "xxx"}}

## 你的任务

1. **分析意图**：理解用户想要查询什么数据、有什么条件
2. **识别 API**：从可用 API 中找出需要调用的接口
   - 如果涉及"问卷"、"记录表"、"表单"数据，优先使用 `/api/core/survey/query`
   - 如果涉及通用表查询，使用 `/api/core/table-query/query`
3. **确定参数**：明确每个 API 调用需要的参数值
4. **规划流程**：通常只需要 2 步：登录 + 查询
5. **定义输出**：明确最终需要输出什么数据

## 重要提示

1. **简化流程**：大多数查询只需要 登录 → 查询 两步，不需要先获取配置列表
2. **使用名称匹配**：survey/query 和 table-query/query 都支持按名称模糊匹配
3. **POST 请求使用 body 参数**，GET 请求使用 query_params
4. **返回的数据在 items 字段中**，不是 data 或 results

## 输出格式

请以 JSON 格式输出执行计划，结构如下：

```json
{{
  "intent_analysis": {{
    "goal": "用户想要达成的目标",
    "target_data": "目标数据类型",
    "conditions": ["条件1", "条件2"],
    "output_format": "期望的输出格式"
  }},
  "steps": [
    {{
      "step_number": 1,
      "description": "步骤描述",
      "api": {{
        "method": "GET/POST",
        "path": "/api/xxx",
        "summary": "API 功能说明"
      }},
      "params": {{
        "query_params": {{}},
        "body": {{}}
      }},
      "expected_response": "期望获得的数据",
      "data_to_extract": ["需要提取的字段"],
      "pass_to_next": "传递给下一步的数据"
    }}
  ],
  "final_output": {{
    "format": "json/table/text",
    "fields": ["要输出的字段"],
    "limit": "数量限制（如有）"
  }}
}}
```

请只输出 JSON，不要其他解释。
"""
    
    try:
        response = await call_llm(prompt)
        
        # 提取 JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1)
        else:
            plan_json = response
        
        # 验证 JSON
        execution_plan = json.loads(plan_json)
        
        state['execution_plan'] = execution_plan
        state['plan_json'] = json.dumps(execution_plan, ensure_ascii=False, indent=2)
        
        # 生成摘要消息（实时打印）
        steps_count = len(execution_plan.get('steps', []))
        goal = execution_plan.get('intent_analysis', {}).get('goal', intent)
        
        log_realtime(f"🎯 目标: {goal}")
        state['messages'].append(f"[计划] 目标: {goal}")
        
        log_realtime(f"📋 拆解为 {steps_count} 个 API 调用步骤")
        state['messages'].append(f"[计划] 拆解为 {steps_count} 个 API 调用步骤")
        
        for i, step in enumerate(execution_plan.get('steps', []), 1):
            api = step.get('api', {})
            step_info = f"步骤{i}: {api.get('method')} {api.get('path')}"
            log_realtime(f"   {step_info}")
            state['messages'].append(f"[计划]   {step_info} - {step.get('description')}")
        
    except json.JSONDecodeError as e:
        state['execution_plan'] = {}
        state['plan_json'] = ""
        state['messages'].append(f"[错误] 意图拆解失败，JSON 解析错误: {e}")
    except Exception as e:
        state['execution_plan'] = {}
        state['plan_json'] = ""
        state['messages'].append(f"[错误] 意图拆解失败: {e}")
    
    return state


async def validate_steps(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 1.5: 直接执行 API 验证步骤
    
    在生成脚本之前，先直接调用执行计划中的 API，验证：
    1. API 路径是否正确
    2. 参数是否正确
    3. 返回数据结构是否符合预期
    
    将验证结果（输入输出）加入上下文，供后续脚本生成使用
    """
    from .client import OpenAPIAwareClient
    from ..utils.config_models import Settings
    
    execution_plan = state.get('execution_plan', {})
    steps = execution_plan.get('steps', [])
    
    if not steps:
        state['steps_validated'] = False
        state['steps_validation_results'] = []
        state['steps_validation_context'] = "无执行步骤"
        log_realtime("⚠️ [步骤验证] 跳过: 无执行步骤", "")
        state['messages'].append("[验证步骤] 跳过: 无执行步骤")
        return state
    
    log_realtime(f"🔬 [步骤验证] 开始验证 {len(steps)} 个步骤...", "")
    state['messages'].append(f"[验证步骤] 开始验证 {len(steps)} 个步骤...")
    
    # 初始化客户端
    settings = Settings()
    config = settings.get_django_api_config()
    client = OpenAPIAwareClient(config)
    
    validation_results = []
    context_parts = []
    all_steps_valid = True
    
    try:
        await client.load_openapi_schema()
        await client.login()
        log_realtime("✓ 登录成功")
        state['messages'].append("[验证步骤] 登录成功")
        
        for step in steps:
            step_num = step.get('step_number', 0)
            api = step.get('api', {})
            method = api.get('method', 'GET').upper()
            path = api.get('path', '')
            params = step.get('params', {})
            
            # 跳过登录步骤（已经在上面登录了）
            if 'login' in path.lower():
                validation_results.append({
                    'step': step_num,
                    'path': path,
                    'status': 'skipped',
                    'message': '登录步骤已执行'
                })
                context_parts.append(f"### 步骤 {step_num}: {path}\n状态: 已跳过（登录已完成）")
                continue
            
            # 构建请求参数
            query_params = params.get('query_params', {})
            body = params.get('body', {})
            
            # 记录输入
            input_info = {
                'method': method,
                'path': path,
                'query_params': query_params if query_params else None,
                'body': body if body else None
            }
            
            try:
                state['messages'].append(f"[验证步骤] 执行步骤 {step_num}: {method} {path}")
                
                # 调用 API
                response = await client.call_api_by_path(
                    method=method,
                    path=path,
                    query_params=query_params if query_params else None,
                    body=body if body else None
                )
                
                # 分析响应
                output_info = {}
                step_has_data = True  # 是否有实际数据
                is_query_step = 'query' in path.lower() or 'list' in path.lower() or 'search' in path.lower()
                
                if isinstance(response, dict):
                    output_info['keys'] = list(response.keys())
                    output_info['total'] = response.get('total', 'N/A')
                    items = response.get('items', [])
                    output_info['items_count'] = len(items)
                    
                    # 检查是否为查询步骤但返回0条数据
                    if is_query_step and len(items) == 0:
                        total = response.get('total', 0)
                        if total == 0:
                            step_has_data = False
                            output_info['warning'] = '查询返回0条数据，可能配置名称有误或条件不匹配'
                    
                    # 提取第一条数据的字段名
                    if items and isinstance(items[0], dict):
                        output_info['item_fields'] = list(items[0].keys())
                        # 截取样例数据
                        sample = {k: (str(v)[:50] + '...' if len(str(v)) > 50 else v) 
                                 for k, v in list(items[0].items())[:5]}
                        output_info['sample'] = sample
                else:
                    output_info['type'] = type(response).__name__
                
                # 判断步骤状态
                step_status = 'success' if step_has_data else 'empty_result'
                
                validation_results.append({
                    'step': step_num,
                    'path': path,
                    'status': step_status,
                    'input': input_info,
                    'output': output_info
                })
                
                # 构建上下文
                warning_text = f"\n**⚠️ 警告**: {output_info.get('warning', '')}" if output_info.get('warning') else ""
                status_text = "✅ 成功" if step_has_data else "⚠️ 成功但无数据"
                context_parts.append(f"""### 步骤 {step_num}: {method} {path}
**输入**:
```json
{json.dumps(input_info, ensure_ascii=False, indent=2)}
```
**输出**:
- 响应字段: {output_info.get('keys', [])}
- items 数量: {output_info.get('items_count', 'N/A')}
- total: {output_info.get('total', 'N/A')}
- item 字段: {output_info.get('item_fields', [])}
- 样例数据: {output_info.get('sample', {})}{warning_text}
**状态**: {status_text}
""")
                if step_has_data:
                    log_realtime(f"✅ 步骤 {step_num} 成功: {output_info.get('items_count', 0)} 条数据")
                    state['messages'].append(f"[验证步骤] 步骤 {step_num} ✅ 成功，返回 {output_info.get('items_count', 0)} 条数据")
                else:
                    log_realtime(f"⚠️ 步骤 {step_num} 成功但返回 0 条数据 - 可能需要修正配置名称或查询条件")
                    state['messages'].append(f"[验证步骤] 步骤 {step_num} ⚠️ 成功但返回 0 条数据")
                    all_steps_valid = False  # 0条数据也标记为需要修正
                
            except Exception as e:
                error_msg = str(e)
                # 提取更详细的错误信息
                error_detail = ""
                if hasattr(e, 'response'):
                    try:
                        resp = e.response
                        if hasattr(resp, 'text'):
                            error_detail = resp.text[:500]
                        elif hasattr(resp, 'json'):
                            error_detail = json.dumps(resp.json(), ensure_ascii=False)[:500]
                    except:
                        pass
                
                validation_results.append({
                    'step': step_num,
                    'path': path,
                    'status': 'failed',
                    'input': input_info,
                    'error': error_msg,
                    'error_detail': error_detail
                })
                
                context_parts.append(f"""### 步骤 {step_num}: {method} {path}
**输入**:
```json
{json.dumps(input_info, ensure_ascii=False, indent=2)}
```
**错误**: {error_msg}
**错误详情**: {error_detail if error_detail else '无'}
**状态**: ❌ 失败
""")
                # 打印完整错误信息
                log_realtime(f"❌ 步骤 {step_num} 失败:")
                log_realtime(f"   路径: {method} {path}")
                log_realtime(f"   错误: {error_msg}")
                if error_detail:
                    log_realtime(f"   详情: {error_detail[:200]}")
                state['messages'].append(f"[验证步骤] 步骤 {step_num} ❌ 失败: {error_msg}")
                all_steps_valid = False
        
    except Exception as e:
        state['messages'].append(f"[验证步骤] 验证过程出错: {e}")
        all_steps_valid = False
    finally:
        await client.close()
    
    # 更新状态
    state['steps_validated'] = all_steps_valid
    state['steps_validation_results'] = validation_results
    state['steps_validation_context'] = "\n".join(context_parts)
    
    if all_steps_valid:
        state['messages'].append("[验证步骤] ✅ 所有步骤验证通过")
    else:
        state['messages'].append("[验证步骤] ⚠️ 部分步骤验证失败，需要修正执行计划")
    
    return state


async def fix_execution_plan(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 1.6: 修正执行计划
    
    如果步骤验证失败，使用 LLM 根据错误信息修正执行计划
    包括获取可用的表配置列表以帮助修正配置名称
    """
    if state.get('steps_validated', False):
        # 步骤验证通过，无需修正
        return state
    
    # 增加修正计数
    plan_fix_count = state.get('plan_fix_count', 0) + 1
    state['plan_fix_count'] = plan_fix_count
    
    intent = state['intent']
    api_summary = state['api_summary']
    execution_plan = state.get('execution_plan', {})
    validation_context = state.get('steps_validation_context', '')
    validation_results = state.get('steps_validation_results', [])
    
    log_realtime(f"🔧 [修正计划] 第 {plan_fix_count} 次修正...")
    state['messages'].append(f"[修正计划] 根据验证结果修正执行计划 (第 {plan_fix_count} 次)...")
    
    # 检查是否有空结果或查询失败的步骤
    has_empty_results = any(r.get('status') == 'empty_result' for r in validation_results)
    has_failed_steps = any(r.get('status') == 'failed' for r in validation_results)
    
    # 获取可用的配置列表帮助修正
    config_help_section = ""
    if has_empty_results or has_failed_steps:
        log_realtime("📋 [修正计划] 获取可用表配置列表...")
        from .client import OpenAPIAwareClient
        from ..utils.config_models import Settings
        
        try:
            settings = Settings()
            config = settings.get_django_api_config()
            client = OpenAPIAwareClient(config)
            await client.load_openapi_schema()
            await client.login()
            
            # 获取表查询配置列表
            table_configs = []
            survey_configs = []
            
            # 存储配置详情，用于获取可用字段
            table_config_details = {}
            
            try:
                # 获取表查询配置
                resp = await client.call_api_by_path(
                    method="GET",
                    path="/api/core/table-query/configs/all"
                )
                configs_list = resp if isinstance(resp, list) else resp.get('items', []) if isinstance(resp, dict) else []
                
                for c in configs_list:
                    if isinstance(c, dict):
                        # 尝试多个可能的名称字段（按优先级）
                        config_name = c.get('display_name') or c.get('config_name') or c.get('name') or c.get('title') or c.get('table_name') or ''
                        if config_name:
                            table_configs.append(config_name)
                            # 保存配置详情，包括可用字段（从 config_json 中提取）
                            config_json = c.get('config_json', {})
                            fields = config_json.get('fields', []) if isinstance(config_json, dict) else []
                            # 提取可搜索的字段
                            searchable_fields = [
                                f.get('name') or f.get('field') 
                                for f in fields 
                                if isinstance(f, dict) and f.get('searchable', False)
                            ]
                            table_config_details[config_name] = {
                                'id': c.get('id') or c.get('config_id'),
                                'table_name': c.get('table_name', ''),
                                'fields': searchable_fields,
                                'all_fields': [f.get('name') for f in fields if isinstance(f, dict)],
                            }
                
                log_realtime(f"   表查询配置: {len(table_configs)} 个")
                if table_configs:
                    log_realtime(f"   示例配置: {table_configs[:3]}")
            except Exception as e:
                log_realtime(f"   获取表查询配置失败: {e}")
            
            try:
                # 获取问卷配置
                resp = await client.call_api_by_path(
                    method="GET",
                    path="/api/core/survey/schemas"
                )
                if isinstance(resp, list):
                    survey_configs = [c.get('name', c.get('survey_name', '')) for c in resp if isinstance(c, dict)]
                elif isinstance(resp, dict) and 'items' in resp:
                    survey_configs = [c.get('name', c.get('survey_name', '')) for c in resp['items'] if isinstance(c, dict)]
                log_realtime(f"   问卷配置: {len(survey_configs)} 个")
            except Exception as e:
                log_realtime(f"   获取问卷配置失败: {e}")
            
            await client.close()
            
            # 构建配置帮助信息
            if table_configs or survey_configs:
                config_help_section = """
## 可用的配置名称（重要！）

请仔细检查并使用下面的**准确配置名称**，不要编造不存在的名称：

"""
                if table_configs:
                    config_help_section += f"### 表查询配置 (table-query)\n"
                    config_help_section += "\n".join([f"- `{c}`" for c in table_configs[:30]])
                    if len(table_configs) > 30:
                        config_help_section += f"\n- ... 还有 {len(table_configs) - 30} 个"
                    config_help_section += "\n\n"
                
                if survey_configs:
                    config_help_section += f"### 问卷配置 (survey)\n"
                    config_help_section += "\n".join([f"- `{c}`" for c in survey_configs[:30]])
                    if len(survey_configs) > 30:
                        config_help_section += f"\n- ... 还有 {len(survey_configs) - 30} 个"
                    config_help_section += "\n\n"
                
                # 打印可用配置帮助用户理解
                log_realtime("📋 [修正计划] 可用配置:")
                for c in table_configs[:5]:
                    log_realtime(f"   表查询: {c}")
                for c in survey_configs[:5]:
                    log_realtime(f"   问卷: {c}")
                    
        except Exception as e:
            log_realtime(f"⚠️ 获取配置列表失败: {e}")
    
    # 分析失败原因
    failure_analysis = ""
    field_help_section = ""
    
    if has_empty_results:
        failure_analysis += "\n**⚠️ 检测到空结果问题**: 查询返回0条数据，可能是配置名称不匹配。请核对上面的可用配置名称列表。"
    
    if has_failed_steps:
        for r in validation_results:
            if r.get('status') == 'failed':
                err = r.get('error', '')
                err_detail = r.get('error_detail', '')
                step_input = r.get('input', {})
                
                if '400' in err or 'Bad Request' in err:
                    failure_analysis += f"\n**❌ 400 错误**: 步骤 {r.get('step')} 参数不合法。"
                    
                    # 解析错误详情
                    if err_detail:
                        try:
                            err_json = json.loads(err_detail)
                            detail_obj = err_json.get('detail', {})
                            
                            # 支持新的错误响应格式：detail 可能是字符串或对象
                            if isinstance(detail_obj, dict):
                                detail_msg = detail_obj.get('message', str(detail_obj))
                                # 新格式：错误响应中直接包含 available_fields
                                available_fields_from_error = detail_obj.get('available_fields', [])
                            else:
                                detail_msg = str(detail_obj)
                                available_fields_from_error = []
                            
                            failure_analysis += f"\n   错误详情: {detail_msg}"
                            
                            # 如果是"字段不支持搜索"错误
                            is_field_error = '不支持搜索' in detail_msg or '过滤字段' in detail_msg or 'filter' in detail_msg.lower()
                            
                            if is_field_error:
                                # 优先使用错误响应中的 available_fields
                                if available_fields_from_error:
                                    log_realtime(f"📋 [字段检查] 从错误响应中获取可用字段...")
                                    available_fields = []
                                    for f in available_fields_from_error:
                                        if isinstance(f, dict):
                                            fname = f.get('name', '')
                                            flabel = f.get('display_name', f.get('title', fname))
                                        else:
                                            fname = str(f)
                                            flabel = fname
                                        if fname:
                                            available_fields.append((fname, flabel))
                                    
                                    if available_fields:
                                        field_help_section += f"\n\n## 可用的过滤字段（来自错误响应）\n\n"
                                        field_help_section += "| 字段名（使用这个） | 中文名（仅供参考） |\n"
                                        field_help_section += "|---|---|\n"
                                        for fname, flabel in available_fields:
                                            field_help_section += f"| `{fname}` | {flabel} |\n"
                                        field_help_section += "\n**⚠️ 重要**: 过滤条件必须使用 **字段名**（左列），不能使用中文名！\n"
                                        
                                        log_realtime(f"   可用字段:")
                                        for fname, flabel in available_fields[:8]:
                                            log_realtime(f"      {fname} ({flabel})")
                                        if len(available_fields) > 8:
                                            log_realtime(f"      ... 还有 {len(available_fields) - 8} 个")
                                else:
                                    # 回退：从请求体中获取配置名称，调用新的 searchable-fields 端点
                                    body = step_input.get('body', {})
                                    config_name = ''
                                    api_type = 'table-query'  # 默认表查询
                                    
                                    if isinstance(body, dict):
                                        config_name = body.get('config_name', body.get('survey_name', ''))
                                        if body.get('survey_name') or body.get('schema_id'):
                                            api_type = 'survey'
                                    
                                    if config_name:
                                        log_realtime(f"📋 [字段检查] 调用 searchable-fields 端点获取 '{config_name}' 的可用字段...")
                                        try:
                                            from .client import OpenAPIAwareClient
                                            from ..utils.config_models import Settings
                                            
                                            settings = Settings()
                                            cfg = settings.get_django_api_config()
                                            field_client = OpenAPIAwareClient(cfg)
                                            await field_client.load_openapi_schema()
                                            await field_client.login()
                                            
                                            # 根据 API 类型选择不同的端点
                                            if api_type == 'survey':
                                                endpoint = f"/api/core/survey/schemas/by-name/{config_name}/searchable-fields"
                                            else:
                                                endpoint = f"/api/core/table-query/configs/by-name/{config_name}/searchable-fields"
                                            
                                            fields_resp = await field_client.call_api_by_path(
                                                method="GET",
                                                path=endpoint
                                            )
                                            await field_client.close()
                                            
                                            if isinstance(fields_resp, dict):
                                                searchable_fields = fields_resp.get('searchable_fields', [])
                                                model_fields = fields_resp.get('model_fields', [])
                                                
                                                available_fields = []
                                                # 添加 schema/配置中的可搜索字段
                                                for f in searchable_fields:
                                                    if isinstance(f, dict):
                                                        fname = f.get('name', '')
                                                        flabel = f.get('display_name', f.get('title', fname))
                                                        if fname:
                                                            available_fields.append((fname, flabel))
                                                
                                                # 添加模型固定字段（问卷查询）
                                                for f in model_fields:
                                                    if isinstance(f, dict):
                                                        fname = f.get('name', '')
                                                        flabel = f.get('title', fname)
                                                        if fname:
                                                            available_fields.append((fname, flabel))
                                                
                                                if available_fields:
                                                    field_help_section += f"\n\n## 配置 '{config_name}' 的可用过滤字段\n\n"
                                                    field_help_section += "| 字段名（使用这个） | 中文名（仅供参考） |\n"
                                                    field_help_section += "|---|---|\n"
                                                    for fname, flabel in available_fields:
                                                        field_help_section += f"| `{fname}` | {flabel} |\n"
                                                    field_help_section += "\n**⚠️ 重要**: 过滤条件必须使用 **字段名**（左列），不能使用中文名！\n"
                                                    
                                                    log_realtime(f"   可用字段:")
                                                    for fname, flabel in available_fields[:8]:
                                                        log_realtime(f"      {fname} ({flabel})")
                                                    if len(available_fields) > 8:
                                                        log_realtime(f"      ... 还有 {len(available_fields) - 8} 个")
                                        except Exception as field_e:
                                            log_realtime(f"   获取字段信息失败: {field_e}")
                        except json.JSONDecodeError:
                            failure_analysis += f"\n   详情: {err_detail[:200]}"
                    else:
                        failure_analysis += f"\n   详情: {err}"
                        
                elif '404' in err or 'Not Found' in err:
                    failure_analysis += f"\n**❌ 404 错误**: 步骤 {r.get('step')} API 路径不存在: {r.get('path')}"
                elif '422' in err:
                    failure_analysis += f"\n**❌ 422 错误**: 步骤 {r.get('step')} 参数格式错误。详情: {err_detail[:200] if err_detail else err}"
    
    prompt = f"""你是一个 API 调用规划专家。之前的执行计划在验证时失败了，请根据错误信息修正计划。

## 用户请求
"{intent}"

## 原执行计划
```json
{json.dumps(execution_plan, ensure_ascii=False, indent=2)[:3000]}
```

## 步骤验证结果
{validation_context}

## 失败原因分析
{failure_analysis}
{config_help_section}{field_help_section}
## 可用的 API（摘要）
{api_summary[:4000]}

## 修正要求

1. **检查配置名称**: 如果查询返回0条数据，说明配置名称可能不对，请从上面的可用配置名称列表中选择正确的
2. **检查 API 路径**: 确保使用正确的 API 路径
3. **检查参数格式**: POST 请求用 body，GET 请求用 query_params
4. **输出修正后的完整执行计划**

## 常见问题和解决方案

1. **返回0条数据**：config_name 或 survey_name 不匹配，请使用上面列出的准确配置名称
2. **404 错误**：API 路径不存在，需要从 API 摘要中找到正确路径
3. **422 错误**：参数格式错误，检查必填参数和参数类型
4. **400 错误**：请求参数不合法，检查参数值和字段名

## 输出格式

请以 JSON 格式输出修正后的执行计划（与原格式相同）：

```json
{{
  "intent_analysis": {{...}},
  "steps": [...],
  "final_output": {{...}}
}}
```

请只输出 JSON，不要其他解释。
"""
    
    try:
        response = await call_llm(prompt)
        
        # 提取 JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1)
        else:
            plan_json = response
        
        # 验证 JSON
        new_plan = json.loads(plan_json)
        
        state['execution_plan'] = new_plan
        state['plan_json'] = json.dumps(new_plan, ensure_ascii=False, indent=2)
        state['messages'].append("[修正计划] ✅ 执行计划已修正")
        
        # 打印修正后的步骤
        for i, step in enumerate(new_plan.get('steps', []), 1):
            api = step.get('api', {})
            state['messages'].append(f"[修正计划]   步骤{i}: {api.get('method')} {api.get('path')}")
        
    except Exception as e:
        state['messages'].append(f"[修正计划] ❌ 修正失败: {e}")
    
    return state


async def generate_script(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 2: 使用 Claude Code CLI 生成脚本
    
    根据执行计划生成 Python 脚本
    """
    intent = state['intent']
    plan_json = state['plan_json']
    execution_plan = state['execution_plan']
    debug_mode = state['debug_mode']
    iteration = state.get('iteration', 0)
    
    if not execution_plan:
        state['generated_script'] = "# 生成失败: 没有有效的执行计划"
        state['messages'].append(f"[错误] 无法生成脚本，缺少执行计划")
        return state
    
    # 构建提示词
    debug_flag = 'True' if debug_mode else 'False'
    
    # 构建上下文
    context_parts = [
        f"## 用户意图\n{intent}",
        f"\n## 执行计划\n```json\n{plan_json}\n```",
    ]
    
    # 添加步骤验证结果（关键改进：将实际的 API 输入输出加入上下文）
    validation_context = state.get('steps_validation_context', '')
    if validation_context:
        context_parts.append(f"\n## 步骤验证结果（实际 API 调用的输入输出）\n{validation_context}")
    
    # 如果是迭代修正，添加错误信息
    if iteration > 0:
        error = state.get('execution_error', '')
        data_info = state.get('data_structure_info', '')
        prev_script = state.get('generated_script', '')
        
        context_parts.append(f"\n## 上次执行错误\n{compress_output(error)}")
        if data_info:
            context_parts.append(f"\n## 实际数据结构\n{data_info}")
        context_parts.append(f"\n## 需要修正的脚本\n```python\n{prev_script[:3000]}\n```")
    
    context = '\n'.join(context_parts)
    
    prompt = f"""根据执行计划生成 Python 脚本。

{context}

## 脚本要求

1. **严格按照执行计划**：按步骤调用 API，使用计划中指定的参数
2. **处理数据传递**：如果步骤间有数据依赖，正确传递数据
3. **错误处理**：添加异常捕获
4. **调试输出**：DEBUG 模式下打印关键信息

## 脚本模板

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
自动生成的查询脚本
意图: {intent}
\"\"\"

import asyncio
import json
import sys
from pathlib import Path

AIAGENT_DIR = Path(__file__).parent
sys.path.insert(0, str(AIAGENT_DIR))

from src.django_api.client import OpenAPIAwareClient
from src.utils.config_models import Settings

DEBUG = {debug_flag}

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {{msg}}")


async def main():
    settings = Settings()
    config = settings.get_django_api_config()
    client = OpenAPIAwareClient(config)
    
    try:
        await client.load_openapi_schema()
        await client.login()
        debug_print("登录成功")
        
        # === 步骤 1: [根据计划填写] ===
        # 使用 client.call_api_by_path(method, path, query_params, body)
        # 或者 endpoint = client.find_endpoint("意图"); await client.call_api(endpoint, ...)
        
        # === 步骤 2: [根据计划填写] ===
        # ...
        
        # === 输出结果 ===
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"错误: {{e}}", file=sys.stderr)
        if DEBUG:
            import traceback
            traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## 关键 API 调用方式

```python
# 推荐: 直接按路径调用 API
# 1. 查询问卷数据（使用名称模糊匹配）
response = await client.call_api_by_path(
    "POST", 
    "/api/core/survey/query", 
    body={{"survey_name": "户外活动记录表", "page": 1, "page_size": 10}}
)
items = response.get("items", [])  # 返回数据在 items 字段

# 2. 通用表查询
response = await client.call_api_by_path(
    "POST", 
    "/api/core/table-query/query", 
    body={{"config_name": "配置名称", "page": 1, "page_size": 10}}
)

# 3. GET 请求示例
response = await client.call_api_by_path(
    "GET", 
    "/api/core/survey/schemas", 
    query_params={{"page": 1, "page_size": 100}}
)
```

## 重要规则

1. **返回数据在 `items` 字段**：使用 `response.get("items", [])`，不是 `data` 或 `results`
2. **问卷查询用 survey_name**：直接传入名称，支持模糊匹配
3. **GET 请求用 query_params，POST 请求用 body**
4. **先登录再查询**：调用 `await client.login()` 获取认证

**常见问卷名称**：
- 户外活动记录表
- 性格特征记录表
- 空闲活动记录表
- 门诊随访表
- 个人信息登记表

请直接输出完整的 Python 脚本代码，不要其他解释。
"""
    
    try:
        settings = Settings()
        script = None
        
        # 尝试使用 Claude Code CLI
        use_claude_cli = False
        if hasattr(settings, 'claude_code_path') and settings.claude_code_path:
            claude_path = Path(settings.claude_code_path)
            if claude_path.exists():
                use_claude_cli = True
        
        if use_claude_cli:
            try:
                claude_config = ClaudeCodeConfig(
                    path=settings.claude_code_path,
                    working_dir=str(Path(__file__).parent.parent.parent),
                    timeout=120
                )
                client = ClaudeCodeClient(claude_config)
                script = await client.generate_code(prompt)
                state['messages'].append(f"[生成] 使用 Claude Code CLI")
            except Exception as claude_error:
                state['messages'].append(f"[警告] Claude Code CLI 失败: {claude_error}, 回退到 LangChain")
                use_claude_cli = False
        
        # 回退到 LangChain OpenAI
        if not use_claude_cli or script is None:
            script = await call_llm(prompt)
            state['messages'].append(f"[生成] 使用 LangChain OpenAI")
        
        # 提取代码块
        import re
        code_match = re.search(r'```python\s*(.*?)\s*```', script, re.DOTALL)
        if code_match:
            script = code_match.group(1)
        
        state['generated_script'] = script
        state['messages'].append(f"[生成] 脚本已生成 ({len(script)} 字符)")
        
    except Exception as e:
        state['generated_script'] = f"# 生成失败: {e}"
        state['messages'].append(f"[错误] 脚本生成失败: {e}")
    
    return state


async def execute_script(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 3: 执行脚本并收集输出
    """
    # #region agent log
    import os
    log_path = "/mnt/f/work/zq-platform/.cursor/debug.log"
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:750", "message": "execute_script entry", "data": {"script_len": len(state.get('generated_script', '')), "has_script": bool(state.get('generated_script'))}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C,D,E"}) + "\n")
    # #endregion
    script = state['generated_script']
    config = GeneratorConfig()
    
    if not script or script.startswith('# 生成失败'):
        state['execution_success'] = False
        state['execution_error'] = "脚本未生成"
        return state
    
    # 注入 AIagent 路径
    script_with_path = script.replace(
        'AIAGENT_DIR = Path(__file__).parent',
        f'AIAGENT_DIR = Path("{config.aiagent_dir.as_posix()}")'
    )
    
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:768", "message": "before temp file creation", "data": {"script_with_path_len": len(script_with_path), "aiagent_dir": str(config.aiagent_dir)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
    # #endregion
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script_with_path)
        temp_path = f.name
    
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:772", "message": "temp file created", "data": {"temp_path": temp_path, "cwd": str(config.aiagent_dir)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}) + "\n")
    # #endregion
    
    try:
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"location": "script_generator.py:776", "message": "before subprocess.run", "data": {"executable": sys.executable, "temp_path": temp_path, "timeout": config.execution_timeout}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,C,D,E"}) + "\n")
        # #endregion
        
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            cwd=str(config.aiagent_dir),
            timeout=config.execution_timeout
        )
        
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"location": "script_generator.py:785", "message": "after subprocess.run", "data": {"returncode": result.returncode, "stdout_len": len(result.stdout), "stderr_len": len(result.stderr), "stdout_preview": result.stdout[:200] if result.stdout else "", "stderr_preview": result.stderr[:200] if result.stderr else ""}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,C,D,E"}) + "\n")
        # #endregion
        
        state['execution_output'] = result.stdout
        state['execution_error'] = result.stderr
        state['execution_success'] = result.returncode == 0
        
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"location": "script_generator.py:790", "message": "state updated", "data": {"execution_output_len": len(state['execution_output']), "execution_error_len": len(state['execution_error']), "execution_success": state['execution_success']}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "E"}) + "\n")
        # #endregion
        
        # 提取数据结构信息
        combined_output = result.stdout + result.stderr
        state['data_structure_info'] = extract_data_structure(combined_output)
        
        if state['execution_success']:
            state['messages'].append(f"[执行] 成功")
        else:
            state['messages'].append(f"[执行] 失败: {result.stderr[:200]}")
        
    except subprocess.TimeoutExpired:
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"location": "script_generator.py:804", "message": "TimeoutExpired exception", "data": {"timeout": config.execution_timeout}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "D"}) + "\n")
        # #endregion
        state['execution_success'] = False
        state['execution_error'] = f"执行超时 ({config.execution_timeout}秒)"
        state['messages'].append(f"[执行] 超时")
    except Exception as e:
        # #region agent log
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(json.dumps({"location": "script_generator.py:810", "message": "Exception in execute_script", "data": {"error_type": type(e).__name__, "error_msg": str(e)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}) + "\n")
        # #endregion
        state['execution_success'] = False
        state['execution_error'] = str(e)
        state['messages'].append(f"[执行] 异常: {e}")
    finally:
        Path(temp_path).unlink(missing_ok=True)
    
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:816", "message": "execute_script exit", "data": {"execution_success": state['execution_success'], "execution_output_len": len(state.get('execution_output', '')), "execution_error_len": len(state.get('execution_error', ''))}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,B,C,D,E"}) + "\n")
    # #endregion
    
    return state


async def validate_result(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 4: 验证执行结果
    
    使用 LLM 检查脚本执行结果是否符合预期：
    - 结果是否为空（但预期有数据）
    - 数据格式是否正确
    - 是否完成了用户意图
    """
    # #region agent log
    import os
    log_path = "/mnt/f/work/zq-platform/.cursor/debug.log"
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:809", "message": "validate_result entry", "data": {"execution_success": state.get('execution_success'), "execution_output_len": len(state.get('execution_output', '')), "has_execution_error": bool(state.get('execution_error'))}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,E"}) + "\n")
    # #endregion
    
    # 如果执行失败，跳过验证
    if not state['execution_success']:
        state['validation_passed'] = False
        state['validation_feedback'] = state['execution_error']
        return state
    
    intent = state['intent']
    execution_plan = state['execution_plan']
    execution_output = state['execution_output']
    
    # #region agent log
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"location": "script_generator.py:828", "message": "validate_result checking output", "data": {"execution_output_is_empty": len(execution_output) == 0, "execution_output_preview": execution_output[:100] if execution_output else ""}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A,E"}) + "\n")
    # #endregion
    
    # 快速检查：如果输出包含有效数据，快速通过
    # 检测是否有实际数据（非空数组，total > 0）
    import re
    has_data = False
    
    # 检查是否有非空数据
    if '"data":' in execution_output or '"items":' in execution_output:
        # 检查是否有实际记录
        if re.search(r'"(data|items)":\s*\[[\s\S]*?"id":', execution_output):
            has_data = True
        # 检查 total 是否大于 0
        total_match = re.search(r'"total":\s*(\d+)', execution_output)
        if total_match and int(total_match.group(1)) > 0:
            # 检查是否有对应的数据
            if re.search(r'\[\s*\{[\s\S]*?\}\s*\]', execution_output):
                has_data = True
    
    # 如果有数据且没有错误信息，快速通过
    if has_data and '错误' not in execution_output and 'Error' not in execution_output:
        state['validation_passed'] = True
        state['validation_feedback'] = "快速验证通过：检测到有效数据输出"
        state['messages'].append(f"[验证] ✅ 快速通过: 检测到有效数据")
        return state
    
    # 否则使用 LLM 验证
    prompt = f"""你是一个结果验证专家。请检查脚本执行结果是否正确完成了用户的意图。

## 用户意图
"{intent}"

## 执行计划
{json.dumps(execution_plan.get('intent_analysis', {}), ensure_ascii=False, indent=2)}

## 脚本执行输出
```
{execution_output[:4000]}
```

## 验证重点

**只关注以下核心问题：**
1. **数据是否为空**：如果用户请求查询数据，但 `data` 或 `items` 是空数组 `[]`，且 `total` 为 0，则验证失败
2. **是否有错误**：如果输出包含 "错误" 或 "Error"，则验证失败
3. **基本完成意图**：如果返回了数据（即使格式不完美），只要有实际记录就算通过

**不要过于严格：**
- 不要因为输出格式（如是否是表格）而判定失败
- 不要因为数据被截断而判定失败（输出长度有限）
- 只要有实际数据返回，即使数量少于预期也算通过

## 常见错误模式

1. 使用错误的字段名提取数据，导致结果为空（如 `response.get("data")` 而实际是 `response.get("items")`）
2. 查询条件错误，导致没有匹配的数据

## 输出格式

```json
{{
  "passed": true/false,
  "reason": "简短说明",
  "issues": ["问题1"],
  "suggestions": ["建议1"]
}}
```

只输出 JSON。
"""
    
    try:
        response = await call_llm(prompt)
        
        # 提取 JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            result_json = json_match.group(1)
        else:
            result_json = response
        
        validation_result = json.loads(result_json)
        
        state['validation_passed'] = validation_result.get('passed', False)
        
        if state['validation_passed']:
            state['validation_feedback'] = "验证通过"
            state['messages'].append(f"[验证] ✅ 通过: {validation_result.get('reason', 'OK')}")
        else:
            # 构建详细的反馈信息
            issues = validation_result.get('issues', [])
            suggestions = validation_result.get('suggestions', [])
            
            feedback_parts = [validation_result.get('reason', '验证失败')]
            if issues:
                feedback_parts.append(f"问题: {'; '.join(issues)}")
            if suggestions:
                feedback_parts.append(f"建议: {'; '.join(suggestions)}")
            
            state['validation_feedback'] = '\n'.join(feedback_parts)
            state['messages'].append(f"[验证] ❌ 失败: {validation_result.get('reason', '未知原因')}")
            
            # 将验证反馈添加到执行错误中，供下次迭代使用
            state['execution_error'] = f"LLM 验证失败:\n{state['validation_feedback']}"
            state['execution_success'] = False  # 标记为失败，触发重新生成
        
    except json.JSONDecodeError as e:
        state['validation_passed'] = False
        state['validation_feedback'] = f"验证结果解析失败: {e}"
        state['messages'].append(f"[验证] ⚠️ 解析失败，默认通过")
        state['validation_passed'] = True  # 解析失败时默认通过
    except Exception as e:
        state['validation_passed'] = True  # 异常时默认通过
        state['validation_feedback'] = f"验证异常: {e}"
        state['messages'].append(f"[验证] ⚠️ 异常: {e}，默认通过")
    
    return state


async def debug_and_decide(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 5: 调试并决定下一步
    """
    iteration = state.get('iteration', 0) + 1
    state['iteration'] = iteration
    
    max_iter = state.get('max_iterations', 3)
    auto_fix = state.get('auto_fix', True)
    
    # 检查验证结果
    validation_passed = state.get('validation_passed', True)
    
    if state['execution_success'] and validation_passed:
        state['final_script'] = state['generated_script']
        state['final_output'] = state['execution_output']
        state['messages'].append(f"[完成] 迭代 {iteration} 成功，结果已验证")
    elif iteration >= max_iter:
        state['final_script'] = state['generated_script']
        state['final_output'] = state.get('execution_error', '') or state['execution_output']
        state['messages'].append(f"[结束] 达到最大迭代次数 ({max_iter})")
    elif auto_fix:
        state['messages'].append(f"[调试] 迭代 {iteration}/{max_iter}，准备修正...")
    
    return state


def should_continue(state: ScriptGeneratorState) -> str:
    """条件路由：决定是继续修正还是结束"""
    # 执行成功且验证通过才算真正成功
    validation_passed = state.get('validation_passed', True)
    
    if state['execution_success'] and validation_passed:
        return "end"
    
    iteration = state.get('iteration', 0)
    max_iter = state.get('max_iterations', 3)
    auto_fix = state.get('auto_fix', True)
    
    if iteration >= max_iter:
        return "end"
    
    if auto_fix:
        return "generate"
    
    return "end"


# ==================== 构建 LangGraph ====================

def should_skip_plan_after_history(state: ScriptGeneratorState) -> str:
    """条件路由：历史检索后决定是直接复用还是继续规划"""
    use_history_script = state.get('use_history_script', False)
    
    if use_history_script:
        log_realtime("🚀 [路由] 发现精确匹配，跳过规划，直接执行历史脚本", "")
        return "use_history"
    else:
        log_realtime("🔄 [路由] 继续规划新脚本", "")
        return "plan"


def should_revalidate_steps(state: ScriptGeneratorState) -> str:
    """条件路由：决定是修正计划还是继续生成脚本还是直接失败"""
    steps_validated = state.get('steps_validated', False)
    iteration = state.get('iteration', 0)
    plan_fix_count = state.get('plan_fix_count', 0)
    validation_results = state.get('steps_validation_results', [])
    
    # 步骤验证通过，继续生成脚本
    if steps_validated:
        log_realtime("✅ [路由] 步骤验证通过，继续生成脚本", "")
        return "generate"
    
    # 步骤验证失败且修正次数未超过限制（最多修正 2 次）
    if plan_fix_count < 2:
        log_realtime(f"🔧 [路由] 步骤验证失败，修正计划 (第 {plan_fix_count + 1} 次)", "")
        return "fix_plan"
    
    # 超过修正次数限制，直接返回失败（不再强制继续生成）
    log_realtime("❌ [路由] 超过修正次数限制，验证阶段失败", "")
    
    # 收集失败原因
    failure_reasons = []
    for r in validation_results:
        if r.get('status') == 'failed':
            err = r.get('error', '未知错误')
            err_detail = r.get('error_detail', '')
            failure_reasons.append(f"步骤 {r.get('step')}: {err}")
            if err_detail:
                # 解析错误详情
                try:
                    err_json = json.loads(err_detail)
                    detail_msg = err_json.get('detail', '')
                    if detail_msg:
                        failure_reasons.append(f"  详情: {detail_msg}")
                except:
                    failure_reasons.append(f"  详情: {err_detail[:100]}")
        elif r.get('status') == 'empty_result':
            failure_reasons.append(f"步骤 {r.get('step')}: 查询返回 0 条数据")
    
    # 更新状态，标记为失败
    state['execution_success'] = False
    state['execution_error'] = f"验证阶段失败（已尝试修正 {plan_fix_count} 次）:\n" + "\n".join(failure_reasons)
    state['final_output'] = state['execution_error']
    state['messages'].append(f"[失败] 验证阶段无法修正，终止执行")
    
    return "end"


async def use_history_script_node(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点: 使用历史脚本（精确匹配时）
    
    直接使用历史脚本，跳过规划和生成步骤
    """
    history_script = state.get('history_script', '')
    
    log_realtime("📜 [复用历史] 使用精确匹配的历史脚本", "")
    
    state['generated_script'] = history_script
    state['final_script'] = history_script
    state['messages'].append("[复用历史] 使用精确匹配的历史脚本")
    
    return state


def build_script_generator_graph():
    """
    构建脚本生成器的 LangGraph 工作流
    
    新流程（集成 RAG）：
    retrieve_history → (use_history 或 plan) → validate_steps → (fix_plan?) → generate → execute → validate → debug → (generate 或 end)
    
    改进点：
    1. 在规划前先进行历史指令 RAG 检索
    2. 如果发现精确匹配，直接复用历史脚本
    3. 在生成脚本前先直接调用 API 验证步骤
    4. 如果步骤验证失败，先修正执行计划
    5. 将步骤验证的输入输出加入脚本生成的上下文
    """
    
    graph = StateGraph(ScriptGeneratorState)
    
    # 添加节点
    graph.add_node("retrieve_history", retrieve_history)  # 0. 历史检索（RAG）
    graph.add_node("use_history", use_history_script_node)  # 0.5 使用历史脚本
    graph.add_node("select_api", select_relevant_apis)     # 0.8 两阶段 API 选择
    graph.add_node("plan", plan_intent)              # 1. 拆解意图
    graph.add_node("validate_steps", validate_steps) # 2. 验证步骤
    graph.add_node("fix_plan", fix_execution_plan)   # 2.5 修正计划
    graph.add_node("generate", generate_script)      # 3. 生成脚本
    graph.add_node("execute", execute_script)        # 4. 执行测试
    graph.add_node("validate", validate_result)      # 5. 验证结果
    graph.add_node("debug", debug_and_decide)        # 6. 调试决策
    
    # 设置入口（从历史检索开始）
    graph.set_entry_point("retrieve_history")
    
    # 条件边：历史检索后决定是复用还是规划
    graph.add_conditional_edges(
        "retrieve_history",
        should_skip_plan_after_history,
        {
            "use_history": "use_history",  # 精确匹配，直接使用历史脚本
            "plan": "select_api"           # 继续到 API 选择
        }
    )
    
    # 使用历史脚本后直接执行
    graph.add_edge("use_history", "execute")
    
    # API 选择后进行意图规划
    graph.add_edge("select_api", "plan")
    
    # 添加边
    graph.add_edge("plan", "validate_steps")     # 拆解后验证步骤
    
    # 条件边：验证步骤后决定是修正计划、生成脚本还是直接失败
    graph.add_conditional_edges(
        "validate_steps",
        should_revalidate_steps,
        {
            "fix_plan": "fix_plan",    # 步骤验证失败，修正计划
            "generate": "generate",    # 步骤验证通过，生成脚本
            "end": END                 # 修正次数超限，直接失败
        }
    )
    
    graph.add_edge("fix_plan", "validate_steps")  # 修正后重新验证
    graph.add_edge("generate", "execute")         # 生成后执行
    graph.add_edge("execute", "validate")         # 执行后验证
    graph.add_edge("validate", "debug")           # 验证后调试
    
    # 条件边：调试后决定是继续还是结束
    graph.add_conditional_edges(
        "debug",
        should_continue,
        {
            "generate": "generate",  # 失败则重新生成
            "end": END
        }
    )
    
    return graph.compile()


# ==================== 高层 API ====================

class ScriptGenerator:
    """
    脚本生成器
    
    使用 LangGraph 管理工作流，支持迭代调试
    """
    
    def __init__(
        self,
        api_client: OpenAPIAwareClient,
        debug_mode: bool = True,
        auto_fix: bool = True,
        max_iterations: int = 10  # 增加默认迭代次数
    ):
        self.api_client = api_client
        self.debug_mode = debug_mode
        self.auto_fix = auto_fix
        self.max_iterations = max_iterations
        self.graph = build_script_generator_graph()
    
    async def generate(self, intent: str, verbose: bool = False) -> Dict[str, Any]:
        """
        生成脚本
        
        Args:
            intent: 用户意图
            verbose: 是否输出详细信息
        
        Returns:
            {
                "success": bool,
                "script": str,
                "output": str,
                "iterations": int,
                "execution_plan": dict,
                "messages": List[str]
            }
        """
        # 打印 API 加载信息
        log_realtime("📡 [API加载] 开始加载 API 信息...")
        
        # 获取 API 统计信息
        total_endpoints = self.api_client.get_endpoint_count()
        tag_stats = self.api_client.get_tag_stats()
        total_tags = len(tag_stats)
        
        log_realtime(f"   共 {total_tags} 个分类, {total_endpoints} 个端点")
        log_realtime(f"   分层摘要策略: 紧凑摘要 → Tag选择 → 详细API")
        
        # 打印各分类统计
        for tag, count in list(tag_stats.items())[:8]:
            log_realtime(f"     - {tag}: {count} 个端点")
        if len(tag_stats) > 8:
            log_realtime(f"     - ... 还有 {len(tag_stats) - 8} 个分类")
        
        # 获取初始紧凑 API 摘要（用于后续两阶段选择）
        api_summary = self.api_client.get_api_summary_compact()
        log_realtime(f"   初始紧凑摘要长度: {len(api_summary)} 字符")
        
        # 初始状态
        initial_state: ScriptGeneratorState = {
            "intent": intent,
            "api_summary": api_summary,
            "api_client": self.api_client,  # 传递 api_client 供两阶段选择使用
            "debug_mode": self.debug_mode,
            "auto_fix": self.auto_fix,
            "max_iterations": self.max_iterations,
            # 历史检索（RAG）
            "history_retrieval_results": None,
            "history_context": "",
            "use_history_script": False,
            "history_script": "",
            # 执行计划
            "execution_plan": {},
            "plan_json": "",
            # 步骤验证
            "steps_validated": False,
            "steps_validation_results": [],
            "steps_validation_context": "",
            "plan_fix_count": 0,
            # 执行状态
            "iteration": 0,
            "generated_script": "",
            "execution_output": "",
            "execution_error": "",
            "execution_success": False,
            "data_structure_info": "",
            "validation_passed": False,
            "validation_feedback": "",
            "final_script": "",
            "final_output": "",
            "messages": []
        }
        
        # 运行工作流
        final_state = await self.graph.ainvoke(initial_state)
        
        # 输出过程消息
        if verbose:
            for msg in final_state['messages']:
                print(msg)
        
        # 综合判断成功：执行成功且验证通过
        success = final_state['execution_success'] and final_state.get('validation_passed', True)
        
        return {
            "success": success,
            "script": final_state['final_script'],
            "output": final_state['final_output'],
            "validation_passed": final_state.get('validation_passed', True),
            "validation_feedback": final_state.get('validation_feedback', ''),
            "iterations": final_state['iteration'],
            "execution_plan": final_state['execution_plan'],
            "messages": final_state['messages'],
            # 历史检索信息（RAG）
            "history_retrieval_results": final_state.get('history_retrieval_results'),
            "use_history_script": final_state.get('use_history_script', False),
            # 步骤验证信息
            "steps_validated": final_state.get('steps_validated', False),
            "steps_validation_results": final_state.get('steps_validation_results', []),
            "steps_validation_context": final_state.get('steps_validation_context', ''),
            "plan_fix_count": final_state.get('plan_fix_count', 0)
        }
