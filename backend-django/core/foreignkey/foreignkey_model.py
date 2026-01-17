# -*- coding: utf-8 -*-
"""
外键关系元数据模型

映射现有的 table_foreignkey_metadata 表，使用 managed = False 避免 Django 迁移干扰。
"""
from django.db import models


class ForeignKeyMetadata(models.Model):
    """
    外键关系元数据模型
    
    映射通过 import_foreignkey_metadata 命令创建的 table_foreignkey_metadata 表。
    存储了从 Oracle SQL 文件中提取的外键关系信息。
    
    字段说明:
    - source_table: 源表名（带前缀，如 gzlry_BS_STAFF）
    - source_columns: 源字段列表（JSON 数组）
    - target_table: 目标表名（带前缀，如 gzlry_BS_DEPARTMENT）
    - target_columns: 目标字段列表（JSON 数组）
    - constraint_name: 外键约束名（带前缀）
    - on_delete: 删除规则（cascade/set_null/restrict/no_action）
    - source_file: 来源 JSON 文件名
    - created_at: 创建时间
    """
    
    id = models.AutoField(
        primary_key=True,
        help_text="主键ID"
    )
    
    source_table = models.CharField(
        max_length=128,
        help_text="源表名（带前缀）",
        db_index=True,
    )
    
    source_columns = models.JSONField(
        help_text="源字段列表（JSON 数组）"
    )
    
    target_table = models.CharField(
        max_length=128,
        help_text="目标表名（带前缀）",
        db_index=True,
    )
    
    target_columns = models.JSONField(
        help_text="目标字段列表（JSON 数组）"
    )
    
    constraint_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="约束名（带前缀）"
    )
    
    on_delete = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="删除规则：cascade/set_null/restrict/no_action"
    )
    
    source_file = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="来源 JSON 文件名"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="创建时间"
    )
    
    class Meta:
        managed = False  # 不由 Django 管理（表已存在）
        db_table = 'table_foreignkey_metadata'
        ordering = ['source_table', 'id']
        verbose_name = '外键关系元数据'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.source_table} -> {self.target_table}"
    
    def get_relation_display(self) -> str:
        """
        获取关系的可读显示
        
        返回格式：源表.源字段 -> 目标表.目标字段
        """
        source_cols = ', '.join(self.source_columns) if self.source_columns else ''
        target_cols = ', '.join(self.target_columns) if self.target_columns else ''
        return f"{self.source_table}({source_cols}) -> {self.target_table}({target_cols})"
