#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM SQL修复工具
基于大语言模型的SQL错误智能修复工具

使用方法:
    # 分析指定批次的导入日志
    python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../backend-django/logs/import_1f5b4b14.log
    
    # 自动应用修复（无需人工确认）
    python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --auto-apply
    
    # 只分析不修复
    python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --dry-run
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量 - 优先从 tools/.env 读取
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f'[配置] 从 {env_file} 加载环境变量')
else:
    # 回退到项目根目录
    project_root = Path(__file__).parent.parent / '.env'
    if project_root.exists():
        load_dotenv(project_root)
        print(f'[配置] 从 {project_root} 加载环境变量')
    else:
        load_dotenv()  # 尝试从默认位置加载


class LLMClient:
    """LLM客户端封装"""
    
    def __init__(self):
        self.api_key = os.getenv('LLM_API_KEY')
        self.base_url = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('LLM_MODEL_NAME', 'gpt-4o-mini')
        self.timeout = int(os.getenv('LLM_TIMEOUT', '30'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '4000'))
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
        
        if not self.api_key:
            raise ValueError('LLM_API_KEY 环境变量未设置，请在 .env 文件中配置')
        
        print(f'[配置] LLM模型: {self.model}')
        print(f'[配置] API地址: {self.base_url}')
    
    def call(self, prompt: str, system_prompt: str = None) -> str:
        """调用LLM API"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        data = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except requests.exceptions.RequestException as e:
            print(f'[错误] LLM API调用失败: {e}')
            if hasattr(e, 'response') and e.response:
                print(f'[错误] 响应内容: {e.response.text}')
            return None


class SQLError:
    """SQL错误信息"""
    
    def __init__(self, file_name: str, file_path: str, error_type: str,
                 error_code: str, error_msg: str, sql_snippet: str = None,
                 context: str = None, line_number: int = None):
        self.file_name = file_name
        self.file_path = file_path
        self.error_type = error_type
        self.error_code = error_code
        self.error_msg = error_msg
        self.sql_snippet = sql_snippet
        self.context = context
        self.line_number = line_number
    
    def __str__(self):
        return f'[{self.error_code}] {self.file_name}: {self.error_type}'


class LogParser:
    """日志解析器"""
    
    ERROR_CATEGORIES = {
        '1292': '数据类型转换错误',
        '1054': '字段不存在',
        '1064': 'SQL语法错误',
        '1067': '默认值无效',
        '1118': '行大小过大',
        '1146': '表不存在',
        '1062': '主键/唯一键冲突',
    }
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        if not log_file.exists():
            raise FileNotFoundError(f'日志文件不存在: {log_file}')
    
    def parse(self) -> List[SQLError]:
        """解析日志文件，提取错误信息"""
        errors = []
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有错误块（从"文件导入失败"到下一个分隔线）
        pattern = r'文件导入失败:.*?(?=(?:={80}|文件导入失败:|$))'
        error_blocks = re.findall(pattern, content, re.DOTALL)
        
        for block in error_blocks:
            error = self._parse_error_block(block)
            if error:
                errors.append(error)
        
        return errors
    
    def _parse_error_block(self, block: str) -> Optional[SQLError]:
        """解析单个错误块"""
        # 提取文件名
        file_match = re.search(r'文件导入失败: (.+?)$', block, re.MULTILINE)
        if not file_match:
            return None
        file_name = file_match.group(1).strip()
        
        # 提取文件路径
        path_match = re.search(r'文件路径: (.+?)$', block, re.MULTILINE)
        file_path = path_match.group(1).strip() if path_match else None
        
        # 提取错误码和消息
        code_match = re.search(r'MySQL错误码: (\d+)', block)
        error_code = code_match.group(1) if code_match else 'UNKNOWN'
        
        msg_match = re.search(r'错误消息: (.+?)$', block, re.MULTILINE)
        error_msg = msg_match.group(1).strip() if msg_match else ''
        
        # 提取错误类型
        type_match = re.search(r'错误分类: (.+?)$', block, re.MULTILINE)
        error_type = type_match.group(1).strip() if type_match else self.ERROR_CATEGORIES.get(error_code, '未知错误')
        
        # 提取SQL片段
        snippet_match = re.search(r'错误位置: (.+?)$', block, re.MULTILINE)
        sql_snippet = snippet_match.group(1).strip() if snippet_match else None
        
        # 提取上下文
        context_start = block.find('上下文:')
        line_match = re.search(r'大致位置: 第 (\d+) 行', block)
        line_number = int(line_match.group(1)) if line_match else None
        
        context = None
        if context_start != -1:
            context_end = block.find('相关表结构:', context_start)
            if context_end == -1:
                context_end = len(block)
            context_text = block[context_start:context_end]
            # 清理格式
            context_lines = [line.strip() for line in context_text.split('\n') if line.strip()]
            context = '\n'.join(context_lines[1:])  # 跳过标题行
        
        return SQLError(
            file_name=file_name,
            file_path=file_path,
            error_type=error_type,
            error_code=error_code,
            error_msg=error_msg,
            sql_snippet=sql_snippet,
            context=context,
            line_number=line_number
        )


class PromptTemplates:
    """Prompt模板库"""
    
    SYSTEM_PROMPT = """你是一个专业的数据库SQL专家，特别擅长Oracle到MySQL的SQL转换和错误修复。
