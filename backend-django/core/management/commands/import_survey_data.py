#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入问卷数据命令

从外部问卷调查 API 导入问卷数据到本地数据库。

用法:
    # 导入所有类型的数据（增量）
    python manage.py import_survey_data
    
    # 导入指定类型
    python manage.py import_survey_data --type fried
    
    # 导入指定日期范围
    python manage.py import_survey_data --start-date 2024-01-01 --end-date 2024-12-31
    
    # 全量导入（不跳过已存在的记录）
    python manage.py import_survey_data --full
"""
from django.core.management.base import BaseCommand

from core.survey.survey_api_client import SurveyAPIError, get_survey_api_client
from core.survey.survey_service import SurveyService


class Command(BaseCommand):
    help = "从外部 API 导入问卷数据"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            dest='survey_type',
            help='要导入的问卷类型（不指定则导入全部）',
        )
        parser.add_argument(
            '--start-date',
            dest='start_date',
            help='开始日期（YYYY-MM-DD）',
        )
        parser.add_argument(
            '--end-date',
            dest='end_date',
            help='结束日期（YYYY-MM-DD）',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            dest='full_import',
            help='全量导入（不跳过已存在的记录）',
        )
        parser.add_argument(
            '--page-size',
            type=int,
            default=100,
            dest='page_size',
            help='每页查询数量（默认 100）',
        )

    def handle(self, *args, **options):
        survey_type = options.get('survey_type')
        start_date = options.get('start_date')
        end_date = options.get('end_date')
        full_import = options.get('full_import', False)
        page_size = options.get('page_size', 100)
        
        incremental = not full_import
        
        try:
            client = get_survey_api_client()
            
            # 输出配置信息
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("=" * 60))
            self.stdout.write(self.style.NOTICE("开始导入问卷数据"))
            self.stdout.write(self.style.NOTICE("=" * 60))
            self.stdout.write("")
            self.stdout.write(f"问卷类型: {survey_type or '全部'}")
            self.stdout.write(f"日期范围: {start_date or '不限'} ~ {end_date or '不限'}")
            self.stdout.write(f"导入模式: {'增量' if incremental else '全量'}")
            self.stdout.write(f"每页数量: {page_size}")
            self.stdout.write("")
            
            # 执行导入
            service = SurveyService(client)
            result = service.import_data(
                survey_type=survey_type,
                start_date=start_date,
                end_date=end_date,
                incremental=incremental,
                trigger_type="manual",
                page_size=page_size,
            )
            
            # 输出结果
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("导入完成"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(f"批次ID: {result['batch_id']}")
            self.stdout.write(f"  总计: {result['total']}")
            self.stdout.write(f"  成功: {result['success']}")
            self.stdout.write(f"  跳过: {result['skipped']}")
            self.stdout.write(f"  失败: {result['failed']}")
            self.stdout.write("")
            
            # 输出错误信息
            if result['errors']:
                self.stdout.write(self.style.WARNING("错误详情（最多显示 10 条）:"))
                for error in result['errors'][:10]:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
                
                if len(result['errors']) > 10:
                    self.stdout.write(self.style.WARNING(f"  ... 还有 {len(result['errors']) - 10} 条错误"))
            
            if result['failed'] > 0:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING("存在导入失败的记录，请检查日志"))
                
        except SurveyAPIError as e:
            self.stdout.write(self.style.ERROR(f"API 错误: {e}"))
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"导入失败: {e}"))
            raise

