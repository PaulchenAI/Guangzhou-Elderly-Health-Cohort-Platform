#!/usr/bin/env python
# -*- coding: utf-8 -*-
# time: 2024/12/19
# file: file_manager_api.py
# author: 臧成龙
# QQ: 939589097

import os
import mimetypes
from typing import List
from uuid import UUID

from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from django.db import transaction
from django.db.models import F
from ninja import Router, Query, File, Form
from ninja.files import UploadedFile
from ninja.pagination import paginate

from common.fu_crud import retrieve, dynamic_query, get_searchable_fields_response
from common.fu_pagination import MyPagination
from common.fu_schema import response_success, DynamicQueryResult, SearchableFieldsResult
from core.file_manager.file_manager_model import FileManager
from core.file_manager.file_manager_schema import (
    FileManagerSchemaOut,
    FileManagerFilters,
    CreateFolderSchemaIn,
    MoveItemsSchemaIn,
    RenameItemSchemaIn,
    BatchDeleteSchemaIn,
    FileStorageConfigSchema,
    FileManagerSimpleSchemaOut,
    FileManagerQueryIn,
    FILE_MANAGER_SEARCHABLE_FIELDS,
)
from core.file_manager.storage_backends import get_storage_backend

router = Router()


@router.post("/file_manager/upload", response=FileManagerSchemaOut, summary="上传文件")
def upload_file(
    request,
    file: UploadedFile = File(...),
    parent_id: str | None = Form(None),
    is_public: bool = Form(False),
):
    """上传文件"""
    # 获取父文件夹
    parent = None
    folder_path = ''
    if parent_id:
        parent = get_object_or_404(FileManager, id=parent_id, type='folder')
        folder_path = parent.path
    
    # 获取存储后端
    storage = get_storage_backend()
    
    # 计算文件信息
    file_ext = os.path.splitext(file.name)[1].lower()
    mime_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
    
    # 保存文件
    storage_path, url = storage.save(file, file.name, folder_path)
    
    # 计算MD5
    md5 = storage.calculate_md5(file)
    
    # 构建完整路径
    full_path = os.path.join(folder_path, file.name).replace('\\', '/')
    
    # 创建数据库记录
    file_obj = FileManager.objects.create(
        name=file.name,
        type='file',
        parent=parent,
        path=full_path,
        size=file.size,
        file_ext=file_ext,
        mime_type=mime_type,
        storage_type=storage.__class__.__name__.replace('StorageBackend', '').lower(),
        storage_path=storage_path,
        url=url,
        md5=md5,
        is_public=is_public,
        sys_creator_id=request.auth.id,
    )
    
    return file_obj


@router.post("/file_manager/folder", response=FileManagerSchemaOut, summary="创建文件夹")
def create_folder(request, data: CreateFolderSchemaIn):
    """创建文件夹"""
    # 获取父文件夹
    parent = None
    parent_path = ''
    if data.parent_id:
        parent = get_object_or_404(FileManager, id=data.parent_id, type='folder')
        parent_path = parent.path
    
    # 构建文件夹路径
    folder_path = os.path.join(parent_path, data.name).replace('\\', '/')
    
    # 检查同名文件夹
    if FileManager.objects.filter(
        parent=parent,
        name=data.name,
        type='folder'
    ).exists():
        return HttpResponse("同名文件夹已存在", status=422)
    
    # 创建文件夹
    folder = FileManager.objects.create(
        name=data.name,
        type='folder',
        parent=parent,
        path=folder_path,
        sys_creator_id=request.auth.id,
    )
    
    return folder


@router.get("/file_manager", response=List[FileManagerSchemaOut], summary="获取文件列表（分页）")
@paginate(MyPagination)
def list_files(request, filters: FileManagerFilters = Query(...)):
    """获取文件列表"""
    query_set = retrieve(request, FileManager, filters)

    if filters.parent_id is None:
        query_set = query_set.filter(parent_id=None)
    
    # 文件夹排在前面
    query_set = query_set.order_by('type', '-sys_create_datetime')
    
    return query_set


