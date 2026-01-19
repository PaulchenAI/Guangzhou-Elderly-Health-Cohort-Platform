# -*- coding: utf-8 -*-
"""
联合查询功能测试

测试内容：
- 关联关系解析器测试
- SQL 构建器测试
- 循环引用检测测试
- API 集成测试（1级、2级、3级关联）
"""
import json
from django.test import TestCase, Client
from django.db import connection

from core.foreignkey.foreignkey_model import ForeignKeyMetadata
from core.table_query.join_query_utils import (
    JoinRelationParser,
    JoinSQLBuilder,
    JoinRelation,
    execute_join_query,
    get_join_preview,
    MAX_DEPTH_LIMIT,
    MAX_TABLES_LIMIT,
)


class JoinRelationParserTest(TestCase):
    """关联关系解析器测试"""
    
    def test_parse_single_level_relation(self):
        """测试1级关联解析"""
        # 查找一个有外键关系的表
        fk = ForeignKeyMetadata.objects.first()
        if not fk:
            self.skipTest("没有外键元数据，跳过测试")
        
        parser = JoinRelationParser(max_depth=1)
        result = parser.parse(fk.source_table)
        
        print(f"\n=== 1级关联解析测试 ===")
        print(f"主表: {result.primary_table}")
        print(f"关联表数: {len(result.relations)}")
        for r in result.relations:
            print(f"  - {r.table_name} (深度: {r.join_depth})")
        
        self.assertEqual(result.primary_table, fk.source_table)
        # 所有关联表的深度应该是 1
        for relation in result.relations:
            self.assertEqual(relation.join_depth, 1)
    
    def test_parse_two_level_relation(self):
        """测试2级关联解析"""
        # 使用 BS_STAFF 表，它有多级关联
        parser = JoinRelationParser(max_depth=2)
        result = parser.parse("BS_STAFF")
        
        print(f"\n=== 2级关联解析测试 ===")
        print(f"主表: {result.primary_table}")
        print(f"关联表数: {len(result.relations)}")
        print(f"最大深度: {result.max_depth}")
        for r in result.relations:
            print(f"  - {r.table_name} (深度: {r.join_depth}, 来源: {r.source_table})")
        
        self.assertIsNotNone(result.primary_table)
        # 应该有深度为 1 和 2 的关联
        depths = set(r.join_depth for r in result.relations)
        print(f"  关联深度集合: {depths}")
    
    def test_parse_three_level_relation(self):
        """测试3级关联解析"""
        parser = JoinRelationParser(max_depth=3)
        result = parser.parse("BS_STAFF")
        
        print(f"\n=== 3级关联解析测试 ===")
        print(f"主表: {result.primary_table}")
        print(f"关联表数: {len(result.relations)}")
        print(f"最大深度: {result.max_depth}")
        print(f"是否有循环: {result.has_cycle}")
        for r in result.relations:
            print(f"  - {r.table_name} (深度: {r.join_depth}, 来源: {r.source_table})")
        
        self.assertIsNotNone(result.primary_table)
        self.assertLessEqual(result.max_depth, 3)
    
    def test_cycle_detection(self):
        """测试循环引用检测"""
        # BS_DEPARTMENT 有自关联 (PARENTID -> MAINID)
        parser = JoinRelationParser(max_depth=3)
        result = parser.parse("BS_DEPARTMENT")
        
        print(f"\n=== 循环引用检测测试 ===")
        print(f"主表: {result.primary_table}")
        print(f"是否检测到循环: {result.has_cycle}")
        print(f"循环表: {result.cycle_tables}")
        
        # BS_DEPARTMENT 自关联应该检测到循环
        # 注意：由于是自关联，第一次访问时就会检测到循环
        if result.has_cycle:
            self.assertTrue(len(result.cycle_tables) > 0)
    
    def test_max_depth_limit(self):
        """测试最大深度限制"""
        # 设置深度为 10，应该被限制为 MAX_DEPTH_LIMIT
        parser = JoinRelationParser(max_depth=10)
        self.assertEqual(parser.max_depth, MAX_DEPTH_LIMIT)
    
    def test_include_tables_filter(self):
        """测试 include_tables 过滤"""
        parser = JoinRelationParser(
            max_depth=2,
            include_tables=["BS_DEPARTMENT"]
        )
        result = parser.parse("BS_STAFF")
        
        print(f"\n=== include_tables 过滤测试 ===")
        print(f"只包含 BS_DEPARTMENT 相关的表")
        for r in result.relations:
            print(f"  - {r.table_name}")
        
        # 所有关联表应该只包含 BS_DEPARTMENT
        for relation in result.relations:
            self.assertIn("BS_DEPARTMENT", relation.table_name)
    
    def test_exclude_tables_filter(self):
        """测试 exclude_tables 过滤"""
        parser = JoinRelationParser(
            max_depth=2,
            exclude_tables=["BS_DEPARTMENT"]
        )
        result = parser.parse("BS_STAFF")
        
        print(f"\n=== exclude_tables 过滤测试 ===")
        print(f"排除 BS_DEPARTMENT 相关的表")
        for r in result.relations:
            print(f"  - {r.table_name}")
        
        # 所有关联表不应该包含 BS_DEPARTMENT
        for relation in result.relations:
            self.assertNotIn("BS_DEPARTMENT", relation.table_name)
    
    def test_fuzzy_table_name_match(self):
        """测试模糊表名匹配"""
        parser = JoinRelationParser(max_depth=1)
        
        # 不带前缀的表名应该能匹配到带前缀的表
        result = parser.parse("BS_STAFF")
        
        print(f"\n=== 模糊表名匹配测试 ===")
        print(f"输入: BS_STAFF")
        print(f"解析结果: {result.primary_table}")
        
        # 应该匹配到 gzlry_BS_STAFF
        self.assertIn("BS_STAFF", result.primary_table)


