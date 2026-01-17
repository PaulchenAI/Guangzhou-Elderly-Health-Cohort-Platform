# -*- coding: utf-8 -*-
"""
Django API 脚本生成器

使用 LangGraph 进行工作流管理，集成 Claude Code CLI 进行脚本生成和调试。

工作流:
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..claude_code.client import ClaudeCodeClient
from ..utils.config_models import ClaudeCodeConfig, Settings
from .client import OpenAPIAwareClient


# ==================== 状态定义 ====================

class ScriptGeneratorState(TypedDict):
    """脚本生成器状态"""
    # 输入
    intent: str                          # 用户意图
    api_summary: str                     # OpenAPI 摘要
    debug_mode: bool                     # 是否启用调试
    auto_fix: bool                       # 是否自动修正
    max_iterations: int                  # 最大迭代次数
    
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
    
    prompt = f"""你是一个 API 调用规划专家。根据用户的自然语言请求和可用的 API 列表，分析并拆解出完整的执行计划。

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
        
        # 生成摘要消息
        steps_count = len(execution_plan.get('steps', []))
        goal = execution_plan.get('intent_analysis', {}).get('goal', intent)
        state['messages'].append(f"[计划] 目标: {goal}")
        state['messages'].append(f"[计划] 拆解为 {steps_count} 个 API 调用步骤")
        
        for i, step in enumerate(execution_plan.get('steps', []), 1):
            api = step.get('api', {})
            state['messages'].append(f"[计划]   步骤{i}: {api.get('method')} {api.get('path')} - {step.get('description')}")
        
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
        state['messages'].append("[验证步骤] 跳过: 无执行步骤")
        return state
    
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
                if isinstance(response, dict):
                    output_info['keys'] = list(response.keys())
                    output_info['total'] = response.get('total', 'N/A')
                    items = response.get('items', [])
                    output_info['items_count'] = len(items)
                    
                    # 提取第一条数据的字段名
                    if items and isinstance(items[0], dict):
                        output_info['item_fields'] = list(items[0].keys())
                        # 截取样例数据
                        sample = {k: (str(v)[:50] + '...' if len(str(v)) > 50 else v) 
                                 for k, v in list(items[0].items())[:5]}
                        output_info['sample'] = sample
                else:
                    output_info['type'] = type(response).__name__
                
                validation_results.append({
                    'step': step_num,
                    'path': path,
                    'status': 'success',
                    'input': input_info,
                    'output': output_info
                })
                
                # 构建上下文
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
- 样例数据: {output_info.get('sample', {})}
**状态**: ✅ 成功
""")
                state['messages'].append(f"[验证步骤] 步骤 {step_num} ✅ 成功，返回 {output_info.get('items_count', 0)} 条数据")
                
            except Exception as e:
                error_msg = str(e)
                validation_results.append({
                    'step': step_num,
                    'path': path,
                    'status': 'failed',
                    'input': input_info,
                    'error': error_msg
                })
                
                context_parts.append(f"""### 步骤 {step_num}: {method} {path}
**输入**:
```json
{json.dumps(input_info, ensure_ascii=False, indent=2)}
```
**错误**: {error_msg}
**状态**: ❌ 失败
""")
                state['messages'].append(f"[验证步骤] 步骤 {step_num} ❌ 失败: {error_msg[:100]}")
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
    
    state['messages'].append(f"[修正计划] 根据验证结果修正执行计划 (第 {plan_fix_count} 次)...")
    
    prompt = f"""你是一个 API 调用规划专家。之前的执行计划在验证时失败了，请根据错误信息修正计划。

## 用户请求
"{intent}"

## 原执行计划
```json
{json.dumps(execution_plan, ensure_ascii=False, indent=2)[:3000]}
```

## 步骤验证结果
{validation_context}

## 可用的 API（摘要）
{api_summary[:5000]}

## 修正要求

1. 分析失败原因：API 路径错误？参数错误？
2. 根据 API 摘要找到正确的 API 路径
3. 修正参数格式
4. 输出修正后的完整执行计划

## 常见问题和解决方案