@router.get("/file_manager/tree", response=List[FileManagerSchemaOut], summary="获取文件夹树结构")
def get_folder_tree(request):
    """获取文件夹树结构"""
    folders = FileManager.objects.filter(type='folder').order_by('name')
    return folders


@router.put("/file_manager/{file_id}/rename", response=FileManagerSchemaOut, summary="重命名文件")
def rename_item(request, file_id: UUID, data: RenameItemSchemaIn):
    """重命名文件/文件夹"""
    item = get_object_or_404(FileManager, id=file_id)
    
    # 检查同级目录下是否有同名文件
    if FileManager.objects.filter(
        parent=item.parent,
        name=data.name,
        type=item.type
    ).exclude(id=file_id).exists():
        return HttpResponse("同名文件/文件夹已存在", status=400)
    
    # 更新名称和路径
    old_path = item.path
    if item.parent:
        new_path = os.path.join(item.parent.path, data.name).replace('\\', '/')
    else:
        new_path = data.name
    
    item.name = data.name
    item.path = new_path
    item.save()
    
    # 如果是文件夹，递归更新子项路径
    if item.type == 'folder':
        _update_children_paths(item, old_path, new_path)
    
    return item


@router.put("/file_manager/move", response=dict, summary="移动文件")
def move_items(request, data: MoveItemsSchemaIn):
    """移动文件/文件夹"""
    # 获取目标文件夹
    target_folder = None
    target_path = ''
    if data.target_folder_id:
        target_folder = get_object_or_404(
            FileManager, 
            id=data.target_folder_id, 
            type='folder'
        )
        target_path = target_folder.path
    
    # 移动文件
    with transaction.atomic():
        for item_id in data.ids:
            item = get_object_or_404(FileManager, id=item_id)
            
            # 不能移动到自己或子文件夹
            if item.type == 'folder' and target_folder:
                if _is_subfolder(target_folder, item):
                    continue
            
            # 检查目标文件夹是否有同名文件
            if FileManager.objects.filter(
                parent=target_folder,
                name=item.name,
                type=item.type
            ).exclude(id=item_id).exists():
                continue
            
            # 更新父文件夹和路径
            old_path = item.path
            item.parent = target_folder
            item.path = os.path.join(target_path, item.name).replace('\\', '/')
            item.save()
            
            # 如果是文件夹，递归更新子项路径
            if item.type == 'folder':
                _update_children_paths(item, old_path, item.path)
    
    return response_success()


@router.delete("/file_manager/{file_id}", summary="删除文件")
def delete_item(request, file_id: UUID):
    """删除文件/文件夹"""
    item = get_object_or_404(FileManager, id=file_id)
    
    # 如果是文件，删除实际文件
    if item.type == 'file':
        storage = get_storage_backend()
        storage.delete(item.storage_path)
    
    # 删除数据库记录（会级联删除子项）
    item.delete()
    
    return response_success()


@router.post("/file_manager/batch/delete", summary="批量删除文件")
def batch_delete(request, data: BatchDeleteSchemaIn):
    """批量删除文件/文件夹"""
    storage = get_storage_backend()
    
    with transaction.atomic():
        for item_id in data.ids:
            item = FileManager.objects.filter(id=item_id).first()
            if item:
                # 如果是文件，删除实际文件
                if item.type == 'file':
                    storage.delete(item.storage_path)
                # 删除数据库记录
                item.delete()
    
    return response_success()


@router.get("/file_manager/file_info/{id}", response=FileManagerSimpleSchemaOut, summary="获取文件信息")
def get_file_info(request, id: UUID):
    """获取文件信息"""
    return get_object_or_404(FileManager, id=id)

