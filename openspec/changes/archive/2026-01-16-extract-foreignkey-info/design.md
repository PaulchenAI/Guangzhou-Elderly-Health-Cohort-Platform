# 外键信息提取设计

## 上下文

`docs/hospital/sql` 目录包含 954 个 Oracle PL/SQL Developer 导出的表结构文件，其中许多表定义了外键约束。这些外键信息使用 Oracle 的 `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` 语法定义。

**示例外键语句**：

```sql
-- 自引用外键（树形结构）
alter table BS_CHECK_TYPE
  add constraint FK_CHECK_R98_CHECK foreign key (PARENTID)
  references BS_CHECK_TYPE (MAINID) on delete cascade;

-- 多外键表
alter table BSE_SERVICE_PACKAGE_DETAIL
  add constraint FK_BSE_SERVICE_PACKAGE_DETAIL1 foreign key (BASE_SERVICE_PACKAGE_ID)
  references BSE_SERVICE_PACKAGE (MAINID) on delete cascade;
alter table BSE_SERVICE_PACKAGE_DETAIL
  add constraint FK_BSE_SERVICE_PACKAGE_DETAIL2 foreign key (SERVICE_ID)
  references BS_SER_MAINFILE (MAINID) on delete cascade;

-- 自引用外键（部门层级）
alter table BS_DEPARTMENT
  add constraint FK_DEPAR_R11_DEPAR foreign key (PARENTID)
  references BS_DEPARTMENT (MAINID);
```

## 目标 / 非目标

### 目标
- 提取完整的外键元数据（约束名、源表、源字段、目标表、目标字段、删除规则）
- 支持单字段和复合字段的外键（如 `(LISTNO, DETAILNO)`）
- 支持不同的删除规则（`on delete cascade`、`on delete set null` 等）
- **支持多种 SQL 格式的外键定义**（标准格式、非标准格式、未知格式）
- **智能格式识别**：自动判断文件格式并选择合适的提取策略
- **LLM 辅助**：对于未知格式，使用 Claude API 分析并生成提取脚本
- 生成结构化 JSON 文件，便于后续分析和可视化
- 提供灵活的存储格式（按表单独存储 vs 统一存储）
- **缓存 LLM 生成的脚本**，避免重复调用 API

### 非目标
- 不处理其他约束类型（主键、唯一键、检查约束）
- 不验证外键引用的有效性（是否存在目标表）
- 不生成 ER 图（可由后续工具基于 JSON 实现）
- 不处理极端复杂的 SQL 语句（如带条件的外键、动态 SQL）

## 决策

### 决策 1：多策略提取架构

**选择**：采用三层提取策略 + LLM 辅助生成

**理由**：
- SQL 文件来源多样，格式可能不统一
- 单一正则表达式无法处理所有格式变体
- LLM 提供智能的格式分析和脚本生成能力
- 策略缓存避免重复分析和 API 调用

**三层策略**：

#### 策略 1：标准正则表达式（优先级最高）

适用于标准 Oracle SQL 格式：

```python
pattern = re.compile(
    r'alter\s+table\s+(\w+)\s+'                          # 表名
    r'add\s+constraint\s+(\w+)\s+'                       # 约束名
    r'foreign\s+key\s*\(([^)]+)\)\s*'                    # 源字段（支持多字段）
    r'references\s+(\w+)\s*\(([^)]+)\)'                  # 目标表和字段
    r'(\s+on\s+delete\s+(cascade|set\s+null|restrict|no\s+action))?',  # 删除规则（可选）
    re.IGNORECASE | re.MULTILINE
)
```

**覆盖率估计**：~80-90% 的文件

#### 策略 2：格式变体脚本库

针对已知的非标准格式维护脚本库：

```python
# 格式 A：单行定义
pattern_a = re.compile(r'FOREIGN KEY\s+\((.+?)\)\s+REFERENCES\s+(\w+)\s*\((.+?)\)')

# 格式 B：多行定义
pattern_b = re.compile(
    r'CONSTRAINT\s+(\w+)\s+FOREIGN\s+KEY\s*\(([^)]+)\)',
    re.MULTILINE | re.DOTALL
)

# 格式 C：带换行和注释
# ... 更多格式
```

**覆盖率估计**：额外 5-10% 的文件

#### 策略 3：LLM 辅助脚本生成（兜底方案）

**流程**：

