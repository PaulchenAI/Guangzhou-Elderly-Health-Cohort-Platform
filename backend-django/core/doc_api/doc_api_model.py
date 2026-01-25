#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Doc API Model - 文档 API 数据模型

定义调用历史等数据模型
"""
import uuid

from django.db import models


class DocApiInvokeLog(models.Model):
    """
    HIS 接口调用历史记录
    
    保存每次接口调用的请求参数、响应数据、耗时等信息
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )
    operation_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="接口操作 ID"
    )
    endpoint_name = models.CharField(
        max_length=200,
        verbose_name="接口名称"
    )
    method = models.CharField(
        max_length=10,
        verbose_name="HTTP 方法"
    )
    path = models.CharField(
        max_length=500,
        verbose_name="接口路径"
    )
    request_params = models.JSONField(
        default=dict,
        verbose_name="请求参数"
    )
    response_data = models.JSONField(
        default=dict,
        verbose_name="响应数据"
    )
    response_status = models.IntegerField(
        default=0,
        verbose_name="HTTP 状态码"
    )
    duration_ms = models.IntegerField(
        default=0,
        verbose_name="耗时（毫秒）"
    )
    success = models.BooleanField(
        default=False,
        verbose_name="是否成功"
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="错误信息"
    )
    user_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="调用用户 ID"
    )
    sys_create_datetime = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="创建时间"
    )
    
    class Meta:
        db_table = "doc_api_invoke_log"
        verbose_name = "接口调用日志"
        verbose_name_plural = "接口调用日志"
        ordering = ["-sys_create_datetime"]
    
    def __str__(self):
        return f"{self.operation_id} - {self.endpoint_name} ({self.sys_create_datetime})"
