#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清除已导入的 gzlry_ 前缀表

使用方法：
    # 方式一：使用环境变量配置数据库连接
    export MYSQL_HOST=localhost
    export MYSQL_PORT=3306
    export MYSQL_USER=root
    export MYSQL_PASSWORD=your_password
    export MYSQL_DATABASE=your_database
    python tools/drop_gzlry_tables.py

    # 方式二：直接修改脚本中的数据库配置
    python tools/drop_gzlry_tables.py

    # 方式三：使用命令行参数
    python tools/drop_gzlry_tables.py --host localhost --port 3306 --user root --password xxx --database xxx
"""

import os
import sys
import argparse


def get_db_config(args):
    """获取数据库配置"""
    config = {
        'host': args.host or os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(args.port or os.environ.get('MYSQL_PORT', 3306)),
        'user': args.user or os.environ.get('MYSQL_USER', 'root'),
        'password': args.password or os.environ.get('MYSQL_PASSWORD', ''),
        'database': args.database or os.environ.get('MYSQL_DATABASE', ''),
    }
    return config


def drop_tables(config, prefix='gzlry_', dry_run=False):
    """删除指定前缀的表"""
    try:
        import pymysql
    except ImportError:
        print("错误：需要安装 pymysql")
        print("请运行：pip install pymysql")
        sys.exit(1)
    
    print(f"连接数据库: {config['host']}:{config['port']}/{config['database']}")
    
    try:
        conn = pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
    except Exception as e:
        print(f"连接数据库失败: {e}")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    # 查询所有以指定前缀开头的表
    cursor.execute(f"SHOW TABLES LIKE '{prefix}%'")
    tables = cursor.fetchall()
    
    if not tables:
        print(f"没有找到以 '{prefix}' 开头的表")
        cursor.close()
        conn.close()
        return
    
    table_names = [t[0] for t in tables]
    print(f"\n找到 {len(table_names)} 个以 '{prefix}' 开头的表：")
    
    # 显示前 20 个表名
    for i, name in enumerate(table_names[:20]):
        print(f"  {i+1}. {name}")
    if len(table_names) > 20:
        print(f"  ... 还有 {len(table_names) - 20} 个表")
    
    if dry_run:
        print(f"\n[DRY RUN] 将删除以上 {len(table_names)} 个表（未实际执行）")
        cursor.close()
        conn.close()
        return
    
    # 确认删除
    print(f"\n警告：即将删除以上 {len(table_names)} 个表！")
    confirm = input("确认删除？输入 'yes' 继续: ")
    
    if confirm.lower() != 'yes':
        print("已取消")
        cursor.close()
        conn.close()
        return
    
    # 禁用外键检查
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    # 删除表
    success_count = 0
    failed_count = 0
    
    for table_name in table_names:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            success_count += 1
            print(f"  ✓ 已删除: {table_name}")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 删除失败: {table_name} - {e}")
    
    # 恢复外键检查
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n删除完成：成功 {success_count}，失败 {failed_count}")


def main():
    parser = argparse.ArgumentParser(
        description='清除已导入的 gzlry_ 前缀表',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用环境变量
  export MYSQL_HOST=localhost MYSQL_USER=root MYSQL_PASSWORD=xxx MYSQL_DATABASE=xxx
  python tools/drop_gzlry_tables.py

  # 使用命令行参数
  python tools/drop_gzlry_tables.py --host localhost --user root --password xxx --database xxx

  # 预览模式（不实际删除）
  python tools/drop_gzlry_tables.py --dry-run

  # 删除其他前缀的表
  python tools/drop_gzlry_tables.py --prefix test_
        """
    )
    
    parser.add_argument('--host', help='MySQL 主机')
    parser.add_argument('--port', type=int, help='MySQL 端口')
    parser.add_argument('--user', help='MySQL 用户名')
    parser.add_argument('--password', help='MySQL 密码')
    parser.add_argument('--database', help='MySQL 数据库名')
    parser.add_argument('--prefix', default='gzlry_', help='表名前缀（默认: gzlry_）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际删除')
    
    args = parser.parse_args()
    
    config = get_db_config(args)
    
    if not config['database']:
        print("错误：未指定数据库名")
        print("请通过 --database 参数或 MYSQL_DATABASE 环境变量指定")
        sys.exit(1)
    
    drop_tables(config, args.prefix, args.dry_run)


if __name__ == '__main__':
    main()
