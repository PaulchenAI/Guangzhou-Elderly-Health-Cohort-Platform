# -*- coding: utf-8 -*-
"""
解析报告输出

报告用于：
- 列出解析到的接口数量、失败原因
- 提供可定位线索（block_index、简要片段）
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict

from .models import DocumentSpec, ParseIssue


def build_report(spec: DocumentSpec, *, openapi_errors: list[str] | None = None) -> Dict[str, Any]:
    openapi_errors = openapi_errors or []
    issues = []
    for i in spec.issues:
        d = asdict(i)
        # Enum 序列化
        if d.get("level") is not None:
            d["level"] = str(d["level"])
        issues.append(d)

    endpoints = []
    for ep in spec.endpoints:
        endpoints.append(
            {
                "operationId": ep.operation_id,
                "name": ep.name,
                "method": ep.method,
                "path": ep.path,
                "requestFields": len(ep.request_fields),
                "responseFields": len(ep.response_fields),
                "requestExamples": len(ep.request_examples),
                "responseExamples": len(ep.response_examples),
                "location": asdict(ep.source_location) if ep.source_location else None,
            }
        )

    return {
        "summary": {
            "title": spec.title,
            "version": spec.version,
            "endpointCount": len(spec.endpoints),
            "issueCount": len(issues),
            "openapiErrorCount": len(openapi_errors),
        },
        "openapiErrors": openapi_errors,
        "issues": issues,
        "endpoints": endpoints,
    }


def dump_report_json(report: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

