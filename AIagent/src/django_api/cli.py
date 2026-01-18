# -*- coding: utf-8 -*-
"""
Django API 命令行工具

提供命令行接口来测试和使用 OpenAPI-Aware Django API 客户端。

使用方法:
    python -m src.django_api info              # 显示 API 信息
    python -m src.django_api login             # 测试登录
    python -m src.django_api search <keyword>  # 搜索 API 端点
    python -m src.django_api call <intent>     # 根据意图调用 API
    python -m src.django_api summary           # 生成 AI 摘要
    python -m src.django_api list-tags         # 列出所有 Tag
    python -m src.django_api list-endpoints    # 列出所有端点
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.django_api.client import OpenAPIAwareClient
from src.django_api.models import DjangoAPIConfig, APIEndpoint
from src.django_api.output_format import OutputFormat
from src.utils.config_models import Settings


async def extract_params_with_llm(
    intent: str, 
    endpoint: APIEndpoint,
    verbose: bool = False
) -> dict:
    """
    使用 LLM 从自然语言中提取 API 参数
    
    Args:
        intent: 用户意图（自然语言）
        endpoint: 匹配到的 API 端点
        verbose: 是否显示详细信息
    
    Returns:
        提取的参数字典
    """
    try:
        from langchain_openai import ChatOpenAI
        
        settings = Settings()
        
        # 构建提示词
        param_info = []
        if endpoint.parameters:
            for p in endpoint.parameters:
                name = p.get("name", "")
                required = "必填" if p.get("required") else "可选"
                schema = p.get("schema", {})
                param_type = schema.get("type", "string")
                desc = p.get("description", schema.get("title", ""))
                param_info.append(f"  - {name} ({param_type}, {required}): {desc}")
        
        if endpoint.request_body:
            body_schema = endpoint.request_body.get("content", {}).get("application/json", {}).get("schema", {})
            props = body_schema.get("properties", {})
            required_fields = body_schema.get("required", [])
            for prop_name, prop_info in props.items():
                required = "必填" if prop_name in required_fields else "可选"
                param_type = prop_info.get("type", "string")
                desc = prop_info.get("description", prop_info.get("title", ""))
                param_info.append(f"  - {prop_name} ({param_type}, {required}): {desc}")
        
        prompt = f"""你是一个参数提取助手。根据用户的自然语言请求，提取 API 调用所需的参数。

API 信息:
- 路径: {endpoint.method} {endpoint.path}
- 描述: {endpoint.summary}
- {endpoint.description[:500] if endpoint.description else "无详细描述"}

可用参数:
{chr(10).join(param_info) if param_info else "  无参数"}

用户请求: "{intent}"

请分析用户请求，提取出需要的参数值。只返回 JSON 格式的参数，不要解释：
- 如果用户请求中包含具体值（如名称、ID、日期等），提取为对应参数
- 如果没有明确的值，不要猜测，返回空对象 {{}}
- 对于问卷类型，常见值有: 个人信息登记表、户外活动记录表、门诊随访表 等

