import os
from pathlib import Path

# 自动加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'

if ENV_FILE.exists():
    # 手动解析 .env 文件（避免添加新依赖）
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            # 解析 KEY=VALUE 格式
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # 移除引号（如果有）
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                # 只有当环境变量不存在时才设置（避免覆盖已存在的环境变量）
                if key and key not in os.environ:
                    os.environ[key] = value

# dev, uat, prd
ENV = os.environ.get('ZQ_ENV', 'dev')


if ENV == 'dev':
    from env.dev_env import *
if ENV == 'uat':
    from env.uat_env import *
if ENV == 'prd':
    from env.prd_env import *


