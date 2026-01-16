#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查迁移状态和数据库表同步情况

用法:
    python manage.py check_migrations
    python manage.py check_migrations --app core  # 只检查 core 应用
    python manage.py check_migrations --detailed  # 显示详细信息
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.apps import apps


class Command(BaseCommand):
    help = "检查迁移状态和数据库表同步情况"

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            default=None,
            help='指定要检查的应用名称（如 core）',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='显示详细信息',
        )

    def handle(self, *args, **options):
        app_name = options.get('app')
        detailed = options.get('detailed', False)

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("数据库迁移和表同步检查"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        # 检查迁移记录表是否存在
        if not self._check_migrations_table():
            self.stdout.write(self.style.ERROR("❌ django_migrations 表不存在！"))
            self.stdout.write(self.style.WARNING("   建议: 运行 python manage.py migrate 初始化数据库"))
            return

        # 获取所有应用或指定应用
        if app_name:
            apps_to_check = [app_name]
        else:
            apps_to_check = [app.label for app in apps.get_app_configs()]

        # 检查每个应用
        for app_label in apps_to_check:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"📦 检查应用: {app_label}"))
            self.stdout.write("-" * 70)
            
            # 检查迁移记录
            migration_status = self._check_migration_records(app_label, detailed)
            
            # 检查表是否存在
            table_status = self._check_tables(app_label, detailed)
            
            # 对比分析
            self._analyze_status(app_label, migration_status, table_status)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("检查完成"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

    def _check_migrations_table(self):
        """检查 django_migrations 表是否存在"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'django_migrations'
                """)
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _check_migration_records(self, app_label, detailed=False):
        """检查迁移记录"""
        try:
            migrations = MigrationRecorder.Migration.objects.filter(app=app_label).order_by('name')
            migration_list = {}
            
            for mig in migrations:
                migration_list[mig.name] = {
                    'applied': mig.applied,
                    'exists': True
                }
            
            if detailed:
                self.stdout.write(f"  迁移记录数: {len(migration_list)}")
                if migration_list:
                    self.stdout.write("  已记录的迁移:")
                    for name, info in migration_list.items():
                        status = "✓" if info['applied'] else "○"
                        self.stdout.write(f"    {status} {name} ({info['applied']})")
                else:
                    self.stdout.write("  ⚠️  没有迁移记录")
            
            return migration_list
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 检查迁移记录时出错: {str(e)}"))
            return {}

    def _check_tables(self, app_label, detailed=False):
        """检查应用相关的表是否存在"""
        try:
            # 获取应用的所有模型
            app_config = apps.get_app_config(app_label)
            models = app_config.get_models()
            
            table_status = {}
            
            with connection.cursor() as cursor:
                for model in models:
                    # 跳过代理模型
                    if model._meta.proxy:
                        continue
                    
                    table_name = model._meta.db_table
                    
                    # 检查表是否存在
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = DATABASE() 
                        AND table_name = %s
                    """, [table_name])
                    
                    exists = cursor.fetchone()[0] > 0
                    
                    # 如果表存在，检查是否有数据
                    row_count = 0
                    if exists:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                            row_count = cursor.fetchone()[0]
                        except Exception:
                            pass
                    
                    table_status[table_name] = {
                        'exists': exists,
                        'model': model.__name__,
                        'row_count': row_count
                    }
            
            if detailed:
                self.stdout.write(f"  模型数: {len(table_status)}")
                if table_status:
                    self.stdout.write("  表状态:")
                    for table_name, info in sorted(table_status.items()):
                        status = "✓" if info['exists'] else "✗"
                        model_name = info['model']
                        row_count = info['row_count']
                        self.stdout.write(
                            f"    {status} {table_name} ({model_name}) - "
                            f"{'存在' if info['exists'] else '不存在'} - "
                            f"数据行数: {row_count}"
                        )
                else:
                    self.stdout.write("  ⚠️  没有找到模型")
            
            return table_status
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 检查表时出错: {str(e)}"))
            return {}

    def _analyze_status(self, app_label, migration_status, table_status):
        """分析迁移记录和表的同步状态"""
        issues = []
        suggestions = []
        
        # 检查表查询相关的迁移和表
        if app_label == 'core':
            table_query_tables = ['table_query_config', 'table_query_log']
            table_query_migration = '0005_table_query'
            
            # 检查迁移记录
            migration_recorded = table_query_migration in migration_status
            
            # 检查表是否存在
            tables_exist = all(
                table_status.get(table, {}).get('exists', False) 
                for table in table_query_tables
            )
            
            # 分析情况
            if migration_recorded and not tables_exist:
                issues.append(
                    f"⚠️  迁移 '{table_query_migration}' 已记录，但相关表不存在"
                )
                missing_tables = [
                    table for table in table_query_tables 
                    if not table_status.get(table, {}).get('exists', False)
                ]
                suggestions.append(
                    f"   修复建议: 删除迁移记录后重新应用，或直接应用迁移\n"
                    f"   python manage.py migrate core {table_query_migration.split('_')[0]} --fake\n"
                    f"   python manage.py migrate core"
                )
                suggestions.append(
                    f"   缺少的表: {', '.join(missing_tables)}"
                )
            elif not migration_recorded and tables_exist:
                issues.append(
                    f"⚠️  表存在但迁移 '{table_query_migration}' 未记录"
                )
                suggestions.append(
                    f"   修复建议: 伪造迁移记录\n"
                    f"   python manage.py migrate core {table_query_migration.split('_')[0]} --fake"
                )
            elif not migration_recorded and not tables_exist:
                issues.append(
                    f"⚠️  迁移 '{table_query_migration}' 未应用，相关表不存在"
                )
                suggestions.append(
                    f"   修复建议: 应用迁移\n"
                    f"   python manage.py migrate core"
                )
            elif migration_recorded and tables_exist:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ 表查询相关迁移和表状态正常"
                ))
        
        # 显示问题和建议
        if issues:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("🔍 发现问题:"))
            for issue in issues:
                self.stdout.write(f"  {issue}")
            
            if suggestions:
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("💡 修复建议:"))
                for suggestion in suggestions:
                    self.stdout.write(f"  {suggestion}")
