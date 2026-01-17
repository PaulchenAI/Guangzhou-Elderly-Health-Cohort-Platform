#!/usr/bin/env python
# -*- coding: utf-8 -*-
# file: chunk_upload_api.py
# 分块上传相关 API

import os
import hashlib
import mimetypes
import uuid
import shutil
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache
from ninja import Router, File, Form

from ninja.files import UploadedFile
from common.fu_schema import response_success
from core.file_manager.file_manager_model import FileManager
from core.file_manager.file_manager_schema import (
    FileManagerSchemaOut,
    InitChunkUploadSchemaIn,
    InitChunkUploadSchemaOut,
    UploadChunkSchemaOut,
    MergeChunksSchemaIn,
    ChunkUploadStatusSchemaOut,
)
from core.file_manager.storage_backends import get_storage_backend

router = Router()

# 分块上传临时目录
CHUNK_UPLOAD_DIR = os.path.join('media', 'chunk_uploads')
os.makedirs(CHUNK_UPLOAD_DIR, exist_ok=True)


def get_chunk_upload_key(upload_id: str) -> str:
    """获取分块上传的缓存键"""
    return f'chunk_upload:{upload_id}'


def get_chunk_dir(upload_id: str) -> str:
    """获取分块存储目录"""
    chunk_dir = os.path.join(CHUNK_UPLOAD_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)
    return chunk_dir


def get_chunk_path(upload_id: str, chunk_index: int) -> str:
    """获取分块文件路径"""
    return os.path.join(get_chunk_dir(upload_id), f'chunk_{chunk_index}')


@router.post("/chunk/init", response=InitChunkUploadSchemaOut, summary="初始化分块上传")
def init_chunk_upload(request, data: InitChunkUploadSchemaIn):
    """
    初始化分块上传（大文件上传第一步）
    
    **调用顺序**: 本接口 → /chunk/upload（循环） → /chunk/merge
    
    功能说明:
    - 检查文件是否已存在（秒传功能）
    - 生成 upload_id（后续接口需要）
    - 计算分块数量
    
    请求参数:
    - filename: 文件名
    - total_size: 文件总大小（字节）
    - chunk_size: 分块大小（建议 5MB = 5242880）
    - file_hash: 文件MD5（可选，用于秒传检测）
    - parent_id: 父文件夹ID（可选）
    
    返回值:
    - upload_id: 上传会话ID（后续 upload/merge 接口需要）
    - total_chunks: 总分块数
    - file_exists: 文件是否已存在（true 则无需上传）
    - file_id: 已存在文件的ID（仅当 file_exists=true）
    """
    # 检查文件是否已存在（秒传）
    if data.file_hash:
        existing_file = FileManager.objects.filter(
            md5=data.file_hash,
            size=data.total_size
        ).first()
        
        if existing_file:
            # 文件已存在，秒传
            return {
                'upload_id': str(uuid.uuid4()),
                'chunk_size': data.chunk_size,
                'total_chunks': 0,
                'uploaded_chunks': [],
                'file_exists': True,
                'file_id': existing_file.id,
            }
    
    # 生成上传ID
    upload_id = str(uuid.uuid4())
    
    # 计算总分块数
    total_chunks = (data.total_size + data.chunk_size - 1) // data.chunk_size
    
    # 在缓存中保存上传信息（7天过期）
    upload_info = {
        'upload_id': upload_id,
        'filename': data.filename,
        'total_size': data.total_size,
        'chunk_size': data.chunk_size,
        'total_chunks': total_chunks,
        'uploaded_chunks': [],
        'parent_id': str(data.parent_id) if data.parent_id else None,
        'is_public': data.is_public,
        'user_id': request.user.id,
        'created_at': datetime.now().isoformat(),
    }
    
    cache_key = get_chunk_upload_key(upload_id)
    cache.set(cache_key, upload_info, timeout=7 * 24 * 3600)  # 7天
    
    return {
        'upload_id': upload_id,
        'chunk_size': data.chunk_size,
        'total_chunks': total_chunks,
        'uploaded_chunks': [],
        'file_exists': False,
        'file_id': None,
    }


