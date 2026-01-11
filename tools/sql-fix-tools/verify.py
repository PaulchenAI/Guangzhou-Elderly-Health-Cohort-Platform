#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQL修复工具 - 验证脚本
检查工具完整性和环境配置
"""

import os
import sys
from pathlib import Path


def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def check_files():
    """检查必需文件是否存在"""
    print_section("1. 文件完整性检查")
    
    required_files = [
        'README.md',
        'INDEX.md',
        '快速参考.md',
        '使用示例.md',
        '修复总结.md',
        'package.json',
        '.gitignore',
        'fix_sql_main.py',
        'fix_special_sql_issues.py',
        'fix_remaining_concat.py'
    ]
    
    missing = []
    for filename in required_files:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✅ {filename:<40} ({size:>6} bytes)")
        else:
            print(f"  ❌ {filename:<40} (缺失)")
            missing.append(filename)
    
    if missing:
        print(f"\n  ⚠️  缺失 {len(missing)} 个文件")
        return False
    else:
        print(f"\n  ✅ 所有文件完整 (共{len(required_files)}个)")
        return True


def check_permissions():
    """检查文件权限"""
    print_section("2. 文件权限检查")
    
    executable_files = [
        'fix_sql_main.py',
        'fix_special_sql_issues.py',
        'fix_remaining_concat.py'
    ]
    
    all_ok = True
    for filename in executable_files:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            is_executable = os.access(filepath, os.X_OK)
            status = "✅" if is_executable else "⚠️"
            print(f"  {status} {filename:<40} {'可执行' if is_executable else '不可执行'}")
            if not is_executable:
                all_ok = False
        else:
            print(f"  ❌ {filename:<40} (文件不存在)")
            all_ok = False
    
    if not all_ok:
        print("\n  💡 提示: 运行 'chmod +x *.py' 添加执行权限")
    else:
        print("\n  ✅ 所有脚本都可执行")
    
    return all_ok


def check_target_directory():
    """检查目标SQL目录"""
    print_section("3. 目标SQL目录检查")
    
    base_path = '/mnt/f/work/zq-platform/docs/hospital/convertsql'
    
    if not os.path.exists(base_path):
        print(f"  ❌ 目标目录不存在: {base_path}")
        return False
    
    print(f"  ✅ 目标目录存在: {base_path}")
    
    # 统计SQL文件
    try:
        sql_files = [f for f in os.listdir(base_path) if f.endswith('.sql')]
        backup_files = [f for f in os.listdir(base_path) if '.backup' in f]
        
        print(f"  📁 SQL文件数量: {len(sql_files)}")
        print(f"  💾 备份文件数量: {len(backup_files)}")
        
        # 检查关键文件
        key_files = [
            'gzlry_HR_CEREBRAL_STROKE.sql',
            'gzlry_OL_RECORD.sql',
            'gzlry_WM_USE_REGISTER.sql'
        ]
        
        print("\n  关键文件检查:")
        for filename in key_files:
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"    ✅ {filename:<40} ({size_mb:.1f} MB)")
            else:
                print(f"    ❌ {filename:<40} (不存在)")
        
        return True
    except Exception as e:
        print(f"  ❌ 检查目录时出错: {str(e)}")
        return False


def check_python_environment():
    """检查Python环境"""
    print_section("4. Python环境检查")
    
    print(f"  Python版本: {sys.version}")
    print(f"  Python路径: {sys.executable}")
    
    # 检查必需的模块
    required_modules = ['os', 're', 'sys', 'subprocess', 'datetime', 'pathlib']
    
    print("\n  模块检查:")
    for module in required_modules:
        try:
            __import__(module)
            print(f"    ✅ {module}")
        except ImportError:
            print(f"    ❌ {module} (未安装)")
    
    return True


def show_usage_hints():
    """显示使用提示"""
    print_section("5. 使用提示")
    
    print("""
  📖 文档阅读顺序（推荐）:
    1. README.md        - 完整介绍 (5分钟)
    2. 快速参考.md      - 常用命令 (2分钟)
    3. 使用示例.md      - 实战场景 (按需阅读)
  
  🚀 快速开始:
    python fix_sql_main.py
  
  📊 查看文档:
    cat README.md       # 完整文档
    cat 快速参考.md     # 命令速查
    cat INDEX.md        # 文件索引
  
  🔧 分步执行:
    python fix_special_sql_issues.py    # 特殊问题修复
    python fix_remaining_concat.py      # CONCAT残留修复
  
  💡 获取帮助:
    cat INDEX.md        # 查看完整索引
""")


def main():
    """主函数"""
    print("="*70)
    print("          SQL修复工具集 - 验证脚本")
    print("="*70)
    print("\n正在检查工具完整性和环境配置...\n")
    
    results = []
    
    # 执行检查
    results.append(('文件完整性', check_files()))
    results.append(('文件权限', check_permissions()))
    results.append(('目标目录', check_target_directory()))
    results.append(('Python环境', check_python_environment()))
    
    # 显示总结
    print_section("检查总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:<20} {status}")
    
    print(f"\n  通过率: {passed}/{total} ({passed*100//total}%)")
    
    if passed == total:
        print("\n  🎉 所有检查通过！工具已就绪。")
        show_usage_hints()
        return 0
    else:
        print("\n  ⚠️  部分检查未通过，请修复上述问题。")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  检查被中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 检查过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