1. **提取外键语句块**（支持大文件优化）：
   ```python
   def extract_fk_statements(sql_content: str, max_size_mb: float = 1.0) -> List[str]:
       """
       提取包含外键定义的语句块
       
       对于大文件（>1MB），使用流式关键字搜索，只提取相关片段
       """
       file_size_mb = len(sql_content.encode('utf-8')) / (1024 * 1024)
       
       if file_size_mb > max_size_mb:
           # 大文件：使用关键字片段提取
           return extract_fk_fragments_streaming(sql_content)
       else:
           # 小文件：直接正则提取
           return extract_fk_statements_regex(sql_content)
   
   def extract_fk_fragments_streaming(sql_content: str) -> List[str]:
       """
       流式提取外键相关片段（大文件优化）
       """
       fragments = []
       lines = sql_content.split('\n')
       
       # 关键字匹配（不区分大小写）
       fk_keywords = [
           r'foreign\s+key',
           r'references\s+\w+',
           r'add\s+constraint.*foreign',
           r'constraint.*references'
       ]
       
       i = 0
       while i < len(lines):
           line = lines[i]
           
           # 检查是否包含外键关键字
           if any(re.search(kw, line, re.I) for kw in fk_keywords):
               # 提取上下文（前后各 5 行）
               start = max(0, i - 5)
               end = min(len(lines), i + 10)
               fragment = '\n'.join(lines[start:end])
               
               # 确保语句完整性（查找分号）
               if ';' not in fragment:
                   # 继续向后查找到分号
                   while end < len(lines) and ';' not in lines[end]:
                       end += 1
                   if end < len(lines):
                       end += 1
                   fragment = '\n'.join(lines[start:end])
               
               fragments.append(fragment)
               i = end  # 跳过已提取的部分
           else:
               i += 1
       
       # 去重并限制数量（最多取 5 个示例）
       unique_fragments = list(dict.fromkeys(fragments))
       return unique_fragments[:5]
   ```

2. **格式指纹识别**：
   ```python
   format_fingerprint = analyze_format(fk_statements)
   # 分析语句结构、关键字顺序、换行符等
   ```

3. **检查缓存**：
   ```python
   if format_fingerprint in cached_strategies:
       return cached_strategies[format_fingerprint]
   ```

4. **调用 Claude API 分析**：
   ```python
   prompt = f"""
   分析以下 SQL 外键定义的格式，生成 Python 正则表达式提取代码：
   
   示例语句片段：
   {fk_statements[:3]}  # 提供 2-3 个示例片段
   
   注意：
   - 原始 SQL 文件可能很大（>10MB），已提取相关片段
   - 生成的代码应支持流式处理或关键字定位
   
   要求：
   1. 生成完整的 Python 函数
   2. 返回标准格式的字典列表
   3. 包含错误处理
   4. 添加注释说明格式特点
   5. 如果需要处理大文件，使用流式或分块处理
   """
   
   generated_code = call_claude_api(prompt)
   ```

5. **验证和缓存**：
   ```python
   # 测试生成的代码
   test_result = test_extractor(generated_code, fk_statements)
   
   if test_result.success:
       save_strategy(format_fingerprint, generated_code)
       return generated_code
   else:
       # 回退或重试
       log_error(test_result.error)
   ```

**覆盖率估计**：剩余 5-10% 的文件

**考虑的替代方案**：
- 纯 SQL Parser 库：过于重型，且对非标准格式支持有限
- 手动编写所有格式：工作量大，无法预见所有格式
- 纯 LLM 提取：成本高，速度慢，不稳定

### 决策 2：格式识别与策略选择

**选择**：自动格式识别 + 策略优先级

**格式指纹计算**：

```python
def compute_format_fingerprint(sql_content: str) -> str:
    """
    计算 SQL 文件的格式指纹，用于策略选择和缓存
    """
    features = {
        'has_alter_table': 'alter table' in sql_content.lower(),
        'has_constraint_keyword': 'constraint' in sql_content.lower(),
        'fk_statement_count': len(re.findall(r'foreign\s+key', sql_content, re.I)),
        'line_breaks_in_fk': '\n' in extract_first_fk_statement(sql_content),
        'has_parentheses': '(' in sql_content and ')' in sql_content,
        'keyword_order': detect_keyword_order(sql_content),  # 关键字顺序
    }
    
    # 生成哈希指纹
    fingerprint = hashlib.md5(
        json.dumps(features, sort_keys=True).encode()
    ).hexdigest()[:8]
    
    return fingerprint
```

**策略选择流程**：

```python
def select_strategy(sql_content: str) -> ExtractionStrategy:
    # 1. 尝试策略 1：标准正则
    result = strategy_1_extract(sql_content)
    if result.success and result.confidence > 0.9:
        return Strategy.STANDARD_REGEX
    
    # 2. 尝试策略 2：格式变体脚本
    fingerprint = compute_format_fingerprint(sql_content)
    if fingerprint in known_formats:
        return Strategy.VARIANT_SCRIPT
    
    # 3. 回退到策略 3：LLM 生成
    return Strategy.LLM_GENERATED
```

