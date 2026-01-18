# -*- coding: utf-8 -*-
"""
Django 管理命令：生成字段描述增强建议

扫描 Django 模型中的 ForeignKey 和 ManyToManyField 字段，
生成符合规范的字段描述建议，帮助 AI 理解表之间的关联关系。

使用方法：
    # 预览模式（显示所有建议）
    python manage.py enhance_field_descriptions --dry-run
    
    # 输出到 JSON 文件
    python manage.py enhance_field_descriptions --output suggestions.json
    
    # 仅扫描指定 app
    python manage.py enhance_field_descriptions --app-labels core
    
    # 排除 Django 内置 app
    python manage.py enhance_field_descriptions --exclude-apps admin,auth,contenttypes,sessions
    
    # JSON 格式输出
    python manage.py enhance_field_descriptions --format json
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models


@dataclass
class FieldSuggestion:
    """字段描述增强建议"""
    model: str                    # 模型名称（如 core.User）
    model_db_table: str           # 模型对应的数据库表名
    field_name: str               # 字段名称
    field_type: str               # 字段类型（ForeignKey/ManyToManyField）
    current_help_text: str        # 当前的 help_text
    suggested_help_text: str      # 建议的 help_text
    target_model: str             # 目标模型名称
    target_table: str             # 目标表名
    target_field: str             # 目标字段（通常为 id）
    is_self_reference: bool       # 是否为自引用
    on_delete: Optional[str]      # 删除规则（仅 ForeignKey）
    through_table: Optional[str]  # 中间表名（仅 ManyToManyField）
    needs_update: bool            # 是否需要更新


@dataclass
class ScanSummary:
    """扫描统计摘要"""
    total_apps: int = 0
    total_models: int = 0
    total_foreignkey_fields: int = 0
    total_m2m_fields: int = 0
    fields_needing_update: int = 0
    fields_already_enhanced: int = 0


class Command(BaseCommand):
    help = '扫描 Django 模型，生成字段描述增强建议'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，仅显示建议',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='输出建议到指定文件',
        )
        parser.add_argument(
            '--app-labels',
            type=str,
            help='指定要扫描的 app（逗号分隔）',
        )
        parser.add_argument(
            '--exclude-apps',
            type=str,
            default='admin,auth,contenttypes,sessions,django_celery_beat,django_celery_results',
            help='排除指定的 app（逗号分隔）',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='输出格式：text/json（默认 text）',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细信息',
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.output_file = options['output']
        self.output_format = options['format']
        self.verbose = options['verbose']
        
        # 解析 app 过滤参数
        app_labels = None
        if options['app_labels']:
            app_labels = [a.strip() for a in options['app_labels'].split(',')]
        
        exclude_apps = []
        if options['exclude_apps']:
            exclude_apps = [a.strip() for a in options['exclude_apps'].split(',')]
        
        # 扫描模型
        suggestions, summary = self._scan_models(app_labels, exclude_apps)
        
        # 输出结果
        if self.output_format == 'json':
            self._output_json(suggestions, summary)
        else:
            self._output_text(suggestions, summary)
        
        # 保存到文件
        if self.output_file:
            self._save_to_file(suggestions, summary)
    
    def _scan_models(
        self, 
        app_labels: Optional[List[str]], 
        exclude_apps: List[str]
    ) -> tuple[List[FieldSuggestion], ScanSummary]:
        """扫描 Django 模型，提取关联字段信息"""
        suggestions = []
        summary = ScanSummary()
        
        # 获取所有 app 配置
        all_apps = apps.get_app_configs()
        
        for app_config in all_apps:
            app_label = app_config.label
            
            # 过滤 app
            if app_labels and app_label not in app_labels:
                continue
            if app_label in exclude_apps:
                continue
            
            summary.total_apps += 1
            
            # 遍历 app 中的所有模型
            for model in app_config.get_models():
                summary.total_models += 1
                model_name = f"{app_label}.{model.__name__}"
                db_table = model._meta.db_table
                
                if self.verbose:
                    self.stdout.write(f"扫描模型: {model_name} ({db_table})")
                
                # 遍历模型的所有字段
                for field_obj in model._meta.get_fields():
                    suggestion = self._analyze_field(model, model_name, db_table, field_obj)
                    if suggestion:
                        suggestions.append(suggestion)
                        
                        if suggestion.field_type == 'ForeignKey':
                            summary.total_foreignkey_fields += 1
                        else:
                            summary.total_m2m_fields += 1
                        
                        if suggestion.needs_update:
                            summary.fields_needing_update += 1
                        else:
                            summary.fields_already_enhanced += 1
        
        return suggestions, summary
    
    def _analyze_field(
        self, 
        model, 
        model_name: str, 
        db_table: str, 
        field_obj
    ) -> Optional[FieldSuggestion]:
        """分析单个字段，生成描述建议"""
        
        # 只处理 ForeignKey 和 ManyToManyField
        if isinstance(field_obj, models.ForeignKey):
            return self._analyze_foreignkey(model, model_name, db_table, field_obj)
        elif isinstance(field_obj, models.ManyToManyField):
            return self._analyze_m2m(model, model_name, db_table, field_obj)
        
        return None
    
    def _analyze_foreignkey(
        self, 
        model, 
        model_name: str, 
        db_table: str, 
        field_obj: models.ForeignKey
    ) -> FieldSuggestion:
        """分析 ForeignKey 字段"""
        field_name = field_obj.name
        current_help_text = field_obj.help_text or ""
        
        # 获取目标模型信息
        related_model = field_obj.related_model
        target_model_name = f"{related_model._meta.app_label}.{related_model.__name__}"
        target_table = related_model._meta.db_table
        target_field = related_model._meta.pk.name if related_model._meta.pk else 'id'
        
        # 判断是否为自引用
        is_self_reference = related_model == model
        
        # 获取删除规则
        on_delete = self._get_on_delete_name(field_obj.remote_field.on_delete)
        
        # 生成建议的 help_text
        suggested_help_text = self._generate_fk_help_text(
            current_help_text, 
            target_table, 
            target_field, 
            is_self_reference
        )
        
        # 判断是否需要更新
        needs_update = not self._is_already_enhanced(current_help_text, target_table)
        
        return FieldSuggestion(
            model=model_name,
            model_db_table=db_table,
            field_name=field_name,
            field_type='ForeignKey',
            current_help_text=current_help_text,
            suggested_help_text=suggested_help_text,
            target_model=target_model_name,
            target_table=target_table,
            target_field=target_field,
            is_self_reference=is_self_reference,
            on_delete=on_delete,
            through_table=None,
            needs_update=needs_update,
        )
    
    def _analyze_m2m(
        self, 
        model, 
        model_name: str, 
        db_table: str, 
        field_obj: models.ManyToManyField
    ) -> Optional[FieldSuggestion]:
        """分析 ManyToManyField 字段"""
        # 跳过反向关系
        if not hasattr(field_obj, 'field'):
            # 这是正向关系
            pass
        else:
            # 这是反向关系（ManyToManyRel），跳过
            return None
        
        field_name = field_obj.name
        current_help_text = field_obj.help_text or ""
        
        # 获取目标模型信息
        related_model = field_obj.related_model
        target_model_name = f"{related_model._meta.app_label}.{related_model.__name__}"
        target_table = related_model._meta.db_table
        target_field = related_model._meta.pk.name if related_model._meta.pk else 'id'
        
        # 获取中间表信息
        through_model = field_obj.remote_field.through
        through_table = through_model._meta.db_table if through_model else None
        
        # 判断是否为自引用
        is_self_reference = related_model == model
        
        # 生成建议的 help_text
        suggested_help_text = self._generate_m2m_help_text(
            current_help_text, 
            target_table, 
            through_table,
            is_self_reference
        )
        
        # 判断是否需要更新
        needs_update = not self._is_already_enhanced(current_help_text, target_table)
        
        return FieldSuggestion(
            model=model_name,
            model_db_table=db_table,
            field_name=field_name,
            field_type='ManyToManyField',
            current_help_text=current_help_text,
            suggested_help_text=suggested_help_text,
            target_model=target_model_name,
            target_table=target_table,
            target_field=target_field,
            is_self_reference=is_self_reference,
            on_delete=None,
            through_table=through_table,
            needs_update=needs_update,
        )
    
    def _get_on_delete_name(self, on_delete) -> str:
        """获取 on_delete 的名称"""
        on_delete_map = {
            models.CASCADE: 'CASCADE',
            models.PROTECT: 'PROTECT',
            models.SET_NULL: 'SET_NULL',
            models.SET_DEFAULT: 'SET_DEFAULT',
            models.DO_NOTHING: 'DO_NOTHING',
        }
        return on_delete_map.get(on_delete, 'UNKNOWN')
    
    def _generate_fk_help_text(
        self, 
        current: str, 
        target_table: str, 
        target_field: str,
        is_self_reference: bool
    ) -> str:
        """生成 ForeignKey 字段的建议 help_text"""
        # 提取业务含义（去除已有的关联信息）
        business_meaning = self._extract_business_meaning(current)
        
        if not business_meaning:
            business_meaning = "关联字段"
        
        # 生成关联信息
        if is_self_reference:
            relation_info = f"自引用 {target_table}.{target_field}"
        else:
            relation_info = f"关联 {target_table}.{target_field}"
        
        return f"{business_meaning}，{relation_info}"
    
    def _generate_m2m_help_text(
        self, 
        current: str, 
        target_table: str, 
        through_table: Optional[str],
        is_self_reference: bool
    ) -> str:
        """生成 ManyToManyField 字段的建议 help_text"""
        # 提取业务含义
        business_meaning = self._extract_business_meaning(current)
        
        if not business_meaning:
            business_meaning = "多对多关联"
        
        # 生成关联信息
        if through_table:
            relation_info = f"多对多关联 {target_table}，中间表 {through_table}"
        else:
            relation_info = f"多对多关联 {target_table}"
        
        if is_self_reference:
            relation_info = f"自引用，{relation_info}"
        
        return f"{business_meaning}，{relation_info}"
    
    def _extract_business_meaning(self, help_text: str) -> str:
        """从 help_text 中提取业务含义（去除关联信息）"""
        if not help_text:
            return ""
        
        # 去除已有的关联信息
        markers = ['，关联', '，自引用', '，多对多关联', '（关联', '（自引用']
        for marker in markers:
            if marker in help_text:
                return help_text.split(marker)[0].strip()
        
        return help_text.strip()
    
    def _is_already_enhanced(self, help_text: str, target_table: str) -> bool:
        """检查 help_text 是否已经包含关联信息"""
        if not help_text:
            return False
        
        # 检查是否包含关联信息
        markers = ['关联', '自引用', '多对多关联']
        has_marker = any(marker in help_text for marker in markers)
        
        # 检查是否包含目标表名
        has_target = target_table in help_text
        
        return has_marker and has_target
    
    def _output_text(self, suggestions: List[FieldSuggestion], summary: ScanSummary):
        """文本格式输出"""
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("字段描述增强建议报告"))
        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))
        
        # 输出统计摘要
        self.stdout.write(f"扫描 App 数量: {summary.total_apps}")
        self.stdout.write(f"扫描模型数量: {summary.total_models}")
        self.stdout.write(f"ForeignKey 字段数: {summary.total_foreignkey_fields}")
        self.stdout.write(f"ManyToManyField 字段数: {summary.total_m2m_fields}")
        self.stdout.write(f"需要更新的字段: {summary.fields_needing_update}")
        self.stdout.write(f"已增强的字段: {summary.fields_already_enhanced}")
        self.stdout.write("")
        
        # 按模型分组输出建议
        current_model = None
        for s in suggestions:
            if s.model != current_model:
                current_model = s.model
                self.stdout.write(self.style.MIGRATE_HEADING(f"\n## {s.model} ({s.model_db_table})"))
            
            status = "✓ 已增强" if not s.needs_update else "⚠ 需更新"
            status_style = self.style.SUCCESS if not s.needs_update else self.style.WARNING
            
            self.stdout.write(f"\n  {s.field_name} ({s.field_type})")
            self.stdout.write(f"    状态: {status_style(status)}")
            self.stdout.write(f"    目标: {s.target_table}.{s.target_field}")
            if s.is_self_reference:
                self.stdout.write(f"    类型: 自引用")
            if s.on_delete:
                self.stdout.write(f"    on_delete: {s.on_delete}")
            if s.through_table:
                self.stdout.write(f"    中间表: {s.through_table}")
            self.stdout.write(f"    当前: \"{s.current_help_text}\"")
            if s.needs_update:
                self.stdout.write(self.style.SUCCESS(f"    建议: \"{s.suggested_help_text}\""))
        
        self.stdout.write("")
    
    def _output_json(self, suggestions: List[FieldSuggestion], summary: ScanSummary):
        """JSON 格式输出"""
        output = {
            "suggestions": [asdict(s) for s in suggestions],
            "summary": asdict(summary),
        }
        self.stdout.write(json.dumps(output, ensure_ascii=False, indent=2))
    
    def _save_to_file(self, suggestions: List[FieldSuggestion], summary: ScanSummary):
        """保存到文件"""
        output = {
            "suggestions": [asdict(s) for s in suggestions],
            "summary": asdict(summary),
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output, ensure_ascii=False, indent=2, fp=f)
        
        self.stdout.write(self.style.SUCCESS(f"\n建议已保存到: {self.output_file}"))
