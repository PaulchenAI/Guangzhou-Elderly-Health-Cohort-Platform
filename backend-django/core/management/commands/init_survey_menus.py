#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化问卷管理菜单命令

用法:
    python manage.py init_survey_menus
    python manage.py init_survey_menus --force  # 强制重新创建
"""
from django.core.management.base import BaseCommand
from core.menu.menu_model import Menu
from core.survey.survey_model import SurveySchemaConfig


class Command(BaseCommand):
    help = "初始化问卷管理菜单"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建所有菜单（删除现有菜单后重建）',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        if force:
            self.stdout.write(self.style.WARNING("强制模式：将删除现有问卷管理菜单后重建"))
            # 删除现有的问卷管理相关菜单
            Menu.objects.filter(path__startswith="/survey").delete()
        
        # 创建或获取父菜单
        parent_menu, parent_created = Menu.objects.get_or_create(
            path="/survey",
            defaults={
                "name": "Survey",
                "title": "问卷管理",
                "type": "catalog",
                "component": "LAYOUT",
                "icon": "ant-design:form-outlined",
                "order": 101,
                "hideInMenu": False,
            }
        )
        
        if parent_created:
            self.stdout.write(self.style.SUCCESS("✓ 创建父菜单：问卷管理"))
        else:
            self.stdout.write(self.style.NOTICE("○ 父菜单已存在：问卷管理"))
        
        # 创建主查询页面菜单
        main_menu, main_created = Menu.objects.get_or_create(
            path="/survey/index",
            defaults={
                "name": "SurveyIndex",
                "title": "问卷数据查询",
                "type": "menu",
                "parent": parent_menu,
                "component": "/survey/index",
                "icon": "ant-design:search-outlined",
                "order": 0,
                "keepAlive": True,
            }
        )
        
        if main_created:
            self.stdout.write(self.style.SUCCESS("✓ 创建菜单：问卷数据查询"))
        else:
            self.stdout.write(self.style.NOTICE("○ 菜单已存在：问卷数据查询"))
        
        # 统计信息
        schemas = SurveySchemaConfig.objects.filter(is_active=True, is_deleted=False)
        schema_count = schemas.count()
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("菜单初始化完成"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  - 父菜单: {'新建' if parent_created else '已存在'}")
        self.stdout.write(f"  - 主菜单: {'新建' if main_created else '已存在'}")
        self.stdout.write(f"  - 已同步 Schema 数: {schema_count}")
        self.stdout.write("")
        
        if schema_count == 0:
            self.stdout.write(self.style.WARNING(
                "提示: 当前没有问卷 Schema，请先运行同步命令"
            ))
            self.stdout.write(self.style.WARNING(
                "      python manage.py sync_survey_schemas"
            ))

