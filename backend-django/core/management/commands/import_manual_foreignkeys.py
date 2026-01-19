# -*- coding: utf-8 -*-
"""
Django 管理命令：导入手动定义的外键关系

将业务逻辑上存在但未在原始 SQL 中定义的外键关系导入到元数据表中。

使用方法：
    # 预览模式（不执行导入）
    python manage.py import_manual_foreignkeys --dry-run
    
    # 导入手动定义的外键
    python manage.py import_manual_foreignkeys
    
    # 指定表名前缀
    python manage.py import_manual_foreignkeys --prefix custom_
    
    # 清空手动导入的记录后重新导入
    python manage.py import_manual_foreignkeys --truncate-manual
    
    # 显示详细进度
    python manage.py import_manual_foreignkeys --verbose
"""

import json
from typing import List, Dict, Tuple
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import connection


@dataclass
class ManualForeignKey:
    """手动定义的外键关系"""
    source_table: str
    source_columns: List[str]
    target_table: str
    target_columns: List[str]
    description: str


# 固定的外键关系定义（6 条核心关系）
# 注意：表名必须与数据库中的实际表名大小写一致
FIXED_FOREIGN_KEYS = [
    ManualForeignKey(
        source_table='OL_RECORD_HISTORY',
        source_columns=['olderid'],
        target_table='BS_OLDER',
        target_columns=['mainid'],
        description='老人记录关联老人基本信息'
    ),
    ManualForeignKey(
        source_table='WORKFLOW_REQUESTBASE',
        source_columns=['recordid'],
        target_table='OL_RECORD_HISTORY',
        target_columns=['mainid'],
        description='工作流关联老人记录'
    ),
    ManualForeignKey(
        source_table='WORKFLOW_REQUESTBASE',
        source_columns=['olderid'],
        target_table='BS_OLDER',
        target_columns=['mainid'],
        description='工作流关联老人'
    ),
    ManualForeignKey(
        source_table='HR_HEALTH_RECORDS',
        source_columns=['bs_older_id'],
        target_table='BS_OLDER',
        target_columns=['mainid'],
        description='健康档案关联老人'
    ),
    ManualForeignKey(
        source_table='HR_HEALTH_RECORDS',
        source_columns=['ol_record_id'],
        target_table='OL_RECORD_HISTORY',
        target_columns=['mainid'],
        description='健康档案关联老人记录'
    ),
    ManualForeignKey(
        source_table='HR_HH_DRUG',
        source_columns=['health_records_id'],
        target_table='HR_HEALTH_RECORDS',
        target_columns=['mainid'],
        description='用药记录关联健康档案'
    ),
]

# 手动导入记录的标识
MANUAL_IMPORT_SOURCE = 'manual_import'


