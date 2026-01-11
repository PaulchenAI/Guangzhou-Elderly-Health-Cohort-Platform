#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Query Model - 表查询模型
用于存储表查询配置和操作日志
"""
from django.db import models
from common.fu_model import RootModel


class TableQueryConfig(RootModel):
    """
    表查询配置模型 - 存储可查询表的配置信息
    
    配置内容（config_json）包含：
    - fields: 字段配置列表
    - default_page_size: 默认分页大小
    - max_page_size: 最大分页大小
    - default_order_by: 默认排序
    - allowed_operations: 允许的操作（query/export）
    """
    
    table_name = models.CharField(
        max_length=100, 
        unique=True,
        db_index=True,
        help_text="数据库表名"
    )
    display_name = models.CharField(
        max_length=200, 
        help_text="显示名称"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="表描述"
    )
    config_json = models.JSONField(
        default=dict, 
        help_text="配置内容（JSON格式）"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="是否激活"
    )
    
    class Meta:
        db_table = "table_query_config"
        verbose_name = "表查询配置"
        verbose_name_plural = verbose_name
        ordering = ["-sort", "-sys_create_datetime"]

    def __str__(self):
        return f"{self.display_name} ({self.table_name})"
    
    def get_visible_fields(self):
        """获取可见字段列表"""
        fields = self.config_json.get('fields', [])
        return [f['name'] for f in fields if f.get('visible', True)]
    
    def get_searchable_fields(self):
        """获取可搜索字段列表"""
        fields = self.config_json.get('fields', [])
        return [f['name'] for f in fields if f.get('searchable', False)]
    
    def get_sortable_fields(self):
        """获取可排序字段列表"""
        fields = self.config_json.get('fields', [])
        return [f['name'] for f in fields if f.get('sortable', False)]
    
    def get_field_config(self, field_name):
        """获取指定字段的配置"""
        fields = self.config_json.get('fields', [])
        for f in fields:
            if f['name'] == field_name:
                return f
        return None


class TableQueryLog(RootModel):
    """
    表查询日志模型 - 记录查询和导出操作
    用于安全审计和使用统计
    """
    
    OPERATION_CHOICES = [
        ("query", "查询"),
        ("export", "导出"),
    ]
    
    user_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="操作用户ID"
    )
    table_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="查询的表名"
    )
    operation = models.CharField(
        max_length=20, 
        choices=OPERATION_CHOICES,
        db_index=True,
        help_text="操作类型"
    )
    filters = models.JSONField(
        default=dict, 
        help_text="查询条件"
    )
    record_count = models.IntegerField(
        default=0, 
        help_text="返回/导出记录数"
    )
    execution_time = models.FloatField(
        default=0,
        help_text="执行时间（毫秒）"
    )
    
    class Meta:
        db_table = "table_query_log"
        verbose_name = "表查询日志"
        verbose_name_plural = verbose_name
        ordering = ["-sys_create_datetime"]
        indexes = [
            models.Index(fields=['user_id', 'table_name']),
            models.Index(fields=['operation', 'sys_create_datetime']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.table_name} ({self.operation})"