返回格式: {{"param_name": "value"}}"""

        # 调用 LLM
        llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0,
        )
        
        if verbose:
            print("\n[LLM 参数提取]")
            print(f"提示词长度: {len(prompt)} 字符")
        
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()
        
        if verbose:
            print(f"LLM 响应: {response_text}")
        
        # 解析 JSON
        import re
        json_match = re.search(r'\{[^{}]*\}', response_text)
        if json_match:
            params = json.loads(json_match.group())
            return params
        
        return {}
        
    except ImportError:
        print("⚠ 警告: 未安装 langchain_openai，无法使用智能参数提取")
        print("  安装: pip install langchain-openai")
        return {}
    except Exception as e:
        if verbose:
            print(f"⚠ LLM 参数提取失败: {e}")
        return {}


def get_client() -> tuple[OpenAPIAwareClient, DjangoAPIConfig]:
    """获取配置和客户端"""
    try:
        settings = Settings()
        config = settings.get_django_api_config()
        client = OpenAPIAwareClient(config)
        return client, config
    except Exception as e:
        print(f"错误: 无法加载配置 - {e}")
        print("提示: 请确保 .env 文件中设置了 DJANGO_API_* 配置")
        sys.exit(1)


async def cmd_info(args):
    """显示 API 信息"""
    client, config = get_client()
    
    print("=" * 60)
    print("Django API 信息")
    print("=" * 60)
    print(f"Base URL: {config.base_url}")
    print(f"Username: {config.username}")
    print()
    
    try:
        print("正在加载 OpenAPI Schema...")
        await client.load_openapi_schema()
        
        info = client._schema.get("info", {})
        print(f"\nAPI 标题: {info.get('title', 'N/A')}")
        print(f"API 版本: {info.get('version', 'N/A')}")
        print(f"API 描述: {info.get('description', 'N/A')[:100]}...")
        print()
        print(f"端点数量: {len(client._endpoints)}")
        print(f"Tag 数量: {len(client._endpoints_by_tag)}")
        
        # 显示 Tag 统计
        print("\nTag 统计:")
        for tag, endpoints in sorted(client._endpoints_by_tag.items(), 
                                     key=lambda x: -len(x[1])):
            print(f"  - {tag}: {len(endpoints)} 个端点")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


async def cmd_login(args):
    """测试登录"""
    client, config = get_client()
    
    print("=" * 60)
    print("测试登录")
    print("=" * 60)
    print(f"Base URL: {config.base_url}")
    print(f"Username: {config.username}")
    print()
    
    try:
        print("正在登录...")
        success = await client.login()
        
        if success:
            print("✓ 登录成功!")
            print(f"Access Token: {client.access_token[:50]}...")
            if client.refresh_token:
                print(f"Refresh Token: {client.refresh_token[:30]}...")
        else:
            print("✗ 登录失败")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


async def cmd_search(args):
    """搜索 API 端点"""
    client, config = get_client()
    keyword = args.keyword
    
    print("=" * 60)
    print(f"搜索 API 端点: '{keyword}'")
    print("=" * 60)
    
    try:
        await client.load_openapi_schema()
        results = client.get_endpoints_by_keyword(keyword)
        
        print(f"找到 {len(results)} 个匹配端点:\n")
        
        for i, ep in enumerate(results[:args.limit], 1):
            print(f"{i}. [{ep.method}] {ep.path}")
            print(f"   操作ID: {ep.operation_id}")
            print(f"   摘要: {ep.summary or 'N/A'}")
            print(f"   Tags: {', '.join(ep.tags)}")
            if args.verbose and ep.parameters:
                params = [p.get('name', '') for p in ep.parameters[:5]]
                print(f"   参数: {', '.join(params)}")
            print()
        
        if len(results) > args.limit:
            print(f"... 还有 {len(results) - args.limit} 个结果")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


async def cmd_call(args):
    """根据意图调用 API"""
    client, config = get_client()
    intent = args.intent
    
    print("=" * 60)
    print(f"根据意图调用 API: '{intent}'")
    print("=" * 60)
    
    try:
        # 加载 Schema
        await client.load_openapi_schema()
        
        # 查找匹配的端点
        endpoint = client.find_endpoint(intent)
        if not endpoint:
            print("✗ 未找到匹配的 API 端点")
            await client.close()
            return
        
        print(f"匹配到: [{endpoint.method}] {endpoint.path}")
        print(f"操作ID: {endpoint.operation_id}")
        print(f"摘要: {endpoint.summary or 'N/A'}")
        
        # 显示参数信息
        if endpoint.parameters:
            param_names = [f"{p.get('name')}{'*' if p.get('required') else ''}" for p in endpoint.parameters[:5]]
            print(f"参数: {', '.join(param_names)}")
        if endpoint.request_body:
            print(f"请求体: 需要 (使用 -p 参数提供 JSON)")
        print()
        
        # 检查 POST/PUT 请求是否缺少必要参数（智能模式不警告，因为会自动提取）
        if endpoint.method in ("POST", "PUT") and endpoint.request_body and not args.params and not args.smart:
            print("⚠ 警告: 此 API 需要请求体参数，但未提供 -p 参数")
            print("  示例: python -m AIagent.src.django_api call \"...\" -p '{\"key\": \"value\"}'")
            print("  提示: 使用 -s/--smart 参数可自动从自然语言中提取参数")
            print()
            # 询问是否继续
            print("是否继续调用？（可能返回 422 错误）[y/N] ", end="")
            try:
                response = input().strip().lower()
                if response != 'y':
                    print("已取消")
                    await client.close()
                    return
            except EOFError:
                # 非交互模式，直接继续
                pass
            print()
        
        # 如果需要认证，先登录
        if not args.no_auth:
            print("正在登录...")
            success = await client.login()
            if not success:
                print("✗ 登录失败，无法调用 API")
                await client.close()
                return
            print("✓ 登录成功")
            print()
        
        # 解析参数
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                # 尝试简单的 key=value 格式
                for p in args.params.split(','):
                    if '=' in p:
                        k, v = p.split('=', 1)
                        params[k.strip()] = v.strip()
        
        # 智能模式：使用 LLM 从自然语言中提取参数
        if args.smart and not params:
            print("🤖 智能模式: 使用 LLM 从自然语言中提取参数...")
            extracted_params = await extract_params_with_llm(intent, endpoint, args.verbose)
            if extracted_params:
                params = extracted_params
                print(f"✓ 提取到参数: {json.dumps(params, ensure_ascii=False)}")
            else:
                print("  未能提取到参数，将使用默认值调用")
            print()
        
        # 调用 API
        print(f"正在调用 API...")
        if params:
            print(f"参数: {json.dumps(params, ensure_ascii=False)}")
        
        result = await client.call_api(endpoint, query_params=params if endpoint.method == "GET" else None,
                                       body=params if endpoint.method != "GET" else None)
        
        print("\n响应:")
        print("-" * 40)
        if isinstance(result, dict):
            print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
            if len(json.dumps(result)) > 2000:
                print("... (响应已截断)")
        else:
            print(result)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
    finally:
        await client.close()


async def cmd_summary(args):
    """生成 AI 摘要"""
    client, config = get_client()
    
    print("=" * 60)
    print("生成 AI 摘要")
    print("=" * 60)
    
    try:
        await client.load_openapi_schema()
        summary = client.get_api_summary_for_ai()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"摘要已保存到: {args.output}")
            print(f"总字符数: {len(summary)}")
        else:
            limit = args.limit
            print(summary[:limit])
            if len(summary) > limit:
                print(f"\n... (共 {len(summary)} 字符，使用 -l 参数调整显示长度)")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


async def cmd_list_tags(args):
    """列出所有 Tag"""
    client, config = get_client()
    
    try:
        await client.load_openapi_schema()
        
        print("=" * 60)
        print("API Tag 列表")
        print("=" * 60)
        
        for tag in sorted(client._endpoints_by_tag.keys()):
            count = len(client._endpoints_by_tag[tag])
            print(f"  {tag} ({count})")
        
        print(f"\n共 {len(client._endpoints_by_tag)} 个 Tag")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


async def cmd_list_endpoints(args):
    """列出所有端点"""
    client, config = get_client()
    
    try:
        await client.load_openapi_schema()
        
        print("=" * 60)
        print("API 端点列表")
        print("=" * 60)
        
        # 按 Tag 过滤
        if args.tag:
            endpoints = client._endpoints_by_tag.get(args.tag, [])
            print(f"Tag: {args.tag}\n")
        else:
            endpoints = list(client._endpoints.values())
        
        # 按方法过滤
        if args.method:
            endpoints = [ep for ep in endpoints if ep.method == args.method.upper()]
        
        for ep in endpoints[:args.limit]:
            print(f"[{ep.method:6}] {ep.path}")
            if args.verbose:
                print(f"         操作ID: {ep.operation_id}")
                print(f"         摘要: {ep.summary or 'N/A'}")
                print()
        
        if len(endpoints) > args.limit:
            print(f"\n... 还有 {len(endpoints) - args.limit} 个端点")
        
        print(f"\n共 {len(endpoints)} 个端点")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await client.close()


def compress_execution_output(output: str, max_length: int = 1500) -> str:
    """
    压缩和提取执行输出中的关键信息
    
    提取策略：
    1. 保留所有 [DEBUG] 行
    2. 保留错误信息和 Traceback
    3. 提取数据结构信息（字段名、类型）
    4. 压缩 JSON 数据，只保留字段名和类型
    """
    import re
    
    lines = output.split('\n')
    compressed_lines = []
    
    # 提取关键行
    for line in lines:
        line_stripped = line.strip()
        
        # 保留 DEBUG 输出
        if '[DEBUG]' in line:
            compressed_lines.append(line_stripped)
            continue
        
        # 保留错误相关
        if any(kw in line for kw in ['错误', 'Error', 'error:', 'Exception', 'Traceback', 'AttributeError', 'KeyError', 'TypeError']):
            compressed_lines.append(line_stripped)
            continue
        
        # 保留字段/键信息
        if any(kw in line for kw in ['键:', 'keys:', '字段', 'field']):
            compressed_lines.append(line_stripped)
            continue
    
    # 尝试从输出中提取 JSON 数据结构
    json_pattern = r'\{[^{}]*\}'
    json_matches = re.findall(json_pattern, output)
    
    if json_matches:
        # 提取第一个 JSON 的字段名
        try:
            import json
            first_json = json.loads(json_matches[0])
            if isinstance(first_json, dict):
                fields_info = f"[数据结构] 字段: {list(first_json.keys())}"
                # 提取字段值类型
                types_info = {k: type(v).__name__ for k, v in first_json.items()}
                fields_info += f"\n[字段类型] {types_info}"
                compressed_lines.append(fields_info)
        except:
            pass
    
    result = '\n'.join(compressed_lines)
    
    # 如果仍然太长，截断
    if len(result) > max_length:
        result = result[:max_length] + "\n... (已截断)"
    
    return result if result else output[:max_length]


def compress_script_for_context(script: str, max_length: int = 1500) -> str:
    """
    压缩脚本，保留关键逻辑部分
    
    提取策略：
    1. 保留 API 调用相关代码
    2. 保留数据处理逻辑
    3. 移除导入语句和模板代码
    """
    lines = script.split('\n')
    important_lines = []
    
    skip_patterns = [
        'import ', 'from ', '#!/', '# -*-', '"""', "'''",
        'AIAGENT_DIR', 'sys.path', 'if not (AIAGENT_DIR',
        'for parent in Path'
    ]
    
    keep_patterns = [
        'find_endpoint', 'call_api', 'response', 'items',
        'endpoint', '.get(', 'if ', 'for ', 'print(',
        'debug_print', 'result', 'matched', 'query_params', 'body='
    ]
    
    in_main_function = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # 跳过空行和注释
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # 跳过导入和模板代码
        if any(p in line for p in skip_patterns):
            continue
        
        # 检测进入 main 函数
        if 'async def main' in line or 'def main' in line:
            in_main_function = True
            important_lines.append(line_stripped)
            continue
        
        # 在 main 函数内，保留关键代码
        if in_main_function:
            if any(p in line for p in keep_patterns):
                important_lines.append(line_stripped)
    
    result = '\n'.join(important_lines)
    
    if len(result) > max_length:
        result = result[:max_length] + "\n... (已截断)"
    
    return result if result else script[:max_length]


