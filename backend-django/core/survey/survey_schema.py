#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey Schema - 问卷数据 Pydantic Schema

用于 API 接口的数据校验和序列化
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import FilterSchema, Schema
from pydantic import Field


# =============================================================================
# Schema 配置相关
# =============================================================================

class SurveySchemaConfigSchemaOut(Schema):
    """问卷 Schema 配置输出"""
    id: str
    survey_type: str
    survey_name: str
    description: Optional[str] = None
    schema_json: Dict[str, Any] = Field(default={})
    guide_url: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    is_active: bool
    sort: int
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class SurveySchemaConfigFilters(FilterSchema):
    """问卷 Schema 配置过滤器"""
    survey_type: Optional[str] = Field(None, q='survey_type__icontains')
    survey_name: Optional[str] = Field(None, q='survey_name__icontains')
    is_active: Optional[bool] = None


# =============================================================================
# 问卷记录相关
# =============================================================================

class SurveyRecordSchemaOut(Schema):
    """问卷记录输出"""
    id: str
    survey_type: str
    survey_id: str
    patient_name: str
    patient_info: Dict[str, Any] = {}
    survey_data: Dict[str, Any] = {}
    scores: Dict[str, Any] = {}
    record_time: datetime
    recorder_info: Dict[str, Any] = {}
    external_created_at: Optional[datetime] = None
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None


class SurveyRecordFilters(FilterSchema):
    """问卷记录过滤器"""
    survey_type: Optional[str] = Field(None, q='survey_type')
    survey_id: Optional[str] = Field(None, q='survey_id__icontains')
    patient_name: Optional[str] = Field(None, q='patient_name__icontains')
    start_date: Optional[str] = Field(None, q='record_time__gte')
    end_date: Optional[str] = Field(None, q='record_time__lte')


# =============================================================================
# 导入日志相关
# =============================================================================

class SurveyImportLogSchemaOut(Schema):
    """导入日志输出"""
    id: str
    batch_id: str
    survey_type: Optional[str] = None
    status: str
    trigger_type: str
    total_count: int
    success_count: int
    skip_count: int
    fail_count: int
    error_details: List[Dict[str, Any]] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    sys_create_datetime: Optional[datetime] = None


class SurveyImportLogFilters(FilterSchema):
    """导入日志过滤器"""
    batch_id: Optional[str] = Field(None, q='batch_id__icontains')
    survey_type: Optional[str] = Field(None, q='survey_type')
    status: Optional[str] = None
    trigger_type: Optional[str] = None


# =============================================================================
# 查询请求相关
# =============================================================================

class SurveyQueryIn(Schema):
    """问卷查询请求"""
    schema_id: Optional[str] = Field(
        None, 
        description="Schema 配置 ID（精确匹配，优先级高于 survey_name）"
    )
    survey_name: Optional[str] = Field(
        None, 
        description="问卷名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="过滤条件")
    order_by: Optional[str] = Field(None, description="排序字段")


class SurveyQueryResult(Schema):
    """问卷查询结果"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


# =============================================================================
# 导出请求相关
# =============================================================================

class SurveyExportIn(Schema):
    """问卷导出请求"""
    schema_id: Optional[str] = Field(
        None, 
        description="Schema 配置 ID（精确匹配，优先级高于 survey_name）"
    )
    survey_name: Optional[str] = Field(
        None, 
        description="问卷名称（支持模糊匹配，AI 调用推荐使用此参数）"
    )
    format: str = Field("excel", description="导出格式: excel/csv")
    value_mode: str = Field("label", description="导出模式: label=文案, value=数值")
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="过滤条件")
    max_rows: int = Field(10000, ge=1, le=50000, description="最大导出行数")


# =============================================================================
# 同步/导入请求相关
# =============================================================================

class SyncSchemasResult(Schema):
    """Schema 同步结果"""
    created: int = Field(..., description="新增数量")
    updated: int = Field(..., description="更新数量")
    failed: int = Field(..., description="失败数量")
    details: List[Dict[str, Any]] = Field(default=[], description="详细信息")


class ImportDataResult(Schema):
    """数据导入结果"""
    batch_id: str = Field(..., description="批次ID")
    total: int = Field(..., description="总数量")
    success: int = Field(..., description="成功数量")
    skipped: int = Field(..., description="跳过数量")
    failed: int = Field(..., description="失败数量")
    errors: List[Dict[str, Any]] = Field(default=[], description="错误详情")


class SurveySyncIn(Schema):
    """手动同步数据请求"""
    incremental: bool = Field(True, description="是否增量同步（默认 True）")
    survey_type: Optional[str] = Field(None, description="问卷类型（为空则同步全部）")


class SurveySyncOut(Schema):
    """手动同步数据响应"""
    batch_id: str = Field(..., description="批次ID")
    total: int = Field(..., description="总处理数量")
    success: int = Field(..., description="成功数量")
    skipped: int = Field(..., description="跳过数量")
    failed: int = Field(..., description="失败数量")
    message: str = Field(..., description="结果消息")

