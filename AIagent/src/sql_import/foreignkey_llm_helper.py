# -*- coding: utf-8 -*-
"""
LLM 辅助外键提取脚本生成
使用 Claude API 分析未知格式并生成提取脚本
"""

import os
import re
import json
from typing import List, Optional, Dict
from datetime import datetime


class LLMHelper:
    """LLM 辅助工具 - 使用 Claude API 生成提取脚本"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 LLM Helper
        
        Args:
            api_key: Anthropic API 密钥
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.client = None
        
        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                print("警告：未安装 anthropic 包，LLM 功能将不可用")
                print("安装命令: pip install anthropic")
    
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return self.client is not None
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 Token 数量
        
        Args:
            text: 要估算的文本
            
        Returns:
            估算的 token 数量
        """
        # 简单估算：1个字符约等于0.4个token（英文）
        # 中文字符约等于1个token
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        non_ascii_chars = len(text) - ascii_chars
        
        estimated_tokens = int(ascii_chars * 0.4 + non_ascii_chars * 1.0)
        return estimated_tokens
    
    def extract_fk_statement_blocks(
        self, 
        sql_content: str, 
        max_examples: int = 3,
        max_tokens: int = 4000
    ) -> List[str]:
        """
        从 SQL 内容中提取外键语句块（用于发送给 LLM）
        
        Args:
            sql_content: SQL 文件内容
            max_examples: 最多提取的示例数量
            max_tokens: 最大 Token 数限制
            
        Returns:
            外键语句块列表
        """
        # 使用正则表达式查找包含外键定义的语句块
        fk_pattern = re.compile(
            r'(alter\s+table.*?foreign\s+key.*?;)',
            re.IGNORECASE | re.DOTALL
        )
        
        matches = fk_pattern.findall(sql_content)
        
        if not matches:
            return []
        
        # 清理和去重
        statements = []
        seen = set()
        total_tokens = 0
        
        for match in matches:
            # 清理空白字符
            cleaned = ' '.join(match.split())
            
            # 去重
            if cleaned in seen:
                continue
            
            # 检查 Token 限制
            tokens = self.estimate_tokens(cleaned)
            if total_tokens + tokens > max_tokens:
                break
            
            seen.add(cleaned)
            statements.append(match.strip())
            total_tokens += tokens
            
            if len(statements) >= max_examples:
                break
        
        return statements
    
    def generate_extraction_script(
        self,
        fk_statements: List[str],
        format_fingerprint: str,
        is_large_file: bool = False
    ) -> Optional[str]:
        """
        使用 Claude API 生成外键提取脚本
        
        Args:
            fk_statements: 外键语句示例列表
            format_fingerprint: 格式指纹
            is_large_file: 是否为大文件
            
        Returns:
            生成的 Python 代码，如果失败则返回 None
        """
        if not self.is_available():
            print("错误：LLM 不可用，请配置 ANTHROPIC_API_KEY")
            return None
        
        if not fk_statements:
            print("错误：没有提供外键语句示例")
            return None
        
        # 构建提示词
        examples_text = '\n\n'.join(
            f"示例 {i+1}:\n```sql\n{stmt}\n```"
            for i, stmt in enumerate(fk_statements[:3])
        )
        
        large_file_note = ""
        if is_large_file:
            large_file_note = """
注意：
- 这些示例是从大文件（>1MB）中提取的片段
- 生成的代码应该支持流式处理或分块处理
- 避免一次性加载整个文件到内存
"""
        
        prompt = f"""你是一个 SQL 解析专家。请分析以下外键定义语句的格式，并生成 Python 提取代码。

## 示例语句

{examples_text}

{large_file_note}

## 要求

1. 生成一个完整的 Python 函数 `extract_foreignkeys(sql_content: str) -> List[dict]`
2. 使用正则表达式提取以下信息：
   - constraint_name: 约束名称
   - source_table: 源表名
   - source_columns: 源字段列表（List[str]）
   - target_table: 目标表名
   - target_columns: 目标字段列表（List[str]）
   - on_delete: 删除规则（可选，值为 'cascade', 'set_null', 'restrict', 'no_action' 之一）
3. 返回标准格式的字典列表
4. 包含错误处理和边界情况处理
5. 添加详细注释说明格式特点
6. 字段名统一转为大写
7. 处理多字段外键（用逗号分隔）

## 输出格式

只输出 Python 代码，不要包含其他说明文字。代码格式：

```python
import re
from typing import List, Dict, Optional

def extract_foreignkeys(sql_content: str) -> List[Dict[str, any]]:
    \"\"\"
    提取外键信息
    
    格式特点：
    - ...（说明这个格式的特殊之处）
    \"\"\"
    foreign_keys = []
    
    # 你的提取逻辑
    pattern = re.compile(r'...', re.IGNORECASE | re.MULTILINE)
    matches = pattern.findall(sql_content)
    
    for match in matches:
        # 解析匹配结果
        fk = {{
            'constraint_name': ...,
            'source_table': ...,
            'source_columns': [...],
            'target_table': ...,
            'target_columns': [...],
            'on_delete': ...  # 可选
        }}
        foreign_keys.append(fk)
    
    return foreign_keys
```

请只输出代码，不要包含 markdown 标记或其他文字。"""

        try:
            # 调用 Claude API
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取代码
            code = response.content[0].text
            
            # 清理代码（移除可能的 markdown 标记）
            code = self._extract_code_block(code)
            
            return code
        
        except Exception as e:
            print(f"错误：调用 Claude API 失败 - {e}")
            return None
    
    def _extract_code_block(self, text: str) -> str:
        """从文本中提取代码块"""
        # 尝试提取 markdown 代码块
        code_block_pattern = re.compile(r'```(?:python)?\s*\n(.*?)\n```', re.DOTALL)
        match = code_block_pattern.search(text)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块标记，返回原文本
        return text.strip()
    
    def validate_generated_script(
        self,
        script_code: str,
        test_statements: List[str]
    ) -> Dict[str, any]:
        """
        验证 LLM 生成的脚本
        
        Args:
            script_code: 生成的 Python 代码
            test_statements: 测试语句列表
            
        Returns:
            验证结果字典 {success: bool, error: str, extracted_count: int}
        """
        result = {
            'success': False,
            'error': None,
            'extracted_count': 0
        }
        
        # 1. 语法检查
        try:
            compile(script_code, '<string>', 'exec')
        except SyntaxError as e:
            result['error'] = f"语法错误: {e}"
            return result
        
        # 2. 执行并测试
        try:
            namespace = {}
            exec(script_code, namespace)
            
            # 检查函数是否存在
            if 'extract_foreignkeys' not in namespace:
                result['error'] = "未找到 extract_foreignkeys 函数"
                return result
            
            extract_fn = namespace['extract_foreignkeys']
            
            # 3. 测试提取
            test_content = '\n\n'.join(test_statements)
            extracted = extract_fn(test_content)
            
            # 4. 检查返回格式
            if not isinstance(extracted, list):
                result['error'] = "返回值不是列表"
                return result
            
            if len(extracted) == 0:
                result['error'] = "未提取到任何外键"
                return result
            
            # 5. 检查字段完整性
            required_fields = {'constraint_name', 'source_table', 'source_columns', 'target_table', 'target_columns'}
            for fk in extracted:
                if not isinstance(fk, dict):
                    result['error'] = "外键项不是字典类型"
                    return result
                
                missing_fields = required_fields - set(fk.keys())
                if missing_fields:
                    result['error'] = f"缺少必需字段: {missing_fields}"
                    return result
                
                # 检查字段类型
                if not isinstance(fk['source_columns'], list) or not isinstance(fk['target_columns'], list):
                    result['error'] = "source_columns 和 target_columns 必须是列表"
                    return result
            
            # 验证成功
            result['success'] = True
            result['extracted_count'] = len(extracted)
            return result
        
        except Exception as e:
            result['error'] = f"执行错误: {e}"
            return result
    
    def generate_with_retry(
        self,
        fk_statements: List[str],
        format_fingerprint: str,
        max_retries: int = 2,
        is_large_file: bool = False
    ) -> Optional[str]:
        """
        带重试的脚本生成
        
        Args:
            fk_statements: 外键语句示例
            format_fingerprint: 格式指纹
            max_retries: 最大重试次数
            is_large_file: 是否为大文件
            
        Returns:
            验证通过的脚本代码，失败返回 None
        """
        for attempt in range(max_retries + 1):
            print(f"尝试生成提取脚本 (第 {attempt + 1}/{max_retries + 1} 次)...")
            
            # 生成脚本
            script_code = self.generate_extraction_script(
                fk_statements,
                format_fingerprint,
                is_large_file
            )
            
            if not script_code:
                continue
            
            # 验证脚本
            validation = self.validate_generated_script(script_code, fk_statements)
            
            if validation['success']:
                print(f"✓ 脚本生成成功！提取到 {validation['extracted_count']} 个外键")
                return script_code
            else:
                print(f"✗ 验证失败: {validation['error']}")
        
        print(f"✗ 所有尝试都失败")
        return None
