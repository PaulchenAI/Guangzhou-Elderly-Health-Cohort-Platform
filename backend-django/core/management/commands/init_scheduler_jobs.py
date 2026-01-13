#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化定时任务命令

用法:
    python manage.py init_scheduler_jobs
    python manage.py init_scheduler_jobs --force  # 强制重新创建
"""
from django.core.management.base import BaseCommand
from scheduler.models import SchedulerJob


class Command(BaseCommand):
    help = "初始化定时任务（包括问卷数据同步任务）"

    # 预定义的定时任务配置
    DEFAULT_JOBS = [
        {
            "name": "问卷Schema同步",
            "code": "sync_survey_schemas",
            "description": "定时从外部API同步问卷Schema定义，建议每天凌晨执行一次",
            "group": "survey",
            "trigger_type": "cron",
            "cron_expression": "0 2 * * *",  # 每天凌晨2点
            "task_func": "scheduler.module.survey_tasks.sync_survey_schemas_task",
            "status": 1,  # 启用
            "priority": 10,
            "max_instances": 1,
            "max_retries": 3,
            "timeout": 300,  # 5分钟超时
            "coalesce": True,
        },
        {
            "name": "问卷数据增量导入",
            "code": "import_survey_data",
            "description": "定时增量导入问卷数据到本地数据库，建议每小时执行一次",
            "group": "survey",
            "trigger_type": "cron",
            "cron_expression": "0 * * * *",  # 每小时整点
            "task_func": "scheduler.module.survey_tasks.import_survey_data_task",
            "status": 1,  # 启用
            "priority": 5,
            "max_instances": 1,
            "max_retries": 3,
            "timeout": 600,  # 10分钟超时
            "coalesce": True,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建所有任务（删除现有任务后重建）',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='创建任务时默认禁用（状态设为0）',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        disable = options.get('disable', False)
        
        if force:
            self.stdout.write(self.style.WARNING("强制模式：将删除现有任务后重建"))
            # 删除预定义任务
            codes = [job["code"] for job in self.DEFAULT_JOBS]
            deleted_count = SchedulerJob.objects.filter(code__in=codes).delete()[0]
            if deleted_count > 0:
                self.stdout.write(self.style.WARNING(f"已删除 {deleted_count} 个现有任务"))
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for job_config in self.DEFAULT_JOBS:
            code = job_config["code"]
            
            # 如果指定了 --disable，将状态设为禁用
            if disable:
                job_config["status"] = 0
            
            # 检查任务是否已存在
            existing_job = SchedulerJob.objects.filter(code=code).first()
            
            if existing_job:
                if force:
                    # 强制模式下已删除，这里不会执行
                    pass
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.NOTICE(f"○ 任务已存在，跳过: {job_config['name']} ({code})")
                    )
                    continue
            
            # 创建新任务
            try:
                SchedulerJob.objects.create(**job_config)
                created_count += 1
                status_text = "禁用" if job_config["status"] == 0 else "启用"
                self.stdout.write(
                    self.style.SUCCESS(f"✓ 创建任务: {job_config['name']} ({code}) [{status_text}]")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ 创建任务失败: {job_config['name']} - {str(e)}")
                )
        
        # 统计信息
        total_jobs = SchedulerJob.objects.count()
        enabled_jobs = SchedulerJob.objects.filter(status=1).count()
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("定时任务初始化完成"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  - 新创建: {created_count}")
        self.stdout.write(f"  - 已跳过: {skipped_count}")
        self.stdout.write(f"  - 任务总数: {total_jobs}")
        self.stdout.write(f"  - 启用任务: {enabled_jobs}")
        self.stdout.write("")
        
        # 提示信息
        self.stdout.write(self.style.WARNING("提示:"))
        self.stdout.write("  1. 确保 ENABLE_SCHEDULER = True 已在环境配置中设置")
        self.stdout.write("  2. 启动调度器: python start_scheduler.py")
        self.stdout.write("  3. 或在前端 /tool/schedule 页面手动启动调度器")
        self.stdout.write("")
