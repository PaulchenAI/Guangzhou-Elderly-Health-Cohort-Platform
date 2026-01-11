#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量创建表查询配置

用法:
    # 列出所有可配置的表
    python manage.py batch_create_table_configs --list
    
    # 按前缀过滤并列出表
    python manage.py batch_create_table_configs --list --prefix WORKFLOW
    
    # 为指定前缀的所有表创建配置
    python manage.py batch_create_table_configs --prefix WORKFLOW
    
    # 为所有表创建配置（谨慎使用）
    python manage.py batch_create_table_configs --all
    
    # 更新现有配置的字段（重新检测表结构）
    python manage.py batch_create_table_configs --prefix BS --update
"""
from django.core.management.base import BaseCommand
from django.db import connection
from core.table_query.table_query_model import TableQueryConfig


# 系统表前缀，这些表不应该被配置
SYSTEM_TABLE_PREFIXES = [
    'core_', 'django_', 'auth_', 'table_query_', 'apscheduler_'
]

# 表名到显示名称的映射（常见前缀）
TABLE_PREFIX_NAMES = {
    'WORKFLOW_': '工作流-',
    'BS_': '基础数据-',
    'BSE_': '基础扩展-',
    'CA_': '护理-',
    'WM_': '仓库物资-',
    'NR_': '护理记录-',
    'FD_': '餐饮-',
    'FIN_': '财务-',
    'HR_': '人事-',
    'OA_': '办公-',
    'PM_': '项目-',
    'SYS_': '系统-',
}


class Command(BaseCommand):
    help = "批量创建表查询配置"

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='只列出表，不创建配置',
        )
        parser.add_argument(
            '--prefix',
            type=str,
            help='按表名前缀过滤（如 WORKFLOW, BS）',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='处理所有表（谨慎使用）',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='更新现有配置（重新检测表结构）',
        )
        parser.add_argument(
            '--max-fields',
            type=int,
            default=30,
            help='每个表最多配置的字段数（默认30）',
        )

    def handle(self, *args, **options):
        list_only = options.get('list', False)
        prefix = options.get('prefix', '').upper() if options.get('prefix') else None
        process_all = options.get('all', False)
        update_existing = options.get('update', False)
        max_fields = options.get('max_fields', 30)
        
        # 获取所有表
        tables = self._get_tables(prefix)
        
        if not tables:
            self.stdout.write(self.style.WARNING("没有找到匹配的表"))
            return
        
        if list_only:
            self._list_tables(tables)
            return
        
        if not process_all and not prefix:
            self.stdout.write(self.style.ERROR(
                "请指定 --prefix 或 --all 参数。使用 --list 查看可用的表。"
            ))
            return
        
        # 批量创建配置
        self._create_configs(tables, update_existing, max_fields)

    def _get_tables(self, prefix=None):
        """获取数据库中的表"""
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            all_tables = [t[0] for t in cursor.fetchall()]
        
        # 过滤系统表
        tables = []
        for table in all_tables:
            is_system = any(table.lower().startswith(p) for p in SYSTEM_TABLE_PREFIXES)
            if not is_system:
                if prefix:
                    if table.upper().startswith(prefix):
                        tables.append(table)
                else:
                    tables.append(table)
        
        return sorted(tables)

    def _list_tables(self, tables):
        """列出表"""
        # 按前缀分组
        grouped = {}
        for table in tables:
            prefix = table.split('_')[0] + '_' if '_' in table else 'OTHER'
            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append(table)
        
        self.stdout.write(f"\n共找到 {len(tables)} 个表:\n")
        
        for prefix in sorted(grouped.keys()):
            prefix_tables = grouped[prefix]
            self.stdout.write(self.style.SUCCESS(f"\n{prefix} ({len(prefix_tables)} 个表):"))
            for t in prefix_tables[:10]:  # 每组最多显示10个
                # 检查是否已有配置
                has_config = TableQueryConfig.objects.filter(
                    table_name__iexact=t, is_deleted=False
                ).exists()
                status = " [已配置]" if has_config else ""
                self.stdout.write(f"  - {t}{status}")
            if len(prefix_tables) > 10:
                self.stdout.write(f"  ... 还有 {len(prefix_tables) - 10} 个表")
        
        # 统计已配置数量
        configured_count = TableQueryConfig.objects.filter(is_deleted=False).count()
        self.stdout.write(f"\n当前已配置: {configured_count} 个表")

    def _create_configs(self, tables, update_existing, max_fields):
        """批量创建配置"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for table in tables:
            try:
                # 检查是否已有配置
                existing = TableQueryConfig.objects.filter(
                    table_name__iexact=table, is_deleted=False
                ).first()
                
                if existing and not update_existing:
                    skipped_count += 1
                    continue
                
                # 获取表结构
                fields = self._detect_table_structure(table, max_fields)
                if not fields:
                    self.stdout.write(self.style.WARNING(f"  跳过 {table}: 无法获取表结构"))
                    error_count += 1
                    continue
                
                # 生成显示名称
                display_name = self._generate_display_name(table)
                
                # 生成配置
                config_json = {
                    "fields": fields,
                    "defaultPageSize": 20,
                    "maxPageSize": 100,
                    "defaultOrderBy": f"{fields[0]['name']} DESC" if fields else "id DESC",
                    "allowedOperations": ["query", "export"]
                }
                
                if existing:
                    # 更新现有配置
                    existing.config_json = config_json
                    existing.save()
                    updated_count += 1
                    self.stdout.write(self.style.NOTICE(f"  ○ 更新: {table}"))
                else:
                    # 创建新配置
                    TableQueryConfig.objects.create(
                        table_name=table,
                        display_name=display_name,
                        description=f"自动生成的 {table} 表配置",
                        config_json=config_json,
                        is_active=True,
                    )
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ 创建: {table}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ 错误 {table}: {e}"))
                error_count += 1
        
        # 输出统计
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("批量配置完成"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  新建: {created_count}")
        self.stdout.write(f"  更新: {updated_count}")
        self.stdout.write(f"  跳过: {skipped_count}")
        self.stdout.write(f"  错误: {error_count}")
        
        total = TableQueryConfig.objects.filter(is_deleted=False).count()
        self.stdout.write(f"\n当前总配置数: {total}")

    def _detect_table_structure(self, table_name, max_fields):
        """自动检测表结构"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
            
            if not columns:
                return None
            
            fields = []
            for col in columns[:max_fields]:
                col_name = col[0]
                col_type = col[1].lower()
                col_key = col[3]  # PRI, UNI, MUL
                
                # 映射数据库类型到前端类型
                if 'int' in col_type:
                    field_type = 'integer'
                elif 'decimal' in col_type or 'float' in col_type or 'double' in col_type:
                    field_type = 'decimal'
                elif 'date' in col_type and 'time' not in col_type:
                    field_type = 'date'
                elif 'datetime' in col_type or 'timestamp' in col_type:
                    field_type = 'datetime'
                elif 'text' in col_type or 'blob' in col_type:
                    field_type = 'string'
                else:
                    field_type = 'string'
                
                # 决定是否可搜索和排序
                is_searchable = field_type == 'string' and 'text' not in col_type and 'blob' not in col_type
                is_sortable = col_key == 'PRI' or field_type in ('integer', 'datetime', 'date')
                
                fields.append({
                    "name": col_name,
                    "displayName": col_name,
                    "type": field_type,
                    "searchable": is_searchable,
                    "sortable": is_sortable,
                    "visible": True,
                    "width": 150 if field_type == 'string' else 100,
                })
            
            return fields
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    检测表结构失败: {e}"))
            return None

    def _generate_display_name(self, table_name):
        """生成显示名称"""
        for prefix, name in TABLE_PREFIX_NAMES.items():
            if table_name.upper().startswith(prefix):
                suffix = table_name[len(prefix):]
                return f"{name}{suffix}"
        return table_name

