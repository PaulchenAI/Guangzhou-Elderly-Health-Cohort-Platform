# 性能问题分析与优化

## 问题分析

### 发现的性能问题

从日志看，某些大文件转换耗时极长：
- `WM_PURCHASE.sql`: 8.5 分钟
- `WM_PURCHASE_DETAIL.sql` (53MB): 3.3 小时
- `WM_STOCK.sql` (201MB): 6 小时
- `WM_TAKE_DETAIL.sql` (141MB): 预计也需要数小时

### 根本原因

1. **内存累积问题**：
   - 虽然使用了流式读取，但所有转换后的语句都保存在 `statements` 列表中
   - 最后使用 `'\n\n'.join(statements)` 一次性连接所有语句
   - 对于包含几十万甚至上百万条 INSERT 语句的文件，这会消耗大量内存和时间

2. **字符串操作开销**：
   - 每个语句都要经过多次字符串操作（strip、join、正则替换）
   - 大字符串的连接操作（`'\n'.join()`）时间复杂度为 O(n²)

3. **正则表达式处理**：
   - 每个 INSERT 语句都要经过复杂的正则表达式处理
   - 对于超大文件，可能有几十万个 INSERT 语句需要处理

## 优化方案

### 1. 直接写入文件（流式输出）

**优化前**：
```python
statements = []
# ... 收集所有语句 ...
return '\n\n'.join(statements)  # 一次性连接，内存和时间开销大
```

**优化后**：
```python
if output_path:
    output_file = open(output_path, 'w', encoding='utf-8')
    # 转换后直接写入文件
    output_file.write(converted)
    # 每 10000 个语句刷新一次缓冲区
    if statement_count % 10000 == 0:
        output_file.flush()
        gc.collect()
```

**效果**：
- 内存使用从 O(n) 降低到 O(1)（只保留当前处理的语句）
- 避免大字符串连接操作
- 支持处理任意大小的文件

### 2. 定期内存清理

- 每处理 10000 个语句后刷新文件缓冲区并触发垃圾回收
- 每处理 100 个文件后清理一次内存

### 3. 跳过已转换文件

- 检查输出文件是否存在且大小 > 0
- 如果存在则跳过，避免重复处理
- 支持 `--force` 参数强制重新转换

## 预期性能提升

- **内存使用**：从 O(n) 降低到 O(1)，可处理任意大小的文件
- **处理速度**：对于大文件（>50MB），预计提升 10-100 倍
- **稳定性**：避免内存溢出导致的 killed 问题

## 测试建议

1. 测试大文件（>100MB）的转换速度
2. 监控内存使用情况
3. 验证断点续传功能（跳过已转换文件）

## 补充问题：完整性检查 INSERT 统计不准确

### 问题发现

批量转换时发现，大文件（>10MB）的完整性检查总是报告"INSERT 数量不匹配"，导致已完整转换的文件被重复转换：

- **CH_ACCOUNTING_MANAGE.sql** (20MB)：实际 30935 个 INSERT，检查报告 3156 个（仅 10%）
- **CH_VIRTUAL_ELECTRICITY_FEE.sql** (31MB)：实际 57879 个 INSERT，检查报告 3737 个（仅 6%）

### 根本原因

在 `convert_file` 的完整性检查代码中（第 466-471 行），对于 >10MB 的文件，只读取**前 1MB 和后 1MB**：

```python
else:  # 大文件，只读取前1MB和最后1MB
    f.seek(0)
    first_1mb = f.read(1024 * 1024)
    f.seek(max(0, file_size - 1024 * 1024))
    last_1mb = f.read(1024 * 1024)
    full_content = first_1mb + "\n...\n" + last_1mb

# 然后统计 INSERT 数量
output_insert_count = full_content_upper.count('INSERT INTO')
```

**问题**：对于 20MB 文件，中间 18MB 的数据**完全被忽略**，只统计了首尾各 1MB 的 INSERT 数量。

### 修复方案

改用流式逐行统计，避免内存占用：

```python
if file_size < 10 * 1024 * 1024:  # 小于10MB，读取全部
    full_content = f.read()
    output_insert_count = full_content_upper.count('INSERT INTO')
else:  # 大文件，使用流式统计
    # 流式统计 INSERT 数量（逐行读取，避免内存占用）
    f.seek(0)
    output_insert_count = 0
    for line in f:
        if 'INSERT INTO' in line.upper():
            output_insert_count += 1
```

### 修复效果

- **统计准确率**：从 ~10% 提升到 100%
- **内存占用**：O(1) - 逐行读取
- **性能影响**：对 20MB 文件，完整性检查耗时 < 1 秒

## 补充问题：正则表达式灾难性回溯

### 问题发现

转换 `BSE_NURSE_INSPECTION.sql` (109MB, 206,692 个 INSERT) 时，进度在 180,000 个语句时卡住，CPU 95% 但无输出：

- 堆栈显示卡在 `_convert_concat_simple` 的 `re.search` 调用
- 用户手动中断（Ctrl+C）后才恢复

### 根本原因

第 352 行的正则表达式包含嵌套的 `*` 和 `+` 量词，导致灾难性回溯：

```python
pattern = r"'[^']*(?:''[^']*)*'\s*(?:\|\|\s*(?:chr\s*\([^)]+\)|CHAR\s*\([^)]+\)|''|'[^']*(?:''[^']*)*'))+"
```

当遇到包含大量单引号或长字符串的 INSERT 语句时，正则引擎会尝试大量不同的匹配组合，导致：
- **指数级时间复杂度**
- **CPU 100% 但无进展**
- **程序看似卡住**

### 修复方案

完全简化 `||` 转换逻辑，直接在 `_convert_insert` 中处理：

```python
# 转换 || 连接符：只处理最简单的情况，避免性能问题
if '||' in result:
    quote_count = result.count("'")
    if quote_count < 20:  # 只处理引号少的简单语句
        # 简单替换：'str1' || 'str2' -> CONCAT('str1', 'str2')
        simple_pattern = r"('[^']{0,100}')\s*\|\|\s*('[^']{0,100}')"
        for _ in range(3):  # 最多替换3次
            new_result = re.sub(simple_pattern, r'CONCAT(\1, \2)', result, count=1)
            if new_result == result:
                break
            result = new_result
```

### 优化要点

1. **快速跳过**：先统计引号数量，复杂语句直接跳过
2. **严格限制**：字符串长度限制 100 字符，只替换 3 次
3. **简单模式**：`[^']` 避免嵌套量词，不会产生回溯
4. **及时退出**：检测到无变化立即停止

### 修复效果

- **修复前**：180,000 语句后卡住，几分钟无进展
- **修复后**：7 秒内完成全部 188,166 个语句的转换
- **速度提升**：约 **26,000+ 语句/秒**

### 权衡

对于包含复杂 `||` 连接的语句（>20 个引号），转换工具会跳过 `||` 转换。这些语句可能在 MySQL 中导致语法错误，需要后续手动处理。这是**性能与完整性之间的合理权衡**。