**置信度评估**：

```python
def evaluate_confidence(extracted_data: List[dict]) -> float:
    """
    评估提取结果的置信度
    """
    score = 1.0
    
    # 检查必填字段
    for fk in extracted_data:
        if not all(k in fk for k in ['source_table', 'target_table', 'source_columns']):
            score *= 0.5
    
    # 检查字段合理性
    if any(len(fk['source_columns']) == 0 for fk in extracted_data):
        score *= 0.3
    
    return score
```

### 决策 3：LLM 集成方案

**选择**：Anthropic Claude API + 提示工程

**Claude API 配置**：

```python
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def generate_extraction_script(
    fk_statements: List[str], 
    format_fingerprint: str
) -> str:
    """
    使用 Claude 生成外键提取脚本
    """
    prompt = f"""你是一个 SQL 解析专家。请分析以下外键定义语句的格式，并生成 Python 提取代码。

## 示例语句

```sql
{chr(10).join(fk_statements[:3])}
```

## 要求

1. 生成一个完整的 Python 函数 `extract_foreignkeys(sql_content: str) -> List[dict]`
2. 使用正则表达式提取以下信息：
   - constraint_name: 约束名称
   - source_table: 源表名
   - source_columns: 源字段列表（List[str]）
   - target_table: 目标表名
   - target_columns: 目标字段列表（List[str]）
   - on_delete: 删除规则（可选）
3. 返回标准格式的字典列表
4. 包含错误处理和边界情况处理
5. 添加详细注释说明格式特点

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
    # 你的代码
    pass
```
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        temperature=0.1,  # 低温度确保一致性
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # 提取代码块
    code = extract_code_block(response.content[0].text)
    return code
```

**脚本缓存策略**：

```python
# 缓存目录结构
docs/hospital/foreignkey/generated_strategies/
├── {fingerprint_1}.py          # LLM 生成的提取脚本
├── {fingerprint_2}.py
├── metadata.json               # 格式指纹和脚本映射
└── test_cases.json             # 测试用例

# metadata.json 示例
{
    "a1b2c3d4": {
        "script_file": "a1b2c3d4.py",
        "format_description": "单行外键定义，无换行",
        "success_count": 15,
        "created_at": "2026-01-16T10:30:00Z",
        "sample_file": "SAMPLE_TABLE.sql"
    }
}
```

**脚本验证**：

```python
def validate_generated_script(
    script_code: str, 
    test_statements: List[str]
) -> ValidationResult:
    """
    验证 LLM 生成的脚本是否正确
    """
    # 1. 语法检查
    try:
        compile(script_code, '<string>', 'exec')
    except SyntaxError as e:
        return ValidationResult(success=False, error=f"语法错误: {e}")
    
    # 2. 运行测试
    namespace = {}
    exec(script_code, namespace)
    extract_fn = namespace.get('extract_foreignkeys')
    
    if not extract_fn:
        return ValidationResult(success=False, error="未找到 extract_foreignkeys 函数")
    
    # 3. 测试提取
    try:
        result = extract_fn('\n'.join(test_statements))
        
        # 检查返回格式
        if not isinstance(result, list):
            return ValidationResult(success=False, error="返回值不是列表")
        
        if len(result) == 0:
            return ValidationResult(success=False, error="未提取到任何外键")
        
        # 检查字段完整性
        required_fields = {'source_table', 'target_table', 'source_columns', 'target_columns'}
        for fk in result:
            if not required_fields.issubset(fk.keys()):
                return ValidationResult(success=False, error=f"缺少必需字段: {required_fields - fk.keys()}")
        
        return ValidationResult(success=True, extracted_count=len(result))
    
    except Exception as e:
        return ValidationResult(success=False, error=f"执行错误: {e}")
```

**错误处理与重试**：

```python
def extract_with_llm_retry(
    sql_content: str, 
    max_retries: int = 2
) -> List[dict]:
    """
    LLM 提取，带重试机制
    """
    fk_statements = extract_fk_statements(sql_content)
    
    for attempt in range(max_retries + 1):
        try:
            script_code = generate_extraction_script(fk_statements, fingerprint)
            
            # 验证脚本
            validation = validate_generated_script(script_code, fk_statements)
            
            if validation.success:
                # 保存脚本
                save_generated_strategy(fingerprint, script_code, metadata)
                
                # 执行提取
                namespace = {}
                exec(script_code, namespace)
                result = namespace['extract_foreignkeys'](sql_content)
                return result
            
            else:
                logger.warning(f"生成的脚本验证失败（尝试 {attempt + 1}/{max_retries + 1}）: {validation.error}")
        
        except Exception as e:
            logger.error(f"LLM 提取失败（尝试 {attempt + 1}/{max_retries + 1}）: {e}")
    
    # 所有重试失败
    return []
