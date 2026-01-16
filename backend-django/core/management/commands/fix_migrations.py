#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复迁移记录和数据库表的不一致问题

用法:
    python manage.py fix_migrations --app core
    python manage.py fix_migrations --app core --dry-run  # 只显示要执行的操作，不实际执行
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError


class Command(BaseCommand):
    help = "修复迁移记录和数据库表的不一致问题"

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            default='core',
            help='指定要修复的应用名称（默认: core）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示要执行的操作，不实际执行',
        )

    def handle(self, *args, **options):
        app_label = options.get('app', 'core')
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("迁移记录和表同步修复"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 模拟模式：只显示操作，不实际执行"))
            self.stdout.write("")

        # 检查迁移记录
        migration_status = self._get_migration_status(app_label)
        
        # 检查表状态
        table_status = self._get_table_status(app_label)
        
        # 分析并修复
        fixes = self._analyze_and_fix(app_label, migration_status, table_status, dry_run)
        
        if fixes:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"✓ 发现 {len(fixes)} 个需要修复的问题"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ 没有发现需要修复的问题"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("修复完成"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

    def _get_migration_status(self, app_label):
        """获取迁移记录状态"""
        try:
            migrations = MigrationRecorder.Migration.objects.filter(app=app_label).order_by('name')
            return {mig.name: mig for mig in migrations}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 获取迁移记录时出错: {str(e)}"))
            return {}

    def _get_table_status(self, app_label):
        """获取表状态"""
        try:
            app_config = apps.get_app_config(app_label)
            models = app_config.get_models()
            
            table_status = {}
            with connection.cursor() as cursor:
                for model in models:
                    if model._meta.proxy:
                        continue
                    
                    table_name = model._meta.db_table
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = DATABASE() 
                        AND table_name = %s
                    """, [table_name])
                    
                    exists = cursor.fetchone()[0] > 0
                    table_status[table_name] = {
                        'exists': exists,
                        'model': model.__name__
                    }
            
            return table_status
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 获取表状态时出错: {str(e)}"))
            return {}

    def _analyze_and_fix(self, app_label, migration_status, table_status, dry_run):
        """分析并修复不一致问题"""
        fixes = []
        
        if app_label == 'core':
            # 处理 0005_table_query 迁移
            migration_0005 = migration_status.get('0005_table_query')
            tables_0005 = ['table_query_config', 'table_query_log']
            
            migration_recorded = migration_0005 is not None
            tables_exist = all(
                table_status.get(table, {}).get('exists', False) 
                for table in tables_0005
            )
            
            if migration_recorded and not tables_exist:
                # 迁移记录存在但表不存在 - 删除迁移记录，然后重新应用
                self.stdout.write(self.style.WARNING(
                    "🔧 修复: 迁移 0005_table_query 有记录但表不存在"
                ))
                self.stdout.write("   1. 删除迁移记录...")
                
                if not dry_run:
                    migration_0005.delete()
                    self.stdout.write(self.style.SUCCESS("     ✓ 已删除迁移记录"))
                else:
                    self.stdout.write("     [模拟] 将删除迁移记录: 0005_table_query")
                
                self.stdout.write("   2. 应用迁移创建表...")
                if not dry_run:
                    # 使用 shell 命令而不是 call_command，以便更好地处理依赖
                    self.stdout.write("     提示: 请手动执行: python manage.py migrate core 0005")
                else:
                    self.stdout.write("     [模拟] 将执行: python manage.py migrate core 0005")
                
                fixes.append('0005_table_query')
            
            # 检查 0006_add_survey_models 迁移
            migration_0006 = migration_status.get('0006_add_survey_models')
            survey_tables = ['survey_schema_config', 'survey_record', 'survey_import_log']
            survey_tables_exist = any(
                table_status.get(table, {}).get('exists', False) 
                for table in survey_tables
            )
            
            # 检查 0006_add_survey_models 迁移
            migration_0006 = migration_status.get('0006_add_survey_models')
            survey_tables = ['survey_schema_config', 'survey_record', 'survey_import_log']
            survey_tables_exist = any(
                table_status.get(table, {}).get('exists', False) 
                for table in survey_tables
            )
            
            if survey_tables_exist:
                # 检查迁移记录状态
                if not migration_0006:
                    # 表存在但迁移记录不存在 - 伪造迁移记录
                    self.stdout.write(self.style.WARNING(
                        "🔧 修复: 表存在但迁移 0006_add_survey_models 记录不存在"
                    ))
                    self.stdout.write("   伪造迁移记录...")
                    
                    if not dry_run:
                        # 确保依赖的迁移已记录
                        if '0005_table_query' not in migration_status:
                            from django.db.migrations.recorder import MigrationRecorder
                            from django.utils import timezone
                            MigrationRecorder.Migration.objects.create(
                                app=app_label,
                                name='0005_table_query',
                                applied=timezone.now()
                            )
                            self.stdout.write("     ✓ 已创建依赖迁移记录: 0005_table_query")
                        
                        # 伪造 0006 的记录
                        from django.db.migrations.recorder import MigrationRecorder
                        from django.utils import timezone
                        MigrationRecorder.Migration.objects.create(
                            app=app_label,
                            name='0006_add_survey_models',
                            applied=timezone.now()
                        )
                        self.stdout.write(self.style.SUCCESS("     ✓ 已伪造迁移记录: 0006_add_survey_models"))
                    else:
                        self.stdout.write("     [模拟] 将创建迁移记录: 0006_add_survey_models")
                    
                    fixes.append('0006_add_survey_models')
                else:
                    self.stdout.write(self.style.SUCCESS(
                        "  ✓ 迁移 0006_add_survey_models 记录和表状态正常"
                    ))
        
        return fixes
