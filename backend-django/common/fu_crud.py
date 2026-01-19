#!/usr/bin/env python
# -*- coding: utf-8 -*-
# time: 1/24/2024 9:38 AM
# file: fu_crud.py
# author: 臧成龙
# QQ: 939589097
import os
import uuid
from datetime import datetime
from typing import Any, Type, List, Tuple, Optional, Dict

import openpyxl
from django.db.models import Model, QuerySet
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from ninja import Schema
from ninja.errors import HttpError
from openpyxl.reader.excel import load_workbook

from application.settings import BASE_DIR, STATIC_URL
from common.fu_auth import get_user_by_token
from common.fu_schema import FuFilters, FilterCondition, ALLOWED_OPERATORS
from urllib.parse import unquote

from common.utils.excel_utils import dict_to_excel
# from system.user.user_model import User
# from system.user.user_schema import UserSchemaGetNameIn


class ImportSchema(Schema):
    path: str


# bach create
def batch_create(request, list_data: list[dict], model: Type[Model]) -> int:
    list_subject = model.objects.bulk_create([model(**item) for item in list_data])
    count = len(list_subject)
    return count


def create(request, data: dict | Schema, model: Type[Model]) -> QuerySet:
    user_info = request.auth
    if not isinstance(data, dict):
        data = data.dict()
    data["sys_creator_id"] = user_info.id
    query_set = model.objects.create(**data)
    if isinstance(query_set.id, uuid.UUID):
        query_set.id = str(query_set.id)
    return query_set


def delete(id: str, model: Type[Model]) -> Type[Model]:
    instance = get_object_or_404(model, id=id)
    instance.delete()
    instance.id = id
    return instance


def batch_delete(ids: list[str], model: Type[Model]) -> int:
    count = model.objects.filter(id__in=ids).delete()[0]
    return count


def update(request, id: str, data: dict | Schema, model: Type[Model]) -> Type[Model]:
    user_info = request.auth
    if not isinstance(data, dict):
        data = data.dict(exclude_none=True)
    # data["sys_modifier"] = user_info.id
    instance = get_object_or_404(model, id=id)
    for attr, value in data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance


def retrieve(request, model: Type[Model], filters: FuFilters = FuFilters()) -> QuerySet:
    query_set = model.objects.all()
    if filters is not None:
        # 将filters空字符串转换为None
        for attr, value in filters.dict().items():
            if getattr(filters, attr) == '':
                setattr(filters, attr, None)
        query_set = filters.filter(query_set)
    return query_set


def get_or_none(model: Type[Model], *args, **kwargs):
    try:
        return model.objects.get(*args, **kwargs)
    except model.DoesNotExist:
        return None


def export_data(request, model, scheme, export_fields):
    """
    导出数据为Excel文件。

    参数:
    - request: HttpRequest对象，表示客户端请求。
    - model: Django模型类，指定要导出数据的模型。
    - scheme: 表示数据转换规则的对象，用于将ORM对象转换为字典。
    - export_fields: 包含要导出的字段名的列表。

    返回值:
    - FileResponse对象，提供下载Excel文件。
    """

    title_dict = {}
    # 根据export_fields列表获取字段的显示名称
    for field in export_fields:
        field_obj = getattr(model, field).field
        title_dict[field] = field_obj.help_text

    qs = retrieve(request, model)
    list_data = []
    # 将查询集中的每一项转换为指定格式的字典
    for qs_item in qs:
        qs_item = scheme.from_orm(qs_item)
        dict_data = {}
        for item, value in title_dict.items():
            dict_data[value] = getattr(qs_item, item)
        list_data.append(dict_data)

    file_url = dict_to_excel(list_data)
    # 返回供下载的文件响应
    return FileResponse(open(file_url, "rb"), as_attachment=True)


def import_data(request, model, scheme, data, import_fields):
    """
    导入数据到指定模型

    参数:
    - request: HttpRequest对象，表示客户端请求
    - model: Django模型类，数据将被导入到这个模型
    - scheme: 一个函数，用于根据给定的数据字典创建模型实例
    - data: 包含要导入文件信息的对象，比如上传的Excel文件
    - import_fields: 一个列表，指定模型中需要导入的字段名

    返回值:
    - FuResponse对象，包含导入结果的消息
    """
    title_dict = {}  # 字段名与Excel列对应的字典
    for field in import_fields:
        field_obj = getattr(model, field).field
        title_dict[field_obj.help_text] = field_obj.column
    # 文件路径处理
    file_path = str(BASE_DIR) + '/' + unquote(data.path)
    # 加载Excel工作簿
    wb = load_workbook(file_path)
    ws = wb.active  # 获取活动工作表
    title_value = []
    for index_row, row in enumerate(ws.values):
        if index_row == 0:
            title_value = row  # 读取Excel表头
        else:
            dict_data = {}  # 存储每一行数据转换后的字典
            for index, cell in enumerate(row):
                title_cell = title_value[index]
                value = title_dict.get(title_cell)  # 根据表头查找对应字段
                if value is not None:
                    dict_data[value] = cell
            print(dict_data)  # 打印处理后的数据，用于调试
            data = scheme(**dict_data)  # 根据处理后的字典创建模型实例
            create(request, data, model)  # 在数据库中创建模型实例
    return {"msg": "导入成功"}  # 返回成功消息


