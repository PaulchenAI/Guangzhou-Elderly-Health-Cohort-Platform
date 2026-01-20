#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步问卷数据到表查询系统命令

将问卷数据（SurveyRecord）同步到表查询系统的对应表中。

用法:
    # 同步所有问卷类型的数据（增量）
    python manage.py sync_survey_to_table_query
    
    # 同步指定类型
    python manage.py sync_survey_to_table_query --type personality
    
    # 全量同步（先清空再导入）
    python manage.py sync_survey_to_table_query --full
    
    # 显示详细进度
    python manage.py sync_survey_to_table_query --verbose
"""
import time
from django.core.management.base import BaseCommand

from core.survey.survey_model import SurveySchemaConfig
from core.table_query.table_query_sync_service import TableQuerySyncService


class Command(BaseCommand):
    help = "同步问卷数据到表查询系统"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            dest='survey_type',
            help='要同步的问卷类型（不指定则同步全部）',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            dest='full_sync',
            help='全量同步（先清空表再导入）',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            dest='batch_size',
            help='批量插入大小（默认 100）',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            dest='verbose',
            help='显示详细进度',
        )

    def handle(self, *args, **options):
        survey_type = options.get('survey_type')
        full_sync = options.get('full_sync', False)
        batch_size = options.get('batch_size', 100)
        verbose = options.get('verbose', False)
        
        start_time = time.time()
        
        # 输出配置信息
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("同步问卷数据到表查询系统"))
        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write("")
        self.stdout.write(f"问卷类型: {survey_type or '全部'}")
        self.stdout.write(f"同步模式: {'全量' if full_sync else '增量'}")
        self.stdout.write(f"批量大小: {batch_size}")
        self.stdout.write("")
        
        try:
            sync_service = TableQuerySyncService()
            
            # 获取要同步的类型列表
            if survey_type:
                survey_types = [survey_type]
            else:
                configs = SurveySchemaConfig.objects.filter(
                    is_active=True,
                    is_deleted=False
                )
                survey_types = [c.survey_type for c in configs]
            
            if not survey_types:
                self.stdout.write(self.style.WARNING("没有可同步的问卷类型"))
                return
            
            self.stdout.write(f"将同步 {len(survey_types)} 个问卷类型:")
            for st in survey_types:
                self.stdout.write(f"  - {st}")
            self.stdout.write("")
            
            # 逐个类型同步
            total_success = 0
            total_failed = 0
            
            for st in survey_types:
                type_start = time.time()
                
                if verbose:
                    self.stdout.write(f"正在同步: {st}...")
                
                result = sync_service.sync_survey_data(
                    survey_type=st,
                    full_sync=full_sync,
                    batch_size=batch_size,
                )
                
                type_duration = time.time() - type_start
                
                total_success += result["success"]
                total_failed += result["failed"]
                
                if result["success"] > 0 or result["failed"] > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {st}: 成功 {result['success']}, "
                            f"失败 {result['failed']}, "
                            f"耗时 {type_duration:.2f}秒"
                        )
                    )
                    if result.get("table_name"):
                        self.stdout.write(f"    表名: {result['table_name']}")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  {st}: 无数据需要同步")
                    )
                
                # 输出错误信息
                if result["errors"] and verbose:
                    self.stdout.write(self.style.ERROR("    错误:"))
                    for error in result["errors"][:5]:
                        self.stdout.write(self.style.ERROR(f"      {error}"))
            
            # 输出汇总
            duration = time.time() - start_time
            
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("同步完成"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(f"总计成功: {total_success}")
            self.stdout.write(f"总计失败: {total_failed}")
            self.stdout.write(f"总耗时: {duration:.2f}秒")
            
            if total_success > 0:
                self.stdout.write(f"平均速度: {total_success / duration:.1f} 条/秒")
            
            self.stdout.write("")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"同步失败: {e}"))
            raise
