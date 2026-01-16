# -*- coding: utf-8 -*-
"""
SQL 导入和外键提取工具

使用方法:
    python -m src.sql_import.foreignkey_cli extract-foreignkey <sql_file> -o <output_dir>
    python -m src.sql_import.foreignkey_cli extract-foreignkey-all <sql_dir> -o <output_dir>
"""

from .foreignkey_cli import main

if __name__ == '__main__':
    main()
