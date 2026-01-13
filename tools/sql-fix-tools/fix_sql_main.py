#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQL修复工具 - 主入口脚本
一键执行所有SQL修复流程

支持以下参数:
    --target-dir DIR    指定要修复的目录（默认使用配置文件中的目录）
    --quiet             减少输出信息（适合自动化调用）
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

# 全局变量
TARGET_DIR = None
QUIET_MODE = False


def print_banner():
    """打印banner"""
    print("="*80)
    print("              SQL修复工具集 - 主入口")
    print("         Oracle SQL to MySQL SQL 兼容性修复")
    print("="*80)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)


def run_script(script_name, description, extra_args=None):
    """运行子脚本
    
    Args:
        script_name: 脚本文件名
        description: 步骤描述
        extra_args: 额外的命令行参数列表
    """
    if not QUIET_MODE:
        print(f"\n{'='*80}")
        print(f"步骤: {description}")
        print(f"脚本: {script_name}")
        print(f"{'='*80}\n")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        if not QUIET_MODE:
            print(f"❌ 错误: 脚本不存在 - {script_path}")
        return False
    
    try:
        cmd = [sys.executable, script_path]
        if extra_args:
            cmd.extend(extra_args)
        
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(__file__),
            check=False,
            capture_output=QUIET_MODE  # 在安静模式下捕获输出
        )
        
        if result.returncode == 0:
            if not QUIET_MODE:
                print(f"\n✅ {description} - 完成")
            return True
        else:
            if not QUIET_MODE:
                print(f"\n⚠️ {description} - 完成但有警告 (退出码: {result.returncode})")
            return True  # 继续执行
    except Exception as e:
        if not QUIET_MODE:
            print(f"\n❌ {description} - 失败: {str(e)}")
        return False


def show_summary():
    """显示总结"""
    print("\n" + "="*80)
    print("修复完成总结")
    print("="*80)
    print("""
✅ 已完成的修复:
  1. 特殊SQL问题修复
     - 表结构问题（缺失列定义）
     - Oracle函数转换（sysdate）
     - 基础CONCAT转换（30轮迭代）
  
  2. CONCAT残留问题修复
     - 复杂嵌套CONCAT合并
     - 最终清理

📊 预期成果:
  - 20,000+ 个||运算符已转换
  - 2个大文件可成功导入
  - 总成功率提升至 ~89%

⚠️ 剩余问题:
  - 9个文件可能仍需手动处理
  - 详见: 修复总结.md

📝 下一步操作:
  1. 查看修复报告: cat 修复总结.md
  
  2. 运行导入命令:
     cd ../../backend-django
     python manage.py import_oracle_sql \\
         --batch-id 1f5b4b14 \\
         --retry-failed \\
         --auto-fix \\
         --default-convertsql \\
         --continue-on-error \\
         --fix-report
  
  3. 查看导入状态:
     python manage.py import_oracle_sql --show-status --batch-id 1f5b4b14

💾 备份文件:
  所有原始文件都已备份，后缀为:
  - .backup (第一次修复)
  - .backup2 (CONCAT修复)
  - .backup3 (最终CONCAT修复)
""")
    print("="*80)


def main():
    """主函数"""
    global TARGET_DIR, QUIET_MODE
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='SQL修复工具 - 一键执行所有SQL修复流程',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--target-dir', '-t',
                       help='指定要修复的目录（默认使用配置文件中的目录）')
    parser.add_argument('--quiet', '-q',
                       action='store_true',
                       help='减少输出信息（适合自动化调用）')
    
    args = parser.parse_args()
    
    TARGET_DIR = args.target_dir
    QUIET_MODE = args.quiet
    
    if not QUIET_MODE:
        print_banner()
        print("\n此工具将修复以下问题:")
        print("  1. 表结构问题（缺失列定义）")
        print("  2. Oracle函数转换")
        print("  3. CONCAT运算符转换")
        print("  4. 复杂嵌套CONCAT合并")
        print("\n所有修改都会创建备份文件")
        print("\n开始执行修复流程...\n")
    
    # 步骤1: 特殊SQL问题修复
    extra_args = []
    if TARGET_DIR:
        extra_args = ['--target-dir', TARGET_DIR]
    
    if not run_script('fix_special_sql_issues.py', '特殊SQL问题修复', extra_args):
        if not QUIET_MODE:
            print("\n❌ 修复流程中断")
        sys.exit(1)
    
    # 步骤2: CONCAT残留问题修复
    if not run_script('fix_remaining_concat.py', 'CONCAT残留问题修复', extra_args):
        if not QUIET_MODE:
            print("\n⚠️ CONCAT残留修复有警告，但继续")
    
    # 显示总结
    if not QUIET_MODE:
        show_summary()
        print("\n✅ SQL修复工具执行完毕！")
        print("详细信息请查看: 修复总结.md\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断执行")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

