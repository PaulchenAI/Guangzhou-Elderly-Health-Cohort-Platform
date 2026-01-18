# -*- coding: utf-8 -*-
"""
历史指令 RAG 检索模块

提供历史执行记录的向量索引和分层检索功能：
- 向量索引：使用归一化后的核心意图生成向量
- 分层检索：精确匹配、高度相似、一般相似
- 上下文构建：根据检索结果构建 LLM 上下文
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .execution_history import (
    ExecutionHistoryStorage,
    ExecutionRecord,
    NormalizedIntent,
    normalize_intent,
    substitute_params,
)

logger = logging.getLogger(__name__)


# ==================== 配置 ====================

@dataclass
class HistoryRetrievalConfig:
    """历史检索配置"""
    # 检索数量
    top_k: int = 10
    
    # 分层阈值
    exact_threshold: float = 0.95      # 精确匹配阈值（直接复用）
    high_threshold: float = 0.80       # 高度相似阈值（主要参考）
    low_threshold: float = 0.60        # 一般相似阈值（辅助参考）
    
    # 上下文限制
    max_exact_results: int = 1         # 精确匹配最多返回数
    max_high_results: int = 3          # 高度相似最多返回数
    max_low_results: int = 2           # 一般相似最多返回数
    
    # 权重配置（多维度加权）
    weight_semantic: float = 0.7       # 语义相似度权重
    weight_api: float = 0.2            # API 重合度权重
    weight_keyword: float = 0.1        # 关键词匹配权重


# ==================== 检索结果 ====================

@dataclass
class SearchResult:
    """检索结果"""
    record_id: str
    intent: str
    normalized_intent: str
    status: str
    score: float
    apis_used: List[str]
    script_content: str = ""
    execution_output: str = ""
    error_type: str = ""
    error_message: str = ""
    intent_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.intent_params is None:
            self.intent_params = {}


@dataclass
class TieredSearchResults:
    """分层检索结果"""
    exact_matches: List[SearchResult]      # 精确匹配（≥0.95）
    high_similar: List[SearchResult]       # 高度相似（0.80-0.95）
    low_similar: List[SearchResult]        # 一般相似（0.60-0.80）
    
    @property
    def has_exact_match(self) -> bool:
        """是否有精确匹配"""
        return len(self.exact_matches) > 0 and self.exact_matches[0].status == "success"
    
    @property
    def best_match(self) -> Optional[SearchResult]:
        """获取最佳匹配"""
        if self.exact_matches:
            return self.exact_matches[0]
        if self.high_similar:
            return self.high_similar[0]
        if self.low_similar:
            return self.low_similar[0]
        return None


# ==================== 历史索引器 ====================

class HistoryIndexer:
    """
    历史指令向量索引器
    
    使用归一化后的核心意图生成向量，支持语义检索
    """
    
    def __init__(
        self,
        embeddings: Embeddings,
        storage: ExecutionHistoryStorage,
        persist_dir: str = "./data/history_index",
        collection_name: str = "execution_history",
    ):
        """
        初始化索引器
        
        Args:
            embeddings: 嵌入模型
            storage: 执行记录存储
            persist_dir: 向量数据库持久化目录
            collection_name: 集合名称
        """
        self.embeddings = embeddings
        self.storage = storage
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.vectorstore = None
        self._record_map: Dict[str, Dict[str, Any]] = {}
    
    def build_index(self) -> int:
        """
        构建向量索引
        
        Returns:
            索引的记录数量
        """
        from langchain_community.vectorstores import Chroma
        
        records = self.storage.get_all_records()
        if not records:
            logger.warning("没有历史记录需要索引")
            return 0
        
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # 将记录转换为 Document
        documents = []
        for entry in records:
            # 使用归一化后的核心意图作为主要内容
            normalized = normalize_intent(entry.get("intent", ""))
            
            # 构建向量化内容
            content_parts = [
                f"意图: {normalized.core_intent}",
                f"API: {', '.join(entry.get('apis_used', []))}",
                f"状态: {entry.get('status', '')}",
            ]
            content = "\n".join(content_parts)
            
            doc = Document(
                page_content=content,
                metadata={
                    "record_id": entry.get("id", ""),
                    "intent": entry.get("intent", ""),
                    "normalized_intent": normalized.core_intent,
                    "status": entry.get("status", ""),
                    "apis_used": json.dumps(entry.get("apis_used", [])),
                    "error_type": entry.get("error_type", ""),
                    "script_path": entry.get("script_path", ""),
                    "meta_path": entry.get("meta_path", ""),
                }
            )
            documents.append(doc)
            
            # 保存映射
            self._record_map[entry.get("id", "")] = entry
        
        # 创建向量索引
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=self.persist_dir,
        )
        self.vectorstore.persist()
        
        logger.info(f"已构建历史记录索引，共 {len(documents)} 条记录")
        return len(documents)
    
    def load_index(self) -> bool:
        """
        加载已存在的索引
        
        Returns:
            是否加载成功
        """
        from langchain_community.vectorstores import Chroma
        
        index_path = Path(self.persist_dir)
        if not index_path.exists():
            logger.warning(f"索引目录不存在: {self.persist_dir}")
            return False
        
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
            
            # 加载记录映射
            records = self.storage.get_all_records()
            for entry in records:
                self._record_map[entry.get("id", "")] = entry
            
            logger.info(f"已加载历史记录索引: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            return False
    
    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        向量相似度检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            (记录索引, 相似度分数) 列表
        """
        if not self.vectorstore:
            logger.warning("向量索引未初始化")
            return []
        
        # 归一化查询意图
        normalized = normalize_intent(query)
        search_text = f"意图: {normalized.core_intent}"
        
        # 使用 similarity_search_with_relevance_scores
        results = self.vectorstore.similarity_search_with_relevance_scores(
            search_text,
            k=top_k,
        )
        
        # 转换结果
        record_scores = []
        for doc, score in results:
            record_id = doc.metadata.get("record_id", "")
            if record_id in self._record_map:
                record_scores.append((self._record_map[record_id], score))
        
        return record_scores
    
    def update_index(self, record_id: str = None):
        """
        增量更新索引
        
        Args:
            record_id: 指定更新的记录 ID（为 None 时全量重建）
        """
        try:
            # 简单实现：全量重建
            self.build_index()
        except Exception as e:
            logger.warning(f"更新向量索引失败（可能是 embedding API 不兼容）: {e}")
            # 失败时不抛出异常，系统将回退到关键词匹配


