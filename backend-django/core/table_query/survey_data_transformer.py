#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey Data Transformer - 问卷数据转换器

负责将问卷系统的 JSON 数据展开为关系型表结构。

功能：
1. JSON 字段展开（支持嵌套结构）
2. 字段类型推断
3. 字段显示名称映射
"""
import logging
import re
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


class SurveyDataTransformer:
    """
    问卷数据转换器
    
    将问卷数据中的 JSON 字段展开为扁平化结构，
    便于存储到关系型数据库表中。
    """
    
    # 字段名中文映射（参考前端 formatFieldName）
    FIELD_NAME_MAP: Dict[str, str] = {
        # 评分相关
        "totalScore": "总分",
        "total_score": "总分",
        "averageScore": "平均分",
        "average_score": "平均分",
        "answeredCount": "已答题数",
        "totalQuestions": "总题数",
        "completeness": "完成度",
        "percentage": "百分比",
        "scores": "各项得分",
        "level": "等级",
        "description": "描述",
        "color": "颜色",
        "total": "总计",
        "filled": "已填",
        "count": "数量",
        "average": "平均值",
        "anxietyScore": "焦虑评分",
        "depressionScore": "抑郁评分",
        # 性格特征/心理状态相关
        "required": "必填项",
        "personality": "性格特征",
        "mentalState": "心理状态",
        "personalityScores": "性格评分",
        "mentalStateScores": "心理状态评分",
        # 户外活动相关
        "mainVenue": "主要场所",
        "weekendRatio": "周末活动比例",
        "totalDuration": "总时长(分钟)",
        "averageDuration": "平均时长(分钟)",
        "totalActivities": "活动总数",
        "mainActivityType": "主要活动类型",
        "activityFrequency": "活动频率",
        "route": "路线",
        "venue": "场所",
        "category": "活动类别",
        "duration": "时长(分钟)",
        "isWeekend": "是否周末",
        "itemsUsed": "使用物品",
        "startTime": "开始时间",
        "activityCode": "活动代码",
        "mostCommonVenue": "最常去场所",
        "mostCommonCategory": "最常见类别",
        "weekdayActivities": "工作日活动数",
        "weekendActivities": "周末活动数",
        "venueDistribution": "场所分布",
        "categoryDistribution": "类别分布",
        # 患者信息相关
        "patientName": "患者姓名",
        "patient_name": "患者姓名",
        "age": "年龄",
        "gender": "性别",
        "height": "身高",
        "weight": "体重",
        "phone": "电话",
        "remarks": "备注",
        # 记录信息
        "recordTime": "记录时间",
        "record_time": "记录时间",
        "createdAt": "创建时间",
        "created_at": "创建时间",
        "recorderName": "记录者姓名",
        "recorder_name": "记录者姓名",
        # 问卷信息
        "surveyId": "问卷ID",
        "survey_id": "问卷ID",
        "surveyType": "问卷类型",
        "survey_type": "问卷类型",
        # 通用评估字段
        "diagnosis": "诊断结果",
        "recommendation": "建议",
        "recommendations": "建议",
        "maxTotalScore": "最高可得分",
        "max_total_score": "最高可得分",
    }
    
    # 需要跳过展开的字段（保持原始 JSON 格式）
    SKIP_EXPAND_FIELDS: Set[str] = {
        "activities",  # 户外活动列表，数据量大
        "raw_data",  # 原始数据
    }
    
    # 日期时间格式正则
    DATETIME_PATTERNS = [
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO 格式
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # 标准格式
    ]
    
    def __init__(
        self,
        schema_config: Optional[Dict[str, Any]] = None,
        max_depth: int = 3,
        skip_expand_fields: Optional[Set[str]] = None,
    ):
        """
        初始化转换器
        
        Args:
            schema_config: 问卷 Schema 配置，用于获取字段类型和显示名称
            max_depth: 最大展开深度
            skip_expand_fields: 额外的跳过展开字段
        """
        self.schema_config = schema_config or {}
        self.max_depth = max_depth
        self.skip_expand_fields = self.SKIP_EXPAND_FIELDS.copy()
        if skip_expand_fields:
            self.skip_expand_fields.update(skip_expand_fields)
        
        # 从 Schema 构建字段配置映射
        self._field_configs: Dict[str, Dict[str, Any]] = {}
        self._build_field_configs()
    
    def _build_field_configs(self):
        """从 Schema 构建字段配置映射"""
        fields = self.schema_config.get("fields", [])
        for field in fields:
            field_name = field.get("name") or field.get("fieldName")
            if field_name:
                self._field_configs[field_name] = field
    
    def expand_record(
        self,
        record: Dict[str, Any],
        prefix: str = "",
        depth: int = 0,
    ) -> Dict[str, Any]:
        """
        展开单条问卷记录的 JSON 字段
        
        Args:
            record: 问卷记录数据
            prefix: 字段前缀
            depth: 当前深度
            
        Returns:
            展开后的扁平化数据
        """
        result = {}
        
        for key, value in record.items():
            # 构建完整的字段名
            full_key = f"{prefix}{key}" if prefix else key
            
            # 检查是否需要跳过展开
            if key in self.skip_expand_fields:
                result[full_key] = value  # 保持原样（可能是 JSON）
                continue
            
            # 根据值类型决定如何处理
            if value is None:
                result[full_key] = None
            elif isinstance(value, dict) and depth < self.max_depth:
                # 递归展开嵌套对象
                nested = self.expand_record(value, f"{full_key}_", depth + 1)
                result.update(nested)
            elif isinstance(value, list):
                # 数组类型处理
                result[full_key] = self._handle_array(value, full_key)
            else:
                # 基本类型直接保存
                result[full_key] = value
        
        return result
    
    def _handle_array(self, value: List, field_name: str) -> Any:
        """
        处理数组类型字段
        
        Args:
            value: 数组值
            field_name: 字段名
            
        Returns:
            处理后的值（JSON 字符串或原值）
        """
        if not value:
            return None
        
        # 如果数组元素是简单类型，转为逗号分隔的字符串
        first_item = value[0]
        if isinstance(first_item, (str, int, float, bool)):
            return ",".join(str(v) for v in value)
        
        # 复杂数组保持为 JSON
        import json
        return json.dumps(value, ensure_ascii=False)
    
    def transform_survey_record(self, survey_record) -> Dict[str, Any]:
        """
        转换问卷记录模型为扁平化数据
        
        Args:
            survey_record: SurveyRecord 模型实例
            
        Returns:
            扁平化后的数据字典
        """
        # 基础字段
        result = {
            "survey_id": survey_record.survey_id,
            "survey_type": survey_record.survey_type,
            "patient_name": survey_record.patient_name,
            "record_time": survey_record.record_time,
            "sys_create_datetime": survey_record.sys_create_datetime,
        }
        
        # 展开 patient_info
        if survey_record.patient_info:
            patient_expanded = self.expand_record(
                survey_record.patient_info, 
                "patient_info_"
            )
            result.update(patient_expanded)
        
        # 展开 survey_data
        if survey_record.survey_data:
            survey_expanded = self.expand_record(
                survey_record.survey_data,
                "survey_data_"
            )
            result.update(survey_expanded)
        
        # 展开 scores
        if survey_record.scores:
            scores_expanded = self.expand_record(
                survey_record.scores,
                "scores_"
            )
            result.update(scores_expanded)
        
        # 展开 recorder_info
        if survey_record.recorder_info:
            recorder_expanded = self.expand_record(
                survey_record.recorder_info,
                "recorder_"
            )
            result.update(recorder_expanded)
        
        return result
    
    def infer_field_type(self, value: Any, field_name: str = "") -> str:
        """
        推断字段类型
        
        Args:
            value: 字段值
            field_name: 字段名（用于从 Schema 获取类型）
            
        Returns:
            字段类型字符串：string/integer/decimal/boolean/datetime/json
        """
        # 优先从 Schema 获取类型
        if field_name in self._field_configs:
            schema_type = self._field_configs[field_name].get("type")
            if schema_type:
                return self._normalize_type(schema_type)
        
        # 空值默认为 string
        if value is None:
            return "string"
        
        # 根据值类型推断
        if isinstance(value, bool):
            return "boolean"
        
        if isinstance(value, int):
            return "integer"
        
        if isinstance(value, float) or isinstance(value, Decimal):
            return "decimal"
        
        if isinstance(value, datetime):
            return "datetime"
        
        if isinstance(value, str):
            # 检查是否为日期时间字符串
            for pattern in self.DATETIME_PATTERNS:
                if re.match(pattern, value):
                    return "datetime"
            return "string"
        
        if isinstance(value, (dict, list)):
            return "json"
        
        return "string"

    def normalize_datetime_value(self, value: Any) -> Optional[datetime]:
        """
        将常见的日期时间字符串转换为 Python datetime，便于写入 MySQL DATETIME 字段。

        支持：
        - 2025-11-10T10:42:35.048Z
        - 2025-11-10T10:42:35Z
        - 2025-11-10T10:42:35
        - 2025-11-10 10:42:35
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = parse_datetime(value)
            if dt is None:
                # 兼容 Z 结尾（标准库/部分解析器对 'Z' 支持不一致）
                v = value.strip()
                if v.endswith("Z"):
                    v = v[:-1] + "+00:00"
                dt = parse_datetime(v)
        else:
            return None

        if dt is None:
            return None

        # MySQL DATETIME 不存储时区，统一转换为 UTC naive
        if timezone.is_aware(dt):
            return timezone.make_naive(dt, timezone=dt_timezone.utc)
        return dt
    
    def _normalize_type(self, schema_type: str) -> str:
        """规范化 Schema 类型到数据库类型"""
        type_map = {
            "int": "integer",
            "number": "decimal",
            "float": "decimal",
            "bool": "boolean",
            "date": "datetime",
            "text": "string",
            "array": "json",
            "object": "json",
        }
        return type_map.get(schema_type.lower(), schema_type.lower())
    
    def get_display_name(self, field_name: str) -> str:
        """
        获取字段显示名称
        
        Args:
            field_name: 字段名
            
        Returns:
            中文显示名称
        """
        # 表同步后的基础字段中文（与前端“问卷数据查询”保持一致）
        base_name_map = {
            "survey_id": "问卷ID",
            "survey_type": "问卷类型",
            "patient_name": "患者姓名",
            "record_time": "记录时间",
            "sys_create_datetime": "创建时间",
            "raw_json": "原始JSON数据",
        }
        if field_name in base_name_map:
            return base_name_map[field_name]

        # 优先从 Schema 获取
        if field_name in self._field_configs:
            display = (
                self._field_configs[field_name].get("title") or
                self._field_configs[field_name].get("label") or
                self._field_configs[field_name].get("display_name")
            )
            if display:
                return display
        
        # 从映射表获取
        if field_name in self.FIELD_NAME_MAP:
            return self.FIELD_NAME_MAP[field_name]

        # 处理展开字段：优先对齐前端“问卷数据查询”的列标题（通常只展示叶子字段中文）
        # 例如：patient_info_age -> 年龄；survey_data_totalScore -> 总分
        for prefix in ("patient_info_", "survey_data_", "scores_", "recorder_"):
            if field_name.startswith(prefix):
                leaf = field_name[len(prefix):]
                # 叶子字段可能仍是多级展开：details_item1 -> item1
                leaf_last = leaf.split("_")[-1] if leaf else leaf

                # 先尝试 Schema（Schema 里通常是原始字段名，无前缀）
                for candidate in (leaf, leaf_last):
                    if candidate in self._field_configs:
                        display = (
                            self._field_configs[candidate].get("title") or
                            self._field_configs[candidate].get("label") or
                            self._field_configs[candidate].get("display_name")
                        )
                        if display:
                            return display

                # 再尝试前端映射（formatFieldName）
                if leaf in self.FIELD_NAME_MAP:
                    return self.FIELD_NAME_MAP[leaf]
                if leaf_last in self.FIELD_NAME_MAP:
                    return self.FIELD_NAME_MAP[leaf_last]

                # 最后兜底：格式化叶子字段
                readable = re.sub(r'([a-z])([A-Z])', r'\1 \2', leaf_last)
                return readable.replace("_", " ").title()

        # 其他包含下划线的字段：尝试使用最后一段做中文映射（避免“前缀_叶子”导致中文错位）
        if "_" in field_name:
            last = field_name.split("_")[-1]
            if last in self.FIELD_NAME_MAP:
                return self.FIELD_NAME_MAP[last]
        
        # camelCase 转为可读格式
        readable = re.sub(r'([a-z])([A-Z])', r'\1 \2', field_name)
        return readable.replace("_", " ").title()
    
    def analyze_fields(
        self,
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        分析记录集合，推断所有字段的配置
        
        Args:
            records: 展开后的记录列表
            
        Returns:
            字段配置列表，每个字段包含 name, display_name, type, searchable, sortable
        """
        if not records:
            return []
        
        # 收集所有字段和示例值
        field_samples: Dict[str, Any] = {}
        for record in records:
            for field, value in record.items():
                if field not in field_samples and value is not None:
                    field_samples[field] = value
        
        # 生成字段配置
        fields = []
        for field_name, sample_value in field_samples.items():
            field_type = self.infer_field_type(sample_value, field_name)
            display_name = self.get_display_name(field_name)
            
            # 默认配置
            searchable = field_type in ("string", "integer")
            sortable = field_type in ("string", "integer", "decimal", "datetime")
            
            # 从 Schema 获取配置
            if field_name in self._field_configs:
                config = self._field_configs[field_name]
                searchable = config.get("searchable", searchable)
                sortable = config.get("sortable", sortable)
            
            fields.append({
                "name": field_name,
                "display_name": display_name,
                "displayName": display_name,  # 兼容前端格式
                "type": field_type,
                "searchable": searchable,
                "sortable": sortable,
                "visible": True,
            })
        
        return fields
    
    def get_sql_column_type(self, field_type: str) -> str:
        """
        获取 SQL 列类型
        
        Args:
            field_type: 推断的字段类型
            
        Returns:
            SQL 列类型定义
        """
        type_map = {
            # NOTE: 对问卷展开字段，列数可能非常多。使用 TEXT 避免 InnoDB 行大小限制（65535）
            "string": "TEXT",
            "integer": "INT",
            "decimal": "DECIMAL(20,4)",
            "boolean": "TINYINT(1)",
            "datetime": "DATETIME",
            "json": "JSON",
        }
        return type_map.get(field_type, "TEXT")
