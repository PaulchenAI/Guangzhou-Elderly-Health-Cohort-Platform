# -*- coding: utf-8 -*-
"""
Django API 集成测试

测试实际的登录和 API 调用功能
需要 backend-django 服务运行
"""

import asyncio
import sys
from pathlib import Path
import os
import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.django_api.client import OpenAPIAwareClient
from src.django_api.models import DjangoAPIConfig
from src.utils.config_models import Settings


@pytest.mark.asyncio
@pytest.mark.integration
async def test_integration():
    """集成测试：测试登录和 API 调用"""
    # 默认跳过：需要真实 backend-django 服务运行
    if os.environ.get("RUN_DJANGO_API_INTEGRATION", "").strip() != "1":
        pytest.skip("需要设置 RUN_DJANGO_API_INTEGRATION=1 并启动 backend-django 才运行该集成测试")
    print("=" * 60)
    print("Django API 集成测试")
    print("=" * 60)
    
    # 1. 加载配置
    print("\n[1/5] 加载配置...")
    try:
        settings = Settings()
        config = settings.get_django_api_config()
        print(f"  ✓ Base URL: {config.base_url}")
        print(f"  ✓ Username: {config.username}")
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        print("  提示: 请确保 .env 文件中设置了 DJANGO_API_* 配置")
        return False
    
    # 2. 创建客户端
    print("\n[2/5] 创建客户端...")
    client = OpenAPIAwareClient(config)
    
    # 3. 加载 OpenAPI Schema
    print("\n[3/5] 加载 OpenAPI Schema...")
    try:
        schema = await client.load_openapi_schema()
        endpoint_count = len(client._endpoints)
        tag_count = len(client._endpoints_by_tag)
        print(f"  ✓ Schema 加载成功")
        print(f"  ✓ 发现 {endpoint_count} 个 API 端点")
        print(f"  ✓ 发现 {tag_count} 个 Tag 分组")
        
        # 显示部分 Tag
        print("  ✓ Tag 列表（前10个）:")
        for tag in list(client._endpoints_by_tag.keys())[:10]:
            count = len(client._endpoints_by_tag[tag])
            print(f"      - {tag} ({count} 个端点)")
    except Exception as e:
        print(f"  ✗ Schema 加载失败: {e}")
        await client.close()
        return False
    
    # 4. 测试登录
    print("\n[4/5] 测试登录...")
    try:
        success = await client.login()
        if success:
            print(f"  ✓ 登录成功")
            print(f"  ✓ Access Token: {client.access_token[:20]}...")
        else:
            print("  ✗ 登录失败（无异常但返回 False）")
            await client.close()
            return False
    except Exception as e:
        print(f"  ✗ 登录失败: {e}")
        print("  提示: 请检查 DJANGO_API_USERNAME 和 DJANGO_API_PASSWORD 配置")
        await client.close()
        return False
    
    # 5. 测试 API 调用
    print("\n[5/5] 测试 API 调用...")
    
    # 5.1 测试关键词搜索
    print("\n  [5.1] 测试关键词搜索...")
    keywords_to_test = ["user", "login", "survey", "table"]
    for keyword in keywords_to_test:
        results = client.get_endpoints_by_keyword(keyword)
        print(f"    - 搜索 '{keyword}': 找到 {len(results)} 个端点")
    
    # 5.2 测试意图匹配
    print("\n  [5.2] 测试意图匹配...")
    intents_to_test = [
        "获取用户信息",
        "查询问卷列表",
        "获取当前登录用户",
    ]
    for intent in intents_to_test:
        endpoint = client.find_endpoint(intent)
        if endpoint:
            print(f"    - '{intent}' → {endpoint.method} {endpoint.path}")
        else:
            print(f"    - '{intent}' → 未找到匹配")
    
    # 5.3 测试实际 API 调用
    print("\n  [5.3] 测试实际 API 调用...")
    try:
        # 尝试调用获取当前用户信息的 API
        user_endpoint = client.find_endpoint("获取当前用户信息")
        if user_endpoint:
            print(f"    调用: {user_endpoint.method} {user_endpoint.path}")
            result = await client.call_api(user_endpoint)
            print(f"    ✓ 调用成功，响应类型: {type(result).__name__}")
            if isinstance(result, dict):
                # 只显示部分字段
                safe_fields = ['id', 'username', 'name', 'email']
                for field in safe_fields:
                    if field in result:
                        print(f"      - {field}: {result[field]}")
        else:
            # 备选：尝试其他 API
            print("    未找到用户信息 API，尝试其他 API...")
            # 查找一个简单的 GET API
            for op_id, endpoint in client._endpoints.items():
                if endpoint.method == "GET" and not endpoint.parameters:
                    print(f"    调用: {endpoint.method} {endpoint.path}")
                    try:
                        result = await client.call_api(endpoint)
                        print(f"    ✓ 调用成功，响应类型: {type(result).__name__}")
                        break
                    except Exception as e:
                        print(f"    ✗ 调用失败: {e}")
                        continue
    except Exception as e:
        print(f"    ✗ API 调用失败: {e}")
    
    # 关闭客户端
    await client.close()
    
    print("\n" + "=" * 60)
    print("✓ 集成测试完成")
    print("=" * 60)
    return True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_summary():
    """测试 AI 摘要生成"""
    # 默认跳过：需要真实 backend-django 服务运行
    if os.environ.get("RUN_DJANGO_API_INTEGRATION", "").strip() != "1":
        pytest.skip("需要设置 RUN_DJANGO_API_INTEGRATION=1 并启动 backend-django 才运行该集成测试")
    print("\n" + "=" * 60)
    print("AI 摘要生成测试")
    print("=" * 60)
    
    settings = Settings()
    config = settings.get_django_api_config()
    client = OpenAPIAwareClient(config)
    
    try:
        await client.load_openapi_schema()
        summary = client.get_api_summary_for_ai()
        
        print(f"\n生成的 AI 摘要（前 2000 字符）：")
        print("-" * 40)
        print(summary[:2000])
        if len(summary) > 2000:
            print(f"\n... (共 {len(summary)} 字符)")
        print("-" * 40)
        
    finally:
        await client.close()


if __name__ == "__main__":
    print("Django API 客户端集成测试")
    print("请确保 backend-django 服务正在运行")
    print()
    
    # 运行集成测试
    result = asyncio.run(test_integration())
    
    if result:
        # 可选：显示 AI 摘要
        print("\n是否显示 AI 摘要？（按 Ctrl+C 跳过）")
        try:
            import time
            time.sleep(1)
            asyncio.run(test_ai_summary())
        except KeyboardInterrupt:
            print("\n跳过 AI 摘要")
    
    sys.exit(0 if result else 1)
