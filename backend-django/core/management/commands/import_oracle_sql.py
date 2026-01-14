# -*- coding: utf-8 -*-
"""
Django 管理命令：导入转换后的 MySQL SQL 文件

使用方法：
    # 导入单个文件
    python manage.py import_oracle_sql ../docs/hospital/convertsql/BS_DEPARTMENT.sql
    
    # 导入目录下所有文件
    python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all
    
    # 快捷导入转换目录
    python manage.py import_oracle_sql --default-convertsql
    
    # 跳过大文件（超过 100MB）
    python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --skip-large-files
    
    # 指定文件大小上限（MB）
    python manage.py import_oracle_sql ../docs/hospital/convertsql/ --all --max-size 50
    
    # 预览模式（不执行，只显示 SQL）
    python manage.py import_oracle_sql ../docs/hospital/convertsql/BS_DEPARTMENT.sql --dry-run
    
    # 自动修复 MySQL 语法错误
    python manage.py import_oracle_sql --default-convertsql --auto-fix
    
    # 自动修复 + 生成报告
    python manage.py import_oracle_sql --default-convertsql --auto-fix --fix-report
    
    # 保存修复后的文件
    python manage.py import_oracle_sql file.sql --auto-fix --save-fixed
    
    # 重试失败的文件（自动修复）
    python manage.py import_oracle_sql --batch-id <ID> --retry-failed --auto-fix
"""

import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from .sql_syntax_fixer import SQLSyntaxFixer, detect_fixable_errors