@router.get("/file_manager/file/download", auth=None, summary="下载文件")
def download_file(request, path: str = Query(...)):
    """下载文件"""
    # 查找文件记录
    file_obj = get_object_or_404(FileManager, storage_path=path, type='file')
    
    # 更新下载次数
    file_obj.download_count = F('download_count') + 1
    file_obj.save(update_fields=['download_count'])
    
    # 获取存储后端
    storage = get_storage_backend()
    
    # 如果是本地存储，直接返回文件
    if file_obj.storage_type == 'local':
        from django.conf import settings
        full_path = os.path.join(
            settings.BASE_DIR, 
            'media', 
            'file_manager', 
            path
        )
        return FileResponse(
            open(full_path, 'rb'),
            as_attachment=True,
            filename=file_obj.name
        )
    else:
        # 其他存储类型，重定向到实际URL
        return HttpResponse(status=302, headers={'Location': file_obj.url})


@router.get("/file_manager/storage/config", response=FileStorageConfigSchema, summary="获取存储配置")
def get_storage_config(request):
    """获取存储配置"""
    from django.conf import settings
    
    config = {
        'storage_type': getattr(settings, 'FILE_STORAGE_TYPE', 'local'),
        'local_base_path': getattr(settings, 'FILE_STORAGE_LOCAL_PATH', None),
    }
    
    # 只返回当前使用的存储类型配置
    return config


@router.put("/file_manager/storage/config", response=dict, summary="更新存储配置")
def update_storage_config(request, data: FileStorageConfigSchema):
    """更新存储配置（需要管理员权限）"""
    # TODO: 实现配置更新逻辑，可能需要保存到数据库或配置文件
    return response_success()


def _is_subfolder(folder: FileManager, potential_parent: FileManager) -> bool:
    """检查folder是否是potential_parent的子文件夹"""
    current = folder
    while current.parent:
        if current.parent_id == potential_parent.id:
            return True
        current = current.parent
    return False


def _update_children_paths(folder: FileManager, old_path: str, new_path: str):
    """递归更新子项路径"""
    children = folder.children.all()
    for child in children:
        child.path = child.path.replace(old_path, new_path, 1)
        child.save()
        if child.type == 'folder':
            _update_children_paths(child, old_path, new_path)


@router.get("/file_manager/url/{file_id}", auth=None, summary="获取文件访问URL")
def get_file_url(request, file_id: UUID):
    """通过文件ID获取文件访问URL"""
    file_obj = get_object_or_404(FileManager, id=file_id, type='file')
    
    # Minio存储，返回临时URL
    if file_obj.storage_type == 'minio':
        storage = get_storage_backend()
        if hasattr(storage, 'get_presigned_url'):
            try:
                temp_url = storage.get_presigned_url(file_obj.storage_path)
                return {'url': temp_url}
            except Exception:
                # 如果获取临时URL失败，返回直接URL
                pass

    # 如果文件有直接的URL（云存储）
    if file_obj.url:
        return response_success(data={'url': file_obj.url})
    
    # 本地存储，构建访问URL
    if file_obj.storage_type == 'local':
        from django.conf import settings
        # 构建本地文件的访问URL
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        file_url = f"{base_url}/api/system/file_manager/download?path={file_obj.storage_path}"
        return response_success(data={'url': file_url})
    
    # 其他情况返回存储路径
    return response_success(data={'url': file_obj.storage_path})


