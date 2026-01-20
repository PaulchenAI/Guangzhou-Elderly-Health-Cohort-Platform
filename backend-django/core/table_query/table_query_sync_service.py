#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Table Query Sync Service - 表查询系统同步服务

负责将问卷数据同步到表查询系统。

功能：
1. 自动创建问卷数据表（survey_{survey_type}）
2. 自动生成表查询配置（TableQueryConfig）
3. 数据同步（增量/全量）
4. 表结构更新（Schema 变更时添加新字段）
"""
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db import connection, transaction
from django.utils import timezone

from core.survey.survey_model import SurveyRecord, SurveySchemaConfig
from core.table_query.survey_data_transformer import SurveyDataTransformer
from core.table_query.table_query_model import TableQueryConfig

logger = logging.getLogger(__name__)


class TableQuerySyncService:
    """
    表查询系统同步服务
    
    将问卷数据同步到对应的表查询表中，
    支持自动创建表、生成配置、增量/全量同步。
    """
    
    # 表名前缀
    TABLE_PREFIX = "survey_"
    
    # 基础字段（所有表都有的字段）
    BASE_COLUMNS = [
        ("id", "BIGINT AUTO_INCREMENT PRIMARY KEY"),
        ("survey_id", "VARCHAR(100) NOT NULL UNIQUE"),
        ("survey_type", "VARCHAR(50) NOT NULL"),
        ("patient_name", "VARCHAR(100)"),
        ("record_time", "DATETIME"),
        ("sys_create_datetime", "DATETIME"),
        ("raw_json", "JSON COMMENT '原始JSON数据'"),
    ]
    
    # 基础索引
    BASE_INDEXES = [
        "INDEX idx_survey_id (survey_id)",
        "INDEX idx_patient_name (patient_name)",
        "INDEX idx_record_time (record_time)",
    ]
    
    def __init__(self):
        """初始化同步服务"""
        self._existing_tables: Set[str] = set()
        self._refresh_existing_tables()
    
    def _refresh_existing_tables(self):
        """刷新已存在的表列表"""
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'survey_%'")
            self._existing_tables = {row[0] for row in cursor.fetchall()}
    
    def _get_table_name(self, survey_type: str) -> str:
        """
        获取问卷类型对应的表名
        
        Args:
            survey_type: 问卷类型
            
        Returns:
            表名（如 survey_personality）
        """
        # 规范化表名（转小写，替换特殊字符）
        safe_type = survey_type.lower().replace("-", "_").replace(" ", "_")
        return f"{self.TABLE_PREFIX}{safe_type}"
    
    def _table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name.lower() in {t.lower() for t in self._existing_tables}
    
    def _get_existing_columns(self, table_name: str) -> Set[str]:
        """获取表的现有列名"""
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            return {row[0] for row in cursor.fetchall()}
    
    def create_survey_table(
        self,
        survey_type: str,
        field_configs: List[Dict[str, Any]],
    ) -> str:
        """
        创建问卷数据表
        
        Args:
            survey_type: 问卷类型
            field_configs: 字段配置列表
            
        Returns:
            创建的表名
        """
        table_name = self._get_table_name(survey_type)
        
        if self._table_exists(table_name):
            logger.info(f"表 {table_name} 已存在，跳过创建")
            return table_name
        
        # 构建列定义
        columns = list(self.BASE_COLUMNS)
        
        # 添加展开的字段
        base_column_names = {col[0] for col in self.BASE_COLUMNS}
        for field in field_configs:
            field_name = field["name"]
            if field_name in base_column_names:
                continue
            
            field_type = field.get("type", "string")
            sql_type = self._get_sql_type(field_type)
            display_name = field.get("display_name", field_name)
            columns.append((field_name, f"{sql_type} COMMENT '{display_name}'"))
        
        # 构建 CREATE TABLE SQL
        column_defs = ",\n    ".join(f"`{col[0]}` {col[1]}" for col in columns)
        index_defs = ",\n    ".join(self.BASE_INDEXES)
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {column_defs},
            {index_defs}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='问卷数据表 - {survey_type}'
        """
        
        logger.info(f"创建表: {table_name}")
        logger.debug(f"SQL: {sql}")
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
        
        self._existing_tables.add(table_name)
        return table_name
    
    def _get_sql_type(self, field_type: str) -> str:
        """获取字段的 SQL 类型"""
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
    
    def update_table_schema(
        self,
        table_name: str,
        field_configs: List[Dict[str, Any]],
    ) -> List[str]:
        """
        更新表结构（添加新字段）
        
        Args:
            table_name: 表名
            field_configs: 字段配置列表
            
        Returns:
            新增的列名列表
        """
        if not self._table_exists(table_name):
            logger.warning(f"表 {table_name} 不存在，无法更新")
            return []
        
        existing_columns = self._get_existing_columns(table_name)
        added_columns = []
        
        for field in field_configs:
            field_name = field["name"]
            if field_name.lower() in {c.lower() for c in existing_columns}:
                continue
            
            field_type = field.get("type", "string")
            sql_type = self._get_sql_type(field_type)
            display_name = field.get("display_name", field_name)
            
            sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {sql_type} COMMENT '{display_name}'"
            
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                added_columns.append(field_name)
                logger.info(f"添加列: {table_name}.{field_name}")
            except Exception as e:
                logger.error(f"添加列失败: {table_name}.{field_name}, {e}")
        
        return added_columns
    
    def create_or_update_config(
        self,
        survey_type: str,
        table_name: str,
        field_configs: List[Dict[str, Any]],
        survey_name: str = None,
    ) -> TableQueryConfig:
        """
        创建或更新表查询配置
        
        Args:
            survey_type: 问卷类型
            table_name: 表名
            field_configs: 字段配置列表
            survey_name: 问卷名称（用于显示）
            
        Returns:
            TableQueryConfig 实例
        """
        display_name = survey_name or f"问卷数据-{survey_type}"
        
        # 构建配置 JSON
        config_json = {
            "fields": field_configs,
            "defaultPageSize": 20,
            "maxPageSize": 100,
            "defaultOrderBy": "record_time DESC",
            "allowedOperations": ["query", "export"],
        }
        
        config, created = TableQueryConfig.objects.update_or_create(
            table_name=table_name,
            defaults={
                "display_name": display_name,
                "description": f"问卷类型: {survey_type} 的数据查询配置",
                "config_json": config_json,
                "is_active": True,
            }
        )
        
        action = "创建" if created else "更新"
        logger.info(f"{action}表查询配置: {table_name} ({display_name})")
        
        return config
    
    def sync_survey_data(
        self,
        survey_type: str,
        records: List[SurveyRecord] = None,
        full_sync: bool = False,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        同步问卷数据到表查询系统
        
        Args:
            survey_type: 问卷类型
            records: 要同步的记录列表（为空则从数据库查询）
            full_sync: 是否全量同步
            batch_size: 批量插入大小
            
        Returns:
            同步结果统计
        """
        result = {
            "survey_type": survey_type,
            "success": 0,
            "failed": 0,
            "errors": [],
            "table_name": None,
            "config_id": None,
        }
        
        records_for_error_count = None
        try:
            # 获取 Schema 配置
            schema_config = SurveySchemaConfig.objects.filter(
                survey_type=survey_type,
                is_active=True,
                is_deleted=False
            ).first()
            
            schema_json = schema_config.schema_json if schema_config else {}
            survey_name = schema_config.survey_name if schema_config else None
            
            # 创建转换器
            transformer = SurveyDataTransformer(schema_config=schema_json)
            
            # 获取要同步的记录
            if records is None:
                records = list(SurveyRecord.objects.filter(
                    survey_type=survey_type,
                    is_deleted=False
                ).order_by('-sys_create_datetime'))
            records_for_error_count = records
            
            if not records:
                logger.info(f"没有需要同步的记录: {survey_type}")
                return result
            
            # 转换数据
            transformed_records = []
            for record in records:
                try:
                    data = transformer.transform_survey_record(record)
                    data["raw_json"] = json.dumps(record.raw_data, ensure_ascii=False) if record.raw_data else None
                    transformed_records.append(data)
                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append({
                        "survey_id": record.survey_id,
                        "error": str(e)
                    })
            
            if not transformed_records:
                return result
            
            # 分析字段配置
            field_configs = transformer.analyze_fields(transformed_records)
            field_type_map = {f["name"]: f.get("type", "string") for f in field_configs}
            
            # 创建或更新表
            table_name = self._get_table_name(survey_type)
            result["table_name"] = table_name
            
            if not self._table_exists(table_name):
                self.create_survey_table(survey_type, field_configs)
            else:
                # 检查是否有新字段需要添加
                self.update_table_schema(table_name, field_configs)
            
            # 创建或更新配置
            config = self.create_or_update_config(
                survey_type, table_name, field_configs, survey_name
            )
            result["config_id"] = str(config.id)
            
            # 批量插入数据
            success_count, failed_count, upsert_errors = self._batch_upsert(
                table_name, 
                transformed_records,
                full_sync=full_sync,
                batch_size=batch_size,
                field_type_map=field_type_map,
                transformer=transformer,
            )
            result["success"] = success_count
            result["failed"] += failed_count
            if upsert_errors:
                result["errors"].extend(upsert_errors)
            
            logger.info(
                f"同步完成: {survey_type}, "
                f"成功 {result['success']}, 失败 {result['failed']}"
            )
            
        except Exception as e:
            logger.error(f"同步失败: {survey_type}, {e}")
            result["errors"].append({"error": str(e)})
            # 如果属于整体失败（例如建表失败/行大小限制），把失败数体现出来，避免“看起来无数据”
            if result.get("success", 0) == 0 and result.get("failed", 0) == 0 and records_for_error_count:
                result["failed"] = len(records_for_error_count)
        
        return result
    
    def _batch_upsert(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        full_sync: bool = False,
        batch_size: int = 100,
        field_type_map: Optional[Dict[str, str]] = None,
        transformer: Optional[SurveyDataTransformer] = None,
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        """
        批量插入或更新数据
        
        Args:
            table_name: 表名
            records: 数据记录列表
            full_sync: 是否全量同步（先删除再插入）
            batch_size: 批量大小
            
        Returns:
            (成功插入/更新的记录数, 失败记录数, 错误列表)
        """
        if not records:
            return 0, 0, []
        
        # 获取表的所有列
        existing_columns = self._get_existing_columns(table_name)
        existing_columns_lower = {c.lower() for c in existing_columns}
        
        # 过滤掉表中不存在的列
        filtered_records = []
        for record in records:
            filtered_record = {}
            for key, value in record.items():
                if key.lower() in existing_columns_lower:
                    filtered_record[key] = value
            filtered_records.append(filtered_record)
        
        if not filtered_records:
            return 0, 0, []
        
        # 获取所有列名（取第一条记录的键）
        columns = list(filtered_records[0].keys())
        
        # 如果全量同步，先清空表
        if full_sync:
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table_name}`")
            logger.info(f"清空表: {table_name}")
        
        success_count = 0
        failed_count = 0
        errors: List[Dict[str, Any]] = []
        
        # 分批处理
        for i in range(0, len(filtered_records), batch_size):
            batch = filtered_records[i:i + batch_size]
            
            try:
                # 构建 INSERT ... ON DUPLICATE KEY UPDATE SQL
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(f"`{c}`" for c in columns)
                
                # 更新子句（排除主键和唯一键）
                update_columns = [c for c in columns if c not in ("id", "survey_id")]
                update_clause = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in update_columns)
                
                sql = f"""
                INSERT INTO `{table_name}` ({column_names})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
                """
                
                # 准备数据
                values = []
                for record in batch:
                    row = []
                    for col in columns:
                        val = record.get(col)
                        # 处理特殊类型
                        if isinstance(val, dict) or isinstance(val, list):
                            val = json.dumps(val, ensure_ascii=False)
                        # 处理 datetime 字符串：MySQL DATETIME 不接受 2025-xx-xxT..Z
                        if field_type_map and field_type_map.get(col) == "datetime" and transformer:
                            dt = transformer.normalize_datetime_value(val)
                            val = dt if dt is not None else None
                        row.append(val)
                    values.append(tuple(row))
                
                with connection.cursor() as cursor:
                    cursor.executemany(sql, values)
                
                success_count += len(batch)
                
            except Exception as e:
                logger.error(f"批量插入失败: {table_name}, batch {i//batch_size + 1}, {e}")
                failed_count += len(batch)
                errors.append({
                    "table_name": table_name,
                    "batch": i // batch_size + 1,
                    "error": str(e),
                })
        
        return success_count, failed_count, errors
    
    def sync_all_survey_types(
        self,
        survey_types: List[str] = None,
        full_sync: bool = False,
    ) -> Dict[str, Any]:
        """
        同步所有问卷类型的数据
        
        Args:
            survey_types: 要同步的类型列表（为空则同步全部）
            full_sync: 是否全量同步
            
        Returns:
            同步结果统计
        """
        # 获取所有活跃的 Schema 配置
        if survey_types:
            configs = SurveySchemaConfig.objects.filter(
                survey_type__in=survey_types,
                is_active=True,
                is_deleted=False
            )
        else:
            configs = SurveySchemaConfig.objects.filter(
                is_active=True,
                is_deleted=False
            )
        
        results = {
            "total_types": 0,
            "success_types": 0,
            "total_records": 0,
            "success_records": 0,
            "failed_records": 0,
            "details": [],
        }
        
        for config in configs:
            results["total_types"] += 1
            
            type_result = self.sync_survey_data(
                survey_type=config.survey_type,
                full_sync=full_sync
            )
            
            if type_result["success"] > 0:
                results["success_types"] += 1
            
            results["total_records"] += type_result["success"] + type_result["failed"]
            results["success_records"] += type_result["success"]
            results["failed_records"] += type_result["failed"]
            results["details"].append(type_result)
        
        logger.info(
            f"全量同步完成: {results['success_types']}/{results['total_types']} 类型, "
            f"{results['success_records']}/{results['total_records']} 记录"
        )
        
        return results