async def generate_script_with_llm(
    intent: str,
    api_summary: str,
    verbose: bool = False,
    debug: bool = False,
    error_context: str = None,
    previous_script: str = None
) -> str:
    """
    使用 LLM 根据用户意图生成多步骤查询脚本
    
    Args:
        intent: 用户意图（自然语言）
        api_summary: OpenAPI 摘要
        verbose: 是否显示详细信息
        debug: 是否添加调试输出
        error_context: 上次执行的错误信息（用于迭代修正）
        previous_script: 上次生成的脚本（用于迭代修正）
    
    Returns:
        生成的 Python 脚本
    """
    try:
        from langchain_openai import ChatOpenAI
        
        settings = Settings()
        
        # 构建迭代修正上下文
        iteration_context = ""
        if error_context and previous_script:
            # 压缩和提取关键信息
            compressed_error = compress_execution_output(error_context)
            compressed_script = compress_script_for_context(previous_script)
            
            iteration_context = f"""
## ⚠️ 上次执行失败，请根据以下信息修正

### 执行输出（已压缩提取关键信息）
```
{compressed_error}
```

### 上次脚本的关键部分
```python
{compressed_script}
```

### 修正要求
1. **分析数据结构**：根据 DEBUG 输出的实际字段名修正代码
2. **使用正确字段**：如输出显示 `survey_name` 则使用该字段，而非猜测的 `name`
3. **检查返回格式**：确认 `items` vs `data` vs `results`
4. **保留调试输出**：继续输出关键变量便于下次修正

"""
        
        # Debug 模式的额外说明
        debug_instructions = ""
        if debug:
            debug_instructions = """
## Debug 模式要求（关键！）

在脚本中添加详细的数据结构输出，便于迭代修正：

1. **输出响应的完整字段列表**：
```python
response = await client.call_api(endpoint, ...)
if isinstance(response, dict):
    print(f"[DEBUG] 响应字段: {list(response.keys())}")
```

2. **输出列表数据的第一条记录的字段名**：
```python
items = response.get("items", [])
if items and isinstance(items[0], dict):
    print(f"[DEBUG] 数据字段: {list(items[0].keys())}")
    # 输出第一条数据的示例值（截断长字段）
    sample = {k: (str(v)[:50] + '...' if len(str(v)) > 50 else v) for k, v in items[0].items()}
    print(f"[DEBUG] 示例数据: {sample}")
```

3. **在查找/匹配失败时输出候选值**：
```python
# 如果匹配失败，输出实际可用的值
if not matched:
    available_names = [item.get("实际字段名") for item in items[:5]]
    print(f"[DEBUG] 可用的名称: {available_names}")
```

4. **关键变量检查**：
```python
print(f"[DEBUG] 变量类型: {type(var)}, 值: {str(var)[:200]}")
```
"""
        
        prompt = f"""你是一个 Python 脚本生成专家。根据用户的自然语言请求和可用的 API 列表，生成一个完整的、可执行的 Python 脚本。

## 可用的 API

{api_summary[:8000]}

## 用户请求

"{intent}"
{iteration_context}
## 重要：API 返回格式说明

本系统的 API 返回格式遵循以下规范：

1. **分页列表接口** 返回格式:
```json
{{
    "items": [...],      // 数据列表（不是 data, results, list）
    "total": 100,        // 总数
    "page": 1,
    "page_size": 10
}}
```

2. **单个对象接口** 直接返回对象:
```json
{{
    "id": "xxx",
    "name": "xxx",
    ...
}}
```

3. **call_api 返回值**:
- `call_api()` 直接返回 dict，不需要调用 `.json()`
- 使用 `response.get("items", [])` 获取列表数据
- 使用 `response.get("total", 0)` 获取总数

## 生成要求

1. **分析用户意图**：识别用户想要查询的数据、条件、以及期望的输出格式
2. **识别 API 依赖**：如果需要多个 API 协同（如先获取 ID 再查询），按正确顺序调用
3. **提取查询条件**：从用户请求中提取具体的筛选条件（如名称、类型、日期等）
4. **正确处理返回格式**：使用 `items` 而非 `data` 获取列表数据
{debug_instructions}
## 脚本模板

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
自动生成的查询脚本
意图: {intent}
运行方式: cd AIagent && python script.py
\"\"\"

import asyncio
import json
import sys
from pathlib import Path

# 添加 AIagent 项目路径
AIAGENT_DIR = Path(__file__).parent
if not (AIAGENT_DIR / "src").exists():
    for parent in Path(__file__).parents:
        if (parent / "src" / "django_api").exists():
            AIAGENT_DIR = parent
            break
sys.path.insert(0, str(AIAGENT_DIR))

from src.django_api.client import OpenAPIAwareClient
from src.utils.config_models import Settings

# Debug 开关
DEBUG = {'True' if debug else 'False'}

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
        
        # === 步骤 1: [描述] ===
        endpoint = client.find_endpoint("意图描述")
        debug_print(f"找到端点: {{endpoint.path if endpoint else 'None'}}")
        
        response = await client.call_api(endpoint, query_params={{...}})
        debug_print(f"响应类型: {{type(response)}}, 键: {{response.keys() if isinstance(response, dict) else 'N/A'}}")
        
        # 正确获取列表数据
        items = response.get("items", [])  # 注意：是 items 不是 data
        debug_print(f"获取到 {{len(items)}} 条数据")
        
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

## 注意事项

1. 使用 `client.find_endpoint("中文意图")` 查找 API 端点
2. `call_api()` 返回 dict，不需要 `.json()`
3. 列表数据用 `response.get("items", [])`，不是 `data` 或 `results`
4. GET 请求用 `query_params`，POST 请求用 `body`
5. 添加错误处理和空结果检查

请直接输出完整的 Python 脚本代码，不需要额外的解释。"""

        # 调用 LLM
        llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=0,
        )
        
        if verbose:
            print("\n[LLM 脚本生成]")
            print(f"提示词长度: {len(prompt)} 字符")
            if iteration_context:
                print("模式: 迭代修正")
        
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()
        
        # 提取代码块
        import re
        code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        # 如果没有代码块，尝试直接返回
        if 'import' in response_text and 'async def' in response_text:
            return response_text
        
        return f"# LLM 生成失败，原始响应:\n# {response_text[:500]}"
        
    except ImportError:
        return "# 错误: 未安装 langchain_openai\n# 安装: pip install langchain-openai"
    except Exception as e:
        return f"# 错误: {e}"


