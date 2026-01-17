# -*- coding: utf-8 -*-
"""
Django 管理命令：导入外键关系元数据

将 JSON 文件中的外键关系信息导入到 MySQL 数据库的元数据表中。

使用方法：
    # 预览模式（不执行导入）
    python manage.py import_foreignkey_metadata --dry-run
    
    # 导入外键元数据（使用默认目录）
    python manage.py import_foreignkey_metadata
    
    # 指定 JSON 目录
    python manage.py import_foreignkey_metadata ../docs/hospital/foreignkey/
    
    # 指定表名前缀
    python manage.py import_foreignkey_metadata --prefix custom_
    
    # 清空后重新导入
    python manage.py import_foreignkey_metadata --truncate
    
    # 显示详细进度
    python manage.py import_foreignkey_metadata --verbose
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


@dataclass
class ForeignKeyMetadata:
    """外键元数据"""
    source_table: str
    source_columns: List[str]
    target_table: str
    target_columns: List[str]
    constraint_name: str
    on_delete: Optional[str]
    source_file: str


class Command(BaseCommand):
    help = '将外键关系元数据导入到当前 Django 配置的数据库'
    
    # 创建元数据表的 SQL
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS table_foreignkey_metadata (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source_table VARCHAR(128) NOT NULL COMMENT '源表名（带前缀）',
        source_columns JSON NOT NULL COMMENT '源字段列表',
        target_table VARCHAR(128) NOT NULL COMMENT '目标表名（带前缀）',
        target_columns JSON NOT NULL COMMENT '目标字段列表',
        constraint_name VARCHAR(128) COMMENT '约束名（带前缀）',
        on_delete VARCHAR(20) COMMENT '删除规则：cascade/set_null/restrict/no_action',
        source_file VARCHAR(255) COMMENT '来源 JSON 文件名',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_source_table (source_table),
        INDEX idx_target_table (target_table)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='外键关系元数据表';
    """
    
    def add_arguments(self, parser):
        parser.add_argument(
            'json_dir',
            type=str,
            nargs='?',
            default=None,
            help='外键 JSON 文件目录（默认: docs/hospital/foreignkey/）'
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='gzlry_',
            help='表名前缀（默认: gzlry_）'
        )
        parser.add_argument(
            '--truncate',
            action='store_true',
            help='导入前清空表'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，不执行实际导入'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细进度'
        )
    
    def handle(self, *args, **options):
        json_dir = options.get('json_dir')
        prefix = options.get('prefix', 'gzlry_')
        truncate = options.get('truncate', False)
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        
        # 处理默认目录
        if not json_dir:
            # 智能查找 docs/hospital/foreignkey 目录
            possible_paths = [
                'docs/hospital/foreignkey/',
                '../docs/hospital/foreignkey/',
                '../../docs/hospital/foreignkey/',
            ]
            
            for p in possible_paths:
                test_path = Path(p)
                if test_path.exists() and test_path.is_dir():
                    json_dir = str(test_path)
                    break
            
            if not json_dir:
                raise CommandError(
                    '找不到 docs/hospital/foreignkey/ 目录。\n'
                    '请指定正确的 JSON 文件目录路径。'
                )
        
        json_dir_path = Path(json_dir)
        if not json_dir_path.exists():
            raise CommandError(f'目录不存在: {json_dir}')
        
        # 显示配置信息
        self.stdout.write(self.style.SUCCESS('外键关系元数据导入'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'JSON 目录: {json_dir_path.absolute()}')
        self.stdout.write(f'表名前缀: {prefix}')
        if truncate:
            self.stdout.write(self.style.WARNING('模式: 清空后导入'))
        if dry_run:
            self.stdout.write(self.style.WARNING('模式: 预览（不执行导入）'))
        self.stdout.write('')
        
        # 扫描 JSON 文件
        self.stdout.write(f'扫描目录: {json_dir}')
        json_files = list(json_dir_path.glob('*_foreignkeys.json'))
        self.stdout.write(f'找到 {len(json_files)} 个外键 JSON 文件')
        
        if not json_files:
            self.stdout.write(self.style.WARNING('没有找到外键 JSON 文件'))
            return
        
        # 收集所有外键信息
        all_fks = []
        files_with_fks = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                foreign_keys = json_data.get('foreign_keys', [])
                if not foreign_keys:
                    continue
                
                files_with_fks += 1
                file_name = json_file.name
                
                for fk in foreign_keys:
                    metadata = ForeignKeyMetadata(
                        source_table=self._add_prefix(fk.get('source_table', ''), prefix),
                        source_columns=fk.get('source_columns', []),
                        target_table=self._add_prefix(fk.get('target_table', ''), prefix),
                        target_columns=fk.get('target_columns', []),
                        constraint_name=self._add_prefix(fk.get('constraint_name', ''), prefix),
                        on_delete=fk.get('on_delete'),
                        source_file=file_name
                    )
                    all_fks.append(metadata)
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'读取文件失败 {json_file.name}: {e}'))
                continue
        
        self.stdout.write(f'有外键的文件: {files_with_fks}')
        self.stdout.write(f'总外键数: {len(all_fks)}')
        
        # 预览模式
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('[预览模式] 将导入以下外键关系：'))
            for i, fk in enumerate(all_fks[:10], 1):
                self.stdout.write(f'  {i}. {fk.source_table} -> {fk.target_table} ({fk.constraint_name})')
            if len(all_fks) > 10:
                self.stdout.write(f'  ... 还有 {len(all_fks) - 10} 条')
            
            self._print_report({
                'total_files': len(json_files),
                'files_with_fks': files_with_fks,
                'total_fks': len(all_fks),
                'imported': 0,
                'failed': 0
            })
            return
        
        # 执行导入
        self.stdout.write('')
        self.stdout.write('开始导入...')
        
        with connection.cursor() as cursor:
            # 创建表（如果不存在）
            self.stdout.write('创建元数据表（如果不存在）...')
            cursor.execute(self.CREATE_TABLE_SQL)
            
            # 清空表（如果需要）
            if truncate:
                self.stdout.write(self.style.WARNING('清空表...'))
                cursor.execute('TRUNCATE TABLE table_foreignkey_metadata')
            
            # 批量插入
            imported = 0
            failed = 0
            errors = []
            
            for i, fk in enumerate(all_fks, 1):
                try:
                    cursor.execute("""
                        INSERT INTO table_foreignkey_metadata 
                        (source_table, source_columns, target_table, target_columns, 
                         constraint_name, on_delete, source_file)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [
                        fk.source_table,
                        json.dumps(fk.source_columns),
                        fk.target_table,
                        json.dumps(fk.target_columns),
                        fk.constraint_name,
                        fk.on_delete,
                        fk.source_file
                    ])
                    imported += 1
                    
                    if verbose:
                        self.stdout.write(f'  [{i}/{len(all_fks)}] {fk.source_table} -> {fk.target_table}')
                    elif i % 100 == 0:
                        self.stdout.write(f'  已导入 {i}/{len(all_fks)}')
                
                except Exception as e:
                    failed += 1
                    error_msg = f'{fk.constraint_name}: {e}'
                    errors.append(error_msg)
                    if verbose:
                        self.stdout.write(self.style.ERROR(f'  [失败] {error_msg}'))
        
        self.stdout.write(self.style.SUCCESS('导入完成！'))
        
        # 打印报告
        self._print_report({
            'total_files': len(json_files),
            'files_with_fks': files_with_fks,
            'total_fks': len(all_fks),
            'imported': imported,
            'failed': failed,
            'errors': errors
        })
    
    def _add_prefix(self, name: str, prefix: str) -> str:
        """为名称添加前缀"""
        if not name:
            return name
        return f"{prefix}{name}"
    
    def _print_report(self, stats: dict):
        """打印导入报告"""
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('导入报告')
        self.stdout.write('=' * 60)
        self.stdout.write(f'总文件数: {stats["total_files"]}')
        self.stdout.write(f'有外键的文件数: {stats["files_with_fks"]}')
        self.stdout.write(f'总外键数: {stats["total_fks"]}')
        self.stdout.write(self.style.SUCCESS(f'成功导入: {stats["imported"]}'))
        
        if stats.get('failed', 0) > 0:
            self.stdout.write(self.style.ERROR(f'导入失败: {stats["failed"]}'))
            
            errors = stats.get('errors', [])
            if errors:
                self.stdout.write('')
                self.stdout.write(self.style.ERROR('错误列表（前 10 条）:'))
                for error in errors[:10]:
                    self.stdout.write(f'  - {error}')
                if len(errors) > 10:
                    self.stdout.write(f'  ... 还有 {len(errors) - 10} 个错误')