# =============================================================================
# 动态查询相关函数
# =============================================================================

def validate_operator(operator: str) -> str:
    """
    验证操作符是否支持
    
    Args:
        operator: 操作符
    
    Returns:
        验证通过的操作符
    
    Raises:
        HttpError: 操作符不支持
    """
    if operator not in ALLOWED_OPERATORS:
        supported_ops = ", ".join([f"{k}({v})" for k, v in ALLOWED_OPERATORS.items()])
        raise HttpError(400, f"不支持的操作符: {operator}。支持的操作符: {supported_ops}")
    return operator


def validate_field(field: str, searchable_fields: List[Dict]) -> Dict:
    """
    验证字段是否可搜索
    
    Args:
        field: 字段名
        searchable_fields: 可搜索字段列表
    
    Returns:
        字段配置信息
    
    Raises:
        HttpError: 字段不支持搜索
    """
    field_map = {f['name'].lower(): f for f in searchable_fields}
    if field.lower() not in field_map:
        available = [{"name": f['name'], "display_name": f.get('display_name', f['name'])} 
                     for f in searchable_fields]
        import json
        error_detail = json.dumps({
            "message": f"字段 {field} 不支持搜索",
            "available_fields": available
        }, ensure_ascii=False)
        raise HttpError(400, error_detail)
    return field_map[field.lower()]


def build_filter_kwargs(
    filters: Optional[List[FilterCondition]], 
    searchable_fields: List[Dict]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    构建 Django ORM 查询参数
    
    Args:
        filters: 过滤条件列表
        searchable_fields: 可搜索字段配置
    
    Returns:
        (filter_kwargs, exclude_kwargs) 用于 filter() 和 exclude() 的参数
    """
    filter_kwargs = {}
    exclude_kwargs = {}
    
    if not filters:
        return filter_kwargs, exclude_kwargs
    
    for condition in filters:
        field = condition.field
        operator = condition.operator
        value = condition.value
        
        # 验证字段和操作符
        validate_field(field, searchable_fields)
        validate_operator(operator)
        
        # 构建查询参数
        if operator == "eq":
            filter_kwargs[field] = value
        elif operator == "ne":
            exclude_kwargs[field] = value
        elif operator == "like":
            filter_kwargs[f"{field}__icontains"] = value
        elif operator == "gt":
            filter_kwargs[f"{field}__gt"] = value
        elif operator == "gte":
            filter_kwargs[f"{field}__gte"] = value
        elif operator == "lt":
            filter_kwargs[f"{field}__lt"] = value
        elif operator == "lte":
            filter_kwargs[f"{field}__lte"] = value
        elif operator == "in":
            if not isinstance(value, (list, tuple)):
                value = [value]
            filter_kwargs[f"{field}__in"] = value
        elif operator == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise HttpError(400, "BETWEEN 操作需要两个值")
            filter_kwargs[f"{field}__gte"] = value[0]
            filter_kwargs[f"{field}__lte"] = value[1]
    
    return filter_kwargs, exclude_kwargs


def dynamic_query(
    model: Type[Model],
    filters: Optional[List[FilterCondition]],
    searchable_fields: List[Dict],
    page: int = 1,
    page_size: int = 20,
    order_by: Optional[str] = None,
    base_queryset: Optional[QuerySet] = None
) -> Tuple[List[Model], int]:
    """
    通用动态查询函数
    
    Args:
        model: Django 模型类
        filters: 过滤条件列表
        searchable_fields: 可搜索字段配置
        page: 页码
        page_size: 每页数量
        order_by: 排序字段（如 "-create_datetime"）
        base_queryset: 基础查询集（可选，用于预过滤）
    
    Returns:
        (查询结果列表, 总数)
    """
    # 构建基础查询
    if base_queryset is not None:
        queryset = base_queryset
    else:
        queryset = model.objects.filter(is_deleted=False)
    
    # 应用过滤条件
    filter_kwargs, exclude_kwargs = build_filter_kwargs(filters, searchable_fields)
    
    if filter_kwargs:
        queryset = queryset.filter(**filter_kwargs)
    if exclude_kwargs:
        queryset = queryset.exclude(**exclude_kwargs)
    
    # 获取总数
    total = queryset.count()
    
    # 排序
    if order_by:
        queryset = queryset.order_by(order_by)
    
    # 分页
    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])
    
    return items, total


def get_searchable_fields_response(
    module: str,
    display_name: str,
    searchable_fields: List[Dict]
) -> Dict:
    """
    构建可搜索字段响应
    
    Args:
        module: 模块名称
        display_name: 模块显示名称
        searchable_fields: 可搜索字段配置
    
    Returns:
        响应字典
    """
    return {
        "module": module,
        "display_name": display_name,
        "searchable_fields": [
            {
                "name": f['name'],
                "display_name": f.get('display_name', f['name']),
                "type": f.get('type', 'string')
            }
            for f in searchable_fields
        ]
    }