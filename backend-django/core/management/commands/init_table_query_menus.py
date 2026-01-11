#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化表查询菜单命令

用法:
    python manage.py init_table_query_menus
    python manage.py init_table_query_menus --force  # 强制重新创建
"""
from django.core.management.base import BaseCommand
from core.menu.menu_model import Menu
from core.table_query.table_query_model import TableQueryConfig


class Command(BaseCommand):
    help = "初始化表查询菜单"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建所有菜单（删除现有菜单后重建）',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        if force:
            self.stdout.write(self.style.WARNING("强制模式：将删除现有表查询菜单后重建"))
            # 删除现有的表查询相关菜单
            Menu.objects.filter(path__startswith="/table-query").delete()
        
        # 创建或获取父菜单
        parent_menu, parent_created = Menu.objects.get_or_create(
            path="/table-query",
            defaults={
                "name": "TableQuery",
                "title": "数据查询",
                "type": "catalog",
                "component": "LAYOUT",
                "icon": "ant-design:database-outlined",
                "order": 100,
                "hideInMenu": False,
            }
        )
        
        if parent_created:
            self.stdout.write(self.style.SUCCESS("✓ 创建父菜单：数据查询"))
        else:
            self.stdout.write(self.style.NOTICE("○ 父菜单已存在：数据查询"))
        
        # 创建主查询页面菜单
        main_menu, main_created = Menu.objects.get_or_create(
            path="/table-query/index",
            defaults={
                "name": "TableQueryIndex",
                "title": "表数据查询",
                "type": "menu",
                "parent": parent_menu,
                "component": "/table-query/index",
                "icon": "ant-design:search-outlined",
                "order": 0,
                "keepAlive": True,
            }
        )
        
        if main_created:
            self.stdout.write(self.style.SUCCESS("✓ 创建菜单：表数据查询"))
        else:
            self.stdout.write(self.style.NOTICE("○ 菜单已存在：表数据查询"))
        
        # 统计信息
        configs = TableQueryConfig.objects.filter(is_active=True, is_deleted=False)
        config_count = configs.count()
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("菜单初始化完成"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  - 父菜单: {'新建' if parent_created else '已存在'}")
        self.stdout.write(f"  - 主菜单: {'新建' if main_created else '已存在'}")
        self.stdout.write(f"  - 可用配置数: {config_count}")
        self.stdout.write("")
        
        if config_count == 0:
            self.stdout.write(self.style.WARNING(
                "提示: 当前没有表查询配置，请先通过 API 或 Admin 创建配置"
            ))
            self.stdout.write(self.style.WARNING(
                "      POST /api/core/table-query/configs"
            ))