async def cmd_generate(args):
    """
    生成多步骤查询脚本（使用 LangGraph 工作流）
    
    重构后使用:
    - LangGraph 管理工作流（分析→生成→执行→调试循环）
    - Claude Code CLI 或 LangChain 进行脚本生成
    """
    from .script_generator import ScriptGenerator
    
    client, config = get_client()
    intent = args.intent
    
    # 确定输出格式
    output_format = OutputFormat.JSON if getattr(args, 'json', False) else OutputFormat.TEXT
    no_save = getattr(args, 'no_save', False)
    
    # JSON 分隔符常量
    JSON_OUTPUT_SEPARATOR = "===JSON_OUTPUT_START==="
    
    # 定义输出函数：JSON 模式下输出到 stderr，文本模式下输出到 stdout
    def info_print(*msg_args, **kwargs):
        """输出流程信息：JSON 模式输出到 stderr，文本模式输出到 stdout"""
        if output_format == OutputFormat.JSON:
            print(*msg_args, file=sys.stderr, **kwargs)
        else:
            print(*msg_args, **kwargs)
    
    # 显示流程信息（两种模式都显示）
    info_print("=" * 60)
    info_print(f"生成多步骤脚本: '{intent}'")
    info_print(f"🔧 模式: LangGraph 工作流")
    if args.debug:
        info_print(f"📝 Debug 输出已启用")
    if args.auto_fix:
        info_print(f"🔄 自动迭代修正已启用 (最大 {args.max_iter} 次)")
    if no_save:
        info_print(f"📝 历史记录保存已禁用")
    if output_format == OutputFormat.JSON:
        info_print(f"📤 输出格式: JSON (分隔符: {JSON_OUTPUT_SEPARATOR})")
    info_print("=" * 60)
    
    try:
        # 加载 OpenAPI Schema
        info_print("\n正在加载 OpenAPI Schema...")
        await client.load_openapi_schema()
        info_print(f"✓ 已加载 {len(client._endpoints)} 个 API 端点")
        
        # 创建脚本生成器
        generator = ScriptGenerator(
            api_client=client,
            debug_mode=args.debug,
            auto_fix=args.auto_fix,
            max_iterations=args.max_iter if hasattr(args, 'max_iter') else 3,
            save_history=not no_save,
            output_format=output_format,
        )
        
        # auto_fix 默认启用，用于执行计划验证阶段的修正
        # 如果不使用 -x 参数，脚本执行后不进行迭代修正
        if not args.execute:
            generator.max_iterations = 1
        
        # 运行 LangGraph 工作流
        info_print("\n🚀 启动 LangGraph 工作流...")
        info_print("  [1/4] 拆解意图...")
        result = await generator.generate(
            intent, 
            verbose=args.verbose,
            output_format=output_format,
            no_save=no_save,
        )
        
        # JSON 格式：输出带分隔符的 JSON
        if output_format == OutputFormat.JSON:
            # 构建完整的 JSON 输出
            json_result = {
                "success": result.get('success', False),
                "iterations": result.get('iterations', 0),
                "intent": intent,
                "execution_plan": result.get('execution_plan', {}),
                "validation_results": result.get('steps_validation_results', []),
                "output": result.get('output', ''),
                "script": result.get('script', ''),
            }
            # 添加格式化的数据输出
            formatted = generator.format_output(result, output_format)
            if formatted:
                try:
                    json_result["formatted_data"] = json.loads(formatted)
                except:
                    json_result["formatted_data"] = formatted
            
            # 完成信息输出到 stderr
            info_print("\n✅ 执行完成")
            info_print(f"  迭代次数: {result.get('iterations', 0)}")
            info_print(f"  状态: {'成功' if result.get('success') else '失败'}")
            
            # 输出分隔符和 JSON（到 stdout，方便程序提取）
            print(JSON_OUTPUT_SEPARATOR)
            print(json.dumps(json_result, ensure_ascii=False, indent=2))
        else:
            # 文本格式：显示执行计划
            if result.get('execution_plan'):
                plan = result['execution_plan']
                print("\n" + "=" * 60)
                print("📋 执行计划")
                print("=" * 60)
                
                # 显示意图分析
                intent_analysis = plan.get('intent_analysis', {})
                if intent_analysis:
                    print(f"\n目标: {intent_analysis.get('goal', 'N/A')}")
                    print(f"目标数据: {intent_analysis.get('target_data', 'N/A')}")
                    conditions = intent_analysis.get('conditions', [])
                    if conditions:
                        print(f"条件: {', '.join(conditions)}")
                
                # 显示步骤
                steps = plan.get('steps', [])
                if steps:
                    print(f"\n执行步骤 ({len(steps)} 个):")
                    for step in steps:
                        if not step or not isinstance(step, dict):
                            continue
                        api = step.get('api', {}) or {}
                        params = step.get('params', {}) or {}
                        print(f"\n  步骤 {step.get('step_number', '?')}: {step.get('description', 'N/A')}")
                        print(f"    API: {api.get('method', '?')} {api.get('path', '?')}")
                        if params.get('query_params'):
                            print(f"    Query: {json.dumps(params['query_params'], ensure_ascii=False)}")
                        if params.get('body'):
                            print(f"    Body: {json.dumps(params['body'], ensure_ascii=False)}")
                        if step.get('data_to_extract'):
                            print(f"    提取: {step['data_to_extract']}")
            
            # 显示步骤验证结果
            if result.get('steps_validation_results'):
                print("\n" + "=" * 60)
                print("🔬 步骤验证结果")
                print("=" * 60)
                
                for step_result in result['steps_validation_results']:
                    step_num = step_result.get('step', '?')
                    path = step_result.get('path', 'N/A')
                    status = step_result.get('status', 'unknown')
                    output = step_result.get('output', {})
                    
                    print(f"\n  步骤 {step_num}: {path}")
                    
                    if status == 'success':
                        print(f"    状态: ✅ 成功")
                    elif status == 'warning':
                        print(f"    状态: ⚠️ 警告")
                        if step_result.get('warning'):
                            print(f"    警告: {step_result['warning']}")
                    elif status == 'skipped':
                        print(f"    状态: ⏭️ 跳过 ({step_result.get('message', '')})")
                        continue
                    else:  # failed
                        print(f"    状态: ❌ 失败")
                        print(f"    错误: {step_result.get('error', 'N/A')[:200]}")
                        continue
                    
                    # 显示输出信息（成功和警告状态都显示）
                    if output:
                        items_count = output.get('items_count', output.get('length', 'N/A'))
                        print(f"    响应字段: {output.get('keys', output.get('item_fields', []))}")
                        print(f"    items 数量: {items_count}")
                        print(f"    total: {output.get('total', 'N/A')}")
                        if output.get('expected_fields'):
                            print(f"    需要提取: {output['expected_fields']}")
                            print(f"    已提取到: {output.get('extracted_fields', [])}")
                            if output.get('missing_fields'):
                                print(f"    ❌ 缺失字段: {output['missing_fields']}")
                        if output.get('placeholder_warning'):
                            print(f"    ℹ️ 占位符: {output.get('placeholder_info', '参数包含占位符')}")
                        if output.get('sample'):
                            print(f"    样例数据: {output['sample']}")
                
                # 显示修正次数
                if result.get('plan_fix_count', 0) > 0:
                    print(f"\n  📝 执行计划修正次数: {result['plan_fix_count']}")
                
                if result.get('steps_validated'):
                    print(f"\n  ✅ 所有步骤验证通过")
                else:
                    print(f"\n  ❌ 步骤验证失败（已尝试修正 {result.get('plan_fix_count', 0)} 次）")
                    if not result.get('script'):
                        print(f"  ⛔ 验证失败，未生成脚本")
            
            # 显示结果
            print("\n" + "=" * 60)
            print(f"结果 (迭代次数: {result['iterations']})")
            print("=" * 60)
            # 文本格式输出
            if result['script']:
                print("\n📜 生成的脚本:")
                print("-" * 40)
                # 限制脚本显示长度
                script_preview = result['script']
                if len(script_preview) > 3000 and not args.verbose:
                    script_preview = script_preview[:3000] + "\n... (已截断，使用 -v 查看完整脚本)"
                print(script_preview)
                
                # 保存到文件
                if args.output:
                    output_path = Path(args.output)
                    output_path.write_text(result['script'], encoding='utf-8')
                    print(f"\n✓ 脚本已保存到: {args.output}")
            
            if result['output']:
                print("\n📤 执行输出:")
                print("-" * 40)
                # 使用格式化输出
                formatted = generator.format_output(result, OutputFormat.TEXT)
                print(formatted)
            
            # 显示过程消息
            if args.verbose and result['messages']:
                print("\n📋 工作流日志:")
                print("-" * 40)
                for msg in result['messages']:
                    print(f"  {msg}")
            
            # 显示验证结果
            if 'validation_passed' in result:
                if result['validation_passed']:
                    print(f"\n🔍 结果验证: ✅ 通过")
                else:
                    print(f"\n🔍 结果验证: ❌ 失败")
                    if result.get('validation_feedback'):
                        print(f"   原因: {result['validation_feedback'][:200]}")
            
            # 显示历史复用信息
            if result.get('history_reused'):
                print(f"\n📚 历史复用: ✅ 使用了历史脚本")
            
            # 显示最终状态
            if result['success']:
                print("\n✅ 脚本执行成功，结果已验证")
            else:
                print(f"\n⚠️ 脚本执行或验证失败 (迭代 {result['iterations']} 次)")
            
            if not args.execute:
                print(f"\n提示: 使用 -x 参数执行脚本，使用 -d 启用调试模式")
                print(f"      使用 --auto-fix 启用自动迭代修正")
                print(f"      使用 --json 输出 JSON 格式结果")
        
    except Exception as e:
        print(f"错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        await client.close()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog='django-api',
        description='Django API 命令行工具 - OpenAPI-Aware 客户端',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s info                          # 显示 API 信息
  %(prog)s login                         # 测试登录
  %(prog)s search user                   # 搜索包含 'user' 的端点
  %(prog)s search 问卷 -v                # 详细搜索
  %(prog)s call "获取用户信息"           # 根据意图调用 API
  %(prog)s call "获取用户列表" -p '{"page":1}'  # 带参数调用
  %(prog)s call "获取户外活动记录表问卷" -s    # 智能模式：自动提取参数
  %(prog)s call "查询问卷类型为个人信息登记表的数据" -s -v  # 智能模式+详细输出
  %(prog)s generate "查询户外活动问卷数据并导出"  # 🆕 生成多步骤脚本
  %(prog)s generate "获取所有用户及其角色" -x -d  # 执行 + 调试模式
  %(prog)s generate "查询问卷数据" -x --auto-fix  # 执行 + 自动迭代修正
  %(prog)s summary -o api_summary.md     # 导出 AI 摘要
  %(prog)s list-tags                     # 列出所有 Tag
  %(prog)s list-endpoints --tag Core-User  # 列出指定 Tag 的端点
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # info 命令
    parser_info = subparsers.add_parser('info', help='显示 API 信息')
    parser_info.set_defaults(func=cmd_info)
    
    # login 命令
    parser_login = subparsers.add_parser('login', help='测试登录')
    parser_login.set_defaults(func=cmd_login)
    
    # search 命令
    parser_search = subparsers.add_parser('search', help='搜索 API 端点')
    parser_search.add_argument('keyword', help='搜索关键词')
    parser_search.add_argument('-l', '--limit', type=int, default=20, help='最大结果数 (默认: 20)')
    parser_search.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser_search.set_defaults(func=cmd_search)
    
    # call 命令
    parser_call = subparsers.add_parser('call', help='根据意图调用 API')
    parser_call.add_argument('intent', help='调用意图（如 "获取用户列表"）')
    parser_call.add_argument('-p', '--params', help='请求参数 (JSON 格式或 key=value,key2=value2)')
    parser_call.add_argument('-s', '--smart', action='store_true', 
                             help='智能模式: 使用 LLM 从自然语言中自动提取参数')
    parser_call.add_argument('--no-auth', action='store_true', help='跳过认证')
    parser_call.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser_call.set_defaults(func=cmd_call)
    
    # summary 命令
    parser_summary = subparsers.add_parser('summary', help='生成 AI 摘要')
    parser_summary.add_argument('-o', '--output', help='输出文件路径')
    parser_summary.add_argument('-l', '--limit', type=int, default=5000, help='最大显示字符数 (默认: 5000)')
    parser_summary.set_defaults(func=cmd_summary)
    
    # list-tags 命令
    parser_tags = subparsers.add_parser('list-tags', help='列出所有 Tag')
    parser_tags.set_defaults(func=cmd_list_tags)
    
    # list-endpoints 命令
    parser_endpoints = subparsers.add_parser('list-endpoints', help='列出所有端点')
    parser_endpoints.add_argument('--tag', help='按 Tag 过滤')
    parser_endpoints.add_argument('--method', help='按 HTTP 方法过滤 (GET/POST/PUT/DELETE)')
    parser_endpoints.add_argument('-l', '--limit', type=int, default=50, help='最大结果数 (默认: 50)')
    parser_endpoints.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser_endpoints.set_defaults(func=cmd_list_endpoints)
    
    # generate 命令 - 生成多步骤查询脚本
    parser_generate = subparsers.add_parser('generate', help='🆕 生成多步骤查询脚本（LLM 驱动）')
    parser_generate.add_argument('intent', help='查询意图（如 "查询户外活动问卷的所有数据并导出"）')
    parser_generate.add_argument('-o', '--output', help='保存脚本到文件')
    parser_generate.add_argument('-x', '--execute', action='store_true', help='生成后立即执行')
    parser_generate.add_argument('-d', '--debug', action='store_true', help='启用调试模式（添加详细输出）')
    parser_generate.add_argument('--auto-fix', action='store_true', help='执行失败时自动迭代修正')
    parser_generate.add_argument('--max-iter', type=int, default=10, help='最大迭代次数（默认: 10）')
    parser_generate.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser_generate.add_argument('--json', action='store_true', help='输出 JSON 格式结果')
    parser_generate.add_argument('--no-save', action='store_true', help='不保存执行记录到历史')
    parser_generate.set_defaults(func=cmd_generate)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # 运行异步命令
    asyncio.run(args.func(args))


if __name__ == '__main__':
    main()
