# -*- coding: utf-8 -*-
"""
OpenAPI 3.x 生成器（中间模型 → OpenAPI JSON）

设计原则：
- 最小可用：保证 openapi/info/paths 与 operation.responses 存在
- 类型映射尽量保守：未知类型 → string，同时保留 x-original-type
- 示例优先放在 application/json 的 example(s)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .models import DocumentSpec, EndpointSpec, FieldSpec


def _slugify_operation_id(method: str, path: str) -> str:
    base = f"{method}_{path}"
    base = base.replace("{", "").replace("}", "")
    base = re.sub(r"[^A-Za-z0-9_]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or f"{method}_root"


def _infer_schema_from_type(raw_type: str) -> Dict[str, Any]:
    t = (raw_type or "").strip().lower()
    if not t:
        return {"type": "string"}

    # 常见类型映射
    if t in {"string", "str", "varchar", "text", "char"}:
        return {"type": "string"}
    if t in {"int", "integer", "long", "int32", "int64"}:
        return {"type": "integer", "format": "int64" if "64" in t or "long" in t else "int32"}
    if t in {"float", "double", "number", "decimal"}:
        return {"type": "number"}
    if t in {"bool", "boolean"}:
        return {"type": "boolean"}
    if "date" in t and "time" in t:
        return {"type": "string", "format": "date-time"}
    if t == "date":
        return {"type": "string", "format": "date"}
    if t.startswith("list") or t.startswith("array") or "[]" in t:
        return {"type": "array", "items": {"type": "string"}}

    # 兜底：string + 保留原始类型
    return {"type": "string", "x-original-type": raw_type}


def _field_to_param(ep: EndpointSpec, f: FieldSpec) -> Dict[str, Any]:
    schema = _infer_schema_from_type(f.raw_type)
    param_in = "query"
    # path 参数：出现在 /{xxx} 形式中
    if f.name and f"{{{f.name}}}" in ep.path:
        param_in = "path"
    return {
        "name": f.name,
        "in": param_in,
        "required": True if param_in == "path" else bool(f.required),
        "description": f.description or "",
        "schema": schema,
    }


def _fields_to_object_schema(fields: List[FieldSpec]) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    required: List[str] = []
    for f in fields:
        props[f.name] = _infer_schema_from_type(f.raw_type) | ({"description": f.description} if f.description else {})
        if f.required:
            required.append(f.name)
    schema: Dict[str, Any] = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def build_openapi(spec: DocumentSpec) -> Dict[str, Any]:
    """
    生成 OpenAPI 3.x JSON dict。
    """
    paths: Dict[str, Any] = {}
    used_operation_ids: set[str] = set()

    def ensure_unique(op_id: str) -> str:
        base = op_id
        i = 2
        while op_id in used_operation_ids:
            op_id = f"{base}_{i}"
            i += 1
        used_operation_ids.add(op_id)
        return op_id

    for ep in spec.endpoints:
        path_item = paths.setdefault(ep.path, {})
        method = (ep.method or "GET").lower()
        op_id = ep.operation_id or _slugify_operation_id(ep.method or "GET", ep.path or "/")
        op_id = ensure_unique(op_id)

        # parameters：优先把 request_fields 作为 query/path；requestBody 作为 JSON body（当字段较多且不是 path/query 时）
        parameters: List[Dict[str, Any]] = []
        body_fields: List[FieldSpec] = []
        for f in ep.request_fields:
            # 启发式：如果字段出现在 path，则认为 path；否则统一 query
            if f.name and f"{{{f.name}}}" in (ep.path or ""):
                parameters.append(_field_to_param(ep, f))
            else:
                # 为了最小可用，这里默认 query；如果未来要更精细区分，可在 parser 里标记 location
                parameters.append(_field_to_param(ep, f))
                # 同时保留一份 body_fields（若用户希望 body，可在后续支持开关）
                body_fields.append(f)

        operation: Dict[str, Any] = {
            "operationId": op_id,
            "summary": ep.summary or ep.name,
            "description": ep.description or "",
            "responses": {},
        }
        if parameters:
            operation["parameters"] = parameters

        # requestBody：如果有示例请求或明确存在 body 字段，生成 application/json
        if ep.request_examples or body_fields:
            req_schema = _fields_to_object_schema(body_fields) if body_fields else {"type": "object"}
            req_content: Dict[str, Any] = {"schema": req_schema}
            if ep.request_examples:
                # 只取第一个可解析 JSON 的示例作为 example；其余未来可扩展 examples
                ex0 = ep.request_examples[0]
                req_content["example"] = ex0.value if ex0.value is not None else ex0.raw
            operation["requestBody"] = {"content": {"application/json": req_content}}

        # responses：默认 200
        resp_schema = _fields_to_object_schema(ep.response_fields) if ep.response_fields else {"type": "object"}
        resp_content: Dict[str, Any] = {"schema": resp_schema}
        if ep.response_examples:
            ex0 = ep.response_examples[0]
            resp_content["example"] = ex0.value if ex0.value is not None else ex0.raw
        operation["responses"]["200"] = {"description": "成功", "content": {"application/json": resp_content}}

        path_item[method] = operation

    openapi: Dict[str, Any] = {
        "openapi": "3.0.0",
        "info": {"title": spec.title, "version": spec.version},
        "paths": paths,
    }
    if spec.servers:
        openapi["servers"] = spec.servers
    return openapi

