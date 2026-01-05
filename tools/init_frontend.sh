#!/bin/bash

# 前端环境初始化脚本
# 功能：检查 Node.js 和 pnpm 环境，安装前端依赖，配置环境变量
# 使用方法:
# bash tools/init_frontend.sh
set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径（相对于脚本位置）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/web"
APP_DIR="${FRONTEND_DIR}/apps/web-ele"
ENV_DEV_FILE="${APP_DIR}/.env.development"
ENV_PROD_FILE="${APP_DIR}/.env.production"

# 版本要求
REQUIRED_NODE_VERSION="20.10.0"
REQUIRED_PNPM_VERSION="9.12.0"

# 默认配置
VITE_APP_TITLE="芷青开发平台"
VITE_APP_NAMESPACE="zq-platform"
VITE_PORT="5173"
VITE_BASE="/"
VITE_GLOB_API_URL="/basic-api"
VITE_NITRO_MOCK="false"
VITE_DEVTOOLS="true"
VITE_INJECT_APP_LOADING="true"
VITE_ROUTER_HISTORY="history"

# 生产环境配置
PROD_API_URL="https://django-ninja.zq-platform.cn"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}开始初始化前端环境${NC}"
echo -e "${GREEN}========================================${NC}"

# 版本比较函数
version_ge() {
    # 检查版本 $1 是否 >= $2
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# 1. 检查 Node.js 版本
echo -e "${YELLOW}[1/5] 检查 Node.js 环境...${NC}"
if command -v node &> /dev/null; then
    CURRENT_NODE_VERSION=$(node -v | sed 's/v//')
    echo -e "${BLUE}当前 Node.js 版本: ${CURRENT_NODE_VERSION}${NC}"
    if version_ge "${CURRENT_NODE_VERSION}" "${REQUIRED_NODE_VERSION}"; then
        echo -e "${GREEN}Node.js 版本符合要求 (>= ${REQUIRED_NODE_VERSION})${NC}"
    else
        echo -e "${RED}错误: Node.js 版本过低，需要 >= ${REQUIRED_NODE_VERSION}${NC}"
        echo -e "${YELLOW}请更新 Node.js 版本后重试${NC}"
        echo -e "${YELLOW}推荐使用 nvm 管理 Node.js 版本:${NC}"
        echo -e "${YELLOW}  nvm install 20${NC}"
        echo -e "${YELLOW}  nvm use 20${NC}"
        exit 1
    fi
else
    echo -e "${RED}错误: 未找到 Node.js${NC}"
    echo -e "${YELLOW}请安装 Node.js >= ${REQUIRED_NODE_VERSION}${NC}"
    echo -e "${YELLOW}推荐使用 nvm 安装:${NC}"
    echo -e "${YELLOW}  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash${NC}"
    echo -e "${YELLOW}  nvm install 20${NC}"
    exit 1
fi

# 2. 检查 pnpm 版本
echo -e "${YELLOW}[2/5] 检查 pnpm 环境...${NC}"
if command -v pnpm &> /dev/null; then
    CURRENT_PNPM_VERSION=$(pnpm -v)
    echo -e "${BLUE}当前 pnpm 版本: ${CURRENT_PNPM_VERSION}${NC}"
    if version_ge "${CURRENT_PNPM_VERSION}" "${REQUIRED_PNPM_VERSION}"; then
        echo -e "${GREEN}pnpm 版本符合要求 (>= ${REQUIRED_PNPM_VERSION})${NC}"
    else
        echo -e "${YELLOW}pnpm 版本过低，正在更新...${NC}"
        npm install -g pnpm@latest
        echo -e "${GREEN}pnpm 已更新到最新版本${NC}"
    fi
else
    echo -e "${YELLOW}pnpm 未安装，正在安装...${NC}"
    npm install -g pnpm@latest
    echo -e "${GREEN}pnpm 安装完成${NC}"
fi

# 3. 安装前端依赖
echo -e "${YELLOW}[3/5] 安装前端依赖...${NC}"
cd "${FRONTEND_DIR}"
if [ -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules 目录已存在，是否重新安装? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}删除现有 node_modules 并重新安装...${NC}"
        rm -rf node_modules
        pnpm install
        echo -e "${GREEN}依赖重新安装完成${NC}"
    else
        echo -e "${GREEN}使用现有 node_modules${NC}"
    fi
else
    echo -e "${YELLOW}正在安装依赖，这可能需要几分钟...${NC}"
    pnpm install
    echo -e "${GREEN}依赖安装完成${NC}"
fi

# 4. 创建开发环境配置文件
echo -e "${YELLOW}[4/5] 创建环境配置文件...${NC}"

# 创建 .env.development 文件
if [ -f "${ENV_DEV_FILE}" ]; then
    echo -e "${YELLOW}.env.development 文件已存在，是否覆盖? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${GREEN}保留现有 .env.development 文件${NC}"
    else
        create_dev_env="true"
    fi
else
    create_dev_env="true"
fi

if [ "$create_dev_env" = "true" ]; then
    cat > "${ENV_DEV_FILE}" << EOF
# 开发环境配置
# 详细配置说明请参考: docs/src/guide/essentials/settings.md

# 应用标题
VITE_APP_TITLE=${VITE_APP_TITLE}

# 应用命名空间（用于缓存、存储等）
VITE_APP_NAMESPACE=${VITE_APP_NAMESPACE}

# 开发服务器端口
VITE_PORT=${VITE_PORT}

# 基础路径
VITE_BASE=${VITE_BASE}

# API 接口地址（开发环境使用代理）
VITE_GLOB_API_URL=${VITE_GLOB_API_URL}

# 是否启用 Nitro Mock 服务
VITE_NITRO_MOCK=${VITE_NITRO_MOCK}

# 是否启用 Vue DevTools
VITE_DEVTOOLS=${VITE_DEVTOOLS}

# 是否注入全局 loading
VITE_INJECT_APP_LOADING=${VITE_INJECT_APP_LOADING}

# 路由模式 (hash | history)
VITE_ROUTER_HISTORY=${VITE_ROUTER_HISTORY}
EOF
    echo -e "${GREEN}.env.development 文件已创建${NC}"
fi

# 创建 .env.production 文件
if [ -f "${ENV_PROD_FILE}" ]; then
    echo -e "${YELLOW}.env.production 文件已存在，是否覆盖? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${GREEN}保留现有 .env.production 文件${NC}"
    else
        create_prod_env="true"
    fi
else
    create_prod_env="true"
fi

if [ "$create_prod_env" = "true" ]; then
    cat > "${ENV_PROD_FILE}" << EOF
# 生产环境配置
# 详细配置说明请参考: docs/src/guide/essentials/settings.md

# 应用标题
VITE_APP_TITLE=${VITE_APP_TITLE}

# 应用命名空间（用于缓存、存储等）
VITE_APP_NAMESPACE=${VITE_APP_NAMESPACE}

# 基础路径
VITE_BASE=${VITE_BASE}

# API 接口地址（生产环境直接请求后端）
VITE_GLOB_API_URL=${PROD_API_URL}

# 是否启用压缩 (gzip | brotli | gzip,brotli | none)
VITE_COMPRESS=gzip

# 是否启用 PWA
VITE_PWA=false

# 路由模式 (hash | history)
VITE_ROUTER_HISTORY=${VITE_ROUTER_HISTORY}

# 是否注入全局 loading
VITE_INJECT_APP_LOADING=${VITE_INJECT_APP_LOADING}

# 是否打包分析
VITE_ARCHIVER=false
EOF
    echo -e "${GREEN}.env.production 文件已创建${NC}"
fi

# 5. 显示配置信息
echo -e "${YELLOW}[5/5] 配置信息汇总...${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}环境配置信息:${NC}"
echo -e "${GREEN}  前端目录: ${FRONTEND_DIR}${NC}"
echo -e "${GREEN}  应用目录: ${APP_DIR}${NC}"
echo -e "${GREEN}  应用标题: ${VITE_APP_TITLE}${NC}"
echo -e "${GREEN}  开发端口: ${VITE_PORT}${NC}"
echo -e "${GREEN}  API 地址: ${VITE_GLOB_API_URL} (通过代理转发到 http://localhost:8000)${NC}"
echo -e "${GREEN}========================================${NC}"

# 询问是否启动开发服务器
echo -e "${YELLOW}是否启动开发服务器? (y/n)${NC}"
read -r start_response
if [[ "$start_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${GREEN}启动开发服务器...${NC}"
    echo -e "${GREEN}访问地址: http://localhost:${VITE_PORT}${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
    cd "${FRONTEND_DIR}"
    pnpm dev
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}前端环境初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}后续操作：${NC}"
echo -e "${GREEN}1. 进入前端目录: cd ${FRONTEND_DIR}${NC}"
echo -e "${GREEN}2. 启动开发服务器: pnpm dev${NC}"
echo -e "${GREEN}3. 构建生产版本: pnpm build:ele${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}注意事项：${NC}"
echo -e "${YELLOW}1. 开发环境 API 请求会通过 vite.config.mts 中的代理转发到 http://localhost:8000${NC}"
echo -e "${YELLOW}2. 确保后端服务已启动后再进行前后端联调${NC}"
echo -e "${YELLOW}3. 可根据需要修改 .env.development 和 .env.production 文件${NC}"

