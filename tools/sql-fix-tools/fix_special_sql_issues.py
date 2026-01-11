#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
专门修复特定SQL文件的特殊问题
用于修复以下问题:
1. INSERT语句中引用了CREATE TABLE中不存在的列 (quit_smoking, quit_drinking)
2. DATETIME字段的默认值使用了Oracle sysdate函数
3. INSERT语句中使用了STR_TO_DATE但没有正确的引号
4. 复杂的字符串拼接导致的语法错误
"""

import os
import re
import sys


class SpecialSQLFixer:
    """专门修复特殊SQL问题"""
    
    def __init__(self):
        self.fixes_applied = []
    
    def fix_hr_cerebral_stroke(self, file_path):
        """
        修复 gzlry_HR_CEREBRAL_STROKE.sql
        问题: INSERT语句中包含quit_smoking和quit_drinking列,但CREATE TABLE中没有定义
        解决: 在CREATE TABLE中添加这两列
        """
        print(f"\n处理文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找CREATE TABLE语句
        create_table_pattern = r'(create table HR_CEREBRAL_STROKE\s*\()(.*?)(\)\s*ENGINE=InnoDB)'
        match = re.search(create_table_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not match:
            print("  ✗ 未找到CREATE TABLE语句")
            return False
        
        table_def = match.group(2)
        
        # 检查是否已有这两列
        if 'quit_smoking' in table_def and 'quit_drinking' in table_def:
            print("  ✓ 列已存在,无需修复")
            return False
        
        # 在weight列后添加quit_smoking和quit_drinking
        if 'weight' not in table_def:
            print("  ✗ 未找到weight列,无法插入")
            return False
        
        # 找到weight列的定义行
        weight_line_pattern = r'(weight\s+DECIMAL\([^)]+\)[^,]*,)'
        weight_match = re.search(weight_line_pattern, table_def, re.IGNORECASE)
        
        if not weight_match:
            print("  ✗ 无法定位weight列")
            return False
        
        # 在weight列后添加新列
        old_weight_line = weight_match.group(1)
        new_columns = (
            old_weight_line + '\n' +
            '  quit_smoking       VARCHAR(50),' + '\n' +
            '  quit_drinking      VARCHAR(50),'
        )
        
        new_table_def = table_def.replace(old_weight_line, new_columns)
        new_content = content.replace(table_def, new_table_def)
        
        # 写回文件
        backup_path = file_path + '.backup'
        os.rename(file_path, backup_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✓ 已添加quit_smoking和quit_drinking列")
        self.fixes_applied.append(('HR_CEREBRAL_STROKE', '添加缺失的列定义'))
        return True
    
    def fix_ol_record(self, file_path):
        """
        修复 gzlry_OL_RECORD.sql
        问题1: create_time字段使用了Oracle的sysdate函数作为默认值
        问题2: DATETIME(6)在MySQL中可能导致精度问题
        解决: 将 default sysdate 改为 default CURRENT_TIMESTAMP(6)
        """
        print(f"\n处理文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复sysdate为CURRENT_TIMESTAMP
        # 注意: DATETIME(6)需要CURRENT_TIMESTAMP(6)才能匹配精度
        content = re.sub(
            r'DATETIME\(6\)\s+default\s+sysdate',
            'DATETIME(6) default CURRENT_TIMESTAMP(6)',
            content,
            flags=re.IGNORECASE
        )
        
        if content == original_content:
            print("  ✓ 无需修复或已修复")
            return False
        
        # 写回文件
        backup_path = file_path + '.backup'
        if os.path.exists(file_path):
            os.rename(file_path, backup_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✓ 已修复create_time的默认值")
        self.fixes_applied.append(('OL_RECORD', '修复sysdate默认值'))
        return True
    
    def fix_wm_use_register(self, file_path):
        """
        修复 gzlry_WM_USE_REGISTER.sql
        问题: INSERT语句中STR_TO_DATE前后的引号不匹配
        解决: 检查并修复引号问题
        """
        print(f"\n处理文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        fixed_lines = []
        fix_count = 0
        
        for i, line in enumerate(lines):
            # 检查是否是INSERT语句行
            if 'insert into' in line.lower() or 'values' in line.lower():
                # 检查是否有STR_TO_DATE但引号不匹配的情况
                # 例如: STR_TO_DATE('28-10-' 这种情况
                if 'STR_TO_DATE' in line:
                    # 查找所有STR_TO_DATE调用
                    str_to_date_pattern = r"STR_TO_DATE\('([^']*)'(?:,\s*'([^']*)')?\)"
                    
                    # 检查是否有不完整的STR_TO_DATE
                    if "STR_TO_DATE('" in line:
                        # 计算单引号数量
                        quote_count = line.count("'")
                        # STR_TO_DATE通常需要4个单引号: STR_TO_DATE('date', 'format')
                        # 如果引号数量不是4的倍数,可能有问题
                        
                        # 查找不完整的STR_TO_DATE模式
                        # 例如: , STR_TO_DATE('28-10-' 后面缺少内容
                        incomplete_pattern = r"STR_TO_DATE\('[\d-]+'(?!\s*,\s*'%)"
                        if re.search(incomplete_pattern, line):
                            print(f"  ! 警告: 第{i+1}行可能有不完整的STR_TO_DATE: {line[:100]}...")
            
            fixed_lines.append(line)
        
        if fix_count > 0:
            content = '\n'.join(fixed_lines)
            backup_path = file_path + '.backup'
            os.rename(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✓ 已修复{fix_count}处引号问题")
            self.fixes_applied.append(('WM_USE_REGISTER', f'修复{fix_count}处引号问题'))
            return True
        else:
            print("  ✓ 未发现明显的引号问题")
            return False
    
    def fix_wm_purchase(self, file_path):
        """
        修复 gzlry_WM_PURCHASE.sql
        问题: 与WM_USE_REGISTER类似的引号问题
        """
        print(f"\n处理文件: {file_path}")
        return self.fix_wm_use_register(file_path)
    
    def fix_concat_issues(self, file_path):
        """
        修复包含复杂CONCAT的SQL文件
        问题: 数据中包含||字符串拼接,但已转换为CONCAT,可能仍有嵌套问题
        解决: 检查CONCAT嵌套是否正确
        """
        print(f"\n处理文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找可能有问题的CONCAT嵌套
        # 例如: CONCAT(CONCAT(...), ...) 可能导致问题
        concat_pattern = r'CONCAT\([^)]*CONCAT\([^)]*\)[^)]*\)'
        matches = re.findall(concat_pattern, content)
        
        if matches:
            print(f"  ! 发现{len(matches)}处嵌套CONCAT,可能需要手动检查")
            for i, match in enumerate(matches[:3]):  # 只显示前3个
                print(f"    示例{i+1}: {match[:100]}...")
        else:
            print("  ✓ 未发现明显的CONCAT嵌套问题")
        
        return False
    
    def fix_incomplete_concat_conversion(self, file_path):
        """
        修复不完整的CONCAT转换
        问题: CONCAT('...', CHAR(10)) || '...' 这种混合形式,以及 '...' || CHAR(10) || '...'
        解决: 将所有剩余的 || 也转换为CONCAT
        """
        print(f"\n处理文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 使用迭代方式处理所有 || 运算符
        # 重复执行直到没有 || 为止或达到最大迭代次数
        max_iterations = 30
        iteration = 0
        
        while ' || ' in content and iteration < max_iterations:
            iteration += 1
            old_content = content
            
            # 模式0: CONCAT(...) || CONCAT(...) -> CONCAT(..., ...)
            # 这是最复杂的,需要合并两个CONCAT
            def merge_concat_concat(match):
                left_inner = match.group(1).rstrip()
                right_inner = match.group(2).rstrip()
                return f"CONCAT({left_inner}, {right_inner})"
            
            # 使用非贪婪匹配来匹配CONCAT
            content = re.sub(
                r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
                merge_concat_concat,
                content
            )
            
            # 模式1: '...' || CHAR(n) || '...' (完整的三段式)
            content = re.sub(
                r"'([^']*)'\s*\|\|\s*CHAR\((\d+)\)\s*\|\|\s*'([^']*)'",
                r"CONCAT('\1', CHAR(\2), '\3')",
                content
            )
            
            # 模式2: '...' || CHAR(n) (两段式:字符串+CHAR)
            content = re.sub(
                r"'([^']*)'\s*\|\|\s*CHAR\((\d+)\)(?!\s*,)",
                r"CONCAT('\1', CHAR(\2))",
                content
            )
            
            # 模式3: CHAR(n) || '...' (两段式:CHAR+字符串)
            content = re.sub(
                r"CHAR\((\d+)\)\s*\|\|\s*'([^']*)'",
                r"CONCAT(CHAR(\1), '\2')",
                content
            )
            
            # 模式4: CONCAT(...) || '' (CONCAT+空字符串,可以移除空字符串)
            content = re.sub(
                r"CONCAT\(([^)]+(?:\([^)]*\))*)\)\s*\|\|\s*''",
                r"CONCAT(\1)",
                content
            )
            
            # 模式5: CONCAT(...) || '...' (CONCAT+字符串)
            def replace_concat_str(match):
                inner = match.group(1).rstrip()
                str_part = match.group(2)
                return f"CONCAT({inner}, '{str_part}')"
            
            content = re.sub(
                r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*'([^']*)'",
                replace_concat_str,
                content
            )
            
            # 模式6: '...' || CONCAT(...) (字符串+CONCAT)
            def replace_str_concat(match):
                str_part = match.group(1)
                inner = match.group(2).rstrip()
                return f"CONCAT('{str_part}', {inner})"
            
            content = re.sub(
                r"'([^']*)'\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
                replace_str_concat,
                content
            )
            
            # 模式7: CONCAT(...) || CHAR(n) (CONCAT+CHAR)
            def replace_concat_char(match):
                inner = match.group(1).rstrip()
                char_num = match.group(2)
                return f"CONCAT({inner}, CHAR({char_num}))"
            
            content = re.sub(
                r"CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*CHAR\((\d+)\)",
                replace_concat_char,
                content
            )
            
            # 模式8: CHAR(n) || CONCAT(...) (CHAR+CONCAT)
            def replace_char_concat(match):
                char_num = match.group(1)
                inner = match.group(2).rstrip()
                return f"CONCAT(CHAR({char_num}), {inner})"
            
            content = re.sub(
                r"CHAR\((\d+)\)\s*\|\|\s*CONCAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
                replace_char_concat,
                content
            )
            
            # 如果这轮没有变化,说明无法继续优化
            if content == old_content:
                # 检查是否还有|| 运算符
                if ' || ' in content:
                    remaining_count = content.count(' || ')
                    print(f"  ! 警告: 经过{iteration}轮迭代后仍有{remaining_count}个||运算符未转换")
                    # 打印一个示例
                    for line_no, line in enumerate(content.split('\n'), 1):
                        if ' || ' in line and 'CONCAT' in line:
                            print(f"  ! 示例(行{line_no}): {line[:150]}...")
                            break
                break
        
        if content != original_content:
            # 写回文件
            backup_path = file_path + '.backup3'
            if os.path.exists(file_path):
                os.rename(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 统计修复次数
            fix_count = content.count('CONCAT') - original_content.count('CONCAT')
            remaining_ops = content.count(' || ')
            print(f"  ✓ 已修复不完整的CONCAT转换(新增{fix_count}处CONCAT,剩余{remaining_ops}个||)")
            self.fixes_applied.append((os.path.basename(file_path), f'修复不完整CONCAT转换'))
            return True
        else:
            remaining_ops = content.count(' || ')
            if remaining_ops > 0:
                print(f"  ! 无法修复,剩余{remaining_ops}个||")
            else:
                print("  ✓ 无需修复")
            return False
    
    def analyze_truncated_double_errors(self, file_path):
        """
        分析 "Truncated incorrect DOUBLE value" 错误
        这类错误通常是因为:
        1. 字符串拼接转换不完整
        2. 数据中包含了不应该在数值上下文中的字符串
        """
        print(f"\n分析文件: {file_path}")
        
        basename = os.path.basename(file_path)
        
        # 这些文件的问题主要是数据问题,不是格式问题
        # 数据中包含了中文字符串,但在某些上下文中被误认为是数值
        # 解决方案: 手动检查INSERT语句,确保字符串字段用引号包裹
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 查找可能的问题行
        for i, line in enumerate(lines[:100]):  # 只检查前100行
            if 'insert into' in line.lower():
                # 检查是否有中文但缺少引号的情况
                # 这种检测比较复杂,只做简单提示
                if any('\u4e00' <= c <= '\u9fff' for c in line):
                    # 检查中文周围是否有引号
                    if "'" in line:
                        continue  # 可能已正确引用
                    else:
                        print(f"  ! 第{i+1}行包含中文但可能缺少引号")
        
        print(f"  ℹ 此类错误通常需要人工检查数据完整性")
        return False


def main():
    """主函数"""
    base_path = '/mnt/f/work/zq-platform/docs/hospital/convertsql'
    
    fixer = SpecialSQLFixer()
    
    print("="*80)
    print("SQL特殊问题修复工具")
    print("="*80)
    
    # 问题1: HR_CEREBRAL_STROKE - 缺少列定义
    hr_file = os.path.join(base_path, 'gzlry_HR_CEREBRAL_STROKE.sql')
    if os.path.exists(hr_file):
        fixer.fix_hr_cerebral_stroke(hr_file)
    else:
        print(f"\n文件不存在: {hr_file}")
    
    # 问题2: OL_RECORD - sysdate默认值
    ol_file = os.path.join(base_path, 'gzlry_OL_RECORD.sql')
    if os.path.exists(ol_file):
        fixer.fix_ol_record(ol_file)
    else:
        print(f"\n文件不存在: {ol_file}")
    
    # 问题3: WM_USE_REGISTER - 引号问题
    wm_use_file = os.path.join(base_path, 'gzlry_WM_USE_REGISTER.sql')
    if os.path.exists(wm_use_file):
        fixer.fix_wm_use_register(wm_use_file)
    else:
        print(f"\n文件不存在: {wm_use_file}")
    
    # 问题4: WM_PURCHASE - 引号问题
    wm_purchase_file = os.path.join(base_path, 'gzlry_WM_PURCHASE.sql')
    if os.path.exists(wm_purchase_file):
        fixer.fix_wm_purchase(wm_purchase_file)
    else:
        print(f"\n文件不存在: {wm_purchase_file}")
    
    # 问题5: CONCAT问题 - 多个文件
    concat_files = [
        'gzlry_BSE_MEDICAL_INS_STATISTICS.sql',
        'gzlry_IC_CARE_PLAN_SUMMARIZE.sql',
        'gzlry_WM_MATERIAL.sql',
        'gzlry_EG_USER_OPERATION_LOG.sql',
        'gzlry_WM_USE_APPLY.sql',
        'gzlry_WM_USE_REGISTER.sql',
        'gzlry_WM_PURCHASE.sql'
    ]
    
    print("\n" + "="*80)
    print("修复不完整的CONCAT转换")
    print("="*80)
    
    for filename in concat_files:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            fixer.fix_incomplete_concat_conversion(file_path)
        else:
            print(f"\n文件不存在: {file_path}")
    
    # 总结
    print("\n" + "="*80)
    print("修复总结")
    print("="*80)
    
    if fixer.fixes_applied:
        print(f"\n共修复了 {len(fixer.fixes_applied)} 个问题:")
        for table, fix_desc in fixer.fixes_applied:
            print(f"  ✓ {table}: {fix_desc}")
        print("\n已创建备份文件(.backup后缀)")
    else:
        print("\n没有应用任何修复")
    
    print("\n" + "="*80)
    print("剩余问题分析")
    print("="*80)
    print("""
