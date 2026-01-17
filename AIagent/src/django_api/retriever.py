# -*- coding: utf-8 -*-
"""
分层检索器

实现三层分层检索策略：
1. 关键词/Tag 快速过滤
2. 向量语义检索
3. 结果融合与排序
"""

import logging
import re
from typing import List, Optional, Dict, Set

from .models import APIEndpoint
from .indexer import APIEndpointIndexer

logger = logging.getLogger(__name__)


class HierarchicalRetriever:
    """
    分层检索器
    
    三层检索策略：
    1. 关键词/Tag 快速过滤（成本=0）
    2. 向量语义检索（成本=低）
    3. 结果融合与排序
    """
    
    def __init__(
        self,
        endpoints: Dict[str, APIEndpoint],
        indexer: Optional[APIEndpointIndexer] = None,
        keyword_filter_threshold: int = 20,
        top_k: int = 10,
        similarity_threshold: float = 0.5,
    ):
        """
        初始化分层检索器
        
        Args:
            endpoints: 所有端点字典 {operation_id: APIEndpoint}
            indexer: 向量索引器（可选，用于语义检索）
            keyword_filter_threshold: 关键词过滤后最多保留多少候选
            top_k: 最终返回结果数量
            similarity_threshold: 向量相似度阈值
        """
        self.endpoints = endpoints
        self.indexer = indexer
        self.keyword_filter_threshold = keyword_filter_threshold
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # 构建 tag 索引
        self._endpoints_by_tag: Dict[str, List[APIEndpoint]] = {}
        for ep in endpoints.values():
            for tag in ep.tags:
                tag_lower = tag.lower()
                if tag_lower not in self._endpoints_by_tag:
                    self._endpoints_by_tag[tag_lower] = []
                self._endpoints_by_tag[tag_lower].append(ep)
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_semantic: bool = True,
    ) -> List[APIEndpoint]:
        """
        分层检索 API 端点
        
        Args:
            query: 用户查询
            top_k: 返回结果数量（默认使用初始化时的配置）
            use_semantic: 是否使用语义检索
        
        Returns:
            最相关的端点列表
        """
        top_k = top_k or self.top_k
        
        # 第一层：关键词/Tag 快速过滤
        candidates = self._keyword_filter(query)
        logger.debug(f"关键词过滤后候选: {len(candidates)} 个")
        
        # 如果候选数量较少，直接返回
        if len(candidates) <= top_k:
            return candidates
        
        # 第二层：向量语义检索（如果启用且有索引）
        if use_semantic and self.indexer and self.indexer.vectorstore:
            semantic_results = self._semantic_search(query, candidates, top_k)
            if semantic_results:
                logger.debug(f"语义检索后: {len(semantic_results)} 个")
                return semantic_results
        
        # 回退：返回关键词过滤结果的前 top_k
        return candidates[:top_k]
    
    def _keyword_filter(self, query: str) -> List[APIEndpoint]:
        """
        第一层：关键词/Tag 快速过滤
        
        Args:
            query: 用户查询
        
        Returns:
            候选端点列表
        """
        query_lower = query.lower()
        
        # 提取查询中的关键词
        keywords = self._extract_keywords(query_lower)
        
        # 计算每个端点的匹配分数
        scored_endpoints: List[tuple[APIEndpoint, int]] = []
        
        for ep in self.endpoints.values():
            score = 0
            
            # 匹配 tag
            for tag in ep.tags:
                tag_lower = tag.lower()
                for kw in keywords:
                    if kw in tag_lower:
                        score += 3  # tag 匹配权重高
            
            # 匹配 operation_id
            for kw in keywords:
                if kw in ep.operation_id.lower():
                    score += 2
            
            # 匹配 summary
            for kw in keywords:
                if kw in ep.summary.lower():
                    score += 2
            
            # 匹配 path
            for kw in keywords:
                if kw in ep.path.lower():
                    score += 1
            
            # 匹配 description
            for kw in keywords:
                if kw in ep.description.lower():
                    score += 1
            
            if score > 0:
                scored_endpoints.append((ep, score))
        
        # 按分数排序
        scored_endpoints.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前 N 个候选
        candidates = [ep for ep, _ in scored_endpoints[:self.keyword_filter_threshold]]
        
        # 如果关键词过滤结果太少，补充一些默认端点
        if len(candidates) < self.keyword_filter_threshold // 2:
            # 补充所有端点（让语义检索有更多选择）
            remaining = [ep for ep in self.endpoints.values() if ep not in candidates]
            candidates.extend(remaining[:self.keyword_filter_threshold - len(candidates)])
        
        return candidates
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
        
        Returns:
            关键词集合
        """
        # 分词（简单实现，按空格和常见分隔符）
        words = re.split(r'[\s,，。.、/\\]+', text)
        
        # 过滤停用词和太短的词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '我', '你', '他', '她', '它',
                      '这', '那', '什么', '怎么', '如何', '帮我', '请', '查询', '获取', '看',
                      'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'to', 'of', 'for', 'in', 'on', 'at', 'by', 'with', 'and', 'or'}
        
        keywords = set()
        for word in words:
            word = word.strip().lower()
            if word and len(word) >= 2 and word not in stop_words:
                keywords.add(word)
        
        return keywords
    
    def _semantic_search(
        self,
        query: str,
        candidates: List[APIEndpoint],
        top_k: int,
    ) -> List[APIEndpoint]:
        """
        第二层：向量语义检索
        
        在候选集中进行语义检索
        
        Args:
            query: 用户查询
            candidates: 候选端点列表
            top_k: 返回数量
        
        Returns:
            语义最相关的端点列表
        """
        if not self.indexer:
            return candidates[:top_k]
        
        # 获取候选端点的 operation_id 集合
        candidate_ids = {ep.operation_id for ep in candidates}
        
        # 向量检索
        results = self.indexer.search(
            query,
            top_k=len(candidates),  # 检索所有候选
            score_threshold=self.similarity_threshold,
        )
        
        # 过滤：只保留在候选集中的端点
        filtered_results = [
            (ep, score) for ep, score in results
            if ep.operation_id in candidate_ids
        ]
        
        # 返回 top_k
        return [ep for ep, _ in filtered_results[:top_k]]
    
    def get_endpoints_by_tag(self, tag: str) -> List[APIEndpoint]:
        """
        根据 tag 获取端点
        
        Args:
            tag: tag 名称
        
        Returns:
            该 tag 下的端点列表
        """
        return self._endpoints_by_tag.get(tag.lower(), [])
    
    def get_all_tags(self) -> List[str]:
        """获取所有 tag"""
        return list(self._endpoints_by_tag.keys())
