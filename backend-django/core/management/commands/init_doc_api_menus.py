#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化文档 API 菜单命令

用法:
    python manage.py init_doc_api_menus
    python manage.py init_doc_api_menus --force  # 强制重新创建
"""
from django.core.management.base import BaseCommand
from core.menu.menu_model import Menu


class Command(BaseCommand):
    help = "初始化文档 API 菜单"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建所有菜单（删除现有菜单后重建）',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        if force:
            self.stdout.write(self.style.WARNING("强制模式：将删除现有文档 API 菜单后重建"))
            # 删除现有的文档 API 相关菜单
            Menu.objects.filter(path__startswith="/doc-api").delete()
        
        # 创建文档 API 菜单
        menu, created = Menu.objects.get_or_create(
            path="/doc-api",
            defaults={
                "name": "DocApi",
                "title": "HIS 接口文档",
                "type": "menu",
                "component": "/doc-api/index",
                "icon": "ant-design:api-outlined",
                "order": 102,
                "hideInMenu": False,
                "keepAlive": True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("✓ 创建菜单：HIS 接口文档"))
        else:
            self.stdout.write(self.style.NOTICE("○ 菜单已存在：HIS 接口文档"))
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("菜单初始化完成"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  - 菜单: {'新建' if created else '已存在'}")
        self.stdout.write(f"  - 路径: /doc-api")
        self.stdout.write(f"  - 组件: /doc-api/index")
        self.stdout.write("")
