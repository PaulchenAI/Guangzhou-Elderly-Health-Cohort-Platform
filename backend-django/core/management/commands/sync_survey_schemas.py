#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步问卷 Schema 命令

从外部问卷调查 API 同步问卷 Schema 定义到本地数据库。

用法:
    python manage.py sync_survey_schemas
    python manage.py sync_survey_schemas --type fried
    python manage.py sync_survey_schemas --type fried --type rockwood
"""
from django.core.management.base import BaseCommand

from core.survey.survey_api_client import SurveyAPIError, get_survey_api_client
from core.survey.survey_service import SurveyService


class Command(BaseCommand):
    help = "从外部 API 同步问卷 Schema 定义"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            action='append',
            dest='types',
            help='要同步的问卷类型（可多次指定），不指定则同步全部',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='仅测试 API 连接，不执行同步',
        )

    def handle(self, *args, **options):
        types = options.get('types')
        test_only = options.get('test_connection', False)
        
        try:
            client = get_survey_api_client()
            
            # 测试连接
            if test_only:
                self.stdout.write("测试 API 连接...")
                if client.test_connection():
                    self.stdout.write(self.style.SUCCESS("✓ API 连接正常"))
                else:
                    self.stdout.write(self.style.ERROR("✗ API 连接失败"))
                
                self.stdout.write("测试认证...")
                if client.test_auth():
                    self.stdout.write(self.style.SUCCESS("✓ 认证正常"))
                else:
                    self.stdout.write(self.style.ERROR("✗ 认证失败"))
                return
            
            # 执行同步
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("=" * 60))
            self.stdout.write(self.style.NOTICE("开始同步问卷 Schema"))
            self.stdout.write(self.style.NOTICE("=" * 60))
            self.stdout.write("")
            
            if types:
                self.stdout.write(f"指定类型: {', '.join(types)}")
            else:
                self.stdout.write("同步所有类型")
            self.stdout.write("")
            
            service = SurveyService(client)
            result = service.sync_schemas(survey_types=types)
            
            # 输出结果
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("同步完成"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(f"  新增: {result['created']}")
            self.stdout.write(f"  更新: {result['updated']}")
            self.stdout.write(f"  失败: {result['failed']}")
            self.stdout.write("")
            
            # 详细信息
            if result['details']:
                self.stdout.write("详细信息:")
                for detail in result['details']:
                    status = "✓" if detail['success'] else "✗"
                    action = detail['action']
                    name = f"{detail['name']} ({detail['type']})"
                    if detail['success']:
                        self.stdout.write(f"  {status} {action}: {name}")
                    else:
                        error = detail.get('error', '')
                        self.stdout.write(self.style.ERROR(f"  {status} {action}: {name} - {error}"))
            
            if result['failed'] > 0:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING("存在同步失败的项目，请检查日志"))
                
        except SurveyAPIError as e:
            self.stdout.write(self.style.ERROR(f"API 错误: {e}"))
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"同步失败: {e}"))
            raise

