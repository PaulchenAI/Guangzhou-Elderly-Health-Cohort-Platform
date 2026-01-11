#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复剩余的少量||运算符
这些通常是非常复杂的嵌套CONCAT,需要手动分析处理
"""

import os
import re


def fix_remaining_pipes(file_path):
    """手动修复剩余的||运算符"""
    print(f"\n处理: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_count = content.count(' || ')
    
    if original_count == 0:
        print(f"  ✓ 无需修复")
        return
    
    # 对于剩余的||,尝试一个简单的方法:
    # 查找形如 CONCAT(...) || CONCAT(...) 的模式
    # 由于可能有多层嵌套,我们使用平衡括号匹配
    
    lines = content.split('\n')
    fixed_lines = []
    fix_count = 0
    
    for line_no, line in enumerate(lines, 1):
        if ' || ' not in line:
            fixed_lines.append(line)
            continue
        
        # 尝试修复这一行
        original_line = line
        attempts = 0
        max_attempts = 10
        
        while ' || ' in line and attempts < max_attempts:
            attempts += 1
            old_line = line
            
            # 最后的尝试:将 X || Y 转换为 CONCAT(X, Y)
            # 其中X和Y都不包含||
            # 使用贪婪匹配查找最外层的||
            
            # 查找包含||的片段
            # 寻找: CONCAT(...) || CONCAT(...)
            match = re.search(
                r'(CONCAT\([^()]*(?:\([^()]*\))*[^()]*\))\s*\|\|\s*(CONCAT\([^()]*(?:\([^()]*\))*[^()]*\))',
                line
            )
            
            if match:
                left = match.group(1)
                right = match.group(2)
                
                # 提取CONCAT内部的内容
                left_inner = left[7:-1]  # 去掉 CONCAT( 和 )
                right_inner = right[7:-1]
                
                # 合并
                merged = f"CONCAT({left_inner}, {right_inner})"
                line = line[:match.start()] + merged + line[match.end():]
                fix_count += 1
                continue
            
            # 没有找到可以修复的模式,退出
            break
        
        if line != original_line:
            print(f"  修复行{line_no}")
        
        fixed_lines.append(line)
    
    new_content = '\n'.join(fixed_lines)
    final_count = new_content.count(' || ')
    
    if final_count < original_count:
        # 创建备份
        backup_path = file_path + '.backup_final'
        os.rename(file_path, backup_path)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✓ 修复完成: {original_count} -> {final_count} 个||")
    else:
        print(f"  ! 无法修复,仍有{final_count}个||")


def main():
    base_path = '/mnt/f/work/zq-platform/docs/hospital/convertsql'
    
    files = [
        'gzlry_BSE_MEDICAL_INS_STATISTICS.sql',
        'gzlry_IC_CARE_PLAN_SUMMARIZE.sql',
        'gzlry_WM_MATERIAL.sql',
        'gzlry_EG_USER_OPERATION_LOG.sql',
        'gzlry_WM_USE_APPLY.sql',
        'gzlry_WM_USE_REGISTER.sql',
        'gzlry_WM_PURCHASE.sql'
    ]
    
    print("="*80)
    print("修复剩余的||运算符")
    print("="*80)
    
    for filename in files:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            fix_remaining_pipes(file_path)


if __name__ == '__main__':
    main()

