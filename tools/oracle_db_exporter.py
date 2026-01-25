#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Oracle 数据库导出工具

连接 Oracle 数据库，将指定 schema 下的表结构（DDL）与数据（DML）导出为 SQL 文件。
支持全量导出与增量导出（基于用户指定的增量列）。

使用方法：
    # 全量导出（未提供增量配置时默认全量）
    python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export
    
    # 指定增量配置 JSON
    python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export \
        --incremental-config tools/incremental_config.json
    
    # 仅导出 DDL
    python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --ddl-only
    
    # 仅导出 DML
    python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --dml-only
    
    # 预览模式（不实际导出）
    python tools/oracle_db_exporter.py export --schema HR --output docs/oracle_export --dry-run

数据库连接配置：
    从项目根目录 .env 文件读取以下环境变量：
    - ORACLE_HOST: 数据库主机
    - ORACLE_PORT: 端口（默认 1521）
    - ORACLE_SERVICE_NAME: 服务名
    - ORACLE_USER: 用户名
    - ORACLE_PASSWORD: 密码

增量配置 JSON 格式示例：
    {
        "default_incremental_column": "UPDATE_TIME",
        "tables": {
            "EMPLOYEES": {
                "incremental_column": "LAST_MODIFIED"
            },
            "DEPARTMENTS": {
                "incremental_column": "UPDATE_TIME"
            }
        }
    }
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_dotenv_from_project_root():
    """从项目根目录加载 .env 文件"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv 未安装，无法从 .env 文件加载配置。请运行: pip install python-dotenv")
        return
    
    # 尝试多个可能的项目根目录位置
    current_dir = Path(__file__).parent
    possible_roots = [
        current_dir.parent,  # tools 的父目录
        current_dir,
        Path.cwd(),
    ]
    
    for root in possible_roots:
        env_file = root / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
            logger.debug(f"已从 {env_file} 加载环境变量")
            return
    
    logger.debug("未找到 .env 文件，将仅使用系统环境变量")


# 加载环境变量
load_dotenv_from_project_root()


class OracleConnectionConfig:
    """Oracle 连接配置"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        service_name: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        dsn: Optional[str] = None,
    ):
        """
        初始化连接配置
        
        优先级：显式参数 > 环境变量
        """
        self.host = host or os.getenv("ORACLE_HOST")
        self.port = port or int(os.getenv("ORACLE_PORT", "1521"))
        self.service_name = service_name or os.getenv("ORACLE_SERVICE_NAME")
        self.user = user or os.getenv("ORACLE_USER")
        self.password = password or os.getenv("ORACLE_PASSWORD")
        self.dsn = dsn or os.getenv("ORACLE_DSN")
    
    def validate(self) -> List[str]:
        """验证配置完整性，返回缺失的配置项列表"""
        missing = []
        
        if not self.dsn:
            # 如果没有 DSN，则需要 host/service_name
            if not self.host:
                missing.append("ORACLE_HOST")
            if not self.service_name:
                missing.append("ORACLE_SERVICE_NAME")
        
        if not self.user:
            missing.append("ORACLE_USER")
        if not self.password:
            missing.append("ORACLE_PASSWORD")
        
        return missing
    
    def get_dsn(self) -> str:
        """获取 DSN 字符串"""
        if self.dsn:
            return self.dsn
        return f"{self.host}:{self.port}/{self.service_name}"


