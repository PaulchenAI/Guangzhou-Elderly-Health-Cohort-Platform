# LLM SQL修复工具 - 配置说明

## 快速开始

### 1. 配置LLM API

在项目根目录创建 `.env` 文件（与backend-django同级），添加以下配置：

```bash
# DeepSeek 配置（推荐）
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner
```

### 2. 安装依赖

```bash
pip install python-dotenv requests
```

### 3. 运行SQL导入（生成详细日志）

```bash
cd backend-django
python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed --continue-on-error
```

导入完成后会显示日志文件位置，例如：
```
详细日志将保存到: /mnt/f/work/zq-platform/backend-django/logs/import_1f5b4b14.log
```

### 4. 使用LLM工具分析和修复

```bash
cd tools
python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../backend-django/logs/import_1f5b4b14.log
```

工具会：
1. 解析日志文件，提取所有错误信息
2. 逐个调用LLM分析错误原因
3. 生成修复建议和修复后的SQL
4. 询问是否应用修复（输入y/n）

### 5. 验证修复效果

```bash
cd backend-django
python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed
```

---

## 配置选项

### LLM服务配置

#### OpenAI 配置
```bash
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini  # 或 gpt-4o, gpt-3.5-turbo
```

#### DeepSeek 配置（推荐，性价比高）
```bash
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner  # 或 deepseek-chat
```

#### Azure OpenAI 配置
```bash
LLM_API_KEY=your-azure-key
LLM_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
LLM_MODEL_NAME=gpt-4
```

#### 本地Ollama 配置（免费）
```bash
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL_NAME=codellama
```

### 可选参数
```bash
# 超时时间（秒），默认30
LLM_TIMEOUT=30

# 最大Token数，默认4000
LLM_MAX_TOKENS=4000

# 温度参数（0-2），默认0.1，越低越确定性
LLM_TEMPERATURE=0.1
```

---

## 使用方法

### 基本用法
```bash
python llm_sql_fixer.py --batch-id <批次ID> --log-file <日志文件路径>
```

### 自动应用修复（无需确认）
```bash
python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --auto-apply
```

### 只分析不修复（干运行）
```bash
python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --dry-run
```

### 指定SQL文件目录
```bash
python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --sql-dir /custom/path
```

---

## 工作流程

```
1. 运行import_oracle_sql导入
   ↓ 生成详细日志
2. 运行llm_sql_fixer分析
   ↓ LLM分析错误
3. 显示修复建议
   ↓ 用户确认
4. 应用修复到SQL文件
   ↓ 自动创建备份
5. 重新运行import_oracle_sql
   ↓ 验证修复效果
```

---

## 支持的错误类型

| 错误码 | 错误类型 | 修复策略 |
|--------|----------|----------|
| 1292 | 数据类型转换错误 | 修复引号、转义、类型匹配 |
| 1054 | 字段不存在 | 在CREATE TABLE中添加缺失字段 |
| 1064 | SQL语法错误 | 修复引号嵌套、特殊字符、关键字 |
| 1067 | 默认值无效 | 修复DATETIME默认值等 |
| 1118 | 行大小过大 | 将VARCHAR转为TEXT |
| 1146 | 表不存在 | 创建缺失的表定义 |
| 1062 | 主键冲突 | 处理重复数据 |

---

## 注意事项

1. **备份文件**：工具会自动创建 `.backup_llm` 后缀的备份文件
2. **手动验证**：应用修复前请仔细检查LLM的修复建议
3. **API成本**：每次LLM调用会消耗token，注意成本控制
4. **网络要求**：需要能访问LLM API的网络环境
5. **模型选择**：
   - `deepseek-reasoner`：推荐，性价比高，推理能力强
   - `gpt-4o-mini`：OpenAI性价比选择
   - `gpt-4o`：最强能力，成本较高

---

## 故障排查

### 问题1：找不到日志文件
```
[错误] 日志文件不存在: logs/import_xxx.log
```
**解决**：确保先运行 `import_oracle_sql` 命令生成日志

### 问题2：LLM_API_KEY未设置
```
[错误] LLM_API_KEY 环境变量未设置
```
**解决**：在项目根目录创建 `.env` 文件并配置API密钥

### 问题3：LLM调用失败
```
[错误] LLM API调用失败: HTTPError
```
**解决**：
- 检查API密钥是否正确
- 检查BASE_URL是否正确
- 检查网络连接
- 检查API额度是否充足

### 问题4：SQL文件不存在
```
[错误] SQL文件不存在: xxx.sql
```
**解决**：使用 `--sql-dir` 参数指定正确的SQL文件目录

---

## 高级用法

### 批量处理多个批次
```bash
for batch in 1f5b4b14 2a3b4c5d 3c4d5e6f; do
    python llm_sql_fixer.py --batch-id $batch --log-file ../logs/import_$batch.log --auto-apply
done
```

### 导出修复报告
```bash
python llm_sql_fixer.py --batch-id 1f5b4b14 --log-file ../logs/import_1f5b4b14.log --dry-run > fix_report.txt
```

---

## 示例输出

```
================================================================================
          LLM SQL修复工具
================================================================================
批次ID: 1f5b4b14
日志文件: ../logs/import_1f5b4b14.log
SQL目录: ../docs/hospital/convertsql
================================================================================

[1/4] 正在解析日志文件...
[结果] 找到 11 个错误

错误列表:
  1. [1292] gzlry_BSE_EXCEL.sql: 数据类型转换错误
  2. [1054] gzlry_HR_CEREBRAL_STROKE.sql: 字段不存在
  3. [1064] gzlry_WM_USE_REGISTER.sql: SQL语法错误
  ...

[2/4] 正在初始化LLM客户端...
[配置] LLM模型: deepseek-reasoner
[配置] API地址: https://api.deepseek.com

[3/4] 正在初始化修复器...

[4/4] 开始处理错误...

================================================================================
正在分析: [1292] gzlry_BSE_EXCEL.sql: 数据类型转换错误
================================================================================
[LLM] 正在调用LLM分析错误...

[分析] 该错误是由于INSERT语句中的字符串值包含特殊字符，但未正确转义...

[修复步骤]
  1. 在问题字符串前后添加正确的引号
  2. 转义特殊字符如单引号
  3. 确保字符串格式符合MySQL语法

[修复后的SQL]
--------------------------------------------------------------------------------
INSERT INTO BSE_EXCEL (id, content) VALUES ('123', 'select * from (
  SELECT * FROM table
)');
--------------------------------------------------------------------------------

[说明] 将多行字符串正确转义，避免MySQL将其误识别为SQL语句...

是否应用此修复? (y/n/s=跳过): y
[备份] 已创建备份: gzlry_BSE_EXCEL.backup_llm.sql
[成功] 修复已应用到文件
...

================================================================================
修复完成
成功: 8/11
================================================================================

💡 提示: 现在可以重新运行导入命令测试修复效果:
  cd ../backend-django
  python manage.py import_oracle_sql --batch-id 1f5b4b14 --retry-failed
```

---

最后更新: 2026-01-09


