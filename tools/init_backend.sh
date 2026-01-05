#!/bin/bash

# 后端环境初始化脚本
# 功能：创建 Python 3.11 虚拟环境，安装 MySQL 和 Redis，配置环境变量，初始化数据库和 Redis
# 使用方法:
# bash -n /tools/init_backend.sh
set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目路径（相对于脚本位置）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend-django"
ENV_FILE="${BACKEND_DIR}/.env"

# 默认配置
DB_USER="fuadmin"
DB_PASSWORD="fuadmin"
DB_NAME="fu_admin_pro"
DB_HOST="127.0.0.1"
DB_PORT="3306"
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
REDIS_PASSWORD=""
REDIS_DB="2"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}开始初始化后端环境${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 检查并安装 Python 3.11
echo -e "${YELLOW}[1/8] 检查 Python 3.11 安装...${NC}"
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}Python 3.11 未安装，正在安装...${NC}"
    sudo apt-get update
    sudo apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
    echo -e "${GREEN}Python 3.11 安装完成${NC}"
else
    echo -e "${GREEN}Python 3.11 已安装${NC}"
fi

# 2. 创建虚拟环境
echo -e "${YELLOW}[2/8] 创建 Python 3.11 虚拟环境...${NC}"
cd "${BACKEND_DIR}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}虚拟环境已存在，是否删除并重新创建? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -rf venv
        python3.11 -m venv venv
        echo -e "${GREEN}虚拟环境重新创建完成${NC}"
    else
        echo -e "${GREEN}使用现有虚拟环境${NC}"
    fi
else
    python3.11 -m venv venv
    echo -e "${GREEN}虚拟环境创建完成${NC}"
fi

# 3. 安装 MySQL
echo -e "${YELLOW}[3/8] 检查并安装 MySQL...${NC}"
if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}MySQL 未安装，正在安装...${NC}"
    sudo apt-get update
    sudo apt-get install -y mysql-server
    sudo systemctl start mysql
    sudo systemctl enable mysql
    echo -e "${GREEN}MySQL 安装完成${NC}"
else
    echo -e "${GREEN}MySQL 已安装${NC}"
    sudo systemctl start mysql || true
fi

# 安装 MySQL 开发库（用于 Python MySQL 客户端）
echo -e "${YELLOW}安装 MySQL 开发库...${NC}"
sudo apt-get install -y default-libmysqlclient-dev build-essential pkg-config || \
sudo apt-get install -y libmysqlclient-dev build-essential pkg-config || true
echo -e "${GREEN}MySQL 开发库安装完成${NC}"

# 4. 安装 Redis
echo -e "${YELLOW}[4/8] 检查并安装 Redis...${NC}"
if ! command -v redis-server &> /dev/null; then
    echo -e "${YELLOW}Redis 未安装，正在安装...${NC}"
    sudo apt-get update
    sudo apt-get install -y redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    echo -e "${GREEN}Redis 安装完成${NC}"
else
    echo -e "${GREEN}Redis 已安装${NC}"
    sudo systemctl start redis-server || true
fi

# 5. 创建 .env 环境配置文件
echo -e "${YELLOW}[5/8] 创建 .env 环境配置文件...${NC}"
if [ -f "${ENV_FILE}" ]; then
    echo -e "${YELLOW}.env 文件已存在，是否覆盖? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${GREEN}保留现有 .env 文件${NC}"
    else
        cat > "${ENV_FILE}" << EOF
# MySQL 数据库配置
DEV_DB_USER=${DB_USER}
DEV_DB_PASSWORD=${DB_PASSWORD}

# JWT 配置
JWT_ACCESS_SECRET_KEY=$(openssl rand -hex 32)
JWT_REFRESH_SECRET_KEY=$(openssl rand -hex 32)
EOF
        echo -e "${GREEN}.env 文件已创建${NC}"
    fi
else
    cat > "${ENV_FILE}" << EOF
# MySQL 数据库配置
DEV_DB_USER=${DB_USER}
DEV_DB_PASSWORD=${DB_PASSWORD}

# JWT 配置
JWT_ACCESS_SECRET_KEY=$(openssl rand -hex 32)
JWT_REFRESH_SECRET_KEY=$(openssl rand -hex 32)
EOF
    echo -e "${GREEN}.env 文件已创建${NC}"
fi