# ==================== 历史检索器 ====================

class HistoryRetriever:
    """
    历史指令分层检索器
    
    实现强制优先检索和分层处理策略
    """
    
    def __init__(
        self,
        storage: ExecutionHistoryStorage,
        indexer: Optional[HistoryIndexer] = None,
        config: Optional[HistoryRetrievalConfig] = None,
    ):
        """
        初始化检索器
        
        Args:
            storage: 执行记录存储
            indexer: 历史索引器（可选，用于向量检索）
            config: 检索配置
        """
        self.storage = storage
        self.indexer = indexer
        self.config = config or HistoryRetrievalConfig()
    
    def retrieve(self, query: str) -> TieredSearchResults:
        """
        分层检索历史指令
        
        Args:
            query: 用户查询意图
        
        Returns:
            分层检索结果
        """
        exact_matches = []
        high_similar = []
        low_similar = []
        
        # 归一化查询意图
        query_normalized = normalize_intent(query)
        
        if self.indexer and self.indexer.vectorstore:
            # 使用向量检索
            results = self.indexer.search(query, top_k=self.config.top_k)
            
            for entry, score in results:
                # 计算加权相似度
                weighted_score = self._compute_weighted_score(
                    query_normalized, entry, score
                )
                
                # 获取完整记录
                full_record = self.storage.get_record(entry.get("id", ""))
                if not full_record:
                    continue
                
                # 构建检索结果
                search_result = SearchResult(
                    record_id=entry.get("id", ""),
                    intent=entry.get("intent", ""),
                    normalized_intent=entry.get("normalized_intent", ""),
                    status=entry.get("status", ""),
                    score=weighted_score,
                    apis_used=entry.get("apis_used", []),
                    script_content=full_record.script_content,
                    execution_output=full_record.execution_output,
                    error_type=full_record.error_type,
                    error_message=full_record.error_message,
                    intent_params=full_record.intent_params,
                )
                
                # 分层
                if weighted_score >= self.config.exact_threshold:
                    exact_matches.append(search_result)
                elif weighted_score >= self.config.high_threshold:
                    high_similar.append(search_result)
                elif weighted_score >= self.config.low_threshold:
                    low_similar.append(search_result)
        else:
            # 回退到简单关键词匹配
            all_records = self.storage.get_all_records()
            for entry in all_records:
                # 简单的字符串匹配分数
                score = self._simple_match_score(query_normalized.core_intent, entry)
                if score < self.config.low_threshold:
                    continue
                
                full_record = self.storage.get_record(entry.get("id", ""))
                if not full_record:
                    continue
                
                search_result = SearchResult(
                    record_id=entry.get("id", ""),
                    intent=entry.get("intent", ""),
                    normalized_intent=entry.get("normalized_intent", ""),
                    status=entry.get("status", ""),
                    score=score,
                    apis_used=entry.get("apis_used", []),
                    script_content=full_record.script_content,
                    execution_output=full_record.execution_output,
                    error_type=full_record.error_type,
                    error_message=full_record.error_message,
                    intent_params=full_record.intent_params,
                )
                
                if score >= self.config.exact_threshold:
                    exact_matches.append(search_result)
                elif score >= self.config.high_threshold:
                    high_similar.append(search_result)
                else:
                    low_similar.append(search_result)
        
        # 排序并限制数量
        exact_matches.sort(key=lambda x: -x.score)
        high_similar.sort(key=lambda x: -x.score)
        low_similar.sort(key=lambda x: -x.score)
        
        return TieredSearchResults(
            exact_matches=exact_matches[:self.config.max_exact_results],
            high_similar=high_similar[:self.config.max_high_results],
            low_similar=low_similar[:self.config.max_low_results],
        )
    
    def _compute_weighted_score(
        self,
        query_normalized: NormalizedIntent,
        entry: Dict[str, Any],
        semantic_score: float,
    ) -> float:
        """
        计算加权相似度分数
        
        Args:
            query_normalized: 归一化后的查询意图
            entry: 历史记录索引
            semantic_score: 语义相似度分数
        
        Returns:
            加权后的分数
        """
        # 1. 语义相似度（来自向量检索）
        semantic_sim = semantic_score
        
        # 2. API 重合度（Jaccard 系数）
        # 注意：这里无法预知查询会使用什么 API，所以简化处理
        api_sim = 0.0
        
        # 3. 关键词匹配
        keyword_sim = self._keyword_overlap(
            query_normalized.core_intent,
            entry.get("normalized_intent", "")
        )
        
        # 加权计算
        weighted = (
            self.config.weight_semantic * semantic_sim +
            self.config.weight_api * api_sim +
            self.config.weight_keyword * keyword_sim
        )
        
        return weighted
    
    def _simple_match_score(self, query: str, entry: Dict[str, Any]) -> float:
        """简单匹配分数（用于无向量索引时的回退）"""
        entry_intent = entry.get("normalized_intent", "")
        
        # 完全匹配
        if query == entry_intent:
            return 1.0
        
        # 包含关系
        if query in entry_intent or entry_intent in query:
            overlap = min(len(query), len(entry_intent)) / max(len(query), len(entry_intent))
            return 0.7 + 0.3 * overlap
        
        # 关键词匹配
        return self._keyword_overlap(query, entry_intent)
    
    def _keyword_overlap(self, text1: str, text2: str) -> float:
        """计算关键词重叠率"""
        # 简单分词（按字符）
        chars1 = set(text1)
        chars2 = set(text2)
        
        if not chars1 or not chars2:
            return 0.0
        
        intersection = len(chars1 & chars2)
        union = len(chars1 | chars2)
        
        return intersection / union if union > 0 else 0.0


