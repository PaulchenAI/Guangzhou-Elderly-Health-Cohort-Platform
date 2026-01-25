#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Doc API - 文档 API 查询模块

提供后台 API 接口，支持查询从 Word 文档解析生成的 OpenAPI JSON 文档信息，
包括接口列表、接口详情、接口搜索等功能。
"""
from core.doc_api.doc_api_model import DocApiInvokeLog

__all__ = ["DocApiInvokeLog"]