@router.get("/file_manager/batch/urls", auth=None, summary="批量获取文件URL")
def get_batch_file_urls(request, ids: str = Query(...)):
    """批量获取文件访问URL"""
    file_ids = [UUID(id_str.strip()) for id_str in ids.split(',') if id_str.strip()]
    
    files = FileManager.objects.filter(id__in=file_ids, type='file')
    
    # 获取存储后端（用于Minio临时URL）
    storage = get_storage_backend()
    has_presigned_method = hasattr(storage, 'get_presigned_url')

    result = {}
    for file_obj in files:
        # Minio存储，返回临时URL
        if file_obj.storage_type == 'minio' and has_presigned_method:
            try:
                temp_url = storage.get_presigned_url(file_obj.storage_path)
                result[str(file_obj.id)] = temp_url
                continue
            except Exception:
                # 如果获取临时URL失败，继续使用其他方式
                pass

        if file_obj.url:
            result[str(file_obj.id)] = file_obj.url
        elif file_obj.storage_type == 'local':
            from django.conf import settings
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            file_url = f"{base_url}/api/system/file_manager/download?path={file_obj.storage_path}"
            result[str(file_obj.id)] = file_url
        else:
            result[str(file_obj.id)] = file_obj.storage_path
    
    return result


@router.get("/file_manager/stream/{file_id}", summary="流式传输文件")
def stream_file(request, file_id: UUID):
    """通过后端流式传输文件（支持所有存储类型）"""
    file_obj = get_object_or_404(FileManager, id=file_id, type='file')

    # 更新下载次数
    file_obj.download_count = F('download_count') + 1
    file_obj.save(update_fields=['download_count'])

    # 获取存储后端
    storage = get_storage_backend()

    try:
        if file_obj.storage_type == 'local':
            # 本地存储直接读取文件
            full_path = os.path.join(
                storage.base_path,
                file_obj.storage_path
            )
            if not os.path.exists(full_path):
                return HttpResponse("文件不存在", status=404)

            response = FileResponse(
                open(full_path, 'rb'),
                content_type=file_obj.mime_type or 'application/octet-stream'
            )

        elif file_obj.storage_type == 'minio' and hasattr(storage, 'get_file_content'):
            # Minio存储，通过后端转发
            try:
                file_response = storage.get_file_content(file_obj.storage_path)

                # 创建流式响应
                response = HttpResponse(
                    file_response.data,
                    content_type=file_obj.mime_type or 'application/octet-stream'
                )
                response['Content-Length'] = file_obj.size

            except Exception as e:
                return HttpResponse(f"获取文件失败: {str(e)}", status=500)

        else:
            # 其他存储类型，重定向到原URL
            if file_obj.url:
                return HttpResponse(status=302, headers={'Location': file_obj.url})
            else:
                return HttpResponse("不支持的存储类型", status=400)

        # 设置文件下载相关的响应头
        response['Content-Disposition'] = f'inline; filename*=UTF-8\'\'{file_obj.name}'
        response['Cache-Control'] = 'public, max-age=3600'  # 缓存1小时
        response['ETag'] = f'"{file_obj.md5}"'

        return response

    except Exception as e:
        return HttpResponse(f"文件传输失败: {str(e)}", status=500)