# ==================== 上下文构建 ====================

def build_history_context(
    query: str,
    search_results: TieredSearchResults,
) -> str:
    """
    根据分层检索结果构建 LLM 上下文
    
    Args:
        query: 用户查询意图
        search_results: 分层检索结果
    
    Returns:
        LLM 上下文文本
    """
    context_parts = []
    query_normalized = normalize_intent(query)
    
    # 精确匹配：直接复用提示
    if search_results.exact_matches:
        best = search_results.exact_matches[0]
        if best.status == "success":
            # 计算参数替换
            new_params = {
                "limit": query_normalized.limit,
                "page": query_normalized.page,
                "page_size": query_normalized.page_size,
            }
            
            # 替换参数后的脚本
            substituted_script = substitute_params(
                best.script_content,
                best.intent_params or {},
                {k: v for k, v in new_params.items() if v is not None}
            )
            
            context_parts.append(f"""
## 🟢 发现精确匹配的历史成功记录（相似度 {best.score:.2f}）

**历史意图**: {best.intent}
**使用的 API**: {', '.join(best.apis_used)}

可直接复用以下脚本（已自动替换参数）:

```python
{substituted_script}
```

**执行结果**: {best.execution_output[:200] if best.execution_output else '无'}
""")
        else:
            # 精确匹配但是失败记录
            context_parts.append(f"""
## ⚠️ 发现精确匹配的历史失败记录（相似度 {best.score:.2f}）

**历史意图**: {best.intent}
**错误类型**: {best.error_type}
**错误原因**: {best.error_message}

请避免同样的错误！
""")
    
    # 高度相似：主要参考
    success_high = [r for r in search_results.high_similar if r.status == "success"]
    failed_high = [r for r in search_results.high_similar if r.status != "success"]
    
    if success_high:
        context_parts.append("## 🟡 高度相似的历史成功记录（可作为主要参考）\n")
        for r in success_high:
            context_parts.append(f"""
### 成功案例（相似度 {r.score:.2f}）
- **历史意图**: {r.intent}
- **使用的 API**: {', '.join(r.apis_used)}
- **参考脚本片段**:
```python
{r.script_content[:800]}
```
""")
    
    if failed_high:
        context_parts.append("## ⚠️ 高度相似的历史失败记录（请避免同样的错误）\n")
        for r in failed_high:
            context_parts.append(f"""
### 失败案例（相似度 {r.score:.2f}）
- **历史意图**: {r.intent}
- **错误类型**: {r.error_type}
- **错误原因**: {r.error_message}
""")
    
    # 一般相似：辅助参考（仅在没有更好匹配时）
    if search_results.low_similar and not search_results.exact_matches and not search_results.high_similar:
        context_parts.append("## 🟠 相关的历史记录（仅供参考思路）\n")
        for r in search_results.low_similar:
            status_icon = "✓" if r.status == "success" else "✗"
            context_parts.append(f"- {status_icon} {r.intent}（相似度 {r.score:.2f}）")
    
    return "\n".join(context_parts)
