# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI CLI

用法示例：
    python -m src.docx_openapi export /path/to/doc.docx -o openapi.json --report report.json
    python -m src.docx_openapi export doc.docx -o openapi.json --only PER_OUTP_0004 --title "Winex接口" --version "1.1"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from typing import Any, Dict

from .pipeline import export_openapi_from_docx, dump_openapi_json
from .report import dump_report_json
from .validator import validate_openapi_minimal
from ..logging.logger import get_logger


def _split_only(values: Optional[List[str]]) -> List[str]:
    if not values:
        return []
    out: List[str] = []
    for v in values:
        if not v:
            continue
        parts = [p.strip() for p in v.split(",") if p.strip()]
        out.extend(parts)
    return out


def cmd_export(args: argparse.Namespace) -> int:
    docx_path: str = args.docx
    out_path: str = args.output
    report_path: str = args.report
    title: str = args.title
    version: str = args.version
    only = _split_only(args.only)
    use_llm = bool(args.use_llm) and (not bool(args.no_llm))
    logger = get_logger(
        "docx_openapi",
        level=args.log_level,
        log_dir=Path(args.log_dir) if args.log_dir else None,
        log_format=args.log_format,
        enable_console=not args.no_console,
        enable_file=bool(args.log_dir),
    )
    log_config: Dict[str, Any] = {
        "level": args.log_level,
        "log_dir": Path(args.log_dir) if args.log_dir else None,
        "log_format": args.log_format,
        "enable_console": not args.no_console,
        "enable_file": bool(args.log_dir),
    }

    if not Path(docx_path).exists():
        logger.error("输入文件不存在", docx_path=docx_path)
        print(f"错误：文件不存在 - {docx_path}")
        return 1

    logger.info("开始导出 OpenAPI", docx_path=docx_path, out_path=out_path, report_path=report_path)
    openapi, report = export_openapi_from_docx(
        docx_path,
        title=title,
        version=version,
        only_operation_ids=only or None,
        log_config=log_config,
        use_llm=use_llm,
        llm_temperature=args.llm_temperature,
        llm_max_tokens=args.llm_max_tokens,
        llm_retries=args.llm_retries,
        llm_cache_dir=args.llm_cache_dir,
        llm_resume=not args.no_resume,
        llm_overwrite_cache=args.overwrite_cache,
    )
    logger.info(
        "解析完成",
        endpoint_count=report.get("summary", {}).get("endpointCount", 0),
        issue_count=report.get("summary", {}).get("issueCount", 0),
    )

    # 最小校验：如果失败，仍写出 report，openapi 默认不写（除非 --force）
    errors = validate_openapi_minimal(openapi)
    if errors and not args.force:
        logger.error("OpenAPI 最小校验失败", error_count=len(errors))
        print("❌ OpenAPI 最小校验失败：")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... 还有 {len(errors) - 20} 条")
        if report_path:
            dump_report_json(report, report_path)
            logger.info("已输出解析报告", report_path=report_path)
            print(f"已输出解析报告：{report_path}")
        print("提示：如需仍然输出 openapi.json，请加 --force")
        return 2

    dump_openapi_json(openapi, out_path)
    logger.info("已输出 OpenAPI", out_path=out_path)
    print(f"✓ 已输出 OpenAPI：{out_path}")

    if report_path:
        dump_report_json(report, report_path)
        logger.info("已输出解析报告", report_path=report_path)
        print(f"✓ 已输出解析报告：{report_path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="docx_openapi", description="将 .docx 接口文档解析为 OpenAPI 3.x JSON")
    sub = p.add_subparsers(dest="command")

    exp = sub.add_parser("export", help="导出 OpenAPI 3.x JSON")
    exp.add_argument("docx", help="输入 .docx 文件路径")
    exp.add_argument("-o", "--output", required=True, help="输出 openapi.json 路径")
    exp.add_argument("--report", default="", help="输出 report.json 路径（可选）")
    exp.add_argument("--title", default="DOCX API", help="OpenAPI info.title")
    exp.add_argument("--version", default="0.0.0", help="OpenAPI info.version")
    exp.add_argument(
        "--only",
        action="append",
        default=[],
        help="仅导出指定 operationId（可多次传入或用英文逗号分隔）",
    )
    exp.add_argument("--force", action="store_true", help="即使最小校验失败也输出 openapi.json")
    exp.add_argument("--use-llm", action="store_true", default=True, help="使用 LLM 进行解析（默认开启，严格输出并校验）")
    exp.add_argument("--no-llm", action="store_true", help="禁用 LLM（仅使用确定性解析，作为兜底）")
    exp.add_argument("--llm-temperature", type=float, default=0.0, help="LLM 温度（默认 0，降低幻觉）")
    exp.add_argument("--llm-max-tokens", type=int, default=2048, help="LLM max_tokens")
    exp.add_argument("--llm-retries", type=int, default=2, help="LLM 解析失败重试次数")
    exp.add_argument("--llm-cache-dir", default=".docx_openapi_cache", help="LLM 解析缓存目录（断点续跑）")
    exp.add_argument("--no-resume", action="store_true", help="禁用断点续跑（每次都重新调用 LLM）")
    exp.add_argument("--overwrite-cache", action="store_true", help="覆盖缓存（忽略已有缓存结果）")
    exp.add_argument("--log-level", default="INFO", help="日志级别（DEBUG/INFO/WARNING/ERROR）")
    exp.add_argument("--log-format", default="json", choices=["json", "text"], help="日志格式")
    exp.add_argument("--log-dir", default="", help="日志目录（设置后会输出文件日志）")
    exp.add_argument("--no-console", action="store_true", help="禁用控制台日志输出")
    exp.set_defaults(func=cmd_export)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        raise SystemExit(1)
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()