class IncrementalConfig:
    """增量导出配置"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化增量配置
        
        Args:
            config_path: JSON 配置文件路径，为 None 时表示全量导出
        """
        self.config_path = config_path
        self.default_column: Optional[str] = None
        self.table_columns: Dict[str, str] = {}
        
        if config_path:
            self._load_config(config_path)
    
    def _load_config(self, config_path: str):
        """加载 JSON 配置文件"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"增量配置文件不存在: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.default_column = config.get("default_incremental_column")
        
        tables = config.get("tables", {})
        for table_name, table_config in tables.items():
            if isinstance(table_config, dict):
                col = table_config.get("incremental_column")
                if col:
                    self.table_columns[table_name.upper()] = col
            elif isinstance(table_config, str):
                # 简化格式：直接是列名
                self.table_columns[table_name.upper()] = table_config
    
    def get_incremental_column(self, table_name: str) -> Optional[str]:
        """
        获取指定表的增量列
        
        Args:
            table_name: 表名（大小写不敏感）
            
        Returns:
            增量列名，如果未配置则返回 None（表示该表使用全量导出）
        """
        table_upper = table_name.upper()
        return self.table_columns.get(table_upper, self.default_column)
    
    def is_incremental_enabled(self) -> bool:
        """是否启用了增量导出（至少配置了一个增量列）"""
        return bool(self.default_column or self.table_columns)


class CheckpointManager:
    """Checkpoint 管理器"""
    
    def __init__(self, checkpoint_path: str):
        """
        初始化 checkpoint 管理器
        
        Args:
            checkpoint_path: checkpoint.json 文件路径
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.data: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """加载 checkpoint 文件"""
        if self.checkpoint_path.exists():
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "created_at": datetime.now().isoformat(),
                "tables": {}
            }
    
    def save(self):
        """保存 checkpoint 文件"""
        self.data["updated_at"] = datetime.now().isoformat()
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False, default=str)
    
    def get_last_value(self, table_name: str) -> Optional[Any]:
        """获取指定表的上次水位线值"""
        table_upper = table_name.upper()
        table_data = self.data.get("tables", {}).get(table_upper)
        if table_data:
            return table_data.get("last_value")
        return None
    
    def set_last_value(self, table_name: str, value: Any, column: str, row_count: int):
        """设置指定表的水位线值"""
        table_upper = table_name.upper()
        if "tables" not in self.data:
            self.data["tables"] = {}
        
        self.data["tables"][table_upper] = {
            "last_value": value,
            "incremental_column": column,
            "row_count": row_count,
            "updated_at": datetime.now().isoformat()
        }