@router.get("/file_manager/proxy/{file_id}", auth=None, summary="代理文件访问")
def proxy_file(request, file_id: UUID, download: bool = Query(False)):
    """代理文件访问（强制通过后端转发，支持断点续传）"""
    file_obj = get_object_or_404(FileManager, id=file_id, type='file')

    # 更新下载次数
    file_obj.download_count = F('download_count') + 1
    file_obj.save(update_fields=['download_count'])

    # 获取存储后端
    storage = get_storage_backend()

    # 处理Range请求（断点续传）
    range_header = request.META.get('HTTP_RANGE')
    start = 0
    end = file_obj.size - 1

    if range_header:
        # 解析Range头
        range_match = range_header.replace('bytes=', '').split('-')
        if len(range_match) == 2:
            if range_match[0]:
                start = int(range_match[0])
            if range_match[1]:
                end = int(range_match[1])

    try:
        if file_obj.storage_type == 'local':
            # 本地文件处理
            full_path = os.path.join(storage.base_path, file_obj.storage_path)
            if not os.path.exists(full_path):
                return HttpResponse("文件不存在", status=404)

            # 创建范围响应
            with open(full_path, 'rb') as f:
                f.seek(start)
                chunk_size = min(8192, end - start + 1)
                content = f.read(chunk_size)

                if range_header:
                    response = HttpResponse(
                        content,
                        status=206,  # Partial Content
                        content_type=file_obj.mime_type or 'application/octet-stream'
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_obj.size}'
                    response['Accept-Ranges'] = 'bytes'
                else:
                    response = HttpResponse(
                        content,
                        content_type=file_obj.mime_type or 'application/octet-stream'
                    )

        elif file_obj.storage_type == 'minio' and hasattr(storage, 'get_file_content'):
            # Minio存储处理
            try:
                if range_header:
                    # 对于范围请求，可以考虑使用预签名URL重定向
                    # 或者获取完整文件后切片（适用于小文件）
                    file_response = storage.get_file_content(file_obj.storage_path)
                    file_data = file_response.read()

                    content = file_data[start:end+1]
                    response = HttpResponse(
                        content,
                        status=206,
                        content_type=file_obj.mime_type or 'application/octet-stream'
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_obj.size}'
                    response['Accept-Ranges'] = 'bytes'
                else:
                    # 完整文件
                    file_response = storage.get_file_content(file_obj.storage_path)
                    response = HttpResponse(
                        file_response.data,
                        content_type=file_obj.mime_type or 'application/octet-stream'
                    )

            except Exception as e:
                return HttpResponse(f"获取文件失败: {str(e)}", status=500)

        else:
            # 其他存储类型重定向
            if file_obj.url:
                return HttpResponse(status=302, headers={'Location': file_obj.url})
            else:
                return HttpResponse("不支持的存储类型", status=400)

        # 设置响应头
        if download:
            response['Content-Disposition'] = f'attachment; filename*=UTF-8\'\'{file_obj.name}'
        else:
            response['Content-Disposition'] = f'inline; filename*=UTF-8\'\'{file_obj.name}'

        response['Content-Length'] = len(response.content)
        response['Cache-Control'] = 'public, max-age=3600'
        response['ETag'] = f'"{file_obj.md5}"'
        response['Last-Modified'] = file_obj.sys_create_datetime.strftime('%a, %d %b %Y %H:%M:%S GMT')

        return response

    except Exception as e:
        return HttpResponse(f"文件传输失败: {str(e)}", status=500)


# =============================================================================
# 动态查询接口
# =============================================================================

@router.post("/file/query", response=DynamicQueryResult, tags=["文件管理"], summary="动态查询文件")
def query_file(request, data: FileManagerQueryIn):
    """
    动态查询文件数据
    
    支持灵活的过滤条件和操作符选择。
    
    支持的操作符: eq, ne, gt, gte, lt, lte, like, in, between
    
    AI 调用建议: 先调用 /file/searchable-fields 获取可搜索字段列表。
    """
    base_queryset = FileManager.objects.filter(is_deleted=False)
    
    items, total = dynamic_query(
        model=FileManager,
        filters=data.filters,
        searchable_fields=FILE_MANAGER_SEARCHABLE_FIELDS,
        page=data.page,
        page_size=data.page_size,
        order_by=data.order_by or "-sys_create_datetime",
        base_queryset=base_queryset
    )
    
    result_items = [FileManagerSchemaOut.from_orm(item) for item in items]
    
    return DynamicQueryResult(
        items=result_items,
        total=total,
        page=data.page,
        page_size=data.page_size
    )


@router.get("/file/searchable-fields", response=SearchableFieldsResult, tags=["文件管理"], summary="获取文件可搜索字段")
def get_file_searchable_fields(request):
    """
    获取文件管理模块的可搜索字段列表
    
    AI 调用建议: 在生成带过滤条件的查询脚本前，先调用此接口获取可用的过滤字段。
    """
    return get_searchable_fields_response(
        module="file_manager",
        display_name="文件管理",
        searchable_fields=FILE_MANAGER_SEARCHABLE_FIELDS
    )
