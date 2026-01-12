#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Survey Tasks - 问卷数据定时任务

提供问卷数据同步和导入的定时任务函数。

任务配置示例：
    1. Schema 同步任务
       - 任务编码: sync_survey_schemas
       - 任务函数: scheduler.module.survey_tasks.sync_survey_schemas_task
       - Cron 表达式: 0 2 * * * (每天凌晨2点)
    
    2. 数据导入任务
       - 任务编码: import_survey_data
       - 任务函数: scheduler.module.survey_tasks.import_survey_data_task
       - Cron 表达式: 0 * * * * (每小时)
"""
import logging

from scheduler.module.executor import scheduler_task

logger = logging.getLogger(__name__)


@scheduler_task
def sync_survey_schemas_task(**kwargs):
    """
    定时同步问卷 Schema
    
    建议调度：每天凌晨执行一次
    Cron 表达式：0 2 * * *
    
    功能：
    1. 从外部 API 获取所有问卷类型
    2. 获取每个类型的 Schema 定义
    3. 更新本地 SurveySchemaConfig 表
    
    Returns:
        str: 同步结果描述
    """
    try:
        from core.survey.survey_service import SurveyService
        
        logger.info("开始执行 Schema 同步定时任务")
        
        service = SurveyService()
        result = service.sync_schemas()
        
        message = (
            f"Schema 同步完成: "
            f"新增 {result['created']}, "
            f"更新 {result['updated']}, "
            f"失败 {result['failed']}"
        )
        
        logger.info(message)
        return message
        
    except Exception as e:
        logger.error(f"Schema 同步定时任务失败: {e}")
        raise


@scheduler_task
def import_survey_data_task(**kwargs):
    """
    定时增量导入问卷数据
    
    建议调度：每小时执行一次
    Cron 表达式：0 * * * *
    
    功能：
    1. 查询外部 API 获取最新问卷数据
    2. 增量导入到本地数据库（跳过已存在的记录）
    3. 记录导入日志
    
    Returns:
        str: 导入结果描述
    """
    try:
        from core.survey.survey_service import SurveyService
        
        logger.info("开始执行数据导入定时任务")
        
        service = SurveyService()
        result = service.import_data(
            incremental=True,
            trigger_type="scheduled",
        )
        
        message = (
            f"数据导入完成 [批次: {result['batch_id']}]: "
            f"总计 {result['total']}, "
            f"成功 {result['success']}, "
            f"跳过 {result['skipped']}, "
            f"失败 {result['failed']}"
        )
        
        logger.info(message)
        return message
        
    except Exception as e:
        logger.error(f"数据导入定时任务失败: {e}")
        raise


@scheduler_task
def import_survey_data_by_type_task(survey_type: str = None, **kwargs):
    """
    按类型导入问卷数据
    
    Args:
        survey_type: 问卷类型（如：fried, rockwood）
        **kwargs: 其他参数
    
    Returns:
        str: 导入结果描述
    """
    try:
        from core.survey.survey_service import SurveyService
        
        logger.info(f"开始执行按类型导入任务: {survey_type}")
        
        service = SurveyService()
        result = service.import_data(
            survey_type=survey_type,
            incremental=True,
            trigger_type="scheduled",
        )
        
        message = (
            f"[{survey_type}] 导入完成: "
            f"成功 {result['success']}, "
            f"跳过 {result['skipped']}, "
            f"失败 {result['failed']}"
        )
        
        logger.info(message)
        return message
        
    except Exception as e:
        logger.error(f"按类型导入任务失败: {e}")
        raise