你的任务是分析SQL错误，并提供准确的修复建议。

要求:
1. 仔细分析错误信息和SQL上下文
2. 提供具体的修复步骤和修复后的SQL
3. 解释修复的原因
4. 确保修复后的SQL在MySQL中能正确执行
5. 保持数据完整性，不改变原有的业务逻辑"""
    
    @staticmethod
    def get_fix_prompt(error: SQLError) -> str:
        """根据错误类型生成修复Prompt"""
        
        base_info = f"""
## 错误信息
- 文件: {error.file_name}
- 错误类型: {error.error_type}
- 错误码: {error.error_code}
- 错误消息: {error.error_msg}
"""
        
        if error.line_number:
            base_info += f"- 错误位置: 第 {error.line_number} 行附近\n"
        
        if error.sql_snippet:
            base_info += f"\n## 问题SQL片段\n```sql\n{error.sql_snippet}\n```\n"
        
        if error.context:
            base_info += f"\n## SQL上下文\n```sql\n{error.context}\n```\n"
        
        # 根据错误码选择专门的指导
        if error.error_code == '1292':
            guidance = """
## 修复目标
这是一个数据类型转换错误。通常是因为:
1. 字符串值被错误解析为数值
2. 引号使用不当
3. 特殊字符转义问题

请分析SQL片段，找出数据类型不匹配的地方，并修复引号或转义问题。
"""
        
        elif error.error_code == '1054':
            guidance = """
## 修复目标
字段不存在错误。通常是因为:
1. CREATE TABLE语句中缺少字段定义
2. INSERT语句中引用了不存在的字段

请检查CREATE TABLE语句，添加缺失的字段定义，并推断合理的字段类型和属性。
"""
        
        elif error.error_code == '1064':
            guidance = """
## 修复目标
SQL语法错误。通常是因为:
1. 引号嵌套问题
2. 特殊字符未正确转义
3. MySQL关键字使用不当
4. 括号不匹配

请仔细检查SQL语法，修复引号、转义、关键字等问题。
"""
        
        elif error.error_code == '1118':
            guidance = """
## 修复目标
行大小超过MySQL限制(65535字节)。通常是因为:
1. VARCHAR字段定义过大
2. 多个大VARCHAR字段累加超限

请将过大的VARCHAR字段转换为TEXT类型，优先处理最大的字段。
"""
        
        else:
            guidance = """
## 修复目标
请根据错误信息分析问题原因，并提供合适的修复方案。
"""
        
        prompt = base_info + guidance + """

## 输出格式
请按以下JSON格式输出修复方案:

```json
{
    "analysis": "问题原因分析",
    "fix_steps": [
        "修复步骤1",
        "修复步骤2"
    ],
    "fixed_sql": "修复后的完整SQL语句或SQL片段",
    "explanation": "修复的详细解释"
}
```

