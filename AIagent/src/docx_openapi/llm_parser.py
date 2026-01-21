# -*- coding: utf-8 -*-
"""
LLM 解析器：把单个接口的大表格交给 LLM 结构化解析

特点：
- 提供完整上下文（表格原文 + 关键提示）
- 只允许输出 JSON
- Pydantic 校验失败会重试（温度低，降低幻觉）
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from ..llm.factory import LLMFactory
from ..utils.config_models import Settings
from ..logging.logger import get_logger
from .llm_models import LLMEndpoint
from .cache import CacheKey, EndpointCache, compute_text_hash, _safe_name


def _render_table_as_text(rows: List[List[str]], *, max_lines: int = 250) -> str:
    lines: List[str] = []
    for r in rows[:max_lines]:
        cols = [c.strip() for c in r if c and c.strip()]
        if not cols:
            continue
        lines.append(" | ".join(cols))
    if len(rows) > max_lines:
        lines.append(f"...（表格过长，已截断，共 {len(rows)} 行）")
    return "\n".join(lines)


def _extract_json_block(text: str) -> str:
    """
    从 LLM 输出中提取 JSON 块（对象）。
    """
    if not text:
        return ""
    # 尽量抓最外层 {...}
    start = text.find("{")
    if start == -1:
        return ""
    cand = text[start:]
    stack = []
    end = None
    for i, ch in enumerate(cand):
        if ch == "{":
            stack.append(ch)
        elif ch == "}":
            if not stack:
                break
            stack.pop()
            if not stack:
                end = i + 1
                break
    if end is None:
        return ""
    return cand[:end]


def _build_system_prompt() -> str:
    return (
        "你是一个严格的接口文档解析器。你的任务：把给定的接口表格内容解析为结构化 JSON。\n"
        "强约束：\n"
        "- 只输出 JSON（不要 Markdown、不要解释、不要多余文本）。\n"
        "- 不要编造文档中不存在的字段/示例/路径。\n"
        "- method 必须是 GET/POST/PUT/DELETE/PATCH 之一（大写）。\n"
        "- path 必须只包含“路径部分”，必须以 / 开头（例如 /dcp-inex-invoke/api/v1/... 或 /cli/getPatientInfoLi）。\n"
        "  如果文档给的是完整 URL（例如 http://ip:port/... 或 //ip:port/... 或包含 ?query），你必须：\n"
        "  1) 去掉 scheme/host（http://ip:port），只保留 / 后的路径；\n"
        "  2) 去掉查询参数（?ak=...）；\n"
        "- request_fields/response_fields 必须来自文档中的输入参数/输出参数表。\n"
        "- 示例报文/请求示例/响应示例：尽量解析为 JSON；解析不了就原样输出字符串。\n"
    )


def _build_user_prompt(table_text: str) -> str:
    schema_hint = {
        "operation_id": "PER_BASE_0001",
        "name": "患者信息接口",
        "method": "GET",
        "path": "/cli/getPatientInfoLi",
        "description": "（可选）",
        "request_fields": [{"name": "startTime", "raw_type": "Date", "required": False, "description": "记录变更开始时间"}],
        "response_fields": [{"name": "id", "raw_type": "String", "required": False, "description": "记录唯一主键"}],
        "request_example": {"payload": {"startTime": "2023-05-01 00:00:00"}},
        "response_example": None,
    }
    return (
        "以下为单个接口的表格内容（按行展开，列之间用 `|` 分隔）：\n"
        "-----\n"
        f"{table_text}\n"
        "-----\n\n"
        "请按照以下 JSON 结构输出（字段名必须完全一致）：\n"
        f"{json.dumps(schema_hint, ensure_ascii=False, indent=2)}\n"
    )


async def llm_parse_endpoint_from_table(
    rows: List[List[str]],
    *,
    cache_dir: Optional[str] = None,
    resume: bool = True,
    overwrite_cache: bool = False,
    cache_key: Optional[CacheKey] = None,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    retries: int = 2,
    log_config: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[LLMEndpoint], Optional[str]]:
    """
    返回 (endpoint, error_message)。成功时 error_message 为 None。
    """
    logger = get_logger("docx_openapi.llm_parser", **(log_config or {}))

    table_text = _render_table_as_text(rows)
    table_hash = compute_text_hash(table_text)
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(table_text)

    cache: Optional[EndpointCache] = EndpointCache(cache_dir) if cache_dir else None
    if cache and resume and cache_key and not overwrite_cache:
        cached = cache.read(cache_key)
        if cached and cached.get("table_hash") == table_hash and cached.get("endpoint"):
            try:
                endpoint = LLMEndpoint.model_validate(cached["endpoint"])
                endpoint.method = endpoint.method.upper()
                logger.info(
                    "命中缓存，跳过 LLM 调用",
                    operation_id=endpoint.operation_id,
                    block_index=cache_key.block_index,
                )
                return endpoint, None
            except Exception:
                # 缓存损坏或模型不匹配，继续走 LLM
                logger.warning("缓存解析失败，回退到 LLM", block_index=cache_key.block_index)

    try:
        settings = Settings()
        llm_config = settings.get_llm_config()
    except Exception as e:
        return None, f"LLM 配置加载失败：{e}"

    # 强制低温，降低幻觉（用户要求）
    llm_config.temperature = temperature
    client = LLMFactory.create_llm(llm_config)

    last_error = ""
    for attempt in range(retries + 1):
        logger.info("LLM 解析接口表格", attempt=attempt, temperature=temperature, max_tokens=max_tokens)
        raw = await client.invoke_prompt(
            user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        json_block = _extract_json_block(raw)
        if not json_block:
            last_error = f"未提取到 JSON：raw={raw[:2000]}"
            logger.warning("LLM 输出不包含可解析 JSON", attempt=attempt)
            continue
        try:
            data = json.loads(json_block)
        except Exception as e:
            last_error = f"JSON 解析失败：{e}；raw_json={json_block[:2000]}"
            logger.warning("LLM JSON 解析失败", attempt=attempt, error=str(e))
            continue

        try:
            endpoint = LLMEndpoint.model_validate(data)
        except Exception as e:
            last_error = f"Pydantic 校验失败：{e}"
            logger.warning("LLM 输出结构校验失败", attempt=attempt, error=str(e))
            continue

        # 最关键字段再做一次硬校验，避免空值
        if not endpoint.method or endpoint.method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
            last_error = f"method 非法：{endpoint.method}"
            logger.warning("LLM 输出 method 非法", attempt=attempt, method=endpoint.method)
            continue
        if not endpoint.path:
            last_error = "path 为空"
            logger.warning("LLM 输出 path 为空", attempt=attempt)
            continue

        # 统一大写 method
        endpoint.method = endpoint.method.upper()

        # 写缓存（成功才落盘）
        if cache and cache_key:
            cache.write(
                cache_key,
                {
                    "table_hash": table_hash,
                    "endpoint": endpoint.model_dump(),
                    "meta": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                },
            )
        return endpoint, None

    return None, last_error