# 6. 配置 dev_env.py 数据库参数
echo -e "${YELLOW}[6/8] 配置 dev_env.py 数据库参数...${NC}"
DEV_ENV_FILE="${BACKEND_DIR}/env/dev_env.py"
if [ -f "${DEV_ENV_FILE}" ]; then
    # 备份原文件
    cp "${DEV_ENV_FILE}" "${DEV_ENV_FILE}.bak"
    # 修改数据库配置
    sed -i "s/DATABASE_TYPE = \"POSTGRESQL\"/DATABASE_TYPE = \"MYSQL\"/" "${DEV_ENV_FILE}"
    sed -i "s/DATABASE_HOST = \"django-ninja.zq-platform.cn\"/DATABASE_HOST = \"${DB_HOST}\"/" "${DEV_ENV_FILE}"
    sed -i "s/DATABASE_PORT = 5323/DATABASE_PORT = ${DB_PORT}/" "${DEV_ENV_FILE}"
    sed -i "s/DATABASE_NAME = \"zq-admin\"/DATABASE_NAME = \"${DB_NAME}\"/" "${DEV_ENV_FILE}"
    echo -e "${GREEN}dev_env.py 配置已更新${NC}"
    echo -e "${GREEN}  数据库类型: MYSQL${NC}"
    echo -e "${GREEN}  数据库主机: ${DB_HOST}${NC}"
    echo -e "${GREEN}  数据库端口: ${DB_PORT}${NC}"
    echo -e "${GREEN}  数据库名: ${DB_NAME}${NC}"
    echo -e "${YELLOW}  原文件已备份为: ${DEV_ENV_FILE}.bak${NC}"
else
    echo -e "${RED}错误: ${DEV_ENV_FILE} 文件不存在${NC}"
    exit 1
fi

# 7. 初始化 MySQL
echo -e "${YELLOW}[7/8] 初始化 MySQL 数据库...${NC}"
# 使用脚本中定义的默认配置变量
# 创建数据库和用户
sudo mysql << EOF
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 删除已存在的用户（如果存在，包括所有可能的host）
DROP USER IF EXISTS '${DB_USER}'@'localhost';
DROP USER IF EXISTS '${DB_USER}'@'%';
DROP USER IF EXISTS '${DB_USER}'@'127.0.0.1';

-- 创建用户，使用 mysql_native_password 认证方式（兼容 pymysql）
CREATE USER '${DB_USER}'@'localhost' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE USER '${DB_USER}'@'%' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';
CREATE USER '${DB_USER}'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY '${DB_PASSWORD}';

-- 授予权限
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';

-- 刷新权限
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}MySQL 数据库初始化完成${NC}"
echo -e "${GREEN}  数据库名: ${DB_NAME}${NC}"
echo -e "${GREEN}  用户名: ${DB_USER}${NC}"
echo -e "${GREEN}  密码: ${DB_PASSWORD}${NC}"
echo -e "${GREEN}  认证方式: mysql_native_password（兼容 pymysql）${NC}"

# 8. 初始化 Redis
echo -e "${YELLOW}[8/8] 检查 Redis 服务状态...${NC}"
if systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}Redis 服务正在运行${NC}"
    # 测试 Redis 连接
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}Redis 连接测试成功${NC}"
    else
        echo -e "${YELLOW}Redis 连接测试失败，但服务正在运行${NC}"
    fi
else
    echo -e "${YELLOW}启动 Redis 服务...${NC}"
    sudo systemctl start redis-server
    if systemctl is-active --quiet redis-server; then
        echo -e "${GREEN}Redis 服务启动成功${NC}"
    else
        echo -e "${RED}Redis 服务启动失败${NC}"
        exit 1
    fi
fi

# 8. 安装 Python 依赖并配置 pymysql
echo -e "${YELLOW}[额外] 是否需要安装 Python 依赖? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}激活虚拟环境并安装依赖...${NC}"
    source "${BACKEND_DIR}/venv/bin/activate"
    pip install --upgrade pip
    pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r "${BACKEND_DIR}/requirements.txt"
    echo -e "${GREEN}Python 依赖安装完成${NC}"
    
    # 下载 Swagger UI 静态文件
    echo -e "${YELLOW}检查 Swagger UI 静态文件...${NC}"
    SWAGGER_DIR="${BACKEND_DIR}/static/swagger-ui"
    SWAGGER_CSS="${SWAGGER_DIR}/swagger-ui.css"
    SWAGGER_JS="${SWAGGER_DIR}/swagger-ui-bundle.js"
    DOWNLOAD_SCRIPT="${SCRIPT_DIR}/download_swagger_ui.py"
    
    if [ -f "${SWAGGER_CSS}" ] && [ -f "${SWAGGER_JS}" ]; then
        echo -e "${GREEN}Swagger UI 静态文件已存在${NC}"
    else
        if [ -f "${DOWNLOAD_SCRIPT}" ]; then
            echo -e "${YELLOW}下载 Swagger UI 静态文件...${NC}"
            python "${DOWNLOAD_SCRIPT}" --target "${SWAGGER_DIR}"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Swagger UI 静态文件下载完成${NC}"
            else
                echo -e "${YELLOW}Swagger UI 静态文件下载失败，API 文档将使用 CDN${NC}"
            fi
        else
            echo -e "${YELLOW}下载脚本不存在: ${DOWNLOAD_SCRIPT}${NC}"
            echo -e "${YELLOW}API 文档将使用 CDN 加载静态资源${NC}"
        fi
    fi
    
    # 配置 Django 使用 pymysql
    echo -e "${YELLOW}配置 Django 使用 pymysql...${NC}"
    APP_INIT_FILE="${BACKEND_DIR}/application/__init__.py"
    if [ -f "${APP_INIT_FILE}" ]; then
        # 检查是否已经配置了 pymysql
        if ! grep -q "pymysql" "${APP_INIT_FILE}"; then
            # 备份原文件
            cp "${APP_INIT_FILE}" "${APP_INIT_FILE}.bak"
            # 在文件开头添加 pymysql 配置
            cat > "${APP_INIT_FILE}" << 'PYMYSQL_EOF'
