#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
同步性能测试

测试内容：
1. 大量数据同步的性能
2. 批量插入的性能
3. 索引和查询优化

运行方式：
    python manage.py test core.table_query.tests.test_sync_performance -v 2
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import List

from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.utils import timezone

from core.survey.survey_model import SurveyRecord, SurveySchemaConfig
from core.table_query.survey_data_transformer import SurveyDataTransformer
from core.table_query.table_query_sync_service import TableQuerySyncService


class SurveyDataTransformerPerformanceTest(TestCase):
    """数据转换器性能测试"""
    
    def test_expand_performance_1000_records(self):
        """测试展开 1000 条记录的性能"""
        transformer = SurveyDataTransformer()
        
        # 生成测试数据
        records = []
        for i in range(1000):
            record = {
                "survey_id": f"test_{i}",
                "patient_name": f"测试患者{i}",
                "patient_info": {
                    "age": 30 + (i % 50),
                    "gender": "male" if i % 2 == 0 else "female",
                    "height": 160 + (i % 30),
                    "weight": 50 + (i % 40),
                },
                "survey_data": {
                    "totalScore": 80 + (i % 20),
                    "level": "正常" if i % 3 == 0 else "偏高",
                    "details": {
                        "item1": i * 10,
                        "item2": i * 20,
                        "item3": i * 30,
                    },
                    "scores": {
                        "anxietyScore": 10 + (i % 5),
                        "depressionScore": 15 + (i % 5),
                    }
                },
                "scores": {
                    "total_score": 100 + i,
                    "max_score": 200,
                },
            }
            records.append(record)
        
        # 测试展开性能
        start_time = time.time()
        
        expanded_records = []
        for record in records:
            expanded = transformer.expand_record(record)
            expanded_records.append(expanded)
        
        elapsed = time.time() - start_time
        
        print(f"\n展开 1000 条记录耗时: {elapsed:.3f}秒")
        print(f"平均每条: {elapsed/1000*1000:.3f}毫秒")
        print(f"展开后字段数: {len(expanded_records[0])}")
        
        # 性能断言：1000 条记录应在 1 秒内完成
        self.assertLess(elapsed, 1.0)
    
    def test_field_analysis_performance(self):
        """测试字段分析性能"""
        transformer = SurveyDataTransformer()
        
        # 生成展开后的测试数据
        records = []
        for i in range(500):
            record = {
                "survey_id": f"test_{i}",
                "patient_name": f"患者{i}",
                "survey_data_totalScore": 80 + i,
                "survey_data_level": "正常",
                "scores_total": 100,
                "patient_info_age": 30 + i,
                "patient_info_gender": "male",
            }
            records.append(record)
        
        start_time = time.time()
        
        field_configs = transformer.analyze_fields(records)
        
        elapsed = time.time() - start_time
        
        print(f"\n分析 500 条记录的字段配置耗时: {elapsed:.3f}秒")
        print(f"检测到字段数: {len(field_configs)}")
        
        # 性能断言
        self.assertLess(elapsed, 0.5)


