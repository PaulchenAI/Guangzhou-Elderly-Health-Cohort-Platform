# -*- coding: utf-8 -*-
"""
外键信息数据结构定义（Pydantic Schema）
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ForeignKey(BaseModel):
    """外键数据模型"""
    
    constraint_name: str = Field(..., description="约束名称")
    source_table: str = Field(..., description="源表名")
    source_columns: List[str] = Field(..., min_items=1, description="源字段列表")
    target_table: str = Field(..., description="目标表名")
    target_columns: List[str] = Field(..., min_items=1, description="目标字段列表")
    on_delete: Optional[str] = Field(None, description="删除规则")
    
    @validator('on_delete')
    def validate_on_delete(cls, v):
        """验证删除规则"""
        if v is not None:
            allowed_values = ['cascade', 'set_null', 'restrict', 'no_action']
            if v not in allowed_values:
                raise ValueError(f"on_delete 必须是以下值之一: {allowed_values}")
        return v
    
    @validator('source_columns', 'target_columns')
    def validate_columns_not_empty(cls, v):
        """验证字段列表不为空"""
        if len(v) == 0:
            raise ValueError("字段列表不能为空")
        return v
    
    @validator('target_columns')
    def validate_columns_length_match(cls, v, values):
        """验证源字段和目标字段数量一致"""
        if 'source_columns' in values and len(v) != len(values['source_columns']):
            raise ValueError(
                f"源字段数量({len(values['source_columns'])}) "
                f"和目标字段数量({len(v)})必须一致"
            )
        return v


class TableForeignKeys(BaseModel):
    """表的外键信息模型（按表存储）"""
    
    table_name: str = Field(..., description="表名")
    source_file: str = Field(..., description="源 SQL 文件名")
    extraction_strategy: Optional[str] = Field(None, description="使用的提取策略")
    strategy_fingerprint: Optional[str] = Field(None, description="格式指纹（LLM生成策略时）")
    foreign_keys: List[ForeignKey] = Field(default_factory=list, description="外键列表")
    extracted_at: datetime = Field(default_factory=datetime.now, description="提取时间")
    file_size_mb: Optional[float] = Field(None, description="文件大小（MB）")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UnifiedForeignKeys(BaseModel):
    """统一外键信息模型（统一存储）"""
    
    class Metadata(BaseModel):
        """元数据"""
        extracted_at: datetime = Field(default_factory=datetime.now)
        total_files: int = Field(0, description="总文件数")
        total_foreignkeys: int = Field(0, description="总外键数")
        tables_with_foreignkeys: int = Field(0, description="有外键的表数量")
        large_files_count: int = Field(0, description="大文件数量（>1MB）")
        strategy_stats: dict = Field(default_factory=dict, description="策略使用统计")
        llm_api_calls: int = Field(0, description="LLM API调用次数")
        estimated_cost_usd: float = Field(0.0, description="估算成本（USD）")
        
        class Config:
            json_encoders = {
                datetime: lambda v: v.isoformat()
            }
    
    metadata: Metadata = Field(default_factory=Metadata)
    foreignkeys: List[dict] = Field(default_factory=list, description="外键列表")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