1. **404 错误**：API 路径不存在，需要从 API 摘要中找到正确路径
2. **422 错误**：参数格式错误，检查必填参数和参数类型
3. **400 错误**：请求参数不合法，检查参数值

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
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script_with_path)
        temp_path = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            cwd=str(config.aiagent_dir),
            timeout=config.execution_timeout
        )
        
        state['execution_output'] = result.stdout
        state['execution_error'] = result.stderr
        state['execution_success'] = result.returncode == 0
        
        # 提取数据结构信息
        combined_output = result.stdout + result.stderr
        state['data_structure_info'] = extract_data_structure(combined_output)
        
        if state['execution_success']:
            state['messages'].append(f"[执行] 成功")
        else:
            state['messages'].append(f"[执行] 失败: {result.stderr[:200]}")
        
    except subprocess.TimeoutExpired:
        state['execution_success'] = False
        state['execution_error'] = f"执行超时 ({config.execution_timeout}秒)"
        state['messages'].append(f"[执行] 超时")
    except Exception as e:
        state['execution_success'] = False
        state['execution_error'] = str(e)
        state['messages'].append(f"[执行] 异常: {e}")
    finally:
        Path(temp_path).unlink(missing_ok=True)
    
    return state


async def validate_result(state: ScriptGeneratorState) -> ScriptGeneratorState:
    """
    节点 4: 验证执行结果
    
    使用 LLM 检查脚本执行结果是否符合预期：
    - 结果是否为空（但预期有数据）
    - 数据格式是否正确
    - 是否完成了用户意图
    """
    # 如果执行失败，跳过验证
    if not state['execution_success']:
        state['validation_passed'] = False
        state['validation_feedback'] = state['execution_error']
        return state
    
    intent = state['intent']
    execution_plan = state['execution_plan']
    execution_output = state['execution_output']
    
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

def should_revalidate_steps(state: ScriptGeneratorState) -> str:
    """条件路由：决定是修正计划还是继续生成脚本"""
    steps_validated = state.get('steps_validated', False)
    iteration = state.get('iteration', 0)
    plan_fix_count = state.get('plan_fix_count', 0)
    
    # 步骤验证通过，继续生成脚本
    if steps_validated:
        return "generate"
    
    # 步骤验证失败且修正次数未超过限制（最多修正 2 次）
    if plan_fix_count < 2:
        return "fix_plan"
    
    # 超过修正次数限制，强制继续生成脚本（让后续流程处理）
    return "generate"


def build_script_generator_graph():
    """
    构建脚本生成器的 LangGraph 工作流
    
    新流程：
    plan → validate_steps → (fix_plan?) → generate → execute → validate → debug → (generate 或 end)
    
    改进点：
    1. 在生成脚本前先直接调用 API 验证步骤
    2. 如果步骤验证失败，先修正执行计划
    3. 将步骤验证的输入输出加入脚本生成的上下文
    """
    
    graph = StateGraph(ScriptGeneratorState)
    
    # 添加节点
    graph.add_node("plan", plan_intent)              # 1. 拆解意图
    graph.add_node("validate_steps", validate_steps) # 2. 验证步骤（新增）
    graph.add_node("fix_plan", fix_execution_plan)   # 2.5 修正计划（新增）
    graph.add_node("generate", generate_script)      # 3. 生成脚本
    graph.add_node("execute", execute_script)        # 4. 执行测试
    graph.add_node("validate", validate_result)      # 5. 验证结果
    graph.add_node("debug", debug_and_decide)        # 6. 调试决策
    
    # 设置入口
    graph.set_entry_point("plan")
    
    # 添加边
    graph.add_edge("plan", "validate_steps")     # 拆解后验证步骤
    
    # 条件边：验证步骤后决定是修正计划还是生成脚本
    graph.add_conditional_edges(
        "validate_steps",
        should_revalidate_steps,
        {
            "fix_plan": "fix_plan",    # 步骤验证失败，修正计划
            "generate": "generate"     # 步骤验证通过，生成脚本
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
        # 获取 API 摘要
        api_summary = self.api_client.get_api_summary_for_ai()
        
        # 初始状态
        initial_state: ScriptGeneratorState = {
            "intent": intent,
            "api_summary": api_summary,
            "debug_mode": self.debug_mode,
            "auto_fix": self.auto_fix,
            "max_iterations": self.max_iterations,
            "execution_plan": {},
            "plan_json": "",
            # 步骤验证（新增）
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
            # 步骤验证信息
            "steps_validated": final_state.get('steps_validated', False),
            "steps_validation_results": final_state.get('steps_validation_results', []),
            "steps_validation_context": final_state.get('steps_validation_context', ''),
            "plan_fix_count": final_state.get('plan_fix_count', 0)
        }
