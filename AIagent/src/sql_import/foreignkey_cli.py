# -*- coding: utf-8 -*-
"""
外键提取 CLI 命令
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List

from .foreignkey_extractor import ForeignKeyExtractor


def extract_foreignkey_single(args):
    """提取单个文件的外键信息"""
    sql_file = args.sql_file
    output_dir = args.output
    overwrite = args.overwrite
    enable_llm = args.enable_llm
    api_key = args.anthropic_api_key
    cache_dir = args.strategy_cache_dir
    
    if not os.path.exists(sql_file):
        print(f"错误：文件不存在 - {sql_file}")
        return 1
    
    print(f"开始提取外键信息: {sql_file}")
    
    # 创建提取器
    extractor = ForeignKeyExtractor(
        enable_llm=enable_llm,
        api_key=api_key,
        cache_dir=cache_dir
    )
    
    # 提取外键
    table_fks = extractor.extract_from_file(sql_file)
    
    # 保存到 JSON
    output_file = extractor.save_to_json(table_fks, output_dir, overwrite)
    
    # 输出结果
    print(f"\n提取完成:")
    print(f"  表名: {table_fks.table_name}")
    print(f"  外键数量: {len(table_fks.foreign_keys)}")
    print(f"  文件大小: {table_fks.file_size_mb:.2f} MB")
    print(f"  提取策略: {table_fks.extraction_strategy}")
    if table_fks.strategy_fingerprint:
        print(f"  格式指纹: {table_fks.strategy_fingerprint}")
    print(f"  保存路径: {output_file}")
    
    return 0


def extract_foreignkey_batch(args):
    """批量提取外键信息"""
    sql_dir = args.sql_dir
    output_dir = args.output
    mode = args.mode
    overwrite = args.overwrite
    verbose = args.verbose
    enable_llm = args.enable_llm
    api_key = args.anthropic_api_key
    cache_dir = args.strategy_cache_dir
    show_strategies = args.show_strategies
    
    if not os.path.exists(sql_dir):
        print(f"错误：目录不存在 - {sql_dir}")
        return 1
    
    # 获取所有 SQL 文件
    sql_files = list(Path(sql_dir).glob('*.sql'))
    
    if len(sql_files) == 0:
        print(f"错误：目录中没有 SQL 文件 - {sql_dir}")
        return 1
    
    print(f"找到 {len(sql_files)} 个 SQL 文件")
    if enable_llm:
        print(f"✓ LLM 辅助已启用")
    print(f"开始批量提取...\n")
    
    # 创建提取器
    extractor = ForeignKeyExtractor(
        enable_llm=enable_llm,
        api_key=api_key,
        cache_dir=cache_dir
    )
    
    # 统计信息
    total_files = len(sql_files)
    processed_files = 0
    tables_with_fks = 0
    total_fks = 0
    large_files_count = 0
    strategy_stats = {}
    llm_api_calls = 0
    
    # 批量提取
    for i, sql_file in enumerate(sql_files, 1):
        try:
            if verbose:
                print(f"[{i}/{total_files}] 处理: {sql_file.name}")
            
            # 提取外键
            table_fks = extractor.extract_from_file(str(sql_file))
            
            # 统计
            processed_files += 1
            if len(table_fks.foreign_keys) > 0:
                tables_with_fks += 1
                total_fks += len(table_fks.foreign_keys)
            
            if table_fks.file_size_mb > 1.0:
                large_files_count += 1
            
            # 策略统计
            strategy = table_fks.extraction_strategy
            strategy_stats[strategy] = strategy_stats.get(strategy, 0) + 1
            
            if strategy == 'llm_generated':
                llm_api_calls += 1
            
            # 保存
            if mode == 'per-table':
                extractor.save_to_json(table_fks, output_dir, overwrite)
            
            if verbose or show_strategies:
                print(f"  → 外键数量: {len(table_fks.foreign_keys)}, "
                      f"策略: {table_fks.extraction_strategy}")
        
        except Exception as e:
            print(f"错误：处理文件失败 - {sql_file.name}: {e}")
            continue
    
    # 输出统计报告
    print(f"\n{'='*60}")
    print(f"批量提取完成")
    print(f"{'='*60}")
    print(f"总文件数: {total_files}")
    print(f"处理成功: {processed_files}")
    print(f"有外键的表: {tables_with_fks}")
    print(f"无外键的表: {processed_files - tables_with_fks}")
    print(f"总外键数: {total_fks}")
    print(f"大文件数量 (>1MB): {large_files_count}")
    
    if show_strategies:
        print(f"\n策略使用统计:")
        for strategy, count in sorted(strategy_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {strategy}: {count} 个文件")
    
    if enable_llm:
        print(f"\nLLM 统计:")
        print(f"  API 调用次数: {llm_api_calls}")
        estimated_cost = llm_api_calls * 0.003  # 估算每次调用 ~$0.003
        print(f"  估算成本: ${estimated_cost:.2f} USD")
    
    print(f"\n输出目录: {output_dir}")
    
    return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SQL 外键信息提取工具'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 单文件提取命令
    parser_single = subparsers.add_parser(
        'extract-foreignkey',
        help='提取单个文件的外键信息'
    )
    parser_single.add_argument('sql_file', help='SQL 文件路径')
    parser_single.add_argument(
        '-o', '--output',
        default='docs/hospital/foreignkey',
        help='输出目录（默认: docs/hospital/foreignkey）'
    )
    parser_single.add_argument(
        '--overwrite',
        action='store_true',
        help='覆盖已存在的文件'
    )
    parser_single.add_argument(
        '--enable-llm',
        action='store_true',
        help='启用 LLM 辅助提取'
    )
    parser_single.add_argument(
        '--anthropic-api-key',
        help='Claude API 密钥（或设置环境变量 ANTHROPIC_API_KEY）'
    )
    parser_single.add_argument(
        '--strategy-cache-dir',
        default='docs/hospital/foreignkey/generated_strategies',
        help='策略缓存目录'
    )
    
    # 批量提取命令
    parser_batch = subparsers.add_parser(
        'extract-foreignkey-all',
        help='批量提取外键信息'
    )
    parser_batch.add_argument('sql_dir', help='SQL 文件目录')
    parser_batch.add_argument(
        '-o', '--output',
        default='docs/hospital/foreignkey',
        help='输出目录（默认: docs/hospital/foreignkey）'
    )
    parser_batch.add_argument(
        '--mode',
        choices=['per-table', 'unified'],
        default='per-table',
        help='存储模式（默认: per-table）'
    )
    parser_batch.add_argument(
        '--overwrite',
        action='store_true',
        help='覆盖已存在的文件'
    )
    parser_batch.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细进度'
    )
    parser_batch.add_argument(
        '--enable-llm',
        action='store_true',
        help='启用 LLM 辅助提取'
    )
    parser_batch.add_argument(
        '--anthropic-api-key',
        help='Claude API 密钥（或设置环境变量 ANTHROPIC_API_KEY）'
    )
    parser_batch.add_argument(
        '--strategy-cache-dir',
        default='docs/hospital/foreignkey/generated_strategies',
        help='策略缓存目录'
    )
    parser_batch.add_argument(
        '--show-strategies',
        action='store_true',
        help='显示每个文件使用的策略'
    )
    
    args = parser.parse_args()
    
    if args.command == 'extract-foreignkey':
        return extract_foreignkey_single(args)
    elif args.command == 'extract-foreignkey-all':
        return extract_foreignkey_batch(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
