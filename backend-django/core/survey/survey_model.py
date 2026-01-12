#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey Model - 问卷数据模型

包含：
- SurveySchemaConfig: 问卷 Schema 配置（缓存外部系统的问卷结构定义）
- SurveyRecord: 问卷数据记录（存储导入的问卷数据）
- SurveyImportLog: 问卷导入日志（记录导入批次和统计信息）
"""
from django.db import models
from common.fu_model import RootModel


class SurveySchemaConfig(RootModel):
    """
    问卷 Schema 配置模型 - 缓存外部系统的问卷结构定义
    
    用于存储从外部 API 同步的问卷 Schema，包括字段定义、评分规则等。
    """
    
    survey_type = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="问卷类型标识（如：fried、rockwood、gpm）"
    )
    survey_name = models.CharField(
        max_length=200,
        help_text="问卷名称"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="问卷描述"
    )
    schema_json = models.JSONField(
        default=dict,
        help_text="Schema 定义（字段、评分规则、解释说明等）"
    )
    guide_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="使用指南链接"
    )
    last_synced_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="最后同步时间"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="是否激活"
    )
    
    class Meta:
        db_table = "survey_schema_config"
        verbose_name = "问卷Schema配置"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-sys_create_datetime"]
    
    def __str__(self):
        return f"{self.survey_name} ({self.survey_type})"
    
    def get_fields(self):
        """获取字段定义列表"""
        return self.schema_json.get('fields', [])
    
    def get_searchable_fields(self):
        """获取可搜索字段列表"""
        fields = self.get_fields()
        return [f for f in fields if f.get('searchable', False)]
    
    def get_visible_fields(self):
        """获取可见字段列表"""
        fields = self.get_fields()
        return [f for f in fields if f.get('visible', True)]


class SurveyRecord(RootModel):
    """
    问卷数据记录模型 - 存储从外部系统导入的问卷数据
    
    使用 JSON 字段存储不同类型问卷的数据，通过 survey_type 区分问卷类型。
    """
    
    survey_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="问卷类型"
    )
    survey_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="外部系统问卷ID"
    )
    patient_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="患者姓名"
    )
    patient_info = models.JSONField(
        default=dict,
        help_text="患者基本信息（年龄、性别、身高、体重等）"
    )
    survey_data = models.JSONField(
        default=dict,
        help_text="问卷答案数据"
    )
    scores = models.JSONField(
        default=dict,
        help_text="评分结果"
    )
    record_time = models.DateTimeField(
        db_index=True,
        help_text="记录时间"
    )
    recorder_info = models.JSONField(
        default=dict,
        help_text="记录者信息（姓名、职位、机构等）"
    )
    external_created_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="外部系统创建时间"
    )
    raw_data = models.JSONField(
        default=dict,
        help_text="原始数据（完整的外部系统返回数据）"
    )
    
    class Meta:
        db_table = "survey_record"
        verbose_name = "问卷数据记录"
        verbose_name_plural = verbose_name
        ordering = ["-record_time", "-sys_create_datetime"]
        indexes = [
            models.Index(fields=['survey_type', 'record_time']),
            models.Index(fields=['patient_name', 'survey_type']),
            models.Index(fields=['survey_type', 'patient_name', 'record_time']),
        ]
    
    def __str__(self):
        return f"{self.survey_type} - {self.patient_name} ({self.survey_id})"


class SurveyImportLog(RootModel):
    """
    问卷导入日志模型 - 记录每次导入的批次信息和统计数据
    """
    
    TRIGGER_TYPE_CHOICES = [
        ('manual', '手动导入'),
        ('scheduled', '定时任务'),
    ]
    
    STATUS_CHOICES = [
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('partial', '部分成功'),
    ]
    
    batch_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="批次ID"
    )
    survey_type = models.CharField(
        max_length=100,
        db_index=True,
        blank=True,
        null=True,
        help_text="问卷类型（为空表示导入所有类型）"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running',
        db_index=True,
        help_text="导入状态"
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_TYPE_CHOICES,
        default='manual',
        help_text="触发类型"
    )
    total_count = models.IntegerField(
        default=0,
        help_text="总数量"
    )
    success_count = models.IntegerField(
        default=0,
        help_text="成功数量"
    )
    skip_count = models.IntegerField(
        default=0,
        help_text="跳过数量（已存在）"
    )
    fail_count = models.IntegerField(
        default=0,
        help_text="失败数量"
    )
    error_details = models.JSONField(
        default=list,
        help_text="错误详情列表"
    )
    start_time = models.DateTimeField(
        help_text="开始时间"
    )
    end_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="结束时间"
    )
    duration_seconds = models.FloatField(
        blank=True,
        null=True,
        help_text="耗时（秒）"
    )
    
    class Meta:
        db_table = "survey_import_log"
        verbose_name = "问卷导入日志"
        verbose_name_plural = verbose_name
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=['batch_id', 'survey_type']),
            models.Index(fields=['status', 'start_time']),
        ]
    
    def __str__(self):
        return f"批次 {self.batch_id} - {self.get_status_display()}"