@router.post("/chunk/upload", response=UploadChunkSchemaOut, summary="上传分块")
def upload_chunk(
    request,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadedFile = File(...),
):
    """
    上传单个分块（大文件上传第二步，需循环调用）
    
    **前置条件**: 必须先调用 /chunk/init 获取 upload_id
    **后续操作**: 所有分块上传完成后调用 /chunk/merge
    
    请求参数（Form-Data）:
    - upload_id: 上传会话ID（来自 init 接口）
    - chunk_index: 分块索引（从 0 开始，到 total_chunks-1）
    - chunk: 分块文件数据
    
    返回值:
    - chunk_index: 当前分块索引
    - uploaded: 是否上传成功
    - total_uploaded: 已上传的分块数量
    """
    # 获取上传信息
    cache_key = get_chunk_upload_key(upload_id)
    upload_info = cache.get(cache_key)
    
    if not upload_info:
        return HttpResponse('上传会话不存在或已过期', status=404)
    
    # 验证分块索引
    if chunk_index < 0 or chunk_index >= upload_info['total_chunks']:
        return HttpResponse(f'无效的分块索引: {chunk_index}', status=400)
    
    # 保存分块文件
    chunk_path = get_chunk_path(upload_id, chunk_index)
    
    try:
        with open(chunk_path, 'wb') as f:
            for chunk_data in chunk.chunks():
                f.write(chunk_data)
        
        # 更新已上传分块列表
        if chunk_index not in upload_info['uploaded_chunks']:
            upload_info['uploaded_chunks'].append(chunk_index)
            upload_info['uploaded_chunks'].sort()
            cache.set(cache_key, upload_info, timeout=7 * 24 * 3600)
        
        return {
            'chunk_index': chunk_index,
            'uploaded': True,
        }
    
    except Exception as e:
        return HttpResponse(f'分块上传失败: {str(e)}', status=500)


@router.get("/chunk/status", response=ChunkUploadStatusSchemaOut, summary="获取分块上传状态")
def get_chunk_upload_status(request, upload_id: str):
    """
    获取分块上传状态（可选，用于断点续传）
    
    **使用场景**: 上传中断后，调用此接口获取已上传的分块，继续上传剩余分块
    
    请求参数:
    - upload_id: 上传会话ID
    
    返回值:
    - uploaded_chunks: 已上传的分块索引列表
    - total_chunks: 总分块数
    - completed: 是否全部上传完成
    """
    cache_key = get_chunk_upload_key(upload_id)
    upload_info = cache.get(cache_key)
    
    if not upload_info:
        return HttpResponse('上传会话不存在或已过期', status=404)
    
    completed = len(upload_info['uploaded_chunks']) == upload_info['total_chunks']
    
    return {
        'upload_id': upload_id,
        'filename': upload_info['filename'],
        'total_size': upload_info['total_size'],
        'total_chunks': upload_info['total_chunks'],
        'uploaded_chunks': upload_info['uploaded_chunks'],
        'completed': completed,
    }


