#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey Service - 问卷数据服务层

负责：
- Schema 同步
- 数据导入
- 数据转换
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from core.survey.survey_api_client import (
    SurveyAPIClient,
    SurveyAPIError,
    get_survey_api_client,
)
from core.survey.survey_model import (
    SurveyImportLog,
    SurveyRecord,
    SurveySchemaConfig,
)

logger = logging.getLogger(__name__)


class SurveyService:
    """
    问卷数据服务
    
    功能：
    1. 同步问卷 Schema
    2. 导入问卷数据
    3. 数据转换
    """
    
    def __init__(self, client: SurveyAPIClient = None):
        """
        初始化服务
        
        Args:
            client: API 客户端（默认使用全局实例）
        """
        self.client = client or get_survey_api_client()
    
    def sync_schemas(
        self, 
        survey_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        同步问卷 Schema
        
        Args:
            survey_types: 要同步的问卷类型列表（为空则同步全部）
            
        Returns:
            {
                "created": 5,
                "updated": 3,
                "failed": 0,
                "details": [...]
            }
        """
        logger.info(f"开始同步问卷 Schema: {survey_types or '全部'}")
        
        result = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # 获取问卷类型列表
            types_response = self.client.get_survey_types()
            all_types = types_response.get("surveys", [])
            
            # 过滤要同步的类型
            if survey_types:
                types_to_sync = [t for t in all_types if t.get("type") in survey_types]
            else:
                types_to_sync = all_types
            
            logger.info(f"将同步 {len(types_to_sync)} 个问卷类型")
            
            for type_info in types_to_sync:
                survey_type = type_info.get("type")
                survey_name = type_info.get("name", survey_type)
                description = type_info.get("description", "")
                
                try:
                    # 获取 Schema
                    schema_data = self.client.get_survey_schema(survey_type)
                    
                    # 更新或创建
                    config, created = SurveySchemaConfig.objects.update_or_create(
                        survey_type=survey_type,
                        defaults={
                            "survey_name": schema_data.get("surveyName", survey_name),
                            "description": schema_data.get("description", description),
                            "schema_json": schema_data,
                            "guide_url": schema_data.get("guideUrl", ""),
                            "last_synced_at": timezone.now(),
                            "is_active": True,
                        }
                    )
                    
                    if created:
                        result["created"] += 1
                        action = "新增"
                    else:
                        result["updated"] += 1
                        action = "更新"
                    
                    result["details"].append({
                        "type": survey_type,
                        "name": survey_name,
                        "action": action,
                        "success": True,
                    })
                    
                    logger.info(f"  {action} Schema: {survey_type} ({survey_name})")
                    
                except SurveyAPIError as e:
                    result["failed"] += 1
                    result["details"].append({
                        "type": survey_type,
                        "name": survey_name,
                        "action": "失败",
                        "success": False,
                        "error": str(e),
                    })
                    logger.error(f"  同步失败: {survey_type} - {e}")
            
            logger.info(
                f"Schema 同步完成: 新增 {result['created']}, "
                f"更新 {result['updated']}, 失败 {result['failed']}"
            )
            
        except SurveyAPIError as e:
            logger.error(f"获取问卷类型列表失败: {e}")
            raise
        
        return result
    
    def import_data(
        self,
        survey_type: str = None,
        start_date: str = None,
        end_date: str = None,
        incremental: bool = True,
        trigger_type: str = "manual",
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        导入问卷数据
        
        Args:
            survey_type: 问卷类型（为空则导入全部）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            incremental: 是否增量导入（跳过已存在的记录）
            trigger_type: 触发类型（manual/scheduled）
            page_size: 每页数量
            
        Returns:
            {
                "batch_id": "xxx",
                "total": 100,
                "success": 95,
                "skipped": 3,
                "failed": 2,
                "errors": [...]
            }
        """
        batch_id = str(uuid.uuid4())[:8]
        start_time = timezone.now()
        
        logger.info(f"开始导入问卷数据 [批次: {batch_id}]")
        logger.info(f"  类型: {survey_type or '全部'}, 增量: {incremental}")
        
        # 创建导入日志
        import_log = SurveyImportLog.objects.create(
            batch_id=batch_id,
            survey_type=survey_type,
            status="running",
            trigger_type=trigger_type,
            start_time=start_time,
        )
        
        result = {
            "batch_id": batch_id,
            "total": 0,
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # 确定要导入的问卷类型
            if survey_type:
                types_to_import = [survey_type]
            else:
                # 获取所有已同步的 Schema
                configs = SurveySchemaConfig.objects.filter(
                    is_active=True, 
                    is_deleted=False
                )
                types_to_import = [c.survey_type for c in configs]
            
            if not types_to_import:
                logger.warning("没有可导入的问卷类型，请先同步 Schema")
                import_log.status = "failed"
                import_log.error_details = [{"error": "没有可导入的问卷类型"}]
                import_log.end_time = timezone.now()
                import_log.save()
                return result
            
            # 逐个类型导入
            for stype in types_to_import:
                type_result = self._import_survey_type(
                    survey_type=stype,
                    start_date=start_date,
                    end_date=end_date,
                    incremental=incremental,
                    page_size=page_size,
                )
                
                result["total"] += type_result["total"]
                result["success"] += type_result["success"]
                result["skipped"] += type_result["skipped"]
                result["failed"] += type_result["failed"]
                result["errors"].extend(type_result["errors"])
            
            # 更新导入日志
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            import_log.total_count = result["total"]
            import_log.success_count = result["success"]
            import_log.skip_count = result["skipped"]
            import_log.fail_count = result["failed"]
            import_log.error_details = result["errors"][:100]  # 只保留前100条错误
            import_log.end_time = end_time
            import_log.duration_seconds = duration
            
            if result["failed"] == 0:
                import_log.status = "success"
            elif result["success"] > 0:
                import_log.status = "partial"
            else:
                import_log.status = "failed"
            
            import_log.save()
            
            logger.info(
                f"数据导入完成 [批次: {batch_id}]: "
                f"总计 {result['total']}, 成功 {result['success']}, "
                f"跳过 {result['skipped']}, 失败 {result['failed']}, "
                f"耗时 {duration:.2f}秒"
            )
            
        except Exception as e:
            logger.error(f"数据导入异常 [批次: {batch_id}]: {e}")
            import_log.status = "failed"
            import_log.error_details = [{"error": str(e)}]
            import_log.end_time = timezone.now()
            import_log.save()
            raise
        
        return result
    
    def _normalize_survey_type_for_api(self, survey_type: str) -> str:
        """
        将本地的 survey_type 格式转换为外部 API 搜索接口需要的格式
        
        外部 API 的搜索接口对类型名称格式敏感：
        - Schema 接口返回：personal_info（带下划线）
        - 搜索接口需要：personalinfo（无下划线）
        
        Args:
            survey_type: 本地存储的类型名称（如 personal_info）
            
        Returns:
            适用于 API 搜索的类型名称（如 personalinfo）
        """
        # 移除下划线以匹配外部 API 搜索接口的格式
        return survey_type.replace("_", "")
    
    def _import_survey_type(
        self,
        survey_type: str,
        start_date: str = None,
        end_date: str = None,
        incremental: bool = True,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """
        导入单个问卷类型的数据
        """
        logger.info(f"  导入问卷类型: {survey_type}")
        
        # 转换类型名称格式用于 API 搜索
        api_survey_type = self._normalize_survey_type_for_api(survey_type)
        
        result = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
        
        page = 1
        while True:
            # 构建查询参数（使用转换后的类型名称）
            params = {
                "survey_type": api_survey_type,
                "page": page,
                "page_size": page_size,
            }
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            try:
                # 查询数据
                response = self.client.search_surveys(params)
                items = response.get("items", [])
                total = response.get("total", 0)
                
                if not items:
                    break
                
                result["total"] += len(items)
                
                # 批量处理
                for item in items:
                    try:
                        # 优先使用外部数据库的唯一 id，组合成全局唯一标识
                        external_id = item.get("id")
                        if external_id:
                            # 使用 survey_type + 外部id 组成唯一标识
                            survey_id = f"{survey_type}_{external_id}"
                        else:
                            # 兼容旧格式
                            survey_id = item.get("surveyId") or item.get("survey_id")
                        
                        if not survey_id:
                            result["failed"] += 1
                            result["errors"].append({
                                "type": survey_type,
                                "error": "缺少唯一标识（id 或 surveyId）",
                                "data": str(item)[:200]
                            })
                            continue
                        
                        # 检查是否已存在
                        if incremental:
                            if SurveyRecord.objects.filter(survey_id=survey_id).exists():
                                result["skipped"] += 1
                                continue
                        
                        # 转换并保存（使用 update_or_create 处理全量模式下的重复）
                        record = self._convert_to_record(survey_type, item, survey_id)
                        if not incremental:
                            # 全量模式：更新或创建
                            SurveyRecord.objects.update_or_create(
                                survey_id=survey_id,
                                defaults={
                                    'survey_type': record.survey_type,
                                    'patient_name': record.patient_name,
                                    'patient_info': record.patient_info,
                                    'survey_data': record.survey_data,
                                    'scores': record.scores,
                                    'record_time': record.record_time,
                                    'recorder_info': record.recorder_info,
                                    'external_created_at': record.external_created_at,
                                }
                            )
                        else:
                            record.save()
                        result["success"] += 1
                        
                    except Exception as e:
                        result["failed"] += 1
                        result["errors"].append({
                            "type": survey_type,
                            "survey_id": survey_id if 'survey_id' in dir() else "unknown",
                            "error": str(e)
                        })
                
                # 检查是否还有更多页
                if page * page_size >= total:
                    break
                page += 1
                
            except SurveyAPIError as e:
                logger.error(f"    查询失败: {e}")
                result["errors"].append({
                    "type": survey_type,
                    "page": page,
                    "error": str(e)
                })
                break
        
        logger.info(
            f"    完成: 总计 {result['total']}, 成功 {result['success']}, "
            f"跳过 {result['skipped']}, 失败 {result['failed']}"
        )
        
        return result
    
    def _convert_to_record(
        self, 
        survey_type: str, 
        item: Dict[str, Any],
        survey_id: str = None
    ) -> SurveyRecord:
        """
        将外部数据转换为本地记录
        
        Args:
            survey_type: 问卷类型
            item: 外部数据
            survey_id: 唯一标识（如果未提供则从 item 中提取）
            
        Returns:
            SurveyRecord 实例
        """
        # 使用传入的 survey_id 或从数据中提取
        if not survey_id:
            external_id = item.get("id")
            if external_id:
                survey_id = f"{survey_type}_{external_id}"
            else:
                survey_id = item.get("surveyId") or item.get("survey_id")
        
        # 外部 API 返回的数据可能嵌套在 data 字段中
        data = item.get("data", {}) or {}
        
        # 提取患者信息（优先从顶层取，否则从 data 中取）
        patient_name = (
            item.get("patient_name") or
            item.get("patientName") or 
            data.get("patientName") or 
            data.get("patient_name") or 
            "未填写"
        )
        
        # 从 data 或顶层提取患者详细信息
        patient_info = {
            "age": data.get("age") or item.get("age"),
            "gender": data.get("gender") or item.get("gender"),
            "height": data.get("height") or item.get("height"),
            "weight": data.get("weight") or item.get("weight"),
            "phone": data.get("phone") or item.get("phone"),
            "remarks": data.get("remarks") or item.get("remarks"),
        }
        # 移除空值
        patient_info = {k: v for k, v in patient_info.items() if v is not None}
        
        # 提取记录者信息
        recorder_info = {
            "name": data.get("recorderName") or item.get("recorder_name"),
            "position": data.get("recorderPosition"),
            "institution": data.get("recorderInstitution"),
            "contact": data.get("recorderContact"),
        }
        recorder_info = {k: v for k, v in recorder_info.items() if v is not None}
        
        # 提取评分信息（从 data 中提取）
        scores = self._extract_scores(survey_type, data if data else item)
        
        # 问卷数据使用 data 字段的内容，或者整个 item（移除通用字段）
        common_fields = {
            "id", "survey_type", "survey_id", "patient_name", "recorder_name", "data",
            "surveyId", "patientName", "age", "gender", "height", "weight", "phone", "remarks",
            "recorderName", "recorderPosition", "recorderInstitution", "recorderContact",
            "recordTime", "record_time", "createdAt", "created_at",
        }
        if data:
            survey_data = data  # 直接使用 data 字段作为问卷数据
        else:
            survey_data = {k: v for k, v in item.items() if k not in common_fields}
        
        # 解析时间（优先从 data 中取）
        record_time_str = data.get("recordTime") or data.get("record_time") or item.get("recordTime") or item.get("record_time")
        created_at_str = data.get("createdAt") or data.get("created_at") or item.get("createdAt") or item.get("created_at")
        
        record_time = self._parse_datetime(record_time_str) or timezone.now()
        external_created_at = self._parse_datetime(created_at_str)
        
        return SurveyRecord(
            survey_type=survey_type,
            survey_id=survey_id,
            patient_name=patient_name,
            patient_info=patient_info,
            survey_data=survey_data,
            scores=scores,
            record_time=record_time,
            recorder_info=recorder_info,
            external_created_at=external_created_at,
            raw_data=item,
        )
    
    def _extract_scores(
        self, 
        survey_type: str, 
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取评分信息
        
        自动提取所有包含 'score' 关键字的字段，以及其他评分相关字段
        """
        scores = {}
        
        # 明确的评分字段列表
        explicit_score_fields = [
            "totalScore", "total_score",
            "diagnosis", "level", "category",
            "cfsScore", "cfs_score",
            "recommendations",
            "maxTotalScore", "max_total_score",
        ]
        
        # 提取明确的评分字段
        for field in explicit_score_fields:
            if field in item and item[field] is not None:
                key = self._to_snake_case(field)
                scores[key] = item[field]
        
        # 自动提取所有包含 'score' 或 'Score' 的字段（支持复合评分数据）
        for field, value in item.items():
            if value is not None:
                field_lower = field.lower()
                # 检查字段名是否包含评分关键字
                if 'score' in field_lower or 'total' in field_lower:
                    key = self._to_snake_case(field)
                    if key not in scores:  # 避免重复
                        scores[key] = value
        
        return scores
    
    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """
        解析日期时间字符串
        """
        if not value:
            return None
        
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        return None
    
    def _to_snake_case(self, name: str) -> str:
        """
        将 camelCase 转换为 snake_case
        """
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

