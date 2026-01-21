# -*- coding: utf-8 -*-
"""
DOCX → OpenAPI 解析测试

说明：
- 不引入 python-docx，直接构造一个最小 zip（含 word/document.xml）
- 覆盖：接口识别、入参/出参、示例提取、OpenAPI 最小校验
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from src.docx_openapi.extractor import extract_blocks_from_docx
from src.docx_openapi.pipeline import export_openapi_from_docx
from src.docx_openapi.validator import validate_openapi_minimal


def _write_min_docx(path: Path, document_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", document_xml)


def test_extract_blocks_from_min_docx(tmp_path: Path):
    docx = tmp_path / "mini.docx"
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>入参</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>接口名称</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>PER_OUTP_0004 门诊患者病历信息</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>method</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>GET</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>path</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>/api/patient/{patientId}</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>
"""
    _write_min_docx(docx, xml)
    blocks = extract_blocks_from_docx(str(docx))
    assert blocks, "应至少解析出一个块"
    assert any(getattr(b, "text", "") == "入参" for b in blocks)
    assert any(getattr(b, "rows", None) for b in blocks)


def test_export_openapi_from_docx_minimal(tmp_path: Path):
    docx = tmp_path / "mini2.docx"
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>接口名称</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>PER_OUTP_0004 门诊患者病历信息</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>请求方式</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>GET</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>请求路径</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>/api/patient/{patientId}</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:r><w:t>入参</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>参数名</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>类型</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>必填</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>说明</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>patientId</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>string</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>是</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>患者ID</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:r><w:t>出参</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>字段名</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>类型</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>说明</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>name</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>string</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>姓名</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p><w:r><w:t>响应示例</w:t></w:r></w:p>
    <w:p><w:r><w:t>{"name":"张三"}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    _write_min_docx(docx, xml)
    # 单元测试不依赖外部 LLM
    openapi, report = export_openapi_from_docx(str(docx), title="T", version="1.0", use_llm=False)
    errs = validate_openapi_minimal(openapi)
    assert errs == [], f"不应有最小校验错误：{errs}"
    assert report["summary"]["endpointCount"] == 1
    assert "/api/patient/{patientId}" in openapi["paths"]
    op = openapi["paths"]["/api/patient/{patientId}"]["get"]
    assert op["responses"]["200"]["content"]["application/json"]["example"]["name"] == "张三"


def test_validate_openapi_minimal_failure():
    errs = validate_openapi_minimal({"openapi": "3.0.0", "info": {"title": "x", "version": "1"}})
    assert errs, "缺少 paths 时应失败"

