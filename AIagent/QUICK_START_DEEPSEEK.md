# DeepSeek快速配置指南

## 快速开始

### 步骤1：创建AIagent/.env文件

在`AIagent`目录下创建`.env`文件：

```bash
cd /mnt/f/work/zq-platform/AIagent
cp .env.example .env
```

### 步骤2：配置DeepSeek

编辑`AIagent/.env`文件，设置以下配置：

```bash
# Claude Code CLI配置（必需）
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform

# LLM配置 - DeepSeek
LLM_PROVIDER=openai
LLM_API_KEY=sk-********
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.1
```

**注意**：
- 如果项目根目录（`/mnt/f/work/zq-platform/.env`）已经有这些配置，AIagent会自动加载
- 您只需要在`AIagent/.env`中设置`CLAUDE_CODE_PATH`和`CLAUDE_CODE_WORKING_DIR`即可
- 系统会优先使用项目根目录的LLM配置

### 步骤3：验证配置

```python
from src.utils.config_manager import get_config_manager
from src.llm import LLMFactory

# 获取配置
config_manager = get_config_manager()
llm_config = config_manager.get_llm_config()

print(f"✅ Provider: {llm_config.provider}")
print(f"✅ Model: {llm_config.model}")
print(f"✅ Base URL: {llm_config.base_url}")

# 创建LLM客户端
llm = LLMFactory.create_llm(llm_config)
print(f"✅ LLM客户端: {type(llm).__name__}")
```

## 配置映射

### 项目根目录.env → AIagent配置

| 项目根目录.env | AIagent配置 | 说明 |
|---------------|------------|------|
| `LLM_API_KEY` | `LLM_API_KEY` | 自动继承 |
| `LLM_BASE_URL` | `LLM_BASE_URL` | 自动继承 |
| `LLM_MODEL_NAME` | `LLM_MODEL` | 自动映射 |
| `LLM_MAX_TOKENS` | `LLM_MAX_TOKENS` | 自动继承 |
| `LLM_TEMPERATURE` | `LLM_TEMPERATURE` | 自动继承 |

**需要额外设置**：
- `LLM_PROVIDER=openai`（在AIagent/.env中设置，因为项目根目录可能没有）

## 最小配置示例

如果项目根目录已有DeepSeek配置，AIagent/.env最小配置：

```bash
# AIagent/.env（最小配置）
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform
LLM_PROVIDER=openai  # 只需设置provider，其他从项目根目录继承
```

## 完整配置示例

如果想在AIagent目录下独立配置：

```bash
# AIagent/.env（完整配置）
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform

LLM_PROVIDER=openai
LLM_API_KEY=sk-****
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.1
```

## 测试LLM调用

```python
import asyncio
from src.llm import LLMFactory
from src.utils.config_manager import get_config_manager

async def test_deepseek():
    config_manager = get_config_manager()
    llm = LLMFactory.create_llm_from_config_manager(config_manager)
    
    response = await llm.invoke_prompt("你好，请用一句话介绍自己")
    print(f"DeepSeek响应: {response}")

# 运行测试
asyncio.run(test_deepseek())
```

## 故障排除

### 问题1：找不到LLM配置

**解决**：确保设置了`LLM_PROVIDER=openai`

### 问题2：模型名称不正确

**解决**：检查`LLM_MODEL_NAME`或`LLM_MODEL`是否正确设置

### 问题3：API调用失败

**解决**：
1. 检查`LLM_API_KEY`是否正确
2. 检查`LLM_BASE_URL`是否为`https://api.deepseek.com`
3. 检查网络连接

## 更多信息

详细配置说明请参考：`DEEPSEEK_CONFIG.md`
