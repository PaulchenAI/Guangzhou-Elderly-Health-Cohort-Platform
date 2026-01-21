# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI 导出管道

单入口函数：export_openapi_from_docx
用于 CLI / Agent 复用。
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple

from .extractor import extract_blocks_from_docx
from .openapi_builder import build_openapi
from .parser import parse_doc_blocks_to_spec, parse_doc_blocks_to_spec_async
from .report import build_report
from .validator import validate_openapi_minimal
from ..logging.logger import get_logger


async def export_openapi_from_docx_async(
    docx_path: str,
    *,
    title: str = "DOCX API",
    version: str = "0.0.0",
    only_operation_ids: Optional[List[str]] = None,
    use_llm: bool = False,
    llm_temperature: float = 0.0,
    llm_max_tokens: int = 2048,
    llm_retries: int = 2,
    llm_cache_dir: str = "",
    llm_resume: bool = True,
    llm_overwrite_cache: bool = False,
    log_config: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    异步版本：支持 LLM 解析（推荐在 agent/服务端场景使用）。
    """
    logger = get_logger("docx_openapi.pipeline", **(log_config or {}))
    logger.info("读取 DOCX 并抽取块流", docx_path=docx_path)
    blocks = extract_blocks_from_docx(docx_path)
    logger.info("抽取完成", block_count=len(blocks))

    if use_llm:
        spec = await parse_doc_blocks_to_spec_async(
            blocks,
            title=title,
            version=version,
            only_operation_ids=only_operation_ids,
            log_config=log_config,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
            llm_retries=llm_retries,
            llm_cache_dir=llm_cache_dir,
            llm_resume=llm_resume,
            llm_overwrite_cache=llm_overwrite_cache,
        )
    else:
        spec = parse_doc_blocks_to_spec(
            blocks,
            title=title,
            version=version,
            only_operation_ids=only_operation_ids,
            log_config=log_config,
        )

    logger.info("解析完成", endpoint_count=len(spec.endpoints), issue_count=len(spec.issues), use_llm=use_llm)
    openapi = build_openapi(spec)
    errors = validate_openapi_minimal(openapi)
    if errors:
        logger.warning("OpenAPI 最小校验失败", error_count=len(errors))
    report = build_report(spec, openapi_errors=errors)
    return openapi, report


def export_openapi_from_docx(
    docx_path: str,
    *,
    title: str = "DOCX API",
    version: str = "0.0.0",
    only_operation_ids: Optional[List[str]] = None,
    log_config: Optional[Dict[str, Any]] = None,
    use_llm: bool = False,
    llm_temperature: float = 0.0,
    llm_max_tokens: int = 2048,
    llm_retries: int = 2,
    llm_cache_dir: str = "",
    llm_resume: bool = True,
    llm_overwrite_cache: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    从 docx 生成 OpenAPI JSON 与 report。

    Returns:
        (openapi_dict, report_dict)
    """
    # 同步包装：若调用方已在事件循环内，应改用 export_openapi_from_docx_async
    try:
        asyncio.get_running_loop()
        raise RuntimeError("当前已存在事件循环，请使用 export_openapi_from_docx_async 以启用 LLM 解析")
    except RuntimeError as e:
        # 没有事件循环时，get_running_loop 会抛 RuntimeError（这是正常路径）
        if "no running event loop" not in str(e).lower() and "事件循环" in str(e):
            raise

    return asyncio.run(
        export_openapi_from_docx_async(
            docx_path,
            title=title,
            version=version,
            only_operation_ids=only_operation_ids,
            use_llm=use_llm,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
            llm_retries=llm_retries,
            llm_cache_dir=llm_cache_dir,
            llm_resume=llm_resume,
            llm_overwrite_cache=llm_overwrite_cache,
            log_config=log_config,
        )
    )


def dump_openapi_json(openapi: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(openapi, f, ensure_ascii=False, indent=2)

