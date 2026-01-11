#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建示例表查询配置

用法:
    python manage.py create_sample_table_configs
    python manage.py create_sample_table_configs --table WORKFLOW_REQUESTBASE
"""
from django.core.management.base import BaseCommand
from django.db import connection
from core.table_query.table_query_model import TableQueryConfig


# 预定义的表配置（注意：MySQL 列名是小写的）
SAMPLE_CONFIGS = {
    "WORKFLOW_REQUESTBASE": {
        "display_name": "工作流请求",
        "description": "工作流系统请求基础数据表",
        "config_json": {
            "fields": [
                {"name": "requestid", "displayName": "请求ID", "type": "integer", "searchable": True, "sortable": True, "visible": True, "width": 100},
                {"name": "requestname", "displayName": "请求名称", "type": "string", "searchable": True, "sortable": True, "visible": True, "width": 200},
                {"name": "creater", "displayName": "创建人", "type": "string", "searchable": True, "visible": True, "width": 100},
                {"name": "createdate", "displayName": "创建日期", "type": "datetime", "searchable": True, "sortable": True, "visible": True, "width": 150},
                {"name": "status", "displayName": "状态", "type": "string", "searchable": True, "sortable": True, "visible": True, "width": 100},
                {"name": "workflowid", "displayName": "流程ID", "type": "integer", "sortable": True, "visible": True, "width": 100},
            ],
            "defaultPageSize": 20,
            "maxPageSize": 100,
            "defaultOrderBy": "requestid DESC",
            "allowedOperations": ["query", "export"]
        }
    },
    "WORKFLOW_BILL": {
        "display_name": "工作流表单",
        "description": "工作流表单定义表",
        "config_json": {
            "fields": [
                {"name": "id", "displayName": "ID", "type": "integer", "searchable": True, "sortable": True, "visible": True, "width": 80},
                {"name": "tablename", "displayName": "表名", "type": "string", "searchable": True, "sortable": True, "visible": True, "width": 200},
                {"name": "namelabel", "displayName": "表单名称", "type": "string", "searchable": True, "visible": True, "width": 200},
                {"name": "createby", "displayName": "创建人", "type": "string", "visible": True, "width": 100},
                {"name": "createdate", "displayName": "创建日期", "type": "datetime", "sortable": True, "visible": True, "width": 150},
            ],
            "defaultPageSize": 20,
            "maxPageSize": 100,
            "defaultOrderBy": "id DESC",
            "allowedOperations": ["query", "export"]
        }
    },
}


class Command(BaseCommand):
    help = "创建示例表查询配置"

    def add_arguments(self, parser):
        parser.add_argument(
            '--table',
            type=str,
            help='指定要创建配置的表名',
        )
        parser.add_argument(
            '--auto-detect',
            action='store_true',
            help='自动检测表结构并创建配置',
        )

    def handle(self, *args, **options):
        table_name = options.get('table')
        auto_detect = options.get('auto_detect', False)
        
        if table_name:
            # 创建指定表的配置
            if table_name in SAMPLE_CONFIGS:
                self._create_config(table_name, SAMPLE_CONFIGS[table_name])
            elif auto_detect:
                self._auto_create_config(table_name)
            else:
                self.stdout.write(self.style.ERROR(
                    f"表 {table_name} 没有预定义配置，使用 --auto-detect 自动检测"
                ))
        else:
            # 创建所有预定义配置
            for tbl_name, config in SAMPLE_CONFIGS.items():
                self._create_config(tbl_name, config)
        
        # 显示统计
        count = TableQueryConfig.objects.filter(is_deleted=False).count()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"当前共有 {count} 个表查询配置"))

    def _create_config(self, table_name, config_data):
        """创建或更新配置"""
        obj, created = TableQueryConfig.objects.update_or_create(
            table_name=table_name,
            defaults={
                "display_name": config_data["display_name"],
                "description": config_data.get("description", ""),
                "config_json": config_data["config_json"],
                "is_active": True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ 创建配置: {table_name}"))
        else:
            self.stdout.write(self.style.NOTICE(f"○ 更新配置: {table_name}"))

    def _auto_create_config(self, table_name):
        """自动检测表结构并创建配置"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
            
            if not columns:
                self.stdout.write(self.style.ERROR(f"表 {table_name} 不存在或没有列"))
                return
            
            # 根据列信息生成字段配置
            fields = []
            for col in columns:
                col_name = col[0]
                col_type = col[1].lower()
                
                # 映射数据库类型到前端类型
                if 'int' in col_type:
                    field_type = 'integer'
                elif 'decimal' in col_type or 'float' in col_type or 'double' in col_type:
                    field_type = 'decimal'
                elif 'date' in col_type and 'time' not in col_type:
                    field_type = 'date'
                elif 'datetime' in col_type or 'timestamp' in col_type:
                    field_type = 'datetime'
                else:
                    field_type = 'string'
                
                fields.append({
                    "name": col_name,
                    "displayName": col_name,
                    "type": field_type,
                    "searchable": field_type == 'string',
                    "sortable": True,
                    "visible": True,
                    "width": 150 if field_type == 'string' else 100,
                })
            
            config_data = {
                "display_name": table_name,
                "description": f"自动生成的 {table_name} 表配置",
                "config_json": {
                    "fields": fields[:20],  # 限制最多20个字段
                    "defaultPageSize": 20,
                    "maxPageSize": 100,
                    "defaultOrderBy": f"{fields[0]['name']} DESC" if fields else "id DESC",
                    "allowedOperations": ["query", "export"]
                }
            }
            
            self._create_config(table_name, config_data)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"自动检测失败: {e}"))

