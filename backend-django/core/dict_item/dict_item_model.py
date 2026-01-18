#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dictionary Item Model - 字典项模型
用于管理字典中的各个选项
"""
from django.db import models
from common.fu_model import RootModel


class DictItem(RootModel):
    """系统字典项表"""
    
    icon = models.CharField(max_length=100, blank=True, null=True, help_text="ICON")
    label = models.CharField(
        max_length=100, blank=True, null=True, help_text="显示名称"
    )
    value = models.CharField(max_length=100, blank=True, null=True, help_text="实际值")
    status = models.BooleanField(default=True, blank=True, help_text="状态")
    dict = models.ForeignKey(
        to="Dict", db_constraint=False, on_delete=models.CASCADE, help_text="所属字典，关联 core_dict.id"
    )
    remark = models.CharField(max_length=2000, blank=True, null=True, help_text="备注")

    class Meta:
        db_table = "core_dict_item"
        ordering = ("-sys_create_datetime",)
    
    def __str__(self):
        return f"{self.label} ({self.value})"

