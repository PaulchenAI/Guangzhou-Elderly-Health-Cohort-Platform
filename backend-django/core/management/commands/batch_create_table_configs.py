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
    
    # 使用外部配置文件指定中文名称映射
    python manage.py batch_create_table_configs --prefix WORKFLOW --config-file path/to/mapping.json
    
    # 使用 meaning.json 文件获取中文名称（优先级高于 config-file）
    python manage.py batch_create_table_configs --prefix FORMTABLE --meaning-dir docs/hospital/commentsql
    
    # 指定数据库表名前缀（匹配 meaning.json 时忽略前缀）
    python manage.py batch_create_table_configs --prefix dbo_FORMTABLE --table-prefix dbo_
"""
import json
import os
from django.core.management.base import BaseCommand
from django.db import connection
from core.table_query.table_query_model import TableQueryConfig


# 系统表前缀，这些表不应该被配置
SYSTEM_TABLE_PREFIXES = [
    'core_', 'django_', 'auth_', 'table_query_', 'apscheduler_'
]


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
        parser.add_argument(
            '--config-file',
            type=str,
            default=None,
            help='外部配置文件路径（JSON格式，包含表名和字段名的中文映射），默认使用 core/management/commands/table_name_mapping.json',
        )
        parser.add_argument(
            '--meaning-dir',
            type=str,
            default=None,
            help='meaning.json 文件所在目录（优先级高于 config-file），默认使用 docs/hospital/commentsql',
        )
        parser.add_argument(
            '--table-prefix',
            type=str,
            default=None,
            help='数据库表名前缀，匹配 meaning.json 时会忽略此前缀（如 dbo_、hospital_）',
        )

    def handle(self, *args, **options):
        list_only = options.get('list', False)
        prefix = options.get('prefix', '').upper() if options.get('prefix') else None
        process_all = options.get('all', False)
        update_existing = options.get('update', False)
        max_fields = options.get('max_fields', 30)
        config_file = options.get('config_file')
        meaning_dir = options.get('meaning_dir')
        table_prefix = options.get('table_prefix', '')
        
        # 加载配置文件
        name_mapping = self._load_name_mapping(config_file)
        
        # 加载 meaning.json 文件
        meaning_mapping = self._load_meaning_files(meaning_dir)
        if meaning_mapping:
            self.stdout.write(self.style.SUCCESS(
                f"已加载 {len(meaning_mapping)} 个表的 meaning.json 文件"
            ))
        if table_prefix:
            self.stdout.write(self.style.SUCCESS(
                f"表名前缀: {table_prefix}（匹配时将忽略此前缀）"
            ))
        
        # 获取所有表
        tables = self._get_tables(prefix)
        
        if not tables:
            self.stdout.write(self.style.WARNING("没有找到匹配的表"))
            return
        
        if list_only:
            self._list_tables(tables, meaning_mapping, table_prefix)
            return
        
        if not process_all and not prefix:
            self.stdout.write(self.style.ERROR(
                "请指定 --prefix 或 --all 参数。使用 --list 查看可用的表。"
            ))
            return
        
        # 批量创建配置
        self._create_configs(tables, update_existing, max_fields, name_mapping, meaning_mapping, table_prefix)

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

    def _strip_table_prefix(self, table_name, table_prefix):
        """去掉表名前缀，用于匹配 meaning.json"""
        if table_prefix and table_name.startswith(table_prefix):
            return table_name[len(table_prefix):]
        return table_name
    
    def _list_tables(self, tables, meaning_mapping=None, table_prefix=None):
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
                # 显示 meaning.json 中的中文名称（去掉前缀后匹配）
                meaning_name = ""
                stripped_name = self._strip_table_prefix(t, table_prefix)
                if meaning_mapping and stripped_name in meaning_mapping:
                    meaning_name = f" ({meaning_mapping[stripped_name].get('table_meaning', '')})"
                self.stdout.write(f"  - {t}{meaning_name}{status}")
            if len(prefix_tables) > 10:
                self.stdout.write(f"  ... 还有 {len(prefix_tables) - 10} 个表")
        
        # 统计已配置数量
        configured_count = TableQueryConfig.objects.filter(is_deleted=False).count()
        self.stdout.write(f"\n当前已配置: {configured_count} 个表")

    def _create_configs(self, tables, update_existing, max_fields, name_mapping, meaning_mapping=None, table_prefix=None):
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
                fields = self._detect_table_structure(table, max_fields, name_mapping, meaning_mapping, table_prefix)
                if not fields:
                    self.stdout.write(self.style.WARNING(f"  跳过 {table}: 无法获取表结构"))
                    error_count += 1
                    continue
                
                # 生成显示名称
                display_name = self._generate_display_name(table, name_mapping, meaning_mapping, table_prefix)
                
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
                    existing.display_name = display_name
                    existing.config_json = config_json
                    existing.save()
                    updated_count += 1
                    self.stdout.write(self.style.NOTICE(f"  ○ 更新: {table} -> {display_name}"))
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
                    self.stdout.write(self.style.SUCCESS(f"  ✓ 创建: {table} -> {display_name}"))
                    
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

    def _detect_table_structure(self, table_name, max_fields, name_mapping, meaning_mapping=None, table_prefix=None):
        """自动检测表结构"""
        try:
            with connection.cursor() as cursor:
                # 获取字段信息和注释
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                    LIMIT %s
                """, [table_name, max_fields])
                columns = cursor.fetchall()
            
            if not columns:
                return None
            
            # 获取 meaning.json 中该表的字段映射（去掉前缀后匹配）
            meaning_fields = {}
            stripped_name = self._strip_table_prefix(table_name, table_prefix)
            if meaning_mapping and stripped_name in meaning_mapping:
                meaning_fields = meaning_mapping[stripped_name].get('fields', {})
            
            fields = []
            for col in columns:
                col_name = col[0]
                col_type = col[1].lower()
                col_key = col[2]  # PRI, UNI, MUL
                col_comment = col[3] or ''  # COMMENT
                
                # 获取字段的中文显示名称（优先级：COMMENT > meaning.json > 配置文件 > 字段名）
                field_display_name = col_name
                if col_comment and col_comment.strip():
                    field_display_name = col_comment.strip()
                elif col_name in meaning_fields:
                    field_display_name = meaning_fields[col_name]
                elif name_mapping and 'fields' in name_mapping:
                    table_fields = name_mapping['fields'].get(table_name, {})
                    if col_name in table_fields:
                        field_display_name = table_fields[col_name]
                
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
                    "displayName": field_display_name,
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

    def _load_name_mapping(self, config_file=None):
        """加载名称映射配置文件"""
        if config_file is None:
            # 使用默认配置文件路径
            default_config = os.path.join(
                os.path.dirname(__file__),
                'table_name_mapping.json'
            )
            config_file = default_config
        
        if not os.path.exists(config_file):
            # 配置文件不存在，返回 None
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                return mapping
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.WARNING(
                f"配置文件格式错误: {config_file}, {e}。将忽略配置文件。"
            ))
            return None
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"读取配置文件失败: {config_file}, {e}。将忽略配置文件。"
            ))
            return None
    
    def _load_meaning_files(self, meaning_dir=None):
        """加载 meaning.json 文件，构建表名和字段名的映射"""
        import glob
        
        # 确定目录路径
        if meaning_dir is None:
            # 默认使用 docs/hospital/commentsql 目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            meaning_dir = os.path.join(project_root, 'docs', 'hospital', 'commentsql')
        
        if not os.path.exists(meaning_dir):
            return None
        
        # 扫描所有 *_meaning.json 文件，忽略 all_meanings.json
        pattern = os.path.join(meaning_dir, '*_meaning.json')
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        # 构建映射结构: {table_name: {table_meaning: str, fields: {field_name: meaning}}}
        mapping = {}
        
        for file_path in files:
            # 忽略 all_meanings.json
            if os.path.basename(file_path) == 'all_meanings.json':
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 解析 JSON 结构
                if 'table' not in data:
                    continue
                
                table_data = data['table']
                table_name = table_data.get('table_name')
                if not table_name:
                    continue
                
                # 提取表的中文含义
                table_meaning = table_data.get('inferred_meaning', '')
                
                # 提取字段的中文含义
                fields_mapping = {}
                for field in table_data.get('fields', []):
                    field_name = field.get('field_name')
                    field_meaning = field.get('inferred_meaning')
                    if field_name and field_meaning:
                        fields_mapping[field_name] = field_meaning
                
                mapping[table_name] = {
                    'table_meaning': table_meaning,
                    'fields': fields_mapping
                }
                
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.WARNING(
                    f"解析 meaning.json 文件失败: {file_path}, {e}"
                ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"读取 meaning.json 文件失败: {file_path}, {e}"
                ))
        
        return mapping if mapping else None
    
    def _get_table_comment(self, table_name):
        """从数据库获取表的 COMMENT"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TABLE_COMMENT
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                """, [table_name])
                result = cursor.fetchone()
                if result and result[0] and result[0].strip():
                    return result[0].strip()
        except Exception as e:
            # 静默失败，不影响主流程
            pass
        return None
    
    def _generate_display_name(self, table_name, name_mapping, meaning_mapping=None, table_prefix=None):
        """生成显示名称（优先级：数据库 COMMENT > meaning.json > 配置文件 > 表名）"""
        # 1. 优先使用数据库表的 COMMENT
        table_comment = self._get_table_comment(table_name)
        if table_comment:
            return table_comment
        
        # 2. 使用 meaning.json 中的映射（去掉前缀后匹配）
        stripped_name = self._strip_table_prefix(table_name, table_prefix)
        if meaning_mapping and stripped_name in meaning_mapping:
            table_meaning = meaning_mapping[stripped_name].get('table_meaning')
            if table_meaning:
                return table_meaning
        
        # 3. 使用配置文件中的映射
        if name_mapping and 'tables' in name_mapping:
            if table_name in name_mapping['tables']:
                return name_mapping['tables'][table_name]
        
        # 4. 返回表名本身
        return table_name

