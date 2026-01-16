#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 LLM 集成功能
"""

import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from AIagent.src.sql_import.foreignkey_llm_helper import LLMHelper
from AIagent.src.sql_import.foreignkey_strategy_cache import StrategyCache


def test_llm_helper():
    """测试 LLM 助手"""
    print("=" * 60)
    print("测试 LLM 助手功能")
    print("=" * 60)
    
    # 1. 检查 API 密钥
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("错误：未设置 ANTHROPIC_API_KEY 环境变量")
        print("\n要测试 LLM 功能，请先设置 API 密钥：")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        return False
    
    # 2. 初始化 LLM 助手
    helper = LLMHelper(api_key)
    
    if not helper.is_available():
        print("错误：LLM 不可用")
        return False
    
    print("✓ LLM 助手初始化成功\n")
    
    # 3. 读取测试文件
    test_file = project_root / 'docs/hospital/sql/TEST_NON_STANDARD_FK.sql'
    
    if not test_file.exists():
        print(f"错误：测试文件不存在 - {test_file}")
        return False
    
    with open(test_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    print(f"读取测试文件: {test_file.name}")
    print(f"文件大小: {len(sql_content)} 字节\n")
    
    # 4. 提取外键语句块
    print("步骤 1: 提取外键语句块...")
    fk_statements = helper.extract_fk_statement_blocks(sql_content)
    
    print(f"✓ 找到 {len(fk_statements)} 个外键语句块")
    for i, stmt in enumerate(fk_statements, 1):
        print(f"\n  语句 {i}:")
        print(f"  {stmt[:100]}..." if len(stmt) > 100 else f"  {stmt}")
    
    # 5. 估算 Token 数量
    print(f"\n步骤 2: 估算 Token 数量...")
    total_tokens = sum(helper.estimate_tokens(stmt) for stmt in fk_statements)
    print(f"✓ 估算总 Token 数: {total_tokens}")
    
    # 6. 生成提取脚本
    print(f"\n步骤 3: 生成提取脚本（调用 Claude API）...")
    script_code = helper.generate_with_retry(
        fk_statements,
        format_fingerprint='test_001',
        max_retries=2,
        is_large_file=False
    )
    
    if not script_code:
        print("✗ 脚本生成失败")
        return False
    
    print(f"✓ 脚本生成成功！")
    print(f"\n生成的代码片段:")
    print("-" * 60)
    lines = script_code.split('\n')
    print('\n'.join(lines[:20]))
    if len(lines) > 20:
        print(f"... ({len(lines) - 20} 行省略)")
    print("-" * 60)
    
    # 7. 测试执行脚本
    print(f"\n步骤 4: 执行生成的脚本...")
    try:
        namespace = {}
        exec(script_code, namespace)
        extract_fn = namespace.get('extract_foreignkeys')
        
        if not extract_fn:
            print("✗ 未找到 extract_foreignkeys 函数")
            return False
        
        # 执行提取
        result = extract_fn(sql_content)
        
        print(f"✓ 提取成功！")
        print(f"\n提取结果:")
        print(f"  外键数量: {len(result)}")
        
        for i, fk in enumerate(result, 1):
            print(f"\n  外键 {i}:")
            print(f"    约束名: {fk.get('constraint_name')}")
            print(f"    源表: {fk.get('source_table')}")
            print(f"    源字段: {', '.join(fk.get('source_columns', []))}")
            print(f"    目标表: {fk.get('target_table')}")
            print(f"    目标字段: {', '.join(fk.get('target_columns', []))}")
            print(f"    删除规则: {fk.get('on_delete', 'N/A')}")
    
    except Exception as e:
        print(f"✗ 执行失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ LLM 集成测试通过！")
    print("=" * 60)
    
    return True


def test_strategy_cache():
    """测试策略缓存"""
    print("\n" + "=" * 60)
    print("测试策略缓存功能")
    print("=" * 60)
    
    # 创建缓存管理器
    cache_dir = project_root / 'docs/hospital/foreignkey/generated_strategies'
    cache = StrategyCache(str(cache_dir))
    
    print(f"缓存目录: {cache_dir}")
    
    # 获取统计信息
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  策略数量: {stats['total_strategies']}")
    print(f"  总使用次数: {stats['total_usage_count']}")
    
    # 列出所有策略
    if stats['total_strategies'] > 0:
        print(f"\n已缓存的策略:")
        strategies = cache.list_all_strategies()
        for strategy in strategies:
            print(f"\n  指纹: {strategy['fingerprint']}")
            print(f"  描述: {strategy.get('format_description', 'N/A')}")
            print(f"  成功次数: {strategy.get('success_count', 0)}")
            print(f"  创建时间: {strategy.get('created_at', 'N/A')}")
    
    print("\n✓ 策略缓存测试完成")
    
    return True


if __name__ == '__main__':
    print("\nLLM 集成功能测试套件\n")
    
    # 测试 LLM 助手
    llm_ok = test_llm_helper()
    
    # 测试策略缓存
    cache_ok = test_strategy_cache()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"LLM 助手: {'✓ 通过' if llm_ok else '✗ 失败'}")
    print(f"策略缓存: {'✓ 通过' if cache_ok else '✗ 失败'}")
    print("=" * 60)
    
    sys.exit(0 if (llm_ok and cache_ok) else 1)
