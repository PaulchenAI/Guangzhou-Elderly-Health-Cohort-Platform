#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化字段级权限命令

用于为动态查询接口添加敏感字段的访问权限控制。

用法:
    python manage.py init_field_permissions
    python manage.py init_field_permissions --list      # 仅列出将要创建的权限
    python manage.py init_field_permissions --remove    # 删除字段级权限

权限编码规范: {module}:query:{field_name}

权限控制逻辑:
- 如果权限表中存在该字段的权限记录，且用户没有该权限 → 隐藏字段
- 如果权限表中不存在该字段的权限记录 → 字段对所有人可见
- 如果用户拥有该权限 → 字段可见可查询
"""
from django.core.management.base import BaseCommand
from core.permission.permission_model import Permission
from core.menu.menu_model import Menu
from core.role.role_model import Role


# 定义字段级权限配置
FIELD_PERMISSIONS = [
    {
        'name': '查询用户手机号',
        'code': 'user:query:mobile',
        'menu_keyword': '用户',
        'permission_type': 2,  # 数据权限
        'description': '允许在用户动态查询中使用手机号字段进行搜索和过滤',
    },
    {
        'name': '查询用户邮箱',
        'code': 'user:query:email',
        'menu_keyword': '用户',
        'permission_type': 2,
        'description': '允许在用户动态查询中使用邮箱字段进行搜索和过滤',
    },
    {
        'name': '查询登录IP',
        'code': 'login_log:query:login_ip',
        'menu_keyword': '登录日志',
        'permission_type': 2,
        'description': '允许在登录日志动态查询中使用IP地址字段进行搜索和过滤',
    },
]


class Command(BaseCommand):
    help = "初始化动态查询接口的字段级权限"

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='仅列出将要创建的权限，不执行创建',
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='删除字段级权限',
        )
        parser.add_argument(
            '--assign-admin',
            action='store_true',
            default=True,
            help='为管理员角色分配新创建的权限（默认开启）',
        )

    def handle(self, *args, **options):
        list_only = options.get('list', False)
        remove = options.get('remove', False)
        assign_admin = options.get('assign_admin', True)

        if remove:
            self._remove_permissions()
            return

        if list_only:
            self._list_permissions()
            return

        self._create_permissions(assign_admin)

    def _find_menu(self, keyword):
        """查找菜单，按优先级尝试不同的匹配方式"""
        # 优先精确匹配
        menu = Menu.objects.filter(name__icontains=keyword, is_deleted=False).first()
        if menu:
            return menu
        
        # 尝试匹配 title
        menu = Menu.objects.filter(title__icontains=keyword, is_deleted=False).first()
        if menu:
            return menu
        
        # 备用：查找系统管理菜单
        menu = Menu.objects.filter(name__icontains='系统', is_deleted=False).first()
        return menu

    def _list_permissions(self):
        """列出将要创建的权限"""
        self.stdout.write(self.style.SUCCESS("\n将要创建的字段级权限："))
        self.stdout.write("=" * 60)
        
        for perm in FIELD_PERMISSIONS:
            menu = self._find_menu(perm['menu_keyword'])
            exists = Permission.objects.filter(code=perm['code']).exists()
            status = self.style.WARNING("已存在") if exists else self.style.SUCCESS("待创建")
            
            self.stdout.write(f"\n  权限编码: {perm['code']}")
            self.stdout.write(f"  权限名称: {perm['name']}")
            self.stdout.write(f"  关联菜单: {menu.name if menu else '未找到'}")
            self.stdout.write(f"  状态: {status}")
        
        self.stdout.write("\n" + "=" * 60)

    def _create_permissions(self, assign_admin):
        """创建字段级权限"""
        self.stdout.write(self.style.SUCCESS("\n开始初始化字段级权限..."))
        self.stdout.write("=" * 60)
        
        created_permissions = []
        skipped_count = 0
        
        for perm in FIELD_PERMISSIONS:
            menu = self._find_menu(perm['menu_keyword'])
            
            if not menu:
                self.stdout.write(self.style.ERROR(
                    f"✗ 跳过 {perm['code']}: 未找到关联菜单 '{perm['menu_keyword']}'"
                ))
                continue
            
            # 使用 get_or_create 确保幂等性
            permission, created = Permission.objects.get_or_create(
                code=perm['code'],
                defaults={
                    'name': perm['name'],
                    'menu': menu,
                    'permission_type': perm['permission_type'],
                    'description': perm['description'],
                    'is_active': True,
                }
            )
            
            if created:
                created_permissions.append(permission)
                self.stdout.write(self.style.SUCCESS(
                    f"✓ 创建权限: {perm['code']} -> {menu.name}"
                ))
            else:
                skipped_count += 1
                self.stdout.write(self.style.NOTICE(
                    f"○ 权限已存在: {perm['code']}"
                ))
        
        # 为管理员角色分配权限
        if assign_admin and created_permissions:
            admin_role = Role.objects.filter(code='admin').first()
            if admin_role:
                for permission in created_permissions:
                    admin_role.permission.add(permission)
                self.stdout.write(self.style.SUCCESS(
                    f"\n✓ 已为管理员角色分配 {len(created_permissions)} 个新权限"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "\n! 未找到管理员角色 (code='admin')，请手动分配权限"
                ))
        
        # 清除缓存
        if created_permissions:
            from common.fu_crud import invalidate_field_permission_cache
            invalidate_field_permission_cache()
            self.stdout.write(self.style.SUCCESS("✓ 已清除字段权限缓存"))
        
        # 统计信息
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("初始化完成"))
        self.stdout.write(f"  - 新建权限: {len(created_permissions)}")
        self.stdout.write(f"  - 跳过(已存在): {skipped_count}")
        self.stdout.write("")

    def _remove_permissions(self):
        """删除字段级权限"""
        self.stdout.write(self.style.WARNING("\n开始删除字段级权限..."))
        self.stdout.write("=" * 60)
        
        codes_to_delete = [perm['code'] for perm in FIELD_PERMISSIONS]
        
        # 查询要删除的权限
        permissions = Permission.objects.filter(code__in=codes_to_delete)
        count = permissions.count()
        
        if count == 0:
            self.stdout.write(self.style.NOTICE("没有找到要删除的字段级权限"))
            return
        
        # 列出将要删除的权限
        for perm in permissions:
            self.stdout.write(f"  - {perm.code}: {perm.name}")
        
        # 执行删除
        deleted_count, _ = permissions.delete()
        
        # 清除缓存
        from common.fu_crud import invalidate_field_permission_cache
        invalidate_field_permission_cache()
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"已删除 {deleted_count} 个字段级权限"))
        self.stdout.write(self.style.SUCCESS("已清除字段权限缓存"))
        self.stdout.write("")
