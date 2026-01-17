# -*- coding: utf-8 -*-
"""
SQL 含义推断 CLI（简化版）
直接把 SQL 发给 LLM 处理
"""

import asyncio
import argparse
from pathlib import Path

from .sql_meaning_llm import SQLMeaningInferencer


async def infer_file(args):
    """推断单个文件"""
    inferencer = SQLMeaningInferencer(
        ignore_prefix=args.ignore_prefix,
        prompt_template=_load_template(args.prompt_template) if args.prompt_template else None
    )
    
    result = await inferencer.infer_file(args.file, args.output)
    print(f"结果已保存到: {result['metadata'].get('output_path', args.output or 'docs/hospital/commentsql/')}")


async def infer_dir(args):
    """批量推断目录"""
    inferencer = SQLMeaningInferencer(
        ignore_prefix=args.ignore_prefix,
        prompt_template=_load_template(args.prompt_template) if args.prompt_template else None,
        skip_existing=args.skip_existing,
        concurrency=args.concurrency
    )
    
    results = await inferencer.infer_directory(
        args.directory, 
        args.output,
        retry_failed=args.retry_failed
    )
    print(f"批量处理完成，共 {len(results)} 个文件")


async def clear_errors(args):
    """清除错误日志"""
    inferencer = SQLMeaningInferencer()
    success = inferencer.clear_error_log(args.output)
    if success:
        print("错误日志已清除")
    else:
        print("没有错误日志需要清除")


def _load_template(template_file: str) -> str:
    """加载自定义模板"""
    path = Path(template_file)
    if not path.exists():
        print(f"警告：模板文件不存在: {template_file}，使用默认模板")
        return None
    return path.read_text(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description="SQL 含义推断工具（简化版 - 直接使用 LLM）"
    )
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 单文件推断
    parser_file = subparsers.add_parser('infer-file', help='推断单个 SQL 文件')
    parser_file.add_argument('file', help='SQL 文件路径')
    parser_file.add_argument('-o', '--output', help='输出文件路径（默认: docs/hospital/commentsql/表名_meaning.json）')
    parser_file.add_argument(
        '--ignore-prefix',
        default='gzlry_',
        help='要忽略的表名前缀（默认: gzlry_）'
    )
    parser_file.add_argument(
        '--prompt-template',
        help='自定义提示词模板文件路径'
    )
    
    # 批量推断
    parser_dir = subparsers.add_parser('infer-dir', help='批量推断目录中的 SQL 文件')
    parser_dir.add_argument('directory', help='SQL 文件目录')
    parser_dir.add_argument('-o', '--output', help='输出目录（默认: docs/hospital/commentsql）')
    parser_dir.add_argument(
        '--ignore-prefix',
        default='gzlry_',
        help='要忽略的表名前缀（默认: gzlry_）'
    )
    parser_dir.add_argument(
        '--prompt-template',
        help='自定义提示词模板文件路径'
    )
    parser_dir.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已存在结果的文件'
    )
    parser_dir.add_argument(
        '--retry-failed',
        action='store_true',
        help='只重试之前失败的任务（从错误日志读取）'
    )
    parser_dir.add_argument(
        '-c', '--concurrency',
        type=int,
        default=1,
        help='并发处理数量（默认: 1，即顺序处理）'
    )
    
    # 清除错误日志
    parser_clear = subparsers.add_parser('clear-errors', help='清除错误日志')
    parser_clear.add_argument('-o', '--output', help='输出目录（默认: docs/hospital/commentsql）')
    
    args = parser.parse_args()
    
    if args.command == 'infer-file':
        asyncio.run(infer_file(args))
    elif args.command == 'infer-dir':
        asyncio.run(infer_dir(args))
    elif args.command == 'clear-errors':
        asyncio.run(clear_errors(args))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
