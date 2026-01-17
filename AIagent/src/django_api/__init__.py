# -*- coding: utf-8 -*-
"""
Django API 集成模块

提供 OpenAPI-Aware 的 Django API 客户端，支持：
- 自动加载和解析 OpenAPI Schema
- AI 可理解的 API 描述生成
- 分层检索（关键词 + RAG + LLM）
- Bearer Token 认证
- 通用 API 调用
- 命令行工具 (CLI)
- LangGraph 驱动的脚本生成（多步骤查询）

CLI 使用方法:
    python -m src.django_api info              # 显示 API 信息
    python -m src.django_api login             # 测试登录
    python -m src.django_api search <keyword>  # 搜索 API 端点
    python -m src.django_api call <intent>     # 根据意图调用 API
    python -m src.django_api generate <intent> # 生成多步骤查询脚本
    python -m src.django_api summary           # 生成 AI 摘要
"""

from .models import APIEndpoint, DjangoAPIConfig
from .client import OpenAPIAwareClient
from .indexer import APIEndpointIndexer
from .retriever import HierarchicalRetriever
from .agent import DjangoAPIAgent
from .script_generator import ScriptGenerator, build_script_generator_graph
from .cli import main as cli_main

__all__ = [
    "APIEndpoint",
    "DjangoAPIConfig",
    "OpenAPIAwareClient",
    "APIEndpointIndexer",
    "HierarchicalRetriever",
    "DjangoAPIAgent",
    "ScriptGenerator",
    "build_script_generator_graph",
    "cli_main",
]
