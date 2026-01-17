# -*- coding: utf-8 -*-
"""
配置模型（Pydantic）
定义所有配置的数据结构和验证规则
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClaudeCodeConfig(BaseModel):
    """Claude Code CLI配置"""
    path: str = Field(..., description="Claude Code CLI路径")
    timeout: int = Field(default=300, ge=1, description="执行超时时间（秒）")
    max_concurrent: int = Field(default=2, ge=1, le=10, description="最大并发数")
    working_dir: str = Field(..., description="工作目录")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: Literal["anthropic", "openai", "local", "azure_openai", "google"] = Field(
        default="anthropic",
        description="LLM提供商"
    )
    api_key: Optional[str] = Field(default=None, description="API密钥")
    model: str = Field(default="claude-sonnet-4-20250514", description="模型名称")
    max_tokens: int = Field(default=4096, ge=1, description="最大Token数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    base_url: Optional[str] = Field(default=None, description="自定义API端点（用于本地模型或OpenAI兼容API）")
    
    # Azure OpenAI特定配置
    azure_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI端点")
    azure_api_version: Optional[str] = Field(default="2024-02-15-preview", description="Azure API版本")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str], info) -> Optional[str]:
        """验证API密钥（local提供商不需要）"""
        provider = info.data.get('provider', 'anthropic')
        if provider != 'local' and not v:
            raise ValueError(f"{provider} 提供商需要设置 api_key")
        return v
    
    @field_validator('azure_endpoint')
    @classmethod
    def validate_azure_endpoint(cls, v: Optional[str], info) -> Optional[str]:
        """验证Azure OpenAI端点"""
        provider = info.data.get('provider', 'anthropic')
        if provider == 'azure_openai' and not v:
            raise ValueError("azure_openai 提供商需要设置 azure_endpoint")
        return v


class VectorDBConfig(BaseModel):
    """向量数据库配置"""
    type: Literal["chromadb", "faiss", "milvus"] = Field(default="chromadb", description="向量数据库类型")
    persist_dir: str = Field(default="./data/chroma", description="持久化目录（ChromaDB）")
    host: Optional[str] = Field(default=None, description="数据库主机（远程服务）")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="数据库端口")


class MemoryConfig(BaseModel):
    """记忆系统配置"""
    backend: Literal["memory", "redis", "chromadb"] = Field(default="redis", description="记忆后端")
    redis_url: Optional[str] = Field(default="redis://localhost:6379/1", description="Redis连接URL")
    ttl: int = Field(default=86400, ge=1, description="TTL（秒）")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="日志级别"
    )
    dir: str = Field(default="./logs", description="日志目录")
    format: Literal["json", "text"] = Field(default="json", description="日志格式")
    max_size: str = Field(default="10MB", description="日志文件最大大小")
    backup_count: int = Field(default=5, ge=0, description="备份文件数量")


class RAGConfig(BaseModel):
    """RAG配置"""
    chunk_size: int = Field(default=1000, ge=1, description="文档分块大小")
    chunk_overlap: int = Field(default=200, ge=0, description="分块重叠大小")
    top_k: int = Field(default=5, ge=1, description="检索返回的Top K结果数")
    embedding_provider: Optional[str] = Field(default=None, description="嵌入模型提供商")
    embedding_model: str = Field(default="text-embedding-3-small", description="嵌入模型名称")
    embedding_api_key: Optional[str] = Field(default=None, description="嵌入模型API密钥")
    embedding_base_url: Optional[str] = Field(default=None, description="嵌入模型API端点（用于阿里云百炼等兼容API）")
    embedding_dimensions: Optional[int] = Field(default=None, ge=64, le=2048, description="向量维度（阿里云百炼支持64/128/256/512/768/1024/1536/2048，默认1024）")
    embedding_max_batch_size: int = Field(default=10, ge=1, le=100, description="同步接口每次最多处理的文本条数（阿里云百炼同步接口最多10条）")


class DjangoAPIConfigModel(BaseModel):
    """Django API 集成配置"""
    base_url: str = Field(default="http://localhost:8000", description="Django API 基础 URL")
    username: str = Field(default="", description="登录用户名")
    password: str = Field(default="", description="登录密码")
    timeout: int = Field(default=30, ge=1, description="请求超时时间（秒）")
    # RAG 检索配置
    enable_rag: bool = Field(default=True, description="是否启用 RAG 检索")
    keyword_filter_threshold: int = Field(default=20, ge=1, description="关键词过滤后最多保留的候选数")
    retrieval_top_k: int = Field(default=10, ge=1, description="向量检索返回的 Top K 结果数")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="向量相似度阈值")


class Settings(BaseSettings):
    """全局设置（从环境变量加载）"""
    model_config = SettingsConfigDict(
        env_file=".env",  # 默认从AIagent/.env加载
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        """初始化时尝试加载项目根目录的.env"""
        from pathlib import Path
        import os
        from dotenv import load_dotenv
        
        # 先尝试加载项目根目录的.env（如果存在）
        project_root_env = Path(__file__).parent.parent.parent.parent / ".env"
        if project_root_env.exists():
            load_dotenv(project_root_env, override=False)  # 不覆盖已存在的环境变量
        
        # 再加载AIagent/.env（如果存在）
        aiagent_env = Path(__file__).parent.parent.parent / ".env"
        if aiagent_env.exists():
            load_dotenv(aiagent_env, override=False)
        
        super().__init__(**kwargs)
    
    # Claude Code CLI配置
    claude_code_path: str = Field(..., alias="CLAUDE_CODE_PATH")
    claude_code_timeout: int = Field(default=300, alias="CLAUDE_CODE_TIMEOUT")
    claude_code_max_concurrent: int = Field(default=2, alias="CLAUDE_CODE_MAX_CONCURRENT")
    claude_code_working_dir: str = Field(..., alias="CLAUDE_CODE_WORKING_DIR")
    
    # LLM配置
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")  # 默认改为openai以支持DeepSeek
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    # 支持LLM_MODEL和LLM_MODEL_NAME（兼容不同配置格式）
    llm_model: str = Field(default="claude-sonnet-4-20250514", alias="LLM_MODEL")
    llm_model_name: Optional[str] = Field(default=None, alias="LLM_MODEL_NAME")  # 兼容LLM_MODEL_NAME
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    llm_base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")
    
    # Azure OpenAI配置
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: Optional[str] = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # 向量数据库配置
    vector_db_type: str = Field(default="chromadb", alias="VECTOR_DB_TYPE")
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    
    # 记忆系统配置
    memory_backend: str = Field(default="redis", alias="MEMORY_BACKEND")
    redis_url: str = Field(default="redis://localhost:6379/1", alias="REDIS_URL")
    memory_ttl: int = Field(default=86400, alias="MEMORY_TTL")
    
    # 日志配置
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_max_size: str = Field(default="10MB", alias="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    
    # RAG配置
    rag_chunk_size: int = Field(default=1000, alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=200, alias="RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    embedding_provider: Optional[str] = Field(default=None, alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_api_key: Optional[str] = Field(default=None, alias="EMBEDDING_API_KEY")
    embedding_base_url: Optional[str] = Field(default=None, alias="EMBEDDING_BASE_URL")
    embedding_dimensions: Optional[int] = Field(default=None, alias="EMBEDDING_DIMENSIONS")
    embedding_max_batch_size: int = Field(default=10, alias="EMBEDDING_MAX_BATCH_SIZE")
    
    # Django API 配置
    django_api_base_url: str = Field(default="http://localhost:8000", alias="DJANGO_API_BASE_URL")
    django_api_username: str = Field(default="", alias="DJANGO_API_USERNAME")
    django_api_password: str = Field(default="", alias="DJANGO_API_PASSWORD")
    django_api_timeout: int = Field(default=30, alias="DJANGO_API_TIMEOUT")
    django_api_enable_rag: bool = Field(default=True, alias="DJANGO_API_ENABLE_RAG")
    django_api_keyword_filter_threshold: int = Field(default=20, alias="DJANGO_API_KEYWORD_FILTER_THRESHOLD")
    django_api_retrieval_top_k: int = Field(default=10, alias="DJANGO_API_RETRIEVAL_TOP_K")
    django_api_similarity_threshold: float = Field(default=0.5, alias="DJANGO_API_SIMILARITY_THRESHOLD")
    
    def get_claude_code_config(self) -> ClaudeCodeConfig:
        """获取Claude Code配置对象"""
        return ClaudeCodeConfig(
            path=self.claude_code_path,
            timeout=self.claude_code_timeout,
            max_concurrent=self.claude_code_max_concurrent,
            working_dir=self.claude_code_working_dir
        )
    
    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置对象"""
        # 优先使用LLM_MODEL_NAME，如果不存在则使用LLM_MODEL
        model = self.llm_model_name if self.llm_model_name else self.llm_model
        
        return LLMConfig(
            provider=self.llm_provider,  # type: ignore
            api_key=self.llm_api_key,
            model=model,
            max_tokens=self.llm_max_tokens,
            temperature=self.llm_temperature,
            base_url=self.llm_base_url,
            azure_endpoint=getattr(self, 'azure_openai_endpoint', None),
            azure_api_version=getattr(self, 'azure_openai_api_version', None)
        )
    
    def get_vector_db_config(self) -> VectorDBConfig:
        """获取向量数据库配置对象"""
        return VectorDBConfig(
            type=self.vector_db_type,  # type: ignore
            persist_dir=self.chroma_persist_dir
        )
    
    def get_memory_config(self) -> MemoryConfig:
        """获取记忆系统配置对象"""
        return MemoryConfig(
            backend=self.memory_backend,  # type: ignore
            redis_url=self.redis_url,
            ttl=self.memory_ttl
        )
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置对象"""
        return LoggingConfig(
            level=self.log_level,  # type: ignore
            dir=self.log_dir,
            format=self.log_format,  # type: ignore
            max_size=self.log_max_size,
            backup_count=self.log_backup_count
        )
    
    def get_rag_config(self) -> RAGConfig:
        """获取RAG配置对象"""
        return RAGConfig(
            chunk_size=self.rag_chunk_size,
            chunk_overlap=self.rag_chunk_overlap,
            top_k=self.rag_top_k,
            embedding_provider=self.embedding_provider,
            embedding_model=self.embedding_model,
            embedding_api_key=self.embedding_api_key,
            embedding_base_url=self.embedding_base_url,
            embedding_dimensions=self.embedding_dimensions,
            embedding_max_batch_size=self.embedding_max_batch_size
        )
    
    def get_django_api_config(self) -> DjangoAPIConfigModel:
        """获取Django API配置对象"""
        return DjangoAPIConfigModel(
            base_url=self.django_api_base_url,
            username=self.django_api_username,
            password=self.django_api_password,
            timeout=self.django_api_timeout,
            enable_rag=self.django_api_enable_rag,
            keyword_filter_threshold=self.django_api_keyword_filter_threshold,
            retrieval_top_k=self.django_api_retrieval_top_k,
            similarity_threshold=self.django_api_similarity_threshold
        )