class Command(BaseCommand):
    help = '将转换后的 MySQL SQL 文件导入到当前 Django 配置的数据库'
    
    # 大文件阈值（字节）
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    ULTRA_LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB，超过此大小自动使用流式模式
    DEFAULT_MAX_SIZE = 100  # MB
    
    def _setup_detail_logger(self, batch_id):
        """设置详细日志记录器"""
        # 创建logs目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 创建日志文件
        log_file = log_dir / f'import_{batch_id}.log'
        
        # 配置日志记录器
        logger = logging.getLogger(f'sql_import_{batch_id}')
        logger.setLevel(logging.DEBUG)
        
        # 移除现有的处理器
        logger.handlers = []
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 详细格式
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        self.stdout.write(self.style.SUCCESS(f'详细日志将保存到: {log_file.absolute()}'))
        
        return logger
    
    def _log_import_error(self, sql_file, error_msg, sql_content, exception):
        """记录详细的导入错误信息到日志文件"""
        self.detail_logger.error('-' * 80)
        self.detail_logger.error(f'文件导入失败: {sql_file.name}')
        self.detail_logger.error(f'文件路径: {sql_file.absolute()}')
        self.detail_logger.error(f'文件大小: {sql_file.stat().st_size / (1024*1024):.2f} MB')
        self.detail_logger.error('-' * 80)
        
        # 记录错误类型和消息
        self.detail_logger.error(f'错误类型: {type(exception).__name__}')
        self.detail_logger.error(f'错误消息: {error_msg}')
        
        # 尝试提取错误码（MySQL错误）
        import re
        error_code_match = re.search(r'\((\d+),', error_msg)
        if error_code_match:
            error_code = error_code_match.group(1)
            self.detail_logger.error(f'MySQL错误码: {error_code}')
            
            # 根据错误码分类
            error_categories = {
                '1292': '数据类型转换错误',
                '1054': '字段不存在',
                '1064': 'SQL语法错误',
                '1067': '默认值无效',
                '1118': '行大小过大',
                '1146': '表不存在',
                '1062': '主键/唯一键冲突',
            }
            if error_code in error_categories:
                self.detail_logger.error(f'错误分类: {error_categories[error_code]}')
        
        # 尝试从错误消息中提取问题SQL片段
        self.detail_logger.error('-' * 80)
        self.detail_logger.error('问题SQL片段:')
        
        # 提取错误消息中的SQL片段（通常在引号中）
        sql_snippet_match = re.search(r"'([^']{20,200})'", error_msg)
        if sql_snippet_match:
            snippet = sql_snippet_match.group(1)
            self.detail_logger.error(f'  错误位置: ...{snippet}...')
            
            # 在完整SQL中定位该片段
            if snippet in sql_content:
                pos = sql_content.index(snippet)
                # 获取上下文（前后各200字符）
                start = max(0, pos - 200)
                end = min(len(sql_content), pos + len(snippet) + 200)
                context = sql_content[start:end]
                
                self.detail_logger.error('  上下文:')
                for line in context.split('\n'):
                    if line.strip():
                        self.detail_logger.error(f'    {line}')
                
                # 计算大致的行号
                lines_before = sql_content[:pos].count('\n')
                self.detail_logger.error(f'  大致位置: 第 {lines_before + 1} 行附近')
        
        # 如果是CREATE TABLE错误，记录表结构定义
        if 'CREATE TABLE' in error_msg.upper() or 'create table' in sql_content[:1000].lower():
            self.detail_logger.error('-' * 80)
            self.detail_logger.error('相关表结构:')
            
            # 提取CREATE TABLE语句
            create_match = re.search(
                r'create\s+table\s+\w+\s*\([^;]+\);',
                sql_content,
                re.IGNORECASE | re.DOTALL
            )
            if create_match:
                create_stmt = create_match.group(0)
                for line in create_stmt.split('\n')[:50]:  # 最多显示50行
                    self.detail_logger.error(f'  {line}')
        
        self.detail_logger.error('=' * 80)
        self.detail_logger.error('')
    
    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            nargs='?',
            default=None,
            help='SQL 文件或目录路径（转换后的 MySQL 格式文件）'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='处理目录下所有 SQL 文件'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只预览 SQL，不执行导入'
        )
        parser.add_argument(
            '--continue-on-error',
            action='store_true',
            help='遇到错误时继续处理下一个文件'
        )
        parser.add_argument(
            '--default-convertsql',
            action='store_true',
            help='快捷导入 docs/hospital/convertsql/ 目录下所有文件'
        )
        parser.add_argument(
            '--skip-large-files',
            action='store_true',
            help='自动跳过超过 100MB 的文件'
        )
        parser.add_argument(
            '--max-size',
            type=int,
            default=None,
            help='跳过超过指定大小的文件（单位：MB）'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='断点续导：继续上次未完成的导入'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='重试上次失败的文件'
        )
        parser.add_argument(
            '--show-status',
            action='store_true',
            help='显示导入状态'
        )
        parser.add_argument(
            '--batch-id',
            type=str,
            default=None,
            help='指定批次ID（用于查看状态或恢复导入）'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新导入（忽略状态表）'
        )
        parser.add_argument(
            '--no-transaction',
            action='store_true',
            help='禁用事务（用于超大文件）'
        )
        parser.add_argument(
            '--auto-fix',
            action='store_true',
            help='自动修复 SQL 语法错误（MySQL 保留字等）'
        )
        parser.add_argument(
            '--save-fixed',
            action='store_true',
            help='保存修复后的 SQL 到新文件（需配合 --auto-fix 使用）'
        )
        parser.add_argument(
            '--fix-report',
            action='store_true',
            help='生成详细的修复报告'
        )
        parser.add_argument(
            '--streaming',
            action='store_true',
            help='启用流式处理模式（用于超大文件，逐语句执行，内存占用低）'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='流式处理时每批提交的语句数（默认 1000）'
        )
    
    def handle(self, *args, **options):
        # 处理 --show-status 参数
        if options['show_status']:
            self._show_import_status(options.get('batch_id'))
            return
        
        # 生成或获取批次 ID（需要提前以便日志文件命名）
        batch_id = options.get('batch_id') or str(uuid.uuid4())[:8]
        
        # 初始化详细日志记录器
        self.detail_logger = self._setup_detail_logger(batch_id)
        self.detail_logger.info('='*80)
        self.detail_logger.info(f'SQL导入任务开始 - 批次ID: {batch_id}')
        self.detail_logger.info(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.detail_logger.info('='*80)
        
        # 初始化 SQL 语法修复器
        sql_fixer = None
        if options['auto_fix']:
            sql_fixer = SQLSyntaxFixer(enable_report=options['fix_report'])
            self.stdout.write(self.style.SUCCESS('已启用自动修复功能'))
            self.detail_logger.info('已启用自动修复功能')
        
        # 处理 --default-convertsql 参数
        if options['default_convertsql']:
            if options['path']:
                raise CommandError('不能同时指定路径和 --default-convertsql 参数')
            
            # 智能查找 docs/hospital/convertsql 目录
            # 尝试多个可能的路径
            possible_paths = [
                'docs/hospital/convertsql/',  # 从项目根目录
                '../docs/hospital/convertsql/',  # 从 backend-django 目录
                '../../docs/hospital/convertsql/',  # 更深的嵌套
            ]
            
            convertsql_path = None
            for p in possible_paths:
                test_path = Path(p)
                if test_path.exists() and test_path.is_dir():
                    convertsql_path = test_path
                    break
            
            if not convertsql_path:
                raise CommandError(
                    '找不到 docs/hospital/convertsql/ 目录。\n'
                    '请确保该目录存在，或使用绝对路径：\n'
                    '  python manage.py import_oracle_sql /mnt/f/work/zq-platform/docs/hospital/convertsql/ --all'
                )
            
            options['path'] = str(convertsql_path)
            options['all'] = True
            self.stdout.write(self.style.SUCCESS(f'使用默认转换目录: {convertsql_path.absolute()}'))
            self.detail_logger.info(f'使用默认转换目录: {convertsql_path.absolute()}')
        
        if not options['path']:
            raise CommandError('请指定 SQL 文件/目录路径，或使用 --default-convertsql 参数')
        
        path = Path(options['path'])
        
        if not path.exists():
            raise CommandError(f'路径不存在: {path}')
        
        self.stdout.write(f'批次 ID: {batch_id}')
        
        # 确保状态表存在
        self._ensure_status_table()
        
        # 计算文件大小上限（字节）
        max_size_bytes = None
        if options['skip_large_files']:
            max_size_bytes = self.DEFAULT_MAX_SIZE * 1024 * 1024
        elif options['max_size']:
            max_size_bytes = options['max_size'] * 1024 * 1024
        
        # 获取要处理的文件列表
        if path.is_file():
            sql_files = [path]
        elif options['all']:
            sql_files = list(path.glob('*.sql'))
        else:
            raise CommandError('请指定 --all 参数来处理目录下所有文件')
        
        if not sql_files:
            self.stdout.write(self.style.WARNING('没有找到 SQL 文件'))
            return
        
        # 按文件大小排序（先处理小文件）
        sql_files_with_size = []
        skipped_files = []
        
        for sql_file in sql_files:
            file_size = sql_file.stat().st_size
            
            # 检查文件大小限制
            if max_size_bytes and file_size > max_size_bytes:
                skipped_files.append((sql_file.name, file_size))
                # 记录跳过状态
                if not options['dry_run']:
                    self._update_file_status(
                        batch_id, sql_file.name, str(sql_file), file_size,
                        'skipped', error_message='文件超过大小限制'
                    )
                continue
            
            # 检查文件状态
            if not options['force'] and not options['dry_run']:
                status = self._get_file_status(batch_id, sql_file.name)
                
                # 断点续导：跳过已成功的文件
                if options['resume'] and status == 'success':
                    self.stdout.write(self.style.WARNING(f'跳过已完成: {sql_file.name}'))
                    continue
                
                # 重试失败：只处理失败的文件
                if options['retry_failed'] and status not in ('failed', None):
                    continue
                
            sql_files_with_size.append((sql_file, file_size))
        
        # 按文件大小排序
        sql_files_with_size.sort(key=lambda x: x[1])
        
        total = len(sql_files_with_size)
        success_count = 0
        failed_files = []
        
        if skipped_files:
            self.stdout.write(self.style.WARNING(
                f'跳过 {len(skipped_files)} 个大文件（超过 {max_size_bytes / 1024 / 1024:.0f}MB）：'))
            for name, size in skipped_files[:5]:  # 只显示前 5 个
                self.stdout.write(f'  - {name} ({self._format_size(size)})')
            if len(skipped_files) > 5:
                self.stdout.write(f'  ... 和其他 {len(skipped_files) - 5} 个文件')
            self.stdout.write('')
        
        self.stdout.write(f'找到 {total} 个待处理的 SQL 文件')
        
        for i, (sql_file, file_size) in enumerate(sql_files_with_size, 1):
            size_str = self._format_size(file_size)
            self.stdout.write(f'[{i}/{total}] 处理: {sql_file.name} ({size_str})')
            
            # 记录开始时间和状态
            start_time = datetime.now()
            if not options['dry_run']:
                self._update_file_status(
                    batch_id, sql_file.name, str(sql_file), file_size,
                    'processing', start_time=start_time
                )
            
            try:
                # 超大文件或手动指定流式模式
                use_streaming = options.get('streaming', False) or file_size > self.ULTRA_LARGE_FILE_THRESHOLD
                
                if use_streaming and not options['dry_run']:
                    # 流式处理超大文件
                    stmt_count, err_count, err_msgs = self._import_file_streaming(
                        sql_file,
                        sql_fixer=sql_fixer,
                        batch_size=options.get('batch_size', 1000),
                        continue_on_error=options['continue_on_error']
                    )
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    if err_count == 0:
                        self.stdout.write(self.style.SUCCESS(
                            f'  导入成功（{stmt_count} 条语句，耗时 {duration:.1f}秒）'))
                        self._update_file_status(
                            batch_id, sql_file.name, str(sql_file), file_size,
                            'success', end_time=end_time, statements_count=stmt_count
                        )
                        success_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  部分成功（{stmt_count} 条成功，{err_count} 条失败，耗时 {duration:.1f}秒）'))
                        if err_msgs:
                            self.stdout.write(self.style.ERROR(f'  错误示例: {err_msgs[0][:100]}...'))
                        # 视为成功（部分成功也算成功）
                        self._update_file_status(
                            batch_id, sql_file.name, str(sql_file), file_size,
                            'success', end_time=end_time, statements_count=stmt_count,
                            error_message=f'{err_count} 条失败'
                        )
                        success_count += 1
                    continue  # 跳过后续处理，进入下一个文件
                
                # 普通文件处理
                # 根据文件大小选择读取方式
                if file_size > self.LARGE_FILE_THRESHOLD:
                    sql_content = self._read_file_streaming(sql_file)
                else:
                    # 小文件直接读取
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                
                # 应用自动修复
                fix_count = 0
                if sql_fixer:
                    original_content = sql_content
                    sql_content, fix_count = sql_fixer.fix_sql_content(sql_content, sql_file.name)
                    
                    if fix_count > 0:
                        self.stdout.write(self.style.WARNING(
                            f'  [自动修复] 检测到 {fix_count} 处 MySQL 保留字问题'))
                    
                    # 保存修复后的文件
                    if options['save_fixed'] and fix_count > 0:
                        fixed_file = sql_file.parent / f"{sql_file.stem}_fixed{sql_file.suffix}"
                        with open(fixed_file, 'w', encoding='utf-8') as f:
                            f.write(sql_content)
                        self.stdout.write(self.style.SUCCESS(
                            f'  已保存修复后的文件: {fixed_file.name}'))
                
                if options['dry_run']:
                    # 预览模式
                    self.stdout.write(self.style.SUCCESS(f'  文件读取成功'))
                    self.stdout.write('=' * 50)
                    self.stdout.write(sql_content[:1000])
                    if len(sql_content) > 1000:
                        self.stdout.write('... (截断)')
                    self.stdout.write('=' * 50)
                    success_count += 1
                else:
                    # 导入模式
                    try:
                        stmt_count = self._execute_sql_with_transaction(
                            sql_content,
                            use_transaction=not options['no_transaction']
                        )
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'  导入成功（{stmt_count} 条语句，耗时 {duration:.1f}秒）'))
                        
                        # 更新成功状态
                        self._update_file_status(
                            batch_id, sql_file.name, str(sql_file), file_size,
                            'success', end_time=end_time, statements_count=stmt_count
                        )
                        success_count += 1
                    except Exception as e:
                        end_time = datetime.now()
                        error_msg = str(e)
                        self.stdout.write(self.style.ERROR(f'  导入失败: {error_msg}'))
                        
                        # 记录详细错误信息到日志
                        self._log_import_error(sql_file, error_msg, sql_content, e)
                        
                        # 检测是否可以自动修复
                        if not options['auto_fix']:
                            suggestions = detect_fixable_errors(error_msg)
                            if suggestions:
                                self.stdout.write(self.style.WARNING('\n  提示:'))
                                for suggestion in suggestions:
                                    for line in suggestion.split('\n'):
                                        self.stdout.write(f'    {line}')
                                self.stdout.write(f'    命令: python manage.py import_oracle_sql --batch-id {batch_id} --retry-failed --auto-fix\n')
                        
                        # 更新失败状态
                        self._update_file_status(
                            batch_id, sql_file.name, str(sql_file), file_size,
                            'failed', end_time=end_time, error_message=error_msg
                        )
                        failed_files.append((sql_file.name, error_msg))
                        
                        if not options['continue_on_error']:
                            break
                            
            except Exception as e:
                error_msg = str(e)
                self.stdout.write(self.style.ERROR(f'  处理失败: {error_msg}'))
                
                if not options['dry_run']:
                    self._update_file_status(
                        batch_id, sql_file.name, str(sql_file), file_size,
                        'failed', end_time=datetime.now(), error_message=error_msg
                    )
                
                failed_files.append((sql_file.name, error_msg))
                if not options['continue_on_error']:
                    break
        
        # 输出报告
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(f'批次 ID: {batch_id}')
        self.stdout.write(f'处理完成: 成功 {success_count}/{total}, 失败 {len(failed_files)}, 跳过 {len(skipped_files)}')
        
        # 生成修复报告
        if sql_fixer and sql_fixer.get_fix_count() > 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'自动修复统计: {sql_fixer.get_fix_count()} 处'))
            
            if options['fix_report']:
                report_file = Path(f'sql_fix_report_{batch_id}.txt')
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(sql_fixer.generate_report())
                self.stdout.write(self.style.SUCCESS(f'修复报告已保存: {report_file}'))
        
        if failed_files:
            self.stdout.write(self.style.WARNING(f'\n失败文件:'))
            for name, error in failed_files[:10]:  # 只显示前 10 个
                error_short = error[:80] + '...' if len(error) > 80 else error
                self.stdout.write(f'  - {name}: {error_short}')
            if len(failed_files) > 10:
                self.stdout.write(f'  ... 和其他 {len(failed_files) - 10} 个文件')
            
            self.stdout.write(f'\n提示: 使用以下命令重试失败的文件:')
            self.stdout.write(f'  python manage.py import_oracle_sql --batch-id {batch_id} --retry-failed')
        
        # 记录总结到日志
        self.detail_logger.info('='*80)
        self.detail_logger.info('导入任务完成')
        self.detail_logger.info(f'成功: {success_count}, 失败: {len(failed_files)}, 跳过: {len(skipped_files)}')
        if failed_files:
            self.detail_logger.info('失败的文件:')
            for name, error in failed_files:
                self.detail_logger.info(f'  - {name}')
                self.detail_logger.info(f'    错误: {error}')
        self.detail_logger.info('='*80)
        
    def _ensure_status_table(self):
        """确保状态表存在"""
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sql_import_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size BIGINT NOT NULL,
                    status ENUM('pending', 'processing', 'success', 'failed', 'skipped') NOT NULL DEFAULT 'pending',
                    error_message TEXT,
                    start_time DATETIME,
                    end_time DATETIME,
                    batch_id VARCHAR(50) NOT NULL,
                    statements_count INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_file_batch (file_name, batch_id),
                    KEY idx_batch_id (batch_id),
                    KEY idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SQL导入状态追踪表'
            """)
    
    def _update_file_status(self, batch_id, file_name, file_path, file_size, 
                           status, start_time=None, end_time=None, 
                           error_message=None, statements_count=0):
        """更新文件导入状态"""
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO sql_import_log 
                (batch_id, file_name, file_path, file_size, status, start_time, end_time, error_message, statements_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                status = VALUES(status),
                start_time = COALESCE(VALUES(start_time), start_time),
                end_time = VALUES(end_time),
                error_message = VALUES(error_message),
                statements_count = VALUES(statements_count),
                updated_at = CURRENT_TIMESTAMP
            """, [batch_id, file_name, file_path, file_size, status, 
                  start_time, end_time, error_message, statements_count])
    
    def _get_file_status(self, batch_id, file_name):
        """获取文件导入状态"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT status FROM sql_import_log 
                WHERE batch_id = %s AND file_name = %s
            """, [batch_id, file_name])
            result = cursor.fetchone()
            return result[0] if result else None
    
    def _show_import_status(self, batch_id=None):
        """显示导入状态"""
        with connection.cursor() as cursor:
            if batch_id:
                # 显示特定批次
                cursor.execute("""
                    SELECT file_name, file_size, status, error_message, start_time, end_time, statements_count
                    FROM sql_import_log 
                    WHERE batch_id = %s
                    ORDER BY FIELD(status, 'processing', 'failed', 'pending', 'success', 'skipped'), file_name
                """, [batch_id])
                
                self.stdout.write(self.style.SUCCESS(f'\n批次 {batch_id} 的导入状态：'))
            else:
                # 显示最近的批次
                cursor.execute("""
                    SELECT DISTINCT batch_id, COUNT(*) as total, 
                           SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
                           SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                           MIN(created_at) as start_time,
                           MAX(updated_at) as update_time
                    FROM sql_import_log 
                    GROUP BY batch_id
                    ORDER BY MAX(updated_at) DESC
                    LIMIT 10
                """)
                
                self.stdout.write(self.style.SUCCESS('\n最近的导入批次：'))
                self.stdout.write('{:<12} {:>8} {:>8} {:>8} {:<20} {:<20}'.format(
                    '批次ID', '总数', '成功', '失败', '开始时间', '更新时间'))
                self.stdout.write('-' * 90)
                
                for row in cursor.fetchall():
                    batch_id, total, success, failed, start, update = row
                    self.stdout.write('{:<12} {:>8} {:>8} {:>8} {:<20} {:<20}'.format(
                        batch_id, total, success, failed,
                        start.strftime('%Y-%m-%d %H:%M:%S') if start else '-',
                        update.strftime('%Y-%m-%d %H:%M:%S') if update else '-'
                    ))
                
                self.stdout.write(f'\n提示: 使用 --batch-id <ID> --show-status 查看详细信息')
                return
            
            # 显示详细文件列表
            self.stdout.write('')
            self.stdout.write('{:<50} {:>12} {:>12} {:>15} {:<30}'.format(
                '文件名', '大小', '语句数', '状态', '错误信息'))
            self.stdout.write('-' * 130)
            
            stats = {'pending': 0, 'processing': 0, 'success': 0, 'failed': 0, 'skipped': 0}
            
            for row in cursor.fetchall():
                file_name, file_size, status, error, start_time, end_time, stmt_count = row
                stats[status] += 1
                
                size_str = self._format_size(file_size)
                error_str = (error[:27] + '...') if error and len(error) > 30 else (error or '')
                
                # 使用颜色标记状态
                if status == 'success':
                    status_str = self.style.SUCCESS(status)
                elif status == 'failed':
                    status_str = self.style.ERROR(status)
                elif status == 'processing':
                    status_str = self.style.WARNING(status)
                else:
                    status_str = status
                
                self.stdout.write('{:<50} {:>12} {:>12} {:>15} {:<30}'.format(
                    file_name[:47] + '...' if len(file_name) > 50 else file_name,
                    size_str,
                    stmt_count if stmt_count else '-',
                    status_str,
                    error_str
                ))
            
            # 统计信息
            self.stdout.write('')
            self.stdout.write('=' * 130)
            self.stdout.write(f'统计: 成功 {stats["success"]}, 失败 {stats["failed"]}, '
                            f'处理中 {stats["processing"]}, 待处理 {stats["pending"]}, '
                            f'跳过 {stats["skipped"]}')
    
    def _execute_sql_with_transaction(self, sql, use_transaction=True):
        """执行 SQL 语句（带事务管理）"""
        # 分割多条语句
        statements = []
        current = []
        
        for line in sql.split('\n'):
            stripped = line.strip()
            if stripped.startswith('--'):
                continue
            current.append(line)
            if stripped.endswith(';'):
                stmt = '\n'.join(current).strip()
                if stmt and stmt != ';':
                    statements.append(stmt.rstrip(';'))
                current = []
        
        # 处理最后一个语句（可能没有分号）
        if current:
            stmt = '\n'.join(current).strip()
            if stmt and stmt != ';':
                statements.append(stmt)
        
        if not statements:
            return 0
        
        # 分离 DDL 和 DML 语句
        ddl_statements = []
        dml_statements = []
        
        for stmt in statements:
            stmt_upper = stmt.upper().strip()
            # DDL 语句会导致隐式提交，需要单独处理
            if (stmt_upper.startswith('CREATE ') or 
                stmt_upper.startswith('ALTER ') or 
                stmt_upper.startswith('DROP ')):
                ddl_statements.append(stmt)
            else:
                dml_statements.append(stmt)
        
        executed_count = 0
        
        # 先执行 DDL（不使用事务）
        if ddl_statements:
            with connection.cursor() as cursor:
                # 禁用外键检查
                cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
                try:
                    for stmt in ddl_statements:
                        if stmt.strip():
                            try:
                                cursor.execute(stmt)
                                executed_count += 1
                            except Exception as e:
                                if not self._is_ignorable_error(e):
                                    raise
                finally:
                    # 恢复外键检查
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
        
        # 再执行 DML（使用事务）
        if dml_statements:
            if use_transaction:
                # 使用事务
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
                        try:
                            for stmt in dml_statements:
                                if stmt.strip():
                                    try:
                                        cursor.execute(stmt)
                                        executed_count += 1
                                    except Exception as e:
                                        if not self._is_ignorable_error(e):
                                            raise
                        finally:
                            cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
            else:
                # 不使用事务（用于超大文件）
                with connection.cursor() as cursor:
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
                    try:
                        for stmt in dml_statements:
                            if stmt.strip():
                                try:
                                    cursor.execute(stmt)
                                    executed_count += 1
                                except Exception as e:
                                    if not self._is_ignorable_error(e):
                                        raise
                    finally:
                        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
        
        return executed_count
    
    def _is_ignorable_error(self, e):
        """判断是否是可忽略的错误"""
        error_code = e.args[0] if e.args else 0
        error_msg = str(e).lower()
        
        # 可忽略的错误码
        ignorable_codes = [
            1050,  # Table already exists
            1060,  # Duplicate column name
            1061,  # Duplicate key name
            1062,  # Duplicate entry
            1068,  # Multiple primary key defined
            1091,  # Can't DROP; check that column/key exists
            1146,  # Table doesn't exist (for DELETE/INSERT before CREATE)
            1215,  # Cannot add foreign key constraint
            1824,  # Failed to open the referenced table
        ]
        
        if error_code in ignorable_codes:
            return True
        if 'already exists' in error_msg:
            return True
        if 'duplicate' in error_msg:
            return True
        if 'multiple primary key' in error_msg:
            return True
        if 'foreign key' in error_msg:
            return True
        
        return False
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f'{size_bytes}B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f}KB'
        elif size_bytes < 1024 * 1024 * 1024:
            return f'{size_bytes / 1024 / 1024:.1f}MB'
        else:
            return f'{size_bytes / 1024 / 1024 / 1024:.2f}GB'
    
    def _read_file_streaming(self, file_path):
        """流式读取大文件"""
        self.stdout.write(self.style.WARNING(f'  使用流式读取（文件较大）'))
        content = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                content.append(line)
        return ''.join(content)

    def _import_file_streaming(self, file_path, sql_fixer=None, batch_size=1000, continue_on_error=True):
        """
        真正的流式导入超大文件（逐语句处理，内存占用极低）
        
        Args:
            file_path: SQL 文件路径
            sql_fixer: SQL 修复器实例（可选）
            batch_size: 每批提交的语句数
            continue_on_error: 遇到错误是否继续
            
        Returns:
            (success_count, error_count, error_messages)
        """
        from django.db import connection
        
        self.stdout.write(self.style.WARNING(f'  [流式模式] 逐语句处理，批量提交（每 {batch_size} 条）'))
        
        success_count = 0
        error_count = 0
        error_messages = []
        current_stmt_lines = []
        pending_stmts = []
        total_fix_count = 0
        line_number = 0
        
        def execute_batch(stmts):
            """执行一批语句"""
            nonlocal success_count, error_count, error_messages
            if not stmts:
                return
            
            with connection.cursor() as cursor:
                cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
                for stmt in stmts:
                    try:
                        if stmt.strip():
                            cursor.execute(stmt)
                            success_count += 1
                    except Exception as e:
                        error_count += 1
                        error_msg = str(e)[:200]
                        if len(error_messages) < 10:  # 最多记录 10 条错误
                            error_messages.append(error_msg)
                        if not continue_on_error:
                            raise
                cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
                connection.commit()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_number += 1
                    stripped = line.strip()
                    
                    # 跳过注释
                    if stripped.startswith('--'):
                        continue
                    
                    current_stmt_lines.append(line)
                    
                    # 检查语句是否结束
                    if stripped.endswith(';'):
                        stmt = ''.join(current_stmt_lines).strip()
                        current_stmt_lines = []
                        
                        if not stmt or stmt == ';':
                            continue
                        
                        # 移除末尾分号
                        stmt = stmt.rstrip(';')
                        
                        # 应用自动修复
                        if sql_fixer:
                            fixed_stmt, fix_count = sql_fixer.fix_sql_content(stmt + ';', f'line_{line_number}')
                            if fix_count > 0:
                                total_fix_count += fix_count
                                stmt = fixed_stmt.rstrip(';')
                        
                        pending_stmts.append(stmt)
                        
                        # 达到批量大小时提交
                        if len(pending_stmts) >= batch_size:
                            execute_batch(pending_stmts)
                            pending_stmts = []
                            
                            # 显示进度
                            if success_count % 10000 == 0:
                                self.stdout.write(f'    已处理: {success_count} 条成功, {error_count} 条失败')
            
            # 处理剩余语句
            if current_stmt_lines:
                stmt = ''.join(current_stmt_lines).strip()
                if stmt and stmt != ';':
                    pending_stmts.append(stmt.rstrip(';'))
            
            execute_batch(pending_stmts)
            
        except Exception as e:
            error_messages.append(f'文件处理错误: {str(e)[:200]}')
        
        if total_fix_count > 0:
            self.stdout.write(self.style.WARNING(f'  [自动修复] 检测到 {total_fix_count} 处 MySQL 保留字问题'))
        
        return success_count, error_count, error_messages