```

### 决策 4：JSON 文件存储格式

**选择**：提供两种模式

1. **按表存储模式**（默认）：每个表的外键信息单独保存
   - 文件名：`{table_name}_foreignkeys.json`
   - 优点：文件小，按需查询，便于单表分析
   - 缺点：文件数量多

2. **统一存储模式**：所有外键信息保存到一个文件
   - 文件名：`all_foreignkeys.json`
   - 优点：便于全局分析、查找引用关系
   - 缺点：文件较大

**JSON 结构**（按表存储）：

```json
{
  "table_name": "BSE_SERVICE_PACKAGE_DETAIL",
  "source_file": "BSE_SERVICE_PACKAGE_DETAIL.sql",
  "foreign_keys": [
    {
      "constraint_name": "FK_BSE_SERVICE_PACKAGE_DETAIL1",
      "source_table": "BSE_SERVICE_PACKAGE_DETAIL",
      "source_columns": ["BASE_SERVICE_PACKAGE_ID"],
      "target_table": "BSE_SERVICE_PACKAGE",
      "target_columns": ["MAINID"],
      "on_delete": "cascade"
    },
    {
      "constraint_name": "FK_BSE_SERVICE_PACKAGE_DETAIL2",
      "source_table": "BSE_SERVICE_PACKAGE_DETAIL",
      "source_columns": ["SERVICE_ID"],
      "target_table": "BS_SER_MAINFILE",
      "target_columns": ["MAINID"],
      "on_delete": "cascade"
    }
  ],
  "extracted_at": "2026-01-16T10:30:00Z"
}
```

**JSON 结构**（统一存储）：

```json
{
  "metadata": {
    "extracted_at": "2026-01-16T10:30:00Z",
    "total_files": 954,
    "total_foreignkeys": 256,
    "tables_with_foreignkeys": 128
  },
  "foreignkeys": [
    {
      "constraint_name": "FK_CHECK_R98_CHECK",
      "source_table": "BS_CHECK_TYPE",
      "source_columns": ["PARENTID"],
      "target_table": "BS_CHECK_TYPE",
      "target_columns": ["MAINID"],
      "on_delete": "cascade",
      "source_file": "BS_CHECK_TYPE.sql"
    },
    ...
  ]
}
```

### 决策 5：CLI 命令设计

**命令 1**：单文件提取

```bash
python -m AIagent.sql_import extract-foreignkey \
  docs/hospital/sql/BS_DEPARTMENT.sql \
  -o docs/hospital/foreignkey/
```

**命令 2**：批量提取（按表存储）

```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --mode per-table
```

**命令 3**：批量提取（统一存储）

```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --mode unified \
  --output-file all_foreignkeys.json
```

**命令 4**：启用 LLM 辅助

```bash
python -m AIagent.sql_import extract-foreignkey-all \
  docs/hospital/sql/ \
  -o docs/hospital/foreignkey/ \
  --enable-llm \
  --anthropic-api-key $ANTHROPIC_API_KEY
```

**命令 5**：查看提取策略统计

```bash
python -m AIagent.sql_import foreignkey-stats \
  --show-strategies
```

**参数说明**：
- `-o, --output`: 输出目录
- `--mode`: 存储模式（`per-table` 或 `unified`）
- `--output-file`: 统一存储模式的文件名（默认 `all_foreignkeys.json`）
- `--overwrite`: 覆盖已存在的文件
- `--verbose`: 显示详细进度
- `--enable-llm`: 启用 LLM 辅助提取（需要 API key）
- `--anthropic-api-key`: Claude API 密钥
- `--max-llm-retries`: LLM 生成脚本的最大重试次数（默认 2）
- `--strategy-cache-dir`: 策略缓存目录（默认 `docs/hospital/foreignkey/generated_strategies/`）
- `--show-strategies`: 显示每个文件使用的提取策略

## 风险 / 权衡

### 风险 1：大文件内存占用

**风险**：某些 SQL 文件可能非常大（>10MB），完整加载会占用大量内存

**缓解措施**：
- 文件大小检测：识别大文件（>1MB）
- **关键字片段提取**：只提取包含外键定义的相关片段
  - 搜索关键字：`foreign key`、`references`、`add constraint`
  - 保留上下文：提取关键字前后各 5-10 行
  - 确保语句完整性：查找分号确保提取完整语句
  - 限制示例数量：最多提取 5 个示例片段
- 流式处理：逐行读取，避免一次性加载整个文件
- Token 限制控制：发送给 LLM 的片段总计 < 4000 tokens

**大文件处理流程**：
```python
def process_large_file(file_path: str) -> List[dict]:
    """处理大文件"""
    # 1. 检查文件大小
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
    
    if file_size > 1.0:
        # 2. 流式提取外键片段
        fragments = extract_fk_fragments_streaming_from_file(file_path)
        
        # 3. 只使用片段进行格式分析和提取
        format_fingerprint = analyze_format(fragments)
        
        # 4. 如果需要 LLM，只发送片段（不是整个文件）
        if need_llm_generation(format_fingerprint):
            script_code = generate_extraction_script(fragments, format_fingerprint)
        
        # 5. 应用生成的脚本到完整文件（流式处理）
        return apply_extractor_streaming(file_path, script_code)
    else:
        # 小文件：正常处理
        return extract_foreignkeys(read_file(file_path))