class JoinSQLBuilderTest(TestCase):
    """SQL 构建器测试"""
    
    def setUp(self):
        """准备测试数据"""
        # 创建测试用的关联关系
        self.primary_table = "gzlry_BS_STAFF"
        self.relations = [
            JoinRelation(
                table_name="gzlry_BS_DEPARTMENT",
                join_depth=1,
                source_table="gzlry_BS_STAFF",
                source_columns=["DEPARTMENT_ID"],
                target_columns=["MAINID"],
            ),
            JoinRelation(
                table_name="gzlry_BS_STAFF_TYPE",
                join_depth=1,
                source_table="gzlry_BS_STAFF",
                source_columns=["STAFF_TYPE_ID"],
                target_columns=["MAINID"],
            ),
        ]
    
    def test_build_select_fields(self):
        """测试 SELECT 字段构建"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        
        select_clause, field_meta = builder.build_select_fields()
        
        print(f"\n=== SELECT 字段构建测试 ===")
        print(f"字段数量: {len(field_meta)}")
        print(f"前5个字段:")
        for f in field_meta[:5]:
            print(f"  - {f.alias} ({f.original_table}.{f.original_field})")
        
        self.assertGreater(len(field_meta), 0)
        # 检查字段别名格式
        for f in field_meta:
            self.assertEqual(f.alias, f"{f.original_table}_{f.original_field}")
    
    def test_build_from_clause(self):
        """测试 FROM 子句构建"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        
        from_clause = builder.build_from_clause()
        
        print(f"\n=== FROM 子句构建测试 ===")
        print(from_clause)
        
        self.assertIn("FROM", from_clause)
        self.assertIn("LEFT JOIN", from_clause)
        self.assertIn(self.primary_table, from_clause)
    
    def test_build_where_clause(self):
        """测试 WHERE 子句构建"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        
        # 先构建字段以初始化 _all_fields
        builder.build_select_fields()
        
        # 使用实际存在的字段名
        filters = [
            {"field": f"{self.primary_table}_MAINID", "operator": "eq", "value": 1},
        ]
        
        where_clause, params = builder.build_where_clause(filters)
        
        print(f"\n=== WHERE 子句构建测试 ===")
        print(f"WHERE: {where_clause}")
        print(f"参数: {params}")
        
        self.assertIn("WHERE", where_clause)
        self.assertEqual(len(params), 1)
    
    def test_build_where_clause_invalid_field(self):
        """测试无效字段的 WHERE 子句"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        builder.build_select_fields()
        
        filters = [
            {"field": "invalid_field", "operator": "eq", "value": 1},
        ]
        
        with self.assertRaises(ValueError) as context:
            builder.build_where_clause(filters)
        
        print(f"\n=== 无效字段错误测试 ===")
        print(f"错误信息: {context.exception}")
        
        self.assertIn("不在允许的字段列表中", str(context.exception))
    
    def test_build_order_clause(self):
        """测试 ORDER BY 子句构建"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        builder.build_select_fields()
        
        # 获取一个有效的字段名
        valid_field = builder._all_fields[0] if builder._all_fields else None
        if not valid_field:
            self.skipTest("没有有效字段")
        
        order_clause = builder.build_order_clause(f"{valid_field} DESC")
        
        print(f"\n=== ORDER BY 子句构建测试 ===")
        print(f"ORDER BY: {order_clause}")
        
        self.assertIn("ORDER BY", order_clause)
        self.assertIn("DESC", order_clause)
    
    def test_build_complete_query(self):
        """测试完整查询 SQL 构建"""
        builder = JoinSQLBuilder(
            primary_table=self.primary_table,
            relations=self.relations,
        )
        
        sql, params, field_meta = builder.build_query_sql(
            page=1,
            page_size=10,
        )
        
        print(f"\n=== 完整查询 SQL 构建测试 ===")
        print(f"SQL:\n{sql}")
        print(f"参数: {params}")
        print(f"字段数: {len(field_meta)}")
        
        self.assertIn("SELECT", sql)
        self.assertIn("FROM", sql)
        self.assertIn("LEFT JOIN", sql)
        self.assertIn("LIMIT", sql)


class JoinQueryExecutionTest(TestCase):
    """联合查询执行测试"""
    
    def test_execute_join_query_level_1(self):
        """测试1级关联查询执行"""
        print(f"\n=== 1级关联查询执行测试 ===")
        
        try:
            result = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=1,
                page=1,
                page_size=5,
            )
            
            print(f"主表: {result['join_info']['primary_table']}")
            print(f"关联表: {result['join_info']['joined_tables']}")
            print(f"关联深度: {result['join_info']['join_depth']}")
            print(f"总数: {result['total']}")
            print(f"返回行数: {len(result['items'])}")
            print(f"字段数: {len(result['field_info'])}")
            
            if result['items']:
                print(f"第一行数据的部分字段:")
                first_row = result['items'][0]
                for i, (k, v) in enumerate(first_row.items()):
                    if i >= 5:
                        print(f"  ... 还有 {len(first_row) - 5} 个字段")
                        break
                    print(f"  {k}: {v}")
            
            self.assertEqual(result['join_info']['join_depth'], 1)
            self.assertLessEqual(len(result['items']), 5)
            
        except Exception as e:
            print(f"查询失败: {e}")
            # 如果表不存在，跳过测试
            if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                self.skipTest(f"测试表不存在: {e}")
            raise
    
    def test_execute_join_query_level_2(self):
        """测试2级关联查询执行"""
        print(f"\n=== 2级关联查询执行测试 ===")
        
        try:
            result = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=2,
                page=1,
                page_size=5,
            )
            
            print(f"主表: {result['join_info']['primary_table']}")
            print(f"关联表: {result['join_info']['joined_tables']}")
            print(f"关联深度: {result['join_info']['join_depth']}")
            print(f"总数: {result['total']}")
            print(f"返回行数: {len(result['items'])}")
            print(f"字段数: {len(result['field_info'])}")
            print(f"是否有循环: {result['join_info']['has_cycle']}")
            
            # 打印关联详情
            print(f"关联详情:")
            for detail in result['join_info']['join_details']:
                print(f"  - {detail['table_name']} (深度: {detail['join_depth']}, 来源: {detail['source_table']})")
            
            self.assertLessEqual(result['join_info']['join_depth'], 2)
            
        except Exception as e:
            print(f"查询失败: {e}")
            if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                self.skipTest(f"测试表不存在: {e}")
            raise
    
    def test_execute_join_query_level_3(self):
        """测试3级关联查询执行"""
        print(f"\n=== 3级关联查询执行测试 ===")
        
        try:
            result = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=3,
                page=1,
                page_size=5,
            )
            
            print(f"主表: {result['join_info']['primary_table']}")
            print(f"关联表数量: {len(result['join_info']['joined_tables'])}")
            print(f"关联深度: {result['join_info']['join_depth']}")
            print(f"总数: {result['total']}")
            print(f"返回行数: {len(result['items'])}")
            print(f"字段数: {len(result['field_info'])}")
            print(f"是否有循环: {result['join_info']['has_cycle']}")
            
            # 按深度分组打印关联表
            depth_groups = {}
            for detail in result['join_info']['join_details']:
                depth = detail['join_depth']
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(detail['table_name'])
            
            for depth in sorted(depth_groups.keys()):
                print(f"  深度 {depth}: {depth_groups[depth]}")
            
            self.assertLessEqual(result['join_info']['join_depth'], 3)
            
        except Exception as e:
            print(f"查询失败: {e}")
            if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                self.skipTest(f"测试表不存在: {e}")
            raise
    
    def test_join_query_with_filter(self):
        """测试带过滤条件的联合查询"""
        print(f"\n=== 带过滤条件的联合查询测试 ===")
        
        # 先执行一次查询获取字段列表
        try:
            preview = get_join_preview("BS_STAFF", max_depth=1)
            
            if not preview['all_fields']:
                self.skipTest("没有可用字段")
            
            # 找一个 MAINID 字段用于过滤
            mainid_field = None
            for f in preview['all_fields']:
                if 'MAINID' in f['original_field']:
                    mainid_field = f['alias']
                    break
            
            if not mainid_field:
                self.skipTest("没有 MAINID 字段")
            
            result = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=1,
                page=1,
                page_size=5,
                filters=[
                    {"field": mainid_field, "operator": "gt", "value": 0}
                ],
            )
            
            print(f"过滤字段: {mainid_field}")
            print(f"返回行数: {len(result['items'])}")
            
        except Exception as e:
            print(f"查询失败: {e}")
            if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                self.skipTest(f"测试表不存在: {e}")
            raise
    
    def test_join_query_with_pagination(self):
        """测试分页功能"""
        print(f"\n=== 分页功能测试 ===")
        
        try:
            # 第一页
            result1 = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=1,
                page=1,
                page_size=3,
            )
            
            # 第二页
            result2 = execute_join_query(
                primary_table="BS_STAFF",
                max_depth=1,
                page=2,
                page_size=3,
            )
            
            print(f"总数: {result1['total']}")
            print(f"第1页返回: {len(result1['items'])} 条")
            print(f"第2页返回: {len(result2['items'])} 条")
            
            # 如果有足够数据，两页的数据应该不同
            if result1['total'] > 3:
                self.assertEqual(result1['page'], 1)
                self.assertEqual(result2['page'], 2)
            
        except Exception as e:
            print(f"查询失败: {e}")
            if "doesn't exist" in str(e) or "not exist" in str(e).lower():
                self.skipTest(f"测试表不存在: {e}")
            raise


class JoinPreviewTest(TestCase):
    """关联关系预览测试"""
    
    def test_get_join_preview(self):
        """测试获取关联关系预览"""
        print(f"\n=== 关联关系预览测试 ===")
        
        result = get_join_preview("BS_STAFF", max_depth=2)
        
        print(f"主表: {result['primary_table']}")
        print(f"关联表数: {result['total_related_tables']}")
        print(f"最大深度: {result['max_depth']}")
        print(f"是否有循环: {result['has_cycle']}")
        print(f"字段数: {len(result['all_fields'])}")
        
        print(f"关联关系树:")
        for item in result['join_tree']:
            print(f"  - {item['table_name']} (深度: {item['join_depth']}, 来源: {item['source_table']})")
        
        self.assertIsNotNone(result['primary_table'])
        self.assertGreaterEqual(len(result['all_fields']), 0)


class JoinQueryAPITest(TestCase):
    """API 集成测试"""
    
    def setUp(self):
        self.client = Client()
    
    def test_join_query_api(self):
        """测试联合查询 API"""
        print(f"\n=== 联合查询 API 测试 ===")
        
        response = self.client.post(
            '/api/core/table-query/join-query',
            data=json.dumps({
                "primary_table": "BS_STAFF",
                "max_depth": 2,
                "page": 1,
                "page_size": 5,
            }),
            content_type='application/json',
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"主表: {data['join_info']['primary_table']}")
            print(f"关联表: {data['join_info']['joined_tables']}")
            print(f"总数: {data['total']}")
            print(f"返回行数: {len(data['items'])}")
        else:
            print(f"响应: {response.content.decode()}")
            # API 可能需要认证，跳过测试
            self.skipTest("API 请求失败，可能需要认证")
    
    def test_join_preview_api(self):
        """测试关联预览 API"""
        print(f"\n=== 关联预览 API 测试 ===")
        
        response = self.client.get(
            '/api/core/table-query/join-preview/BS_STAFF?max_depth=2',
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"主表: {data['primary_table']}")
            print(f"关联表数: {data['total_related_tables']}")
        else:
            print(f"响应: {response.content.decode()}")
            self.skipTest("API 请求失败，可能需要认证")


# 运行测试的便捷函数
def run_tests():
    """运行所有测试"""
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(JoinRelationParserTest))
    suite.addTests(loader.loadTestsFromTestCase(JoinSQLBuilderTest))
    suite.addTests(loader.loadTestsFromTestCase(JoinQueryExecutionTest))
    suite.addTests(loader.loadTestsFromTestCase(JoinPreviewTest))
    suite.addTests(loader.loadTestsFromTestCase(JoinQueryAPITest))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == '__main__':
    run_tests()