@router.post("/chunk/merge", response=FileManagerSchemaOut, summary="合并分块文件")
def merge_chunks(request, data: MergeChunksSchemaIn):
    """
    合并分块文件（大文件上传最后一步）
    
    **前置条件**: 所有分块必须已通过 /chunk/upload 上传完成
    
    处理流程:
    - 验证所有分块已上传
    - 按顺序合并分块为完整文件
    - 计算文件 MD5 并检查秒传
    - 保存到存储后端（本地/MinIO）
    - 创建数据库记录
    - 清理临时分块文件
    
    请求参数:
    - upload_id: 上传会话ID（来自 init 接口）
    
    返回值:
    - 完整的文件信息（id, name, url 等）
    """
    upload_id = data.upload_id
    cache_key = get_chunk_upload_key(upload_id)
    upload_info = cache.get(cache_key)
    
    if not upload_info:
        return HttpResponse('上传会话不存在或已过期', status=404)
    
    # 验证所有分块已上传
    if len(upload_info['uploaded_chunks']) != upload_info['total_chunks']:
        missing_chunks = [
            i for i in range(upload_info['total_chunks']) 
            if i not in upload_info['uploaded_chunks']
        ]
        return HttpResponse(
            f'分块上传未完成，缺少分块: {missing_chunks}',
            status=400
        )
    
    try:
        # 获取父文件夹
        parent = None
        folder_path = ''
        if upload_info['parent_id']:
            parent = get_object_or_404(FileManager, id=upload_info['parent_id'], type='folder')
            folder_path = parent.path
        
        # 创建临时合并文件
        temp_merged_path = os.path.join(get_chunk_dir(upload_id), 'merged_file')
        md5_hash = hashlib.md5()
        
        # 按顺序合并分块
        with open(temp_merged_path, 'wb') as merged_file:
            for chunk_index in range(upload_info['total_chunks']):
                chunk_path = get_chunk_path(upload_id, chunk_index)
                
                if not os.path.exists(chunk_path):
                    return HttpResponse(f'分块 {chunk_index} 不存在', status=500)
                
                with open(chunk_path, 'rb') as chunk_file:
                    chunk_data = chunk_file.read()
                    merged_file.write(chunk_data)
                    md5_hash.update(chunk_data)
        
        # 计算MD5
        file_md5 = md5_hash.hexdigest()
        
        # 检查是否已存在相同文件（合并后的秒传检查）
        existing_file = FileManager.objects.filter(
            md5=file_md5,
            size=upload_info['total_size']
        ).first()
        
        if existing_file:
            # 清理临时文件
            shutil.rmtree(get_chunk_dir(upload_id), ignore_errors=True)
            cache.delete(cache_key)
            
            # 返回已存在的文件
            return existing_file
        
        # 获取存储后端
        storage = get_storage_backend()
        
        # 计算文件信息
        filename = upload_info['filename']
        file_ext = os.path.splitext(filename)[1].lower()
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # 保存到存储后端
        with open(temp_merged_path, 'rb') as merged_file:
            # 创建一个类似 UploadedFile 的对象
            class TempUploadedFile:
                def __init__(self, file_obj, name, size):
                    self.file = file_obj
                    self.name = name
                    self.size = size
                
                def chunks(self, chunk_size=64 * 1024):
                    self.file.seek(0)
                    while True:
                        chunk = self.file.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            
            temp_file = TempUploadedFile(merged_file, filename, upload_info['total_size'])
            storage_path, url = storage.save(temp_file, filename, folder_path)
        
        # 构建完整路径
        full_path = os.path.join(folder_path, filename).replace('\\', '/')
        
        # 创建数据库记录
        file_obj = FileManager.objects.create(
            name=filename,
            type='file',
            parent=parent,
            path=full_path,
            size=upload_info['total_size'],
            file_ext=file_ext,
            mime_type=mime_type,
            storage_type=storage.__class__.__name__.replace('StorageBackend', '').lower(),
            storage_path=storage_path,
            url=url,
            md5=file_md5,
            is_public=upload_info['is_public'],
            sys_creator_id=upload_info['user_id'],
        )
        
        # 清理临时文件
        shutil.rmtree(get_chunk_dir(upload_id), ignore_errors=True)
        cache.delete(cache_key)
        
        return file_obj
    
    except Exception as e:
        return HttpResponse(f'合并文件失败: {str(e)}', status=500)


@router.delete("/chunk/cancel", summary="取消分块上传")
def cancel_chunk_upload(request, upload_id: str):
    """
    取消分块上传（清理未完成的上传）
    
    **使用场景**: 用户取消上传或上传失败时，调用此接口清理临时数据
    
    处理流程:
    - 清理临时分块文件
    - 删除缓存中的上传会话信息
    
    请求参数:
    - upload_id: 上传会话ID
    """
    try:
        # 清理临时文件
        shutil.rmtree(get_chunk_dir(upload_id), ignore_errors=True)
        
        # 删除缓存
        cache_key = get_chunk_upload_key(upload_id)
        cache.delete(cache_key)
        
        return response_success(message='上传已取消')
    
    except Exception as e:
        return HttpResponse(f'取消上传失败: {str(e)}', status=500)

