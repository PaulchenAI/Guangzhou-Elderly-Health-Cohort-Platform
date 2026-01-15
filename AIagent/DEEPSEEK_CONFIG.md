# DeepSeek配置说明

## 概述

AIagent框架支持DeepSeek等OpenAI兼容的API。DeepSeek使用OpenAI兼容的接口，因此可以使用`openai` provider配合`base_url`配置。

## 配置方式

### 方式1：使用项目根目录的.env（推荐）

如果您的项目根目录（`/mnt/f/work/zq-platform/.env`）已经有DeepSeek配置：

```bash
# 项目根目录 .env
LLM_API_KEY=sk-***
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.1
```

**AIagent会自动从项目根目录加载这些配置！**

只需在AIagent目录下创建`.env`文件，添加以下必需配置：

```bash
# AIagent/.env
# Claude Code CLI配置（必需）
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform

# LLM配置（如果项目根目录已有，这里可以不设置，会自动继承）
# 或者显式设置以覆盖项目根目录的配置
LLM_PROVIDER=openai  # DeepSeek使用openai provider
```

### 方式2：在AIagent/.env中完整配置

如果您想在AIagent目录下独立配置：

```bash
# AIagent/.env
# Claude Code CLI配置
CLAUDE_CODE_PATH=/usr/local/bin/claude
CLAUDE_CODE_WORKING_DIR=/mnt/f/work/zq-platform

# LLM配置（DeepSeek）
LLM_PROVIDER=openai
LLM_API_KEY=sk-***
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-reasoner  # 或使用 LLM_MODEL=deepseek-reasoner
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.1
```

## 配置说明

### 关键配置项

1. **LLM_PROVIDER=openai**
   - DeepSeek是OpenAI兼容API，必须使用`openai` provider

2. **LLM_BASE_URL=https://api.deepseek.com**
   - DeepSeek的API端点

3. **LLM_MODEL_NAME 或 LLM_MODEL**
   - 模型名称，如`deepseek-reasoner`
   - 系统优先使用`LLM_MODEL_NAME`，如果不存在则使用`LLM_MODEL`

4. **LLM_API_KEY**
   - DeepSeek的API密钥

### 配置优先级

1. 系统环境变量（最高优先级）
2. AIagent/.env
3. 项目根目录/.env（如果AIagent/.env不存在对应配置）

## 验证配置

运行以下命令验证配置是否正确加载：

```python
from src.utils.config_manager import get_config_manager
from src.llm import LLMFactory

config_manager = get_config_manager()
llm_config = config_manager.get_llm_config()

print(f"Provider: {llm_config.provider}")
print(f"Model: {llm_config.model}")
print(f"Base URL: {llm_config.base_url}")

# 创建LLM客户端
llm = LLMFactory.create_llm(llm_config)
print(f"LLM客户端类型: {type(llm).__name__}")
```

## 使用示例

```python
from src.llm import LLMFactory
from src.utils.config_manager import get_config_manager

# 从配置管理器创建LLM客户端
config_manager = get_config_manager()
llm = LLMFactory.create_llm_from_config_manager(config_manager)

# 调用DeepSeek
response = await llm.invoke_prompt("你好，请介绍一下自己")
print(response)
```

## 常见问题

### Q: 为什么使用openai provider而不是deepseek？

A: DeepSeek使用OpenAI兼容的API接口，因此可以使用OpenAI客户端。只需要设置正确的`base_url`即可。

### Q: LLM_MODEL_NAME和LLM_MODEL有什么区别？

A: 两者都可以使用，系统会优先使用`LLM_MODEL_NAME`。这是为了兼容不同项目的配置格式。

### Q: 如何确认配置已正确加载？

A: 运行验证脚本，检查输出的provider、model和base_url是否正确。

## 其他OpenAI兼容API

此配置方式同样适用于其他OpenAI兼容的API，如：
- DeepSeek
- 其他OpenAI兼容服务

只需修改`LLM_BASE_URL`和`LLM_MODEL`即可。