class OracleDBExporter:
    """Oracle 数据库导出器"""
    
    # 批量读取大小
    BATCH_SIZE = 1000
    
    def __init__(
        self,
        conn_config: OracleConnectionConfig,
        incremental_config: Optional[IncrementalConfig] = None,
    ):
        """
        初始化导出器
        
        Args:
            conn_config: 数据库连接配置
            incremental_config: 增量配置，为 None 时使用全量导出
        """
        self.conn_config = conn_config
        self.incremental_config = incremental_config or IncrementalConfig()
        self.connection = None
    
    def connect(self) -> bool:
        """
        连接数据库
        
        Returns:
            连接是否成功
        """
        try:
            import oracledb
        except ImportError:
            logger.error(
                "oracledb 未安装。请运行: pip install oracledb\n"
                "或安装 tools 依赖: pip install -r tools/requirements.txt"
            )
            return False
        
        # 验证配置
        missing = self.conn_config.validate()
        if missing:
            logger.error(f"缺少必需的数据库配置: {', '.join(missing)}")
            logger.error("请在项目根目录 .env 文件中配置，或通过命令行参数传递")
            return False
        
        dsn = self.conn_config.get_dsn()
        prefer_thick = os.getenv("ORACLE_THICK_MODE", "").strip().lower() in ("1", "true", "yes", "y", "on")
        client_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")

        def _connect_once() -> None:
            self.connection = oracledb.connect(
                user=self.conn_config.user,
                password=self.conn_config.password,
                dsn=dsn,
            )

        try:
            logger.info(f"正在连接 Oracle: {dsn}")
            if prefer_thick:
                try:
                    if client_lib_dir:
                        oracledb.init_oracle_client(lib_dir=client_lib_dir)
                    else:
                        oracledb.init_oracle_client()
                except Exception as init_err:
                    logger.error(f"初始化 Oracle thick 模式失败: {init_err}")
                    return False

            _connect_once()
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            msg = str(e)
            if "DPY-3010" in msg and client_lib_dir and not prefer_thick:
                try:
                    oracledb.init_oracle_client(lib_dir=client_lib_dir)
                    _connect_once()
                    logger.info("数据库连接成功")
                    return True
                except Exception as thick_err:
                    logger.error(f"数据库连接失败: {thick_err}")
                    return False

            logger.error(f"数据库连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭连接时出错: {e}")
            self.connection = None
    
    def get_tables(
        self,
        schema: str,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取指定 schema 下的表列表
        
        Args:
            schema: schema 名称
            include_tables: 要包含的表（为空则包含所有）
            exclude_tables: 要排除的表
            
        Returns:
            表名列表
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT table_name FROM all_tables WHERE owner = :owner ORDER BY table_name",
                {"owner": schema.upper()}
            )
            all_tables = [row[0] for row in cursor.fetchall()]
            
            # 应用过滤
            if include_tables:
                include_upper = {t.upper() for t in include_tables}
                all_tables = [t for t in all_tables if t.upper() in include_upper]
            
            if exclude_tables:
                exclude_upper = {t.upper() for t in exclude_tables}
                all_tables = [t for t in all_tables if t.upper() not in exclude_upper]
            
            return all_tables
            
        finally:
            cursor.close()
    
    def get_table_columns(self, schema: str, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Returns:
            列信息列表，每个元素包含 name, data_type, nullable, data_length 等
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    data_length,
                    data_precision,
                    data_scale,
                    nullable,
                    data_default
                FROM all_tab_columns 
                WHERE owner = :owner AND table_name = :table_name
                ORDER BY column_id
            """, {"owner": schema.upper(), "table_name": table_name.upper()})
            
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "data_type": row[1],
                    "data_length": row[2],
                    "data_precision": row[3],
                    "data_scale": row[4],
                    "nullable": row[5] == 'Y',
                    "data_default": row[6],
                })
            return columns
            
        finally:
            cursor.close()
    
    def get_table_comments(self, schema: str, table_name: str) -> Tuple[Optional[str], Dict[str, str]]:
        """
        获取表和列的注释
        
        Returns:
            (表注释, {列名: 列注释})
        """
        cursor = self.connection.cursor()
        try:
            # 表注释
            cursor.execute("""
                SELECT comments FROM all_tab_comments 
                WHERE owner = :owner AND table_name = :table_name
            """, {"owner": schema.upper(), "table_name": table_name.upper()})
            row = cursor.fetchone()
            table_comment = row[0] if row else None
            
            # 列注释
            cursor.execute("""
                SELECT column_name, comments FROM all_col_comments 
                WHERE owner = :owner AND table_name = :table_name
            """, {"owner": schema.upper(), "table_name": table_name.upper()})
            column_comments = {row[0]: row[1] for row in cursor.fetchall() if row[1]}
            
            return table_comment, column_comments
            
        finally:
            cursor.close()
    
    def export_ddl(
        self,
        schema: str,
        table_name: str,
        include_comments: bool = True,
    ) -> str:
        """
        导出表的 DDL（CREATE TABLE）
        
        Args:
            schema: schema 名称
            table_name: 表名
            include_comments: 是否包含注释
            
        Returns:
            DDL SQL 字符串
        """
        columns = self.get_table_columns(schema, table_name)
        table_comment, column_comments = self.get_table_comments(schema, table_name) if include_comments else (None, {})
        
        # 构建 CREATE TABLE
        lines = [f"CREATE TABLE {table_name} ("]
        
        col_defs = []
        for col in columns:
            col_def = f"  {col['name']} {self._format_column_type(col)}"
            if not col['nullable']:
                col_def += " NOT NULL"
            if col['data_default']:
                col_def += f" DEFAULT {col['data_default'].strip()}"
            col_defs.append(col_def)
        
        lines.append(",\n".join(col_defs))
        lines.append(");")
        
        ddl = "\n".join(lines)
        
        # 添加注释语句
        if include_comments:
            if table_comment:
                ddl += f"\n\nCOMMENT ON TABLE {table_name} IS '{self._escape_string(table_comment)}';"
            for col_name, comment in column_comments.items():
                if comment:
                    ddl += f"\nCOMMENT ON COLUMN {table_name}.{col_name} IS '{self._escape_string(comment)}';"
        
        return ddl
    
    def _format_column_type(self, col: Dict[str, Any]) -> str:
        """格式化列类型"""
        dtype = col['data_type']
        
        if dtype in ('VARCHAR2', 'NVARCHAR2', 'CHAR', 'NCHAR'):
            return f"{dtype}({col['data_length']})"
        elif dtype == 'NUMBER':
            if col['data_precision'] is not None:
                if col['data_scale'] and col['data_scale'] > 0:
                    return f"NUMBER({col['data_precision']},{col['data_scale']})"
                else:
                    return f"NUMBER({col['data_precision']})"
            return "NUMBER"
        elif dtype in ('FLOAT', 'BINARY_FLOAT', 'BINARY_DOUBLE'):
            return dtype
        elif dtype in ('DATE', 'TIMESTAMP', 'CLOB', 'BLOB', 'LONG', 'RAW'):
            return dtype
        else:
            # 其他类型直接返回
            return dtype
    
    def _escape_string(self, s: str) -> str:
        """转义字符串中的单引号"""
        if s is None:
            return ""
        return s.replace("'", "''")
    
    def export_dml(
        self,
        schema: str,
        table_name: str,
        output_file: Path,
        incremental_column: Optional[str] = None,
        last_value: Optional[Any] = None,
    ) -> Tuple[int, Optional[Any]]:
        """
        导出表的 DML（INSERT INTO），支持增量
        
        Args:
            schema: schema 名称
            table_name: 表名
            output_file: 输出文件路径
            incremental_column: 增量列名
            last_value: 上次水位线值
            
        Returns:
            (导出行数, 新水位线值)
        """
        columns = self.get_table_columns(schema, table_name)
        column_names = [col['name'] for col in columns]
        
        # 构建查询
        base_sql = f"SELECT {', '.join(column_names)} FROM {schema}.{table_name}"
        params = {}
        
        if incremental_column and last_value is not None:
            # 验证增量列存在
            if incremental_column.upper() not in [c.upper() for c in column_names]:
                raise ValueError(f"表 {table_name} 不存在增量列 {incremental_column}")
            base_sql += f" WHERE {incremental_column} > :last_value"
            params["last_value"] = last_value
        
        if incremental_column:
            base_sql += f" ORDER BY {incremental_column}"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(base_sql, params)
            
            row_count = 0
            max_incremental_value = last_value
            incremental_col_idx = None
            
            if incremental_column:
                for idx, col in enumerate(column_names):
                    if col.upper() == incremental_column.upper():
                        incremental_col_idx = idx
                        break
            
            # 确保输出目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                while True:
                    rows = cursor.fetchmany(self.BATCH_SIZE)
                    if not rows:
                        break
                    
                    for row in rows:
                        values = []
                        for val in row:
                            values.append(self._format_value(val))
                        
                        insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(values)});\n"
                        f.write(insert_sql)
                        row_count += 1
                        
                        # 更新水位线
                        if incremental_col_idx is not None:
                            val = row[incremental_col_idx]
                            if val is not None:
                                if max_incremental_value is None or val > max_incremental_value:
                                    max_incremental_value = val
            
            return row_count, max_incremental_value
            
        finally:
            cursor.close()
    
    def _format_value(self, val: Any) -> str:
        """格式化 SQL 值"""
        if val is None:
            return "NULL"
        elif isinstance(val, bool):
            return "1" if val else "0"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, datetime):
            return f"TO_DATE('{val.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"
        elif isinstance(val, bytes):
            # BLOB 类型，转为十六进制
            return f"HEXTORAW('{val.hex().upper()}')"
        else:
            # 字符串类型
            escaped = str(val).replace("'", "''")
            return f"'{escaped}'"
    
    def export_all(
        self,
        schema: str,
        output_dir: str,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
        export_ddl: bool = True,
        export_dml: bool = True,
        include_comments: bool = True,
        overwrite: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        批量导出指定 schema 下的表
        
        Args:
            schema: schema 名称
            output_dir: 输出目录
            include_tables: 要包含的表
            exclude_tables: 要排除的表
            export_ddl: 是否导出 DDL
            export_dml: 是否导出 DML
            include_comments: DDL 是否包含注释
            overwrite: 是否覆盖已存在的文件
            dry_run: 预览模式，不实际导出
            
        Returns:
            导出结果摘要
        """
        output_path = Path(output_dir)
        create_dir = output_path / "create"
        insert_dir = output_path / "insert"
        
        # 获取表列表
        tables = self.get_tables(schema, include_tables, exclude_tables)
        logger.info(f"找到 {len(tables)} 张表待导出")
        
        if dry_run:
            logger.info("=== 预览模式 ===")
            for table in tables:
                inc_col = self.incremental_config.get_incremental_column(table)
                mode = f"增量({inc_col})" if inc_col else "全量"
                logger.info(f"  - {table}: {mode}")
            return {
                "status": "dry_run",
                "tables": tables,
                "incremental_enabled": self.incremental_config.is_incremental_enabled(),
            }
        
        # 初始化 checkpoint（仅在启用增量时）
        checkpoint = None
        if self.incremental_config.is_incremental_enabled():
            checkpoint = CheckpointManager(output_path / "checkpoint.json")
        
        # 创建输出目录
        if export_ddl:
            create_dir.mkdir(parents=True, exist_ok=True)
        if export_dml:
            insert_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出结果
        results = {
            "exported_at": datetime.now().isoformat(),
            "schema": schema,
            "output_dir": str(output_path),
            "tables": [],
            "total_rows": 0,
            "errors": [],
        }
        
        for table in tables:
            logger.info(f"正在导出: {table}")
            table_result = {"name": table, "ddl": None, "dml": None, "rows": 0}
            
            try:
                # 导出 DDL
                if export_ddl:
                    ddl_file = create_dir / f"{table}.sql"
                    if ddl_file.exists() and not overwrite:
                        logger.info(f"  跳过 DDL（文件已存在）: {ddl_file}")
                    else:
                        ddl = self.export_ddl(schema, table, include_comments)
                        with open(ddl_file, 'w', encoding='utf-8') as f:
                            f.write(ddl)
                        table_result["ddl"] = str(ddl_file)
                        logger.info(f"  DDL 已导出: {ddl_file}")
                
                # 导出 DML
                if export_dml:
                    dml_file = insert_dir / f"{table}_data.sql"
                    if dml_file.exists() and not overwrite:
                        logger.info(f"  跳过 DML（文件已存在）: {dml_file}")
                    else:
                        inc_col = self.incremental_config.get_incremental_column(table)
                        last_val = checkpoint.get_last_value(table) if checkpoint and inc_col else None
                        
                        mode_str = f"增量(>{last_val})" if last_val else ("增量(首次)" if inc_col else "全量")
                        logger.info(f"  导出模式: {mode_str}")
                        
                        row_count, new_val = self.export_dml(
                            schema, table, dml_file,
                            incremental_column=inc_col,
                            last_value=last_val
                        )
                        
                        table_result["dml"] = str(dml_file)
                        table_result["rows"] = row_count
                        results["total_rows"] += row_count
                        
                        # 更新 checkpoint
                        if checkpoint and inc_col and new_val is not None:
                            checkpoint.set_last_value(table, new_val, inc_col, row_count)
                        
                        logger.info(f"  DML 已导出: {dml_file} ({row_count} 行)")
                
                results["tables"].append(table_result)
                
            except Exception as e:
                error_msg = f"导出 {table} 失败: {e}"
                logger.error(error_msg)
                results["errors"].append({"table": table, "error": str(e)})
        
        # 保存 checkpoint
        if checkpoint:
            checkpoint.save()
            logger.info(f"Checkpoint 已保存: {checkpoint.checkpoint_path}")
        
        # 保存 manifest
        manifest_path = output_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Manifest 已保存: {manifest_path}")
        
        return results


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Oracle 数据库导出工具 - 将表结构和数据导出为 SQL 文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全量导出
  python oracle_db_exporter.py export --schema HR --output ./export

  # 指定增量配置
  python oracle_db_exporter.py export --schema HR --output ./export \\
      --incremental-config incremental.json

  # 仅导出 DDL
  python oracle_db_exporter.py export --schema HR --output ./export --ddl-only

  # 预览模式
  python oracle_db_exporter.py export --schema HR --output ./export --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # export 命令
    export_parser = subparsers.add_parser("export", help="导出数据库表")
    export_parser.add_argument("--schema", "-s", required=True, help="Schema 名称")
    export_parser.add_argument("--output", "-o", required=True, help="输出目录")
    
    # 连接参数（可选，优先于 .env）
    export_parser.add_argument("--host", help="Oracle 主机")
    export_parser.add_argument("--port", type=int, help="Oracle 端口")
    export_parser.add_argument("--service-name", help="Oracle 服务名")
    export_parser.add_argument("--user", "-u", help="用户名")
    export_parser.add_argument("--password", "-p", help="密码")
    export_parser.add_argument("--dsn", help="完整 DSN（优先于 host/port/service-name）")
    
    # 表过滤
    export_parser.add_argument("--include", nargs="+", help="要包含的表（逗号分隔或多个参数）")
    export_parser.add_argument("--exclude", nargs="+", help="要排除的表（逗号分隔或多个参数）")
    
    # 导出选项
    export_parser.add_argument("--ddl-only", action="store_true", help="仅导出 DDL")
    export_parser.add_argument("--dml-only", action="store_true", help="仅导出 DML")
    export_parser.add_argument("--no-comments", action="store_true", help="DDL 不包含注释")
    export_parser.add_argument("--skip-existing", action="store_true", help="跳过已存在的文件")
    
    # 增量配置
    export_parser.add_argument(
        "--incremental-config", "-i",
        help="增量配置 JSON 文件路径（未提供则使用全量导出）"
    )
    
    # 其他选项
    export_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际导出")
    export_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.command == "export":
        # 构建连接配置
        conn_config = OracleConnectionConfig(
            host=args.host,
            port=args.port,
            service_name=args.service_name,
            user=args.user,
            password=args.password,
            dsn=args.dsn,
        )
        
        # 加载增量配置
        inc_config = None
        if args.incremental_config:
            try:
                inc_config = IncrementalConfig(args.incremental_config)
                logger.info(f"已加载增量配置: {args.incremental_config}")
            except FileNotFoundError as e:
                logger.error(str(e))
                return 1
        
        # 创建导出器
        exporter = OracleDBExporter(conn_config, inc_config)
        
        # 连接数据库
        if not exporter.connect():
            return 1
        
        try:
            # 处理表过滤参数
            include_tables = None
            exclude_tables = None
            
            if args.include:
                include_tables = []
                for item in args.include:
                    include_tables.extend(item.split(","))
            
            if args.exclude:
                exclude_tables = []
                for item in args.exclude:
                    exclude_tables.extend(item.split(","))
            
            # 执行导出
            result = exporter.export_all(
                schema=args.schema,
                output_dir=args.output,
                include_tables=include_tables,
                exclude_tables=exclude_tables,
                export_ddl=not args.dml_only,
                export_dml=not args.ddl_only,
                include_comments=not args.no_comments,
                overwrite=not args.skip_existing,
                dry_run=args.dry_run,
            )
            
            # 输出摘要
            if args.dry_run:
                logger.info(f"预览完成，共 {len(result.get('tables', []))} 张表")
            else:
                logger.info("=" * 50)
                logger.info(f"导出完成！")
                logger.info(f"  表数量: {len(result.get('tables', []))}")
                logger.info(f"  总行数: {result.get('total_rows', 0)}")
                if result.get('errors'):
                    logger.warning(f"  错误数: {len(result['errors'])}")
                logger.info(f"  输出目录: {args.output}")
            
            return 0
            
        finally:
            exporter.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