import pymysql
pymysql.install_as_MySQLdb()

PYMYSQL_EOF
            # 如果原文件有内容，追加到新文件后面
            if [ -s "${APP_INIT_FILE}.bak" ]; then
                cat "${APP_INIT_FILE}.bak" >> "${APP_INIT_FILE}"
            fi
            echo -e "${GREEN}Django 已配置使用 pymysql${NC}"
        else
            echo -e "${GREEN}Django 已配置使用 pymysql（无需重复配置）${NC}"
        fi
    else
        echo -e "${YELLOW}警告: ${APP_INIT_FILE} 文件不存在，将创建${NC}"
        cat > "${APP_INIT_FILE}" << 'PYMYSQL_EOF'
import pymysql
pymysql.install_as_MySQLdb()

PYMYSQL_EOF
        echo -e "${GREEN}Django 已配置使用 pymysql${NC}"
    fi
fi

# 9. 自动执行 Django 迁移和初始化
echo -e "${YELLOW}[额外步骤] 是否自动执行 Django 迁移和初始化? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}执行 Django 迁移和初始化...${NC}"
    cd "${BACKEND_DIR}"
    
    # 激活虚拟环境
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${GREEN}虚拟环境已激活${NC}"
    else
        echo -e "${RED}错误: 虚拟环境不存在，请先创建虚拟环境${NC}"
        exit 1
    fi
    
    # 运行迁移
    echo -e "${YELLOW}生成迁移文件...${NC}"
    set +e  # 暂时关闭错误退出，以便检查退出码
    python manage.py makemigrations core scheduler 2>&1 | tee /tmp/makemigrations.log
    MAKEMIGRATIONS_STATUS=${PIPESTATUS[0]}
    set -e  # 重新开启错误退出
    if [ ${MAKEMIGRATIONS_STATUS} -eq 0 ]; then
        echo -e "${GREEN}迁移文件生成完成${NC}"
    else
        echo -e "${YELLOW}迁移文件生成完成（可能有警告）${NC}"
    fi
    
    # 执行迁移
    echo -e "${YELLOW}执行数据库迁移...${NC}"
    set +e  # 暂时关闭错误退出，以便检查退出码
    python manage.py migrate 2>&1 | tee /tmp/migrate.log
    MIGRATE_STATUS=${PIPESTATUS[0]}
    set -e  # 重新开启错误退出
    if [ ${MIGRATE_STATUS} -ne 0 ]; then
        echo -e "${RED}数据库迁移失败（退出码: ${MIGRATE_STATUS}），请检查错误信息${NC}"
        echo -e "${RED}错误日志: /tmp/migrate.log${NC}"
        exit 1
    fi
    echo -e "${GREEN}数据库迁移完成${NC}"
    
    # 初始化数据（如果文件存在）
    if [ -f "db_init.json" ]; then
        echo -e "${YELLOW}初始化数据...${NC}"
        set +e  # 暂时关闭错误退出，以便检查退出码
        python manage.py loaddata db_init.json 2>&1 | tee /tmp/loaddata.log
        LOADDATA_STATUS=${PIPESTATUS[0]}
        set -e  # 重新开启错误退出
        if [ ${LOADDATA_STATUS} -eq 0 ]; then
            echo -e "${GREEN}数据初始化完成${NC}"
        else
            echo -e "${YELLOW}数据初始化失败或已存在（可忽略，退出码: ${LOADDATA_STATUS}）${NC}"
        fi
    else
        echo -e "${YELLOW}db_init.json 文件不存在，跳过数据初始化${NC}"
    fi
    
    echo -e "${GREEN}Django 迁移和初始化完成！${NC}"
    
    # 询问是否启动项目
    echo -e "${YELLOW}是否启动 Django 开发服务器? (y/n)${NC}"
    read -r start_response
    if [[ "$start_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${GREEN}启动 Django 开发服务器...${NC}"
        echo -e "${GREEN}服务器地址: http://0.0.0.0:8000${NC}"
        echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
        python manage.py runserver 0.0.0.0:8000
    fi
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}环境初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}后续操作：${NC}"
echo -e "${GREEN}1. 进入后端目录: cd ${BACKEND_DIR}${NC}"
echo -e "${GREEN}2. 激活虚拟环境: source venv/bin/activate${NC}"
echo -e "${GREEN}3. 启动项目: python manage.py runserver 0.0.0.0:8000${NC}"
echo -e "${GREEN}注意: .env 文件会在 Django 启动时自动加载，无需手动加载环境变量${NC}"