class Command(BaseCommand):
    help = '导入手动定义的外键关系到元数据表'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--prefix',
            type=str,
            default='gzlry_',
            help='表名前缀（默认: gzlry_）'
        )
        parser.add_argument(
            '--truncate-manual',
            action='store_true',
            help='导入前清空手动导入的记录'
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
        prefix = options.get('prefix', 'gzlry_')
        truncate_manual = options.get('truncate_manual', False)
        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        
        # 显示配置信息
        self.stdout.write(self.style.SUCCESS('手动外键关系导入'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'表名前缀: {prefix}')
        if truncate_manual:
            self.stdout.write(self.style.WARNING('模式: 清空手动记录后导入'))
        if dry_run:
            self.stdout.write(self.style.WARNING('模式: 预览（不执行导入）'))
        self.stdout.write('')
        
        # 收集所有外键关系
        all_fks: List[Tuple[str, str, List[str], str, List[str], str]] = []
        skipped_fks: List[str] = []  # 跳过的外键关系（字段不存在）
        
        # 1. 添加固定的外键关系（验证字段存在性）
        self.stdout.write('收集固定外键关系...')
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            
            for fk in FIXED_FOREIGN_KEYS:
                source_table = f"{prefix}{fk.source_table}"
                target_table = f"{prefix}{fk.target_table}"
                
                # 先验证表是否存在
                source_table_exists = self._table_exists(cursor, db_name, source_table)
                target_table_exists = self._table_exists(cursor, db_name, target_table)
                
                if not source_table_exists or not target_table_exists:
                    skip_reason = []
                    if not source_table_exists:
                        skip_reason.append(f"源表 {source_table} 不存在")
                    if not target_table_exists:
                        skip_reason.append(f"目标表 {target_table} 不存在")
                    skipped_fks.append(f"{fk.source_table} -> {fk.target_table}: {'; '.join(skip_reason)}")
                    if verbose:
                        self.stdout.write(self.style.WARNING(f'  [跳过] {fk.source_table} -> {fk.target_table}: {"; ".join(skip_reason)}'))
                    continue
                
                # 再验证源字段和目标字段是否存在
                source_valid = all(
                    self._table_has_column(cursor, db_name, source_table, col)
                    for col in fk.source_columns
                )
                target_valid = all(
                    self._table_has_column(cursor, db_name, target_table, col)
                    for col in fk.target_columns
                )
                
                if not source_valid or not target_valid:
                    skip_reason = []
                    if not source_valid:
                        skip_reason.append(f"源字段 {fk.source_columns} 不存在于 {source_table}")
                    if not target_valid:
                        skip_reason.append(f"目标字段 {fk.target_columns} 不存在于 {target_table}")
                    skipped_fks.append(f"{fk.source_table} -> {fk.target_table}: {'; '.join(skip_reason)}")
                    if verbose:
                        self.stdout.write(self.style.WARNING(f'  [跳过] {fk.source_table} -> {fk.target_table}: {"; ".join(skip_reason)}'))
                    continue
                
                constraint_name = f"FK_MANUAL_{fk.source_table}_{fk.source_columns[0]}"
                all_fks.append((
                    source_table,
                    json.dumps(fk.source_columns),
                    fk.source_columns,
                    target_table,
                    fk.target_columns,
                    constraint_name
                ))
                if verbose:
                    self.stdout.write(f'  + {fk.source_table}.{fk.source_columns[0]} -> {fk.target_table}.{fk.target_columns[0]} ({fk.description})')
        
        valid_fixed_count = len(FIXED_FOREIGN_KEYS) - len([s for s in skipped_fks if '->' in s])
        self.stdout.write(f'固定外键关系: {valid_fixed_count} 条（跳过 {len(skipped_fks)} 条）')
        
        # 2. 动态发现 formtable_* 和 DC_* 表
        self.stdout.write('')
        self.stdout.write('发现动态表...')
        
        # 先检查 WORKFLOW_REQUESTBASE 表是否存在
        workflow_table = f"{prefix}WORKFLOW_REQUESTBASE"
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            workflow_exists = self._table_exists(cursor, db_name, workflow_table)
        
        if not workflow_exists:
            self.stdout.write(self.style.WARNING(f'  [跳过] 目标表 {workflow_table} 不存在，跳过动态表外键关系'))
            formtables, dc_tables = [], []
        else:
            formtables, dc_tables = self._discover_dynamic_tables(prefix)
        
        self.stdout.write(f'发现 FORMTABLE_MAIN_* 表: {len(formtables)} 个')
        self.stdout.write(f'发现 DC_FORM_* 表: {len(dc_tables)} 个')
        
        # 为动态表生成外键关系（WORKFLOW_REQUESTBASE 的主键是 requestid）
        for table_name in formtables:
            constraint_name = f"FK_MANUAL_{table_name}_requestid"
            all_fks.append((
                table_name,
                json.dumps(['requestid']),
                ['requestid'],
                workflow_table,
                ['requestid'],  # WORKFLOW_REQUESTBASE 的主键是 requestid
                constraint_name
            ))
            if verbose:
                self.stdout.write(f'  + {table_name}.requestid -> WORKFLOW_REQUESTBASE.requestid')
        
        for table_name in dc_tables:
            constraint_name = f"FK_MANUAL_{table_name}_requestid"
            all_fks.append((
                table_name,
                json.dumps(['requestid']),
                ['requestid'],
                workflow_table,
                ['requestid'],  # WORKFLOW_REQUESTBASE 的主键是 requestid
                constraint_name
            ))
            if verbose:
                self.stdout.write(f'  + {table_name}.requestid -> WORKFLOW_REQUESTBASE.requestid')
        
        self.stdout.write('')
        self.stdout.write(f'总外键关系数: {len(all_fks)}')
        
        # 预览模式
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('[预览模式] 将导入以下外键关系：'))
            self.stdout.write('')
            self.stdout.write('固定外键关系:')
            for i, fk in enumerate(FIXED_FOREIGN_KEYS, 1):
                self.stdout.write(f'  {i}. {prefix}{fk.source_table}.{fk.source_columns[0]} -> {prefix}{fk.target_table}.{fk.target_columns[0]}')
                self.stdout.write(f'     说明: {fk.description}')
            
            if formtables:
                self.stdout.write('')
                self.stdout.write(f'FORMTABLE_MAIN_* 表 ({len(formtables)} 个):')
                for table in formtables[:10]:
                    self.stdout.write(f'  - {table}.requestid -> {workflow_table}.requestid')
                if len(formtables) > 10:
                    self.stdout.write(f'  ... 还有 {len(formtables) - 10} 个')
            
            if dc_tables:
                self.stdout.write('')
                self.stdout.write(f'DC_FORM_* 表 ({len(dc_tables)} 个):')
                for table in dc_tables[:10]:
                    self.stdout.write(f'  - {table}.requestid -> {workflow_table}.requestid')
                if len(dc_tables) > 10:
                    self.stdout.write(f'  ... 还有 {len(dc_tables) - 10} 个')
            
            self._print_report({
                'fixed_fks': len(FIXED_FOREIGN_KEYS),
                'formtables': len(formtables),
                'dc_tables': len(dc_tables),
                'total_fks': len(all_fks),
                'imported': 0,
                'failed': 0
            })
            return
        
        # 执行导入
        self.stdout.write('')
        self.stdout.write('开始导入...')
        
        with connection.cursor() as cursor:
            # 清空手动导入的记录（如果需要）
            if truncate_manual:
                self.stdout.write(self.style.WARNING('清空手动导入的记录...'))
                cursor.execute(
                    "DELETE FROM table_foreignkey_metadata WHERE source_file = %s",
                    [MANUAL_IMPORT_SOURCE]
                )
                deleted_count = cursor.rowcount
                self.stdout.write(f'已删除 {deleted_count} 条手动导入的记录')
            
            # 批量插入
            imported = 0
            failed = 0
            errors = []
            
            for i, (source_table, source_cols_json, source_cols, target_table, target_cols, constraint_name) in enumerate(all_fks, 1):
                try:
                    # 检查是否已存在
                    cursor.execute("""
                        SELECT id FROM table_foreignkey_metadata 
                        WHERE source_table = %s AND target_table = %s 
                        AND JSON_CONTAINS(source_columns, %s)
                    """, [source_table, target_table, source_cols_json])
                    
                    if cursor.fetchone():
                        if verbose:
                            self.stdout.write(f'  [跳过] {source_table} -> {target_table} (已存在)')
                        continue
                    
                    cursor.execute("""
                        INSERT INTO table_foreignkey_metadata 
                        (source_table, source_columns, target_table, target_columns, 
                         constraint_name, on_delete, source_file)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, [
                        source_table,
                        source_cols_json,
                        target_table,
                        json.dumps(target_cols),
                        constraint_name,
                        None,
                        MANUAL_IMPORT_SOURCE
                    ])
                    imported += 1
                    
                    if verbose:
                        self.stdout.write(f'  [{i}/{len(all_fks)}] {source_table} -> {target_table}')
                    elif i % 50 == 0:
                        self.stdout.write(f'  已处理 {i}/{len(all_fks)}')
                
                except Exception as e:
                    failed += 1
                    error_msg = f'{source_table} -> {target_table}: {e}'
                    errors.append(error_msg)
                    if verbose:
                        self.stdout.write(self.style.ERROR(f'  [失败] {error_msg}'))
        
        self.stdout.write(self.style.SUCCESS('导入完成！'))
        
        # 打印报告
        self._print_report({
            'fixed_fks': len(FIXED_FOREIGN_KEYS),
            'formtables': len(formtables),
            'dc_tables': len(dc_tables),
            'total_fks': len(all_fks),
            'imported': imported,
            'failed': failed,
            'errors': errors
        })
    
    def _discover_dynamic_tables(self, prefix: str) -> Tuple[List[str], List[str]]:
        """
        发现数据库中的动态表，并验证 requestid 字段存在
        
        返回:
            (FORMTABLE_MAIN_* 表列表, DC_FORM_* 表列表)
        """
        formtables = []
        dc_tables = []
        
        with connection.cursor() as cursor:
            # 获取数据库名
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            
            # 查询 FORMTABLE_MAIN_* 表
            formtable_pattern1 = f'{prefix}FORMTABLE_MAIN_%'
            formtable_pattern2 = 'FORMTABLE_MAIN_%'
            
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = %s 
                AND (table_name LIKE %s OR table_name LIKE %s)
                ORDER BY table_name
            """, [db_name, formtable_pattern1, formtable_pattern2])
            
            for row in cursor.fetchall():
                table_name = row[0]
                # 验证表中存在 requestid 字段
                if self._table_has_column(cursor, db_name, table_name, 'requestid'):
                    # 确保表名有前缀
                    if not table_name.startswith(prefix):
                        table_name = f"{prefix}{table_name}"
                    formtables.append(table_name)
            
            # 查询 DC_FORM_* 表
            dc_pattern1 = f'{prefix}DC_FORM_%'
            dc_pattern2 = 'DC_FORM_%'
            
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = %s 
                AND (table_name LIKE %s OR table_name LIKE %s)
                ORDER BY table_name
            """, [db_name, dc_pattern1, dc_pattern2])
            
            for row in cursor.fetchall():
                table_name = row[0]
                # 验证表中存在 requestid 字段
                if self._table_has_column(cursor, db_name, table_name, 'requestid'):
                    # 确保表名有前缀
                    if not table_name.startswith(prefix):
                        table_name = f"{prefix}{table_name}"
                    dc_tables.append(table_name)
        
        return formtables, dc_tables
    
    def _table_exists(self, cursor, db_name: str, table_name: str) -> bool:
        """检查表是否存在"""
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """, [db_name, table_name])
        return cursor.fetchone()[0] > 0
    
    def _table_has_column(self, cursor, db_name: str, table_name: str, column_name: str) -> bool:
        """检查表中是否存在指定字段"""
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """, [db_name, table_name, column_name])
        return cursor.fetchone()[0] > 0
    
    def _print_report(self, stats: dict):
        """打印导入报告"""
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('导入报告')
        self.stdout.write('=' * 60)
        self.stdout.write(f'固定外键关系: {stats["fixed_fks"]}')
        self.stdout.write(f'FORMTABLE_MAIN_* 表: {stats["formtables"]}')
        self.stdout.write(f'DC_FORM_* 表: {stats["dc_tables"]}')
        self.stdout.write(f'总外键关系数: {stats["total_fks"]}')
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