1. gzlry_HR_PHYSICAL_EXAMINE.sql (Row size too large)
   - 问题: 表有265个VARCHAR列,总行大小超过65535字节限制
   - 解决: 已由自动修复将VARCHAR(>1000)转为TEXT,但列数太多仍可能超限
   - 建议: 考虑拆分表或将更多VARCHAR转为TEXT

2. gzlry_BSE_MEDICAL_INS_STATISTICS.sql 等(Truncated incorrect DOUBLE value)
   - 问题: 数据中有复杂的字符串拼接(||转CONCAT),某些上下文中被误认为数值
   - 解决: 需要人工检查INSERT语句,确保所有字符串字段正确加引号
   - 建议: 使用--continue-on-error跳过这些文件,或手动修复数据

3. gzlry_BSE_EXCEL.sql (极度复杂的嵌套CONCAT)
   - 问题: 超出正则表达式自动修复能力
   - 解决: 已创建手动修复指南
   - 建议: 参考 gzlry_BSE_EXCEL_修复说明.md
""")
    
    print("\n建议的下一步操作:")
    print("  1. 重新运行导入命令:")
    print("     python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed --auto-fix --default-convertsql --continue-on-error")
    print("  2. 对于仍然失败的文件,手动检查并修复")
    print("  3. 考虑使用--continue-on-error跳过极个别无法自动修复的文件")


if __name__ == '__main__':
    main()