```

### 风险 2：LLM API 调用成本

**风险**：批量处理 954 个文件时，如果大量文件需要 LLM 辅助，API 成本可能较高

**缓解措施**：
- 优先使用正则表达式（预计覆盖 80-90%）
- 维护格式变体脚本库（额外覆盖 5-10%）
- LLM 生成的脚本会被缓存，相同格式只调用一次 API
- **关键字片段提取**：只发送相关片段给 LLM（平均 500-1000 tokens），而非整个文件
- 提供 `--disable-llm` 参数，允许跳过 LLM 策略
- 预估成本：假设 10% 文件需要 LLM（~100 文件），每次调用 ~1000 tokens（使用片段），总计 ~$0.30

### 风险 3：LLM 生成的脚本不可靠

**风险**：LLM 生成的代码可能有语法错误或逻辑错误

**缓解措施**：
- 严格的脚本验证流程（语法检查 + 功能测试）
- 最多重试 2 次，提供不同的提示词
- 验证失败的脚本不会被缓存
- 记录失败的文件，提供人工审核接口
- 所有 LLM 生成的脚本保存到 `generated_strategies/` 目录，便于审查

### 风险 4：格式指纹冲突

**风险**：不同格式可能产生相同的指纹哈希

**缓解措施**：
- 使用多维度特征计算指纹（关键字、顺序、换行等）
- 在缓存时附加样本文件，便于人工验证
- 提供 `--force-regenerate` 参数强制重新生成脚本
- 冲突率预计 < 1%

### 风险 5：正则表达式无法处理极端复杂格式

**风险**：某些格式可能超出正则表达式能力（如带嵌套的外键定义）

**缓解措施**：
- 对于极端情况，LLM 策略可以生成更复杂的解析逻辑（非正则）
- 允许 LLM 生成使用 `sqlparse` 或其他库的代码
- 记录无法提取的文件，提供跳过或手动处理选项

## 迁移计划

本变更不涉及数据库迁移，仅新增功能。

**步骤**：
1. 实现外键提取器和 CLI 命令
2. 在开发环境测试 10 个样本文件
3. 批量提取所有 954 个文件的外键信息
4. 将 JSON 文件提交到 Git
5. 更新 `AIagent/README.md` 文档

**回滚**：
- 删除 `foreignkey_extractor.py` 和 `foreignkey_cli.py` 文件
- 删除生成的 JSON 文件

## 待决问题

1. **LLM 提供商选择**
   - 当前选择：Anthropic Claude（claude-3-5-sonnet）
   - 原因：代码生成能力强，支持长上下文
   - 备选：OpenAI GPT-4（如果 Claude 不可用）
   
2. **是否需要处理 `on update` 规则？**
   - 当前 SQL 文件未见 `on update` 语句，暂不支持
   - 如果发现需要，可通过 LLM 策略扩展
   
3. **LLM 生成脚本的审核流程**
   - 自动验证 + 人工审查
   - 建议：首次运行时，输出所有 LLM 生成的脚本路径，供人工检查
   
4. **是否需要校验目标表是否存在？**
   - 不校验，仅提取信息，校验留给后续工具
   
5. **策略缓存的版本控制**
   - LLM 生成的脚本应该提交到 Git 吗？
   - 建议：提交，便于团队共享和版本追踪
   
6. **API 密钥管理**
   - 通过环境变量 `ANTHROPIC_API_KEY` 传递
   - 或通过 `--anthropic-api-key` 命令行参数
   - 如果都未提供且需要 LLM，则跳过 LLM 策略
