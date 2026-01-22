# -*- coding: utf-8 -*-
"""
DOCX 块流解析器

实现一个尽量稳健的“弱假设”解析：
- 通过 KV 表格识别接口基本信息（接口名称、method、path 等）
- 通过列式表格识别入参/出参字段列表
- 通过段落区块识别请求/响应示例（JSON 优先，否则保留 raw）

本实现尽量做到：
- 能在格式不完全一致时仍输出“部分可用”的 OpenAPI
- 关键字段缺失时，给出 issues 以便人工修正文档
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
import asyncio
from urllib.parse import urlsplit

from .extractor import DocBlock, ParagraphBlock, TableBlock
from .models import (
    DocumentSpec,
    EndpointSpec,
    ExampleSpec,
    FieldSpec,
    IssueLevel,
    ParseIssue,
)
from ..logging.logger import get_logger
from .llm_parser import llm_parse_endpoint_from_table
from .cache import CacheKey


_METHODS_ORDERED = ["GET", "POST", "PUT", "DELETE", "PATCH"]
_METHODS_SET = set(_METHODS_ORDERED)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip()


def _find_code(text: str) -> str:
    # 常见接口编号：PER_OUTP_0004 这类
    m = re.search(r"\b[A-Z]{2,}_[A-Z]{2,}_[0-9]{3,}\b", text or "")
    return m.group(0) if m else ""


def _guess_method(s: str) -> str:
    up = (s or "").upper()
    # 使用稳定顺序，避免 set 遍历顺序导致误判
    for m in _METHODS_ORDERED:
        if re.search(rf"\b{m}\b", up):
            return m
    return ""


def _guess_path(s: str) -> str:
    # 常见：/api/xxx 或 /xxx/{id}
    m = re.search(r"(/[^\\s，。,；;]+)", s or "")
    if m:
        return m.group(1).strip().rstrip("。.,;；")
    return ""


def _is_yes(v: str) -> bool:
    t = (v or "").strip()
    return t in {"Y", "y", "是", "必填", "必输", "1", "true", "True", "TRUE", "√", "✓"}


def _extract_json_candidate(text: str) -> Tuple[Optional[Any], str]:
    """
    尝试从文本中提取 JSON（对象或数组）。
    成功返回 (value, raw_json_string)，失败返回 (None, "")。
    """
    if not text:
        return None, ""

    # 先找一个可能的 JSON 起始位置
    start_obj = text.find("{")
    start_arr = text.find("[")
    if start_obj == -1 and start_arr == -1:
        return None, ""
    start = min([i for i in [start_obj, start_arr] if i != -1])
    cand = text[start:].strip()

    # 简单做“括号配对”截断（不追求完美，优先稳定）
    stack = []
    end = None
    for i, ch in enumerate(cand):
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if not stack:
                break
            top = stack.pop()
            if (top == "{" and ch != "}") or (top == "[" and ch != "]"):
                # 配对异常，停止
                break
            if not stack:
                end = i + 1
                break
    if end is None:
        return None, ""
    raw = cand[:end]

    try:
        return json.loads(raw), raw
    except Exception:
        return None, raw


def _table_to_kv(rows: List[List[str]]) -> Dict[str, str]:
    """
    将“标签-值”式表格解析为 dict。
    仅处理每行至少 2 列的情况：第一列作为 key，第二列作为 value（剩余列拼接）。
    """
    kv: Dict[str, str] = {}
    for r in rows:
        if len(r) < 2:
            continue
        k = (r[0] or "").strip()
        v = " ".join([c.strip() for c in r[1:] if c and c.strip()]).strip()
        if k and v:
            kv[k] = v
    return kv


def _looks_like_endpoint_kv(kv: Dict[str, str]) -> bool:
    keys = "".join(kv.keys())
    return ("接口名称" in keys) or ("请求方式" in keys) or ("请求路径" in keys) or ("path" in keys.lower() and "method" in keys.lower())


def _detect_section(text: str) -> str:
    t = text.strip()
    if not t:
        return ""
    # 常见段落标题
    if "入参" == t or t.startswith("入参"):
        return "in"
    if "出参" == t or t.startswith("出参"):
        return "out"
    if "请求示例" in t or t.startswith("请求示例"):
        return "req_example"
    if "响应示例" in t or t.startswith("响应示例"):
        return "resp_example"
    if "示例" == t:
        return "example"
    return ""


def _detect_param_table_kind(rows: List[List[str]]) -> str:
    """
    识别表格属于入参还是出参。
    返回 "in" / "out" / ""。
    """
    flat = " ".join([" ".join(r) for r in rows if r])
    if "入参" in flat and "出参" not in flat:
        return "in"
    if "出参" in flat and "入参" not in flat:
        return "out"
    return ""


def _parse_param_table(rows: List[List[str]]) -> List[FieldSpec]:
    """
    将列式参数表解析为字段列表。

    兼容不同列名：
    - name: 参数名/字段名/名称
    - type: 类型/数据类型
    - required: 必填/是否必填/必输
    - desc: 说明/描述/含义
    """
    if not rows:
        return []

    # 查找表头行：在前 3 行中寻找包含“参数/字段/类型/说明”等关键词的一行
    header_idx = 0
    header_row: List[str] = rows[0]
    for i in range(min(3, len(rows))):
        joined = " ".join(rows[i])
        if any(k in joined for k in ["参数", "字段", "类型", "说明", "描述", "必填", "必输"]):
            header_idx = i
            header_row = rows[i]
            break

    norm_headers = [_normalize(h) for h in header_row]

    def find_col(candidates: Sequence[str]) -> int:
        for c in candidates:
            c_norm = _normalize(c)
            for idx, h in enumerate(norm_headers):
                if c_norm and c_norm in h:
                    return idx
        return -1

    name_i = find_col(["参数名", "字段名", "名称", "参数", "字段"])
    type_i = find_col(["类型", "数据类型"])
    req_i = find_col(["必填", "是否必填", "必输", "required"])
    desc_i = find_col(["说明", "描述", "含义", "备注"])

    fields: List[FieldSpec] = []
    for r in rows[header_idx + 1 :]:
        if not any((c or "").strip() for c in r):
            continue
        name = (r[name_i] if 0 <= name_i < len(r) else "").strip()
        if not name or name in {"-", "—"}:
            continue
        raw_type = (r[type_i] if 0 <= type_i < len(r) else "").strip()
        required = _is_yes((r[req_i] if 0 <= req_i < len(r) else "").strip())
        desc = (r[desc_i] if 0 <= desc_i < len(r) else "").strip()
        fields.append(FieldSpec(name=name, raw_type=raw_type, required=required, description=desc))

    return fields


def _extract_fields_and_examples_from_combined_table(rows: List[List[str]]) -> tuple[List[FieldSpec], List[FieldSpec], List[ExampleSpec], List[ExampleSpec]]:
    """
    处理“单个大表格内包含接口信息 + 输入参数 + 输出参数 + 示例报文”的常见格式。

    典型结构（示例）：
    - ...（若干行接口信息）
    - 参数编码 | 参数说明 | 参数类型 | 非空 | 备注
    - 输入参数
    - <多行输入参数>
    - 示例报文：{ ... }
    - 输出参数
    - <多行输出参数>
    """
    request_fields: List[FieldSpec] = []
    response_fields: List[FieldSpec] = []
    request_examples: List[ExampleSpec] = []
    response_examples: List[ExampleSpec] = []

    section: str = ""  # in/out/req_example/resp_example
    in_header_seen = False
    example_buf: List[str] = []

    def flush_example(kind: str) -> None:
        nonlocal example_buf
        if not example_buf:
            return
        text = "\n".join(example_buf).strip()
        value, raw = _extract_json_candidate(text)
        ex = ExampleSpec(kind="request" if kind == "req_example" else "response", value=value, raw=raw or text)
        if ex.kind == "request":
            request_examples.append(ex)
        else:
            response_examples.append(ex)
        example_buf = []

    for r in rows:
        joined = " ".join([c for c in r if c]).strip()
        if not joined:
            continue

        # 分段标记
        if any(k in joined for k in ["输入参数", "入参"]):
            flush_example(section) if section in {"req_example", "resp_example"} else None
            section = "in"
            continue
        if any(k in joined for k in ["输出参数", "出参"]):
            flush_example(section) if section in {"req_example", "resp_example"} else None
            section = "out"
            continue
        if "请求示例" in joined or "示例报文" in joined or joined.startswith("示例"):
            # 大多数文档的示例报文是请求示例（payload），先按 request 处理
            flush_example(section) if section in {"req_example", "resp_example"} else None
            section = "req_example"
            # 如果当前行本身包含 JSON 片段，也要收集
            example_buf.append(joined)
            continue
        if "响应示例" in joined:
            flush_example(section) if section in {"req_example", "resp_example"} else None
            section = "resp_example"
            example_buf.append(joined)
            continue

        # 示例内容收集（可能跨多行）
        if section in {"req_example", "resp_example"}:
            example_buf.append(joined)
            continue

        # 参数表头识别（同一张表里常见）
        if any(h in joined for h in ["参数编码", "参数名", "字段名"]) and ("类型" in joined or "参数类型" in joined):
            in_header_seen = True
            continue

        # 参数行：通常至少包含 name/type 两列
        if in_header_seen and section in {"in", "out"}:
            # 兼容列布局：name | desc | type | required | remark
            name = (r[0] or "").strip() if len(r) > 0 else ""
            desc = (r[1] or "").strip() if len(r) > 1 else ""
            raw_type = (r[2] or "").strip() if len(r) > 2 else ""
            required = _is_yes((r[3] or "").strip()) if len(r) > 3 else False
            # 跳过明显的非字段行
            if not name or name in {"-", "—"}:
                continue
            if any(x in name for x in ["参数编码", "输入参数", "输出参数"]):
                continue
            f = FieldSpec(name=name, raw_type=raw_type, required=required, description=desc)
            if section == "in":
                request_fields.append(f)
            else:
                response_fields.append(f)
            continue

    if section in {"req_example", "resp_example"}:
        flush_example(section)

    return request_fields, response_fields, request_examples, response_examples


def parse_doc_blocks_to_spec(
    blocks: List[DocBlock],
    *,
    title: str = "DOCX API",
    version: str = "0.0.0",
    only_operation_ids: Optional[List[str]] = None,
    log_config: Optional[Dict[str, Any]] = None,
) -> DocumentSpec:
    """
    将 docx block 流解析为 DocumentSpec。

    Args:
        blocks: extractor 输出的顺序块
        title/version: OpenAPI info 信息来源（可由 CLI 覆盖）
        only_operation_ids: 仅导出指定 operationId（可选）
    """
    logger = get_logger("docx_openapi.parser", **(log_config or {}))
    spec = DocumentSpec(title=title, version=version)
    only_set = set([o for o in (only_operation_ids or []) if o])

    current: Optional[EndpointSpec] = None
    current_section: str = ""  # in/out/req_example/resp_example/...
    example_buffer: List[str] = []

    def flush_examples(kind: str):
        nonlocal example_buffer, current
        if not current or not example_buffer:
            example_buffer = []
            return
        text = "\n".join(example_buffer).strip()
        value, raw = _extract_json_candidate(text)
        ex = ExampleSpec(kind="request" if kind == "req_example" else "response", value=value, raw=raw or text)
        if ex.kind == "request":
            current.request_examples.append(ex)
        else:
            current.response_examples.append(ex)
        example_buffer = []

    for b in blocks:
        # 碰到新的接口 KV 表格/标题时，需要 flush 示例缓冲
        if isinstance(b, ParagraphBlock):
            sec = _detect_section(b.text)
            if sec:
                # 切换 section 前先 flush
                if current_section in {"req_example", "resp_example"} and sec != current_section:
                    flush_examples(current_section)
                current_section = sec
                continue

            # 在示例区块内累积
            if current and current_section in {"req_example", "resp_example"}:
                # 一些文档会在示例中混入“说明：”等文字，这里先照收，后续 JSON 提取会截取子串
                example_buffer.append(b.text)
                continue

            # 不在示例段落时，尝试捕获接口编号/名称（弱启发式）
            if "接口名称" in b.text and current:
                # 常见：段落里出现“接口名称：xxx”
                m = re.search(r"接口名称[:：]\\s*(.+)$", b.text)
                if m:
                    current.name = m.group(1).strip() or current.name
            continue

        # 表格处理
        tbl = b
        kv = _table_to_kv(tbl.rows)
        if kv and _looks_like_endpoint_kv(kv):
            # 新接口开始：flush 旧接口的示例缓冲
            if current_section in {"req_example", "resp_example"}:
                flush_examples(current_section)
                current_section = ""

            name = kv.get("接口名称") or kv.get("接口名") or kv.get("接口") or ""
            # method/path 可能在不同 key 下
            raw_method = kv.get("method") or kv.get("请求方式") or kv.get("请求方法") or kv.get("HTTP方法") or ""
            raw_method = raw_method or kv.get("接口实现方式") or ""
            raw_path = kv.get("path") or kv.get("请求路径") or kv.get("请求地址") or kv.get("URL") or kv.get("接口地址") or ""
            method = _guess_method(raw_method) or _guess_method(raw_path) or _guess_method(" ".join(kv.values()))
            path = _guess_path(raw_path) or _guess_path(" ".join(kv.values()))

            # operationId：优先接口编号，其次从 method+path 派生（生成阶段再做去重）
            op_id = _find_code(name) or _find_code(" ".join(kv.values()))

            endpoint = EndpointSpec(
                name=name or op_id or "(未命名接口)",
                method=method or "GET",
                path=path or "/",
                operation_id=op_id,
                summary=name or op_id,
                description=kv.get("接口描述") or kv.get("接口说明") or kv.get("说明") or "",
                source_location=tbl.location,
            )

            # 尝试从同一张大表格里抽取入参/出参/示例
            req_fields, resp_fields, req_exs, resp_exs = _extract_fields_and_examples_from_combined_table(tbl.rows)
            if req_fields:
                endpoint.request_fields.extend(req_fields)
            if resp_fields:
                endpoint.response_fields.extend(resp_fields)
            if req_exs:
                endpoint.request_examples.extend(req_exs)
            if resp_exs:
                endpoint.response_examples.extend(resp_exs)
            logger.debug(
                "解析接口表格",
                operation_id=endpoint.operation_id,
                endpoint_name=endpoint.name,
                endpoint_method=endpoint.method,
                endpoint_path=endpoint.path,
                request_fields=len(endpoint.request_fields),
                response_fields=len(endpoint.response_fields),
                request_examples=len(endpoint.request_examples),
                response_examples=len(endpoint.response_examples),
                block_index=tbl.location.block_index,
            )

            # only 过滤：如果 only_set 非空，且当前接口无法匹配，先创建但不加入（便于 report）
            if only_set and endpoint.operation_id and endpoint.operation_id not in only_set:
                current = endpoint
                continue

            spec.endpoints.append(endpoint)
            current = endpoint
            continue

        # 参数表：需要依赖 current 接口
        if current:
            kind = _detect_param_table_kind(tbl.rows) or ("in" if current_section == "in" else "out" if current_section == "out" else "")
            fields = _parse_param_table(tbl.rows)
            if fields:
                if kind == "in":
                    current.request_fields.extend(fields)
                elif kind == "out":
                    current.response_fields.extend(fields)
                else:
                    # 无法判断：默认作为出参（更常见是响应结构）
                    current.response_fields.extend(fields)

    # 文档结束时 flush 示例
    if current_section in {"req_example", "resp_example"}:
        flush_examples(current_section)

    # 基本质量检查
    if not spec.endpoints:
        spec.issues.append(ParseIssue(level=IssueLevel.ERROR, message="未解析到任何接口定义（请检查文档格式或解析规则）"))
    else:
        # 缺 method/path 的接口记录 warning
        for ep in spec.endpoints:
            if not ep.method or ep.method.upper() not in _METHODS_SET:
                spec.issues.append(
                    ParseIssue(
                        level=IssueLevel.WARNING,
                        message=f"接口 method 不明确，已使用默认值：{ep.method}",
                        location=ep.source_location,
                        endpoint_hint=ep.operation_id or ep.name,
                    )
                )
            if not ep.path or ep.path == "/":
                spec.issues.append(
                    ParseIssue(
                        level=IssueLevel.WARNING,
                        message="接口 path 不明确，已使用默认值：/（建议修订文档以包含请求路径）",
                        location=ep.source_location,
                        endpoint_hint=ep.operation_id or ep.name,
                    )
                )

    return spec


async def parse_doc_blocks_to_spec_async(
    blocks: List[DocBlock],
    *,
    title: str = "DOCX API",
    version: str = "0.0.0",
    only_operation_ids: Optional[List[str]] = None,
    log_config: Optional[Dict[str, Any]] = None,
    llm_temperature: float = 0.0,
    llm_max_tokens: int = 2048,
    llm_retries: int = 2,
    llm_cache_dir: str = "",
    llm_resume: bool = True,
    llm_overwrite_cache: bool = False,
) -> DocumentSpec:
    """
    异步解析版本：对每个接口表格使用 LLM 解析入参/出参/示例（用户要求）。
    """
    logger = get_logger("docx_openapi.parser", **(log_config or {}))
    spec = DocumentSpec(title=title, version=version)
    only_set = set([o for o in (only_operation_ids or []) if o])
    servers_seen: set[str] = set()

    def normalize_path_and_collect_server(raw: str) -> str:
        """
        将 LLM 返回的 path 规范化为 OpenAPI paths key：
        - 若为完整 URL（http://... 或 //...），提取 path 并记录 servers
        - 去掉 query/fragment
        - 去掉多余空白
        - 确保以 / 开头
        """
        s = (raw or "").strip()
        if not s:
            return "/"
        # 去掉空白后的尾巴（LLM 有时会拼接说明）
        s = s.split()[0]

        # scheme-less URL: //ip:port/xxx
        if s.startswith("//"):
            u = urlsplit("http:" + s)
            if u.netloc:
                servers_seen.add(f"http://{u.netloc}")
            return u.path or "/"

        # full URL
        if s.startswith("http://") or s.startswith("https://"):
            u = urlsplit(s)
            if u.scheme and u.netloc:
                servers_seen.add(f"{u.scheme}://{u.netloc}")
            return u.path or "/"

        # 可能是 /path?query
        if "?" in s:
            s = s.split("?", 1)[0]
        if "#" in s:
            s = s.split("#", 1)[0]
        if not s.startswith("/"):
            s = "/" + s
        return s

    for b in blocks:
        if not isinstance(b, TableBlock):
            continue
        kv = _table_to_kv(b.rows)
        if not (kv and _looks_like_endpoint_kv(kv)):
            continue

        # 先从 kv 里拿到接口名称/编号，作为 LLM 的先验约束
        name_hint = kv.get("接口名称") or kv.get("接口名") or kv.get("接口") or ""
        op_hint = _find_code(name_hint) or _find_code(" ".join(kv.values()))

        # --only 过滤：优先用 op_hint，其次用表格全文包含匹配（避免 op_hint 为空时误解析其他接口）
        if only_set:
            table_text_joined = " ".join([" ".join(r) for r in b.rows if r])
            matched = (op_hint in only_set) if op_hint else False
            if not matched:
                for oid in only_set:
                    if oid and oid in table_text_joined:
                        matched = True
                        break
            if not matched:
                continue

        llm_ep, err = await llm_parse_endpoint_from_table(
            b.rows,
            cache_dir=llm_cache_dir or None,
            resume=llm_resume,
            overwrite_cache=llm_overwrite_cache,
            cache_key=CacheKey(block_index=b.location.block_index, operation_id=op_hint or ""),
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            retries=llm_retries,
            log_config=log_config,
        )
        if llm_ep is None:
            spec.issues.append(
                ParseIssue(
                    level=IssueLevel.ERROR,
                    message=f"LLM 解析失败：{err}",
                    location=b.location,
                    endpoint_hint=op_hint or name_hint,
                )
            )
            continue

        # 规范化 path，并收集 servers（如果 LLM 给了完整 URL）
        llm_ep.path = normalize_path_and_collect_server(llm_ep.path)

        # 将 LLM 输出映射回内部中间模型
        endpoint = EndpointSpec(
            name=llm_ep.name,
            method=llm_ep.method,
            path=llm_ep.path,
            operation_id=llm_ep.operation_id or op_hint,
            summary=llm_ep.name,
            description=llm_ep.description,
            source_location=b.location,
        )
        for f in llm_ep.request_fields:
            endpoint.request_fields.append(FieldSpec(name=f.name, raw_type=f.raw_type, required=f.required, description=f.description))
        for f in llm_ep.response_fields:
            endpoint.response_fields.append(FieldSpec(name=f.name, raw_type=f.raw_type, required=f.required, description=f.description))
        if llm_ep.request_example is not None:
            endpoint.request_examples.append(ExampleSpec(kind="request", value=llm_ep.request_example, raw=str(llm_ep.request_example)))
        if llm_ep.response_example is not None:
            endpoint.response_examples.append(ExampleSpec(kind="response", value=llm_ep.response_example, raw=str(llm_ep.response_example)))

        logger.debug(
            "LLM 解析接口表格",
            operation_id=endpoint.operation_id,
            endpoint_name=endpoint.name,
            endpoint_method=endpoint.method,
            endpoint_path=endpoint.path,
            request_fields=len(endpoint.request_fields),
            response_fields=len(endpoint.response_fields),
            request_examples=len(endpoint.request_examples),
            response_examples=len(endpoint.response_examples),
            block_index=b.location.block_index,
        )
        spec.endpoints.append(endpoint)

    if not spec.endpoints:
        spec.issues.append(ParseIssue(level=IssueLevel.ERROR, message="未解析到任何接口定义（LLM 路径）"))

    # 写入 servers（按出现顺序不严格保证，但稳定即可）
    if servers_seen:
        spec.servers = [{"url": s} for s in sorted(servers_seen)]

    return spec

