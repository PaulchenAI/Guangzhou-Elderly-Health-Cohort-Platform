# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI 导出智能体

最小实现：把 state 中的 docx_path 导出为 openapi.json/report.json
（后续可扩展为：LLM 辅助解析、增量对比、与后端路由对齐等）
"""

from __future__ import annotations

from typing import Any, Dict

from .base_agent import BaseAgent, AgentResult
from ..docx_openapi.pipeline import export_openapi_from_docx, dump_openapi_json
from ..docx_openapi.report import dump_report_json
from ..docx_openapi.validator import validate_openapi_minimal


class DocxOpenAPIExtractorAgent(BaseAgent):
    """DOCX OpenAPI 导出智能体"""

    name = "docx_openapi_extractor"

    async def run(self, state: Dict[str, Any]) -> AgentResult:
        docx_path = state.get("docx_path") or state.get("input_docx")
        output_path = state.get("openapi_output") or state.get("output_openapi")
        report_path = state.get("report_output") or ""
        title = state.get("openapi_title") or "DOCX API"
        version = state.get("openapi_version") or "0.0.0"
        only = state.get("only_operation_ids")

        if not docx_path or not output_path:
            return AgentResult(
                updates={},
                output_text="缺少必要参数：docx_path 与 openapi_output",
            )

        openapi, report = export_openapi_from_docx(
            docx_path,
            title=title,
            version=version,
            only_operation_ids=only,
        )
        errors = validate_openapi_minimal(openapi)
        if errors:
            # 仍然输出 report，方便定位问题
            if report_path:
                dump_report_json(report, report_path)
            return AgentResult(
                updates={"openapi_errors": errors, "report": report},
                output_text="OpenAPI 最小校验失败，已生成报告（如提供 report_output）",
            )

        dump_openapi_json(openapi, output_path)
        if report_path:
            dump_report_json(report, report_path)
        return AgentResult(
            updates={"openapi_path": output_path, "report_path": report_path, "endpoint_count": report["summary"]["endpointCount"]},
            output_text="已成功导出 OpenAPI 3.x JSON",
        )

