# -*- coding: utf-8 -*-
"""
联合查询工具模块

提供外键关联关系解析和 SQL 构建功能。
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set

from django.db import connection

from core.foreignkey.foreignkey_model import ForeignKeyMetadata

logger = logging.getLogger(__name__)

# =============================================================================
# 常量定义
# =============================================================================

# 最大关联深度上限
MAX_DEPTH_LIMIT = 5

# 最大关联表数量
MAX_TABLES_LIMIT = 10

# 默认分页大小
DEFAULT_PAGE_SIZE = 20

# 最大分页大小
MAX_PAGE_SIZE = 100

# 表名和字段名的合法字符正则
IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# 允许的 SQL 操作符
ALLOWED_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "like": "LIKE",
    "in": "IN",
    "between": "BETWEEN",
}

# 表存在性缓存（避免重复查询）
_table_exists_cache: Dict[str, bool] = {}


def check_table_exists(table_name: str) -> bool:
    """
    检查表是否存在于数据库中
    
    Args:
        table_name: 表名
        
    Returns:
        bool: 表是否存在
    """
    global _table_exists_cache
    
    if table_name in _table_exists_cache:
        return _table_exists_cache[table_name]
    
    try:
        with connection.cursor() as cursor:
            # 使用 SHOW TABLES LIKE 检查表是否存在
            cursor.execute("SHOW TABLES LIKE %s", [table_name])
            exists = cursor.fetchone() is not None
            _table_exists_cache[table_name] = exists
            if not exists:
                logger.warning(f"表不存在: {table_name}")
            return exists
    except Exception as e:
        logger.error(f"检查表 {table_name} 存在性时出错: {e}")
        return False


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class JoinRelation:
    """关联关系"""
    table_name: str
    join_depth: int
    source_table: str
    source_columns: List[str]
    target_columns: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "join_depth": self.join_depth,
            "source_table": self.source_table,
            "source_columns": self.source_columns,
            "target_columns": self.target_columns,
        }


@dataclass
class FieldMeta:
    """字段元信息"""
    alias: str
    original_table: str
    original_field: str
    field_type: str = "string"
    field_comment: str = ""  # 字段注释（中文名称）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "original_table": self.original_table,
            "original_field": self.original_field,
            "field_type": self.field_type,
            "field_comment": self.field_comment,
        }


@dataclass
class JoinParseResult:
    """关联解析结果"""
    primary_table: str
    relations: List[JoinRelation] = field(default_factory=list)
    max_depth: int = 0
    has_cycle: bool = False
    cycle_tables: List[str] = field(default_factory=list)
    
    @property
    def joined_tables(self) -> List[str]:
        """获取所有关联表名列表"""
        return [r.table_name for r in self.relations]
    
    @property
    def total_tables(self) -> int:
        """总表数（包含主表）"""
        return len(self.relations) + 1


# =============================================================================
# 关联关系解析器
# =============================================================================

class JoinRelationParser:
    """
    外键关联关系解析器
    
    从 table_foreignkey_metadata 表递归解析关联关系，
    支持深度限制和循环检测。
    """
    
    def __init__(
        self,
        max_depth: int = 2,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
    ):
        """
        初始化解析器
        
        Args:
            max_depth: 最大关联深度（1-5）
            include_tables: 要包含的关联表（优先级高于 exclude_tables）
            exclude_tables: 要排除的关联表
        """
        self.max_depth = min(max_depth, MAX_DEPTH_LIMIT)
        self.include_tables = set(include_tables) if include_tables else None
        self.exclude_tables = set(exclude_tables) if exclude_tables else set()
        
        # 解析状态
        self._visited: Set[str] = set()
        self._relations: List[JoinRelation] = []
        self._has_cycle = False
        self._cycle_tables: List[str] = []
    
    def parse(self, primary_table: str) -> JoinParseResult:
        """
        解析主表的关联关系
        
        Args:
            primary_table: 主表名（支持模糊匹配）
        
        Returns:
            JoinParseResult: 解析结果
        """
        # 重置状态
        self._visited = set()
        self._relations = []
        self._has_cycle = False
        self._cycle_tables = []
        
        # 解析主表名（支持模糊匹配）
        resolved_table = self._resolve_table_name(primary_table)
        if not resolved_table:
            logger.warning(f"未找到匹配的表: {primary_table}")
            return JoinParseResult(primary_table=primary_table)
        
        # 递归解析关联关系
        self._visited.add(resolved_table)
        self._parse_recursive(resolved_table, depth=1)
        
        # 计算最大深度
        max_depth = max([r.join_depth for r in self._relations], default=0)
        
        return JoinParseResult(
            primary_table=resolved_table,
            relations=self._relations,
            max_depth=max_depth,
            has_cycle=self._has_cycle,
            cycle_tables=self._cycle_tables,
        )
    
    def _resolve_table_name(self, table_name: str) -> Optional[str]:
        """
        解析表名（支持模糊匹配）
        
        查询逻辑:
        1. 精确匹配
        2. 后缀匹配（支持不带前缀的表名）
        3. 模糊匹配
        """
        # 从外键元数据中查找
        # 1. 精确匹配
        if ForeignKeyMetadata.objects.filter(source_table=table_name).exists():
            return table_name
        if ForeignKeyMetadata.objects.filter(target_table=table_name).exists():
            return table_name
        
        # 2. 后缀匹配
        fk = ForeignKeyMetadata.objects.filter(source_table__iendswith=table_name).first()
        if fk:
            return fk.source_table
        fk = ForeignKeyMetadata.objects.filter(target_table__iendswith=table_name).first()
        if fk:
            return fk.target_table
        
        # 3. 模糊匹配
        fk = ForeignKeyMetadata.objects.filter(source_table__icontains=table_name).first()
        if fk:
            return fk.source_table
        fk = ForeignKeyMetadata.objects.filter(target_table__icontains=table_name).first()
        if fk:
            return fk.target_table
        
        # 如果外键元数据中没有，返回原表名（可能是没有外键的表）
        return table_name
    
    def _parse_recursive(self, source_table: str, depth: int):
        """
        递归解析关联关系
        
        Args:
            source_table: 源表名
            depth: 当前深度
        """
        # 深度限制检查
        if depth > self.max_depth:
            return
        
        # 关联表数量限制检查
        if len(self._relations) >= MAX_TABLES_LIMIT:
            logger.warning(f"关联表数量已达上限 {MAX_TABLES_LIMIT}，停止解析")
            return
        
        # 查询该表的出向外键关系（该表引用的其他表）
        foreign_keys = ForeignKeyMetadata.objects.filter(source_table=source_table)
        
        for fk in foreign_keys:
            target_table = fk.target_table
            
            # 检查是否应该包含该表
            if not self._should_include_table(target_table):
                continue
            
            # 检查表是否存在
            if not check_table_exists(target_table):
                logger.warning(f"跳过不存在的关联表: {target_table}")
                continue
            
            # 循环检测
            if target_table in self._visited:
                self._has_cycle = True
                if target_table not in self._cycle_tables:
                    self._cycle_tables.append(target_table)
                logger.debug(f"检测到循环引用: {source_table} -> {target_table}")
                continue
            
            # 添加关联关系
            relation = JoinRelation(
                table_name=target_table,
                join_depth=depth,
                source_table=source_table,
                source_columns=fk.source_columns or [],
                target_columns=fk.target_columns or [],
            )
            self._relations.append(relation)
            
            # 标记已访问
            self._visited.add(target_table)
            
            # 递归解析下一级
            self._parse_recursive(target_table, depth + 1)
    
    def _should_include_table(self, table_name: str) -> bool:
        """
        检查是否应该包含该表
        
        Args:
            table_name: 表名
        
        Returns:
            bool: 是否包含
        """
        # 如果指定了 include_tables，只包含指定的表
        if self.include_tables is not None:
            return self._match_table_in_set(table_name, self.include_tables)
        
        # 否则排除 exclude_tables 中的表
        return not self._match_table_in_set(table_name, self.exclude_tables)
    
    def _match_table_in_set(self, table_name: str, table_set: Set[str]) -> bool:
        """
        检查表名是否匹配集合中的任一项（支持模糊匹配）
        """
        if not table_set:
            return False
        
        for pattern in table_set:
            # 精确匹配
            if table_name == pattern:
                return True
            # 后缀匹配
            if table_name.endswith(pattern):
                return True
            # 包含匹配
            if pattern in table_name:
                return True
        
        return False


# =============================================================================
# SQL 构建器
# =============================================================================

class JoinSQLBuilder:
    """
    联合查询 SQL 构建器
    
    动态构建带 LEFT JOIN 的 SQL 语句。
    """
    
    def __init__(
        self,
        primary_table: str,
        relations: List[JoinRelation],
    ):
        """
        初始化构建器
        
        Args:
            primary_table: 主表名
            relations: 关联关系列表
        """
        self.primary_table = primary_table
        self.relations = relations
        self._field_meta: List[FieldMeta] = []
        self._all_fields: List[str] = []
        self._alias_to_original: Dict[str, Tuple[str, str]] = {}  # alias -> (table, field)
    
    def build_select_fields(self) -> Tuple[str, List[FieldMeta]]:
        """
        构建 SELECT 字段列表
        
        Returns:
            (字段列表SQL, 字段元信息列表)
        """
        self._field_meta = []
        self._all_fields = []
        self._alias_to_original = {}
        select_parts = []
        
        # 获取所有表（主表 + 关联表），过滤掉不存在的表
        all_tables = [self.primary_table]
        for r in self.relations:
            if check_table_exists(r.table_name):
                all_tables.append(r.table_name)
            else:
                logger.warning(f"跳过不存在的关联表: {r.table_name}")
        
        for table_name in all_tables:
            # 获取表的字段列表
            fields = self._get_table_fields(table_name)
            
            for field_name, field_type, field_comment in fields:
                # 构建别名：表名_字段名
                alias = f"{table_name}_{field_name}"
                
                # 添加到 SELECT
                select_parts.append(
                    f"{self._quote(table_name)}.{self._quote(field_name)} AS {self._quote(alias)}"
                )
                
                # 记录字段元信息
                self._field_meta.append(FieldMeta(
                    alias=alias,
                    original_table=table_name,
                    original_field=field_name,
                    field_type=field_type,
                    field_comment=field_comment,
                ))
                self._all_fields.append(alias)
                # 记录别名到原始表名/字段名的映射
                self._alias_to_original[alias] = (table_name, field_name)
        
        return ", ".join(select_parts), self._field_meta
    
    def build_from_clause(self) -> str:
        """
        构建 FROM 子句（包含 LEFT JOIN）
        
        Returns:
            FROM 子句 SQL
        """
        parts = [f"FROM {self._quote(self.primary_table)}"]
        
        for relation in self.relations:
            # 检查关联表是否存在
            if not check_table_exists(relation.table_name):
                logger.warning(f"跳过不存在的关联表: {relation.table_name}")
                continue
                
            # 构建 JOIN 条件
            join_conditions = []
            for src_col, tgt_col in zip(relation.source_columns, relation.target_columns):
                join_conditions.append(
                    f"{self._quote(relation.source_table)}.{self._quote(src_col)} = "
                    f"{self._quote(relation.table_name)}.{self._quote(tgt_col)}"
                )
            
            if join_conditions:
                parts.append(
                    f"LEFT JOIN {self._quote(relation.table_name)} "
                    f"ON {' AND '.join(join_conditions)}"
                )
        
        return "\n".join(parts)
    
    def build_where_clause(
        self,
        filters: Optional[List[Dict[str, Any]]],
    ) -> Tuple[str, List[Any]]:
        """
        构建 WHERE 子句
        
        Args:
            filters: 过滤条件列表，字段名使用别名格式（表名_字段名）
        
        Returns:
            (WHERE 子句 SQL, 参数列表)
        
        Raises:
            ValueError: 字段不在允许列表中
        """
        if not filters:
            return "", []
        
        where_parts = []
        params = []
        
        for condition in filters:
            field = condition.get("field", "")
            operator = condition.get("operator", "eq")
            value = condition.get("value")
            
            # 验证字段名（接受别名格式）
            if field not in self._all_fields:
                raise ValueError(
                    f"字段 {field} 不在允许的字段列表中。"
                    f"可用字段: {', '.join(self._all_fields[:10])}..."
                )
            
            # 验证操作符
            if operator not in ALLOWED_OPERATORS:
                raise ValueError(f"不支持的操作符: {operator}")
            
            sql_operator = ALLOWED_OPERATORS[operator]
            
            # 将别名转换为原始的 表名.字段名 格式
            table_name, field_name = self._alias_to_original[field]
            quoted_field = f"{self._quote(table_name)}.{self._quote(field_name)}"
            
            # 根据操作符构建条件
            if operator == "like":
                where_parts.append(f"{quoted_field} {sql_operator} %s")
                params.append(f"%{value}%")
            elif operator == "in":
                if not isinstance(value, (list, tuple)):
                    value = [value]
                placeholders = ", ".join(["%s"] * len(value))
                where_parts.append(f"{quoted_field} IN ({placeholders})")
                params.extend(value)
            elif operator == "between":
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    raise ValueError("BETWEEN 操作需要两个值")
                where_parts.append(f"{quoted_field} BETWEEN %s AND %s")
                params.extend(value)
            else:
                where_parts.append(f"{quoted_field} {sql_operator} %s")
                params.append(value)
        
        if where_parts:
            return "WHERE " + " AND ".join(where_parts), params
        return "", []
    
    def build_order_clause(self, order_by: Optional[str]) -> str:
        """
        构建 ORDER BY 子句
        
        Args:
            order_by: 排序字符串，字段名使用别名格式（表名_字段名）
        
        Returns:
            ORDER BY 子句 SQL
        """
        if not order_by:
            # 默认按主表的第一个字段降序
            if self._field_meta:
                first_field = self._field_meta[0]
                quoted_field = f"{self._quote(first_field.original_table)}.{self._quote(first_field.original_field)}"
                return f"ORDER BY {quoted_field} DESC"
            return ""
        
        # 解析排序字符串
        parts = []
        for part in order_by.split(","):
            part = part.strip()
            if not part:
                continue
            
            tokens = part.split()
            field_name = tokens[0]
            direction = tokens[1].upper() if len(tokens) > 1 else "ASC"
            
            # 验证字段名（接受别名格式）
            if field_name not in self._all_fields:
                raise ValueError(f"排序字段 {field_name} 不在允许的字段列表中")
            
            # 验证排序方向
            if direction not in ("ASC", "DESC"):
                raise ValueError(f"非法的排序方向: {direction}")
            
            # 将别名转换为原始的 表名.字段名 格式
            table_name, orig_field = self._alias_to_original[field_name]
            quoted_field = f"{self._quote(table_name)}.{self._quote(orig_field)}"
            parts.append(f"{quoted_field} {direction}")
        
        if parts:
            return "ORDER BY " + ", ".join(parts)
        return ""
    
    def build_limit_clause(self, page: int, page_size: int) -> Tuple[str, List[int]]:
        """
        构建 LIMIT 子句
        
        Args:
            page: 页码
            page_size: 每页数量
        
        Returns:
            (LIMIT 子句 SQL, 参数列表)
        """
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        return "LIMIT %s OFFSET %s", [page_size, offset]
    
    def build_count_sql(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[Any]]:
        """
        构建计数 SQL
        
        Args:
            filters: 过滤条件
        
        Returns:
            (SQL, 参数列表)
        """
        # 先构建字段以初始化 _all_fields
        if not self._all_fields:
            self.build_select_fields()
        
        from_clause = self.build_from_clause()
        where_clause, params = self.build_where_clause(filters)
        
        sql = f"SELECT COUNT(*) {from_clause}"
        if where_clause:
            sql += f" {where_clause}"
        
        return sql, params
    
    def build_query_sql(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> Tuple[str, List[Any], List[FieldMeta]]:
        """
        构建完整的查询 SQL
        
        Args:
            filters: 过滤条件
            order_by: 排序
            page: 页码
            page_size: 每页数量
        
        Returns:
            (SQL, 参数列表, 字段元信息)
        """
        select_clause, field_meta = self.build_select_fields()
        from_clause = self.build_from_clause()
        where_clause, where_params = self.build_where_clause(filters)
        order_clause = self.build_order_clause(order_by)
        limit_clause, limit_params = self.build_limit_clause(page, page_size)
        
        sql_parts = [f"SELECT {select_clause}", from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if order_clause:
            sql_parts.append(order_clause)
        sql_parts.append(limit_clause)
        
        sql = "\n".join(sql_parts)
        params = where_params + limit_params
        
        return sql, params, field_meta
    
    def _get_table_fields(self, table_name: str) -> List[Tuple[str, str, str]]:
        """
        获取表的字段列表
        
        Args:
            table_name: 表名
        
        Returns:
            [(字段名, 字段类型, 字段注释), ...]
        """
        try:
            with connection.cursor() as cursor:
                # 使用 INFORMATION_SCHEMA 获取字段信息，包含注释
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, [table_name])
                
                fields = []
                for row in cursor.fetchall():
                    field_name = row[0]
                    data_type = row[1].lower() if row[1] else "string"
                    field_comment = row[2] or ""  # 字段注释，可能为空
                    
                    # 映射数据库类型到简单类型
                    field_type = self._map_db_type(data_type)
                    fields.append((field_name, field_type, field_comment))
                
                return fields
        except Exception as e:
            logger.error(f"获取表 {table_name} 字段失败: {e}")
            return []
    
    def _map_db_type(self, db_type: str) -> str:
        """映射数据库类型到简单类型"""
        if any(t in db_type for t in ["int", "bigint", "smallint", "tinyint"]):
            return "integer"
        if any(t in db_type for t in ["decimal", "numeric", "float", "double", "real"]):
            return "decimal"
        if "date" in db_type and "time" not in db_type:
            return "date"
        if "datetime" in db_type or "timestamp" in db_type:
            return "datetime"
        if "bool" in db_type or "bit" in db_type:
            return "boolean"
        return "string"
    
    def _quote(self, identifier: str) -> str:
        """使用反引号转义标识符"""
        identifier = identifier.replace("`", "")
        return f"`{identifier}`"


# =============================================================================
# 辅助函数
# =============================================================================

def execute_join_query(
    primary_table: str,
    max_depth: int = 2,
    include_tables: Optional[List[str]] = None,
    exclude_tables: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[str] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    """
    执行联合查询
    
    Args:
        primary_table: 主表名
        max_depth: 最大关联深度
        include_tables: 要包含的关联表
        exclude_tables: 要排除的关联表
        filters: 过滤条件
        order_by: 排序
        page: 页码
        page_size: 每页数量
    
    Returns:
        {
            "items": [...],
            "total": int,
            "page": int,
            "page_size": int,
            "join_info": {...},
            "field_info": [...]
        }
    """
    # 解析关联关系
    parser = JoinRelationParser(
        max_depth=max_depth,
        include_tables=include_tables,
        exclude_tables=exclude_tables,
    )
    parse_result = parser.parse(primary_table)
    
    # 检查关联表数量
    if len(parse_result.relations) > MAX_TABLES_LIMIT:
        raise ValueError(
            f"关联表数量 ({len(parse_result.relations)}) 超过限制 ({MAX_TABLES_LIMIT})。"
            f"请减少关联深度或使用 include_tables 限制关联表。"
        )
    
    # 构建 SQL
    builder = JoinSQLBuilder(
        primary_table=parse_result.primary_table,
        relations=parse_result.relations,
    )
    
    # 执行计数查询
    count_sql, count_params = builder.build_count_sql(filters)
    with connection.cursor() as cursor:
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()[0]
    
    # 执行数据查询
    query_sql, query_params, field_meta = builder.build_query_sql(
        filters=filters,
        order_by=order_by,
        page=page,
        page_size=page_size,
    )
    
    logger.debug(f"联合查询 SQL: {query_sql}")
    logger.debug(f"参数: {query_params}")
    
    with connection.cursor() as cursor:
        cursor.execute(query_sql, query_params)
        columns = [col[0] for col in cursor.description]
        items = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    field_info_list = [f.to_dict() for f in field_meta]
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": min(page_size, MAX_PAGE_SIZE),
        "join_info": {
            "primary_table": parse_result.primary_table,
            "joined_tables": parse_result.joined_tables,
            "join_depth": parse_result.max_depth,
            "total_tables": parse_result.total_tables,
            "has_cycle": parse_result.has_cycle,
            "join_details": [r.to_dict() for r in parse_result.relations],
        },
        "field_info": field_info_list,
    }


def get_join_preview(
    table_name: str,
    max_depth: int = 2,
) -> Dict[str, Any]:
    """
    获取表的关联关系预览
    
    Args:
        table_name: 表名
        max_depth: 最大关联深度
    
    Returns:
        {
            "primary_table": str,
            "join_tree": [...],
            "total_related_tables": int,
            "max_depth": int,
            "has_cycle": bool,
            "all_fields": [...]
        }
    """
    # 解析关联关系
    parser = JoinRelationParser(max_depth=max_depth)
    parse_result = parser.parse(table_name)
    
    # 获取所有字段
    builder = JoinSQLBuilder(
        primary_table=parse_result.primary_table,
        relations=parse_result.relations,
    )
    _, field_meta = builder.build_select_fields()
    
    return {
        "primary_table": parse_result.primary_table,
        "join_tree": [r.to_dict() for r in parse_result.relations],
        "total_related_tables": len(parse_result.relations),
        "max_depth": parse_result.max_depth,
        "has_cycle": parse_result.has_cycle,
        "all_fields": [f.to_dict() for f in field_meta],
    }
