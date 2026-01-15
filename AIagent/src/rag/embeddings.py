# -*- coding: utf-8 -*-
"""
向量嵌入封装

根据配置创建可用于 LangChain 的 Embeddings 实例。
（最小实现：支持 OpenAI / Azure OpenAI；其余提供商给出明确错误提示）
"""

from __future__ import annotations

from typing import Optional

from langchain_core.embeddings import Embeddings

from ..logging.logger import get_logger
from ..utils.config_models import LLMConfig, RAGConfig

logger = get_logger("rag.embeddings")


def create_embeddings(rag_config: RAGConfig, llm_config: Optional[LLMConfig] = None) -> Embeddings:
    """
    创建 Embeddings 实例。

    优先级：
    1) RAGConfig.embedding_provider / embedding_api_key / embedding_model
    2) 若未配置 embedding_provider，尝试根据 llm_config.provider 推断
    """

    provider = (rag_config.embedding_provider or (llm_config.provider if llm_config else None) or "openai").lower()
    model = rag_config.embedding_model
    api_key = rag_config.embedding_api_key

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not api_key:
            raise ValueError("使用 openai 嵌入时需要配置 EMBEDDING_API_KEY")

        return OpenAIEmbeddings(model=model, api_key=api_key)

    if provider in ("azure", "azure_openai"):
        from langchain_openai import AzureOpenAIEmbeddings

        if not api_key:
            raise ValueError("使用 azure_openai 嵌入时需要配置 EMBEDDING_API_KEY")

        if not llm_config or not llm_config.azure_endpoint:
            raise ValueError("使用 azure_openai 嵌入时需要配置 AZURE_OPENAI_ENDPOINT（通过 LLMConfig.azure_endpoint）")

        # Azure Embeddings 还需要 api_version；复用 llm_config.azure_api_version
        return AzureOpenAIEmbeddings(
            model=model,
            api_key=api_key,
            azure_endpoint=llm_config.azure_endpoint,
            api_version=llm_config.azure_api_version or "2024-02-15-preview",
        )

    raise ValueError(
        f"暂不支持的嵌入提供商: {provider}。"
        "请在环境变量中设置 EMBEDDING_PROVIDER=openai 或 azure_openai，并配置 EMBEDDING_API_KEY。"
    )