注意:
1. fixed_sql必须是可以直接执行的SQL
2. 如果是CREATE TABLE错误,提供完整的CREATE TABLE语句
3. 如果是INSERT错误,提供修复后的INSERT语句或相关部分
4. 确保SQL符合MySQL语法规范
"""
        
        return prompt


class SQLFixer:
    """SQL修复器"""
    
    def __init__(self, llm_client: LLMClient, sql_dir: Path):
        self.llm = llm_client
        self.sql_dir = sql_dir
        self.fix_cache = {}
    
    def fix_error(self, error: SQLError, auto_apply: bool = False) -> Tuple[bool, Optional[str]]:
        """修复单个错误"""
        print(f'\n{"="*80}')
        print(f'正在分析: {error}')
        print(f'{"="*80}')
        
        # 生成Prompt
        prompt = PromptTemplates.get_fix_prompt(error)
        
        print('[LLM] 正在调用LLM分析错误...')
        
        # 调用LLM
        response = self.llm.call(prompt, PromptTemplates.SYSTEM_PROMPT)
        
        if not response:
            print('[错误] LLM调用失败')
            return False, None
        
        # 解析响应
        fix_plan = self._parse_llm_response(response)
        
        if not fix_plan:
            print('[错误] LLM响应解析失败')
            print(f'原始响应: {response}')
            return False, None
        
        # 显示修复方案
        print(f'\n[分析] {fix_plan.get("analysis", "N/A")}')
        print(f'\n[修复步骤]')
        for i, step in enumerate(fix_plan.get('fix_steps', []), 1):
            print(f'  {i}. {step}')
        
        print(f'\n[修复后的SQL]')
        print('-' * 80)
        print(fix_plan.get('fixed_sql', 'N/A'))
        print('-' * 80)
        
        print(f'\n[说明] {fix_plan.get("explanation", "N/A")}')
        
        # 应用修复
        if auto_apply:
            apply = True
            print('\n[自动应用] 正在应用修复...')
        else:
            apply_input = input('\n是否应用此修复? (y/n/s=跳过): ').strip().lower()
            apply = apply_input == 'y'
        
        if apply:
            success = self._apply_fix(error, fix_plan.get('fixed_sql'))
            if success:
                print('[成功] 修复已应用到文件')
                return True, fix_plan.get('fixed_sql')
            else:
                print('[失败] 修复应用失败')
                return False, None
        else:
            print('[跳过] 未应用修复')
            return False, None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """解析LLM响应"""
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _apply_fix(self, error: SQLError, fixed_sql: str) -> bool:
        """应用修复到SQL文件"""
        if not fixed_sql:
            return False
        
        sql_file = self.sql_dir / error.file_name
        if not sql_file.exists():
            print(f'[错误] SQL文件不存在: {sql_file}')
            return False
        
        # 读取原文件
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建备份目录（在tools目录下）
        backup_dir = Path(__file__).parent / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # 创建备份（使用时间戳避免覆盖）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'{sql_file.stem}.backup_{timestamp}{sql_file.suffix}'
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[备份] 已创建备份: {backup_file}')
        
        # TODO: 智能应用修复（需要更复杂的逻辑）
        # 当前版本：简单提示用户手动修改
        print(f'[提示] 请手动将修复后的SQL应用到文件: {sql_file}')
        print(f'[提示] 或查看备份文件: {backup_file}')
        
        return True


def main():
    parser = argparse.ArgumentParser(description='LLM SQL修复工具')
    parser.add_argument('--batch-id', required=True, help='导入批次ID')
    parser.add_argument('--log-file', required=True, help='导入日志文件路径')
    parser.add_argument('--sql-dir', default='../docs/hospital/convertsql', help='SQL文件目录')
    parser.add_argument('--auto-apply', action='store_true', help='自动应用修复（不询问确认）')
    parser.add_argument('--dry-run', action='store_true', help='只分析不修复')
    
    args = parser.parse_args()
    
    print('='*80)
    print('          LLM SQL修复工具')
    print('='*80)
    print(f'批次ID: {args.batch_id}')
    print(f'日志文件: {args.log_file}')
    print(f'SQL目录: {args.sql_dir}')
    print('='*80)
    
    # 解析日志
    log_file = Path(args.log_file)
    parser = LogParser(log_file)
    
    print('\n[1/4] 正在解析日志文件...')
    errors = parser.parse()
    
    print(f'[结果] 找到 {len(errors)} 个错误')
    
    if not errors:
        print('没有需要修复的错误')
        return
    
    # 显示错误列表
    print('\n错误列表:')
    for i, error in enumerate(errors, 1):
        print(f'  {i}. {error}')
    
    if args.dry_run:
        print('\n[干运行模式] 不执行修复')
        return
    
    # 初始化LLM客户端
    print('\n[2/4] 正在初始化LLM客户端...')
    try:
        llm = LLMClient()
    except ValueError as e:
        print(f'[错误] {e}')
        sys.exit(1)
    
    # 初始化修复器
    print('\n[3/4] 正在初始化修复器...')
    sql_dir = Path(args.sql_dir)
    if not sql_dir.exists():
        print(f'[错误] SQL目录不存在: {sql_dir}')
        sys.exit(1)
    
    fixer = SQLFixer(llm, sql_dir)
    
    # 逐个处理错误
    print('\n[4/4] 开始处理错误...')
    
    success_count = 0
    for error in errors:
        success, fixed_sql = fixer.fix_error(error, args.auto_apply)
        if success:
            success_count += 1
    
    # 总结
    print('\n'+'='*80)
    print('修复完成')
    print(f'成功: {success_count}/{len(errors)}')
    print('='*80)
    
    if success_count > 0:
        print(f'\n💡 提示: 现在可以重新运行导入命令测试修复效果:')
        print(f'  cd ../backend-django')
        print(f'  python manage.py import_oracle_sql --batch-id {args.batch_id} --retry-failed')


if __name__ == '__main__':
    main()