class TableQuerySyncPerformanceTest(TransactionTestCase):
    """表查询同步服务性能测试"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试 Schema
        self.schema = SurveySchemaConfig.objects.create(
            survey_type="perf_test",
            survey_name="性能测试问卷",
            description="用于性能测试的问卷",
            schema_json={
                "fields": [
                    {"name": "totalScore", "type": "integer", "title": "总分"},
                    {"name": "level", "type": "string", "title": "等级"},
                ]
            },
            is_active=True,
        )
    
    def tearDown(self):
        """清理测试数据"""
        # 删除测试表
        table_name = "survey_perf_test"
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        except Exception:
            pass
        
        # 删除测试配置
        from core.table_query.table_query_model import TableQueryConfig
        TableQueryConfig.objects.filter(table_name=table_name).delete()
        
        # 删除测试记录
        SurveyRecord.objects.filter(survey_type="perf_test").delete()
    
    def _create_test_records(self, count: int) -> List[SurveyRecord]:
        """创建测试记录"""
        records = []
        base_time = timezone.now()
        
        for i in range(count):
            record = SurveyRecord(
                survey_type="perf_test",
                survey_id=f"perf_test_{uuid.uuid4().hex[:8]}_{i}",
                patient_name=f"性能测试患者{i}",
                patient_info={
                    "age": 25 + (i % 60),
                    "gender": "male" if i % 2 == 0 else "female",
                },
                survey_data={
                    "totalScore": 60 + (i % 40),
                    "level": ["轻度", "中度", "重度"][i % 3],
                    "details": {
                        "item1": i * 2,
                        "item2": i * 3,
                    },
                },
                scores={
                    "total_score": 100 + i,
                    "max_total_score": 200,
                },
                record_time=base_time - timedelta(hours=i),
                raw_data={"test": True, "index": i},
            )
            records.append(record)
        
        # 批量创建
        SurveyRecord.objects.bulk_create(records)
        
        return records
    
    def test_sync_100_records(self):
        """测试同步 100 条记录的性能"""
        records = self._create_test_records(100)
        
        sync_service = TableQuerySyncService()
        
        start_time = time.time()
        
        result = sync_service.sync_survey_data(
            survey_type="perf_test",
            records=records,
            full_sync=True,
            batch_size=50,
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n同步 100 条记录:")
        print(f"  耗时: {elapsed:.3f}秒")
        print(f"  成功: {result['success']}")
        print(f"  失败: {result['failed']}")
        print(f"  速度: {result['success'] / elapsed:.1f} 条/秒")
        
        self.assertEqual(result["success"], 100)
        self.assertEqual(result["failed"], 0)
    
    def test_sync_500_records(self):
        """测试同步 500 条记录的性能"""
        records = self._create_test_records(500)
        
        sync_service = TableQuerySyncService()
        
        start_time = time.time()
        
        result = sync_service.sync_survey_data(
            survey_type="perf_test",
            records=records,
            full_sync=True,
            batch_size=100,
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n同步 500 条记录:")
        print(f"  耗时: {elapsed:.3f}秒")
        print(f"  成功: {result['success']}")
        print(f"  失败: {result['failed']}")
        print(f"  速度: {result['success'] / elapsed:.1f} 条/秒")
        
        self.assertEqual(result["success"], 500)
        self.assertEqual(result["failed"], 0)
        # 性能断言：500 条记录应在 5 秒内完成
        self.assertLess(elapsed, 5.0)
    
    def test_batch_size_comparison(self):
        """测试不同批量大小的性能差异"""
        records = self._create_test_records(200)
        
        sync_service = TableQuerySyncService()
        
        batch_sizes = [10, 50, 100, 200]
        results = []
        
        for batch_size in batch_sizes:
            # 清空表
            table_name = "survey_perf_test"
            with connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table_name}` " if sync_service._table_exists(table_name) else "SELECT 1")
            
            start_time = time.time()
            
            result = sync_service.sync_survey_data(
                survey_type="perf_test",
                records=records,
                full_sync=True,
                batch_size=batch_size,
            )
            
            elapsed = time.time() - start_time
            
            results.append({
                "batch_size": batch_size,
                "elapsed": elapsed,
                "speed": result["success"] / elapsed,
            })
        
        print("\n批量大小性能对比:")
        print("-" * 50)
        for r in results:
            print(f"  batch_size={r['batch_size']:3d}: {r['elapsed']:.3f}秒, {r['speed']:.1f}条/秒")
    
    def test_incremental_sync(self):
        """测试增量同步性能"""
        # 先同步 100 条
        records1 = self._create_test_records(100)
        
        sync_service = TableQuerySyncService()
        
        result1 = sync_service.sync_survey_data(
            survey_type="perf_test",
            records=records1,
            full_sync=True,
        )
        
        # 再增量同步 50 条新数据
        records2 = self._create_test_records(50)
        
        start_time = time.time()
        
        result2 = sync_service.sync_survey_data(
            survey_type="perf_test",
            records=records2,
            full_sync=False,  # 增量同步
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n增量同步 50 条新记录:")
        print(f"  耗时: {elapsed:.3f}秒")
        print(f"  成功: {result2['success']}")
        
        self.assertEqual(result2["success"], 50)


class QueryPerformanceTest(TransactionTestCase):
    """查询性能测试"""
    
    def setUp(self):
        """设置测试数据"""
        # 创建测试 Schema
        self.schema = SurveySchemaConfig.objects.create(
            survey_type="query_perf_test",
            survey_name="查询性能测试问卷",
            schema_json={"fields": []},
            is_active=True,
        )
        
        # 创建并同步测试数据
        self._create_and_sync_data(500)
    
    def _create_and_sync_data(self, count: int):
        """创建并同步测试数据"""
        records = []
        base_time = timezone.now()
        
        for i in range(count):
            record = SurveyRecord(
                survey_type="query_perf_test",
                survey_id=f"query_test_{i}",
                patient_name=f"查询患者{i % 100}",
                patient_info={"age": 20 + (i % 60)},
                survey_data={"totalScore": i % 100},
                scores={"total": i},
                record_time=base_time - timedelta(days=i),
            )
            records.append(record)
        
        SurveyRecord.objects.bulk_create(records)
        
        sync_service = TableQuerySyncService()
        sync_service.sync_survey_data(
            survey_type="query_perf_test",
            records=records,
            full_sync=True,
        )
    
    def tearDown(self):
        """清理测试数据"""
        table_name = "survey_query_perf_test"
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        except Exception:
            pass
        
        from core.table_query.table_query_model import TableQueryConfig
        TableQueryConfig.objects.filter(table_name=table_name).delete()
        SurveyRecord.objects.filter(survey_type="query_perf_test").delete()
    
    def test_simple_query_performance(self):
        """测试简单查询性能"""
        table_name = "survey_query_perf_test"
        
        # 测试全表查询
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 100")
            results = cursor.fetchall()
        
        elapsed = time.time() - start_time
        
        print(f"\n简单查询 (LIMIT 100):")
        print(f"  耗时: {elapsed*1000:.2f}毫秒")
        print(f"  返回: {len(results)} 条")
        
        self.assertEqual(len(results), 100)
        self.assertLess(elapsed, 0.1)
    
    def test_filtered_query_performance(self):
        """测试过滤查询性能"""
        table_name = "survey_query_perf_test"
        
        # 测试带索引的查询
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM `{table_name}` WHERE patient_name LIKE %s LIMIT 50",
                ["查询患者1%"]
            )
            results = cursor.fetchall()
        
        elapsed = time.time() - start_time
        
        print(f"\n过滤查询 (patient_name LIKE):")
        print(f"  耗时: {elapsed*1000:.2f}毫秒")
        print(f"  返回: {len(results)} 条")
        
        self.assertLess(elapsed, 0.5)
    
    def test_count_query_performance(self):
        """测试计数查询性能"""
        table_name = "survey_query_perf_test"
        
        start_time = time.time()
        
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
        
        elapsed = time.time() - start_time
        
        print(f"\n计数查询:")
        print(f"  耗时: {elapsed*1000:.2f}毫秒")
        print(f"  总数: {count}")
        
        self.assertEqual(count, 500)
        self.assertLess(elapsed, 0.1)
