#!/bin/bash
# ================================================= #
# ZQ Platform Backend Django 启动脚本
# ================================================= #

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_WORKERS="4"
DEFAULT_ENV="dev"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo ""
    echo "=========================================="
    echo "  ZQ Platform Backend Django 启动脚本"
    echo "=========================================="
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  dev           启动开发服务器 (Django runserver)"
    echo "  prod          启动生产服务器 (Gunicorn + Uvicorn)"
    echo "  uvicorn       启动 Uvicorn ASGI 服务器"
    echo "  scheduler     启动任务调度器"
    echo "  migrate       执行数据库迁移"
    echo "  init          初始化项目 (安装依赖 + 迁移 + 初始化数据)"
    echo "  install       安装依赖"
    echo "  loaddata      加载初始数据"
    echo "  shell         进入 Django Shell"
    echo "  stop          停止所有后台进程"
    echo "  status        查看运行状态"
    echo "  help          显示此帮助信息"
    echo ""
    echo "选项:"
    echo "  -h, --host    绑定主机地址 (默认: $DEFAULT_HOST)"
    echo "  -p, --port    绑定端口 (默认: $DEFAULT_PORT)"
    echo "  -w, --workers Worker 进程数 (默认: $DEFAULT_WORKERS)"
    echo "  -e, --env     运行环境 dev|uat|prd (默认: $DEFAULT_ENV)"
    echo ""
    echo "示例:"
    echo "  $0 dev                          # 启动开发服务器"
    echo "  $0 prod -p 8080 -w 8            # 生产模式，端口8080，8个worker"
    echo "  $0 uvicorn -e prd               # 生产环境启动 uvicorn"
    echo "  $0 init -e dev                  # 初始化开发环境"
    echo ""
}

# 检查并激活虚拟环境
activate_venv() {
    if [ -d "venv" ]; then
        print_info "激活虚拟环境..."
        source venv/bin/activate
        print_success "虚拟环境已激活"
    else
        print_warning "虚拟环境不存在，尝试创建..."
        python3 -m venv venv
        source venv/bin/activate
        print_success "虚拟环境已创建并激活"
    fi
}

# 检查依赖
check_dependencies() {
    if ! python -c "import django" 2>/dev/null; then
        print_warning "Django 未安装，正在安装依赖..."
        install_dependencies
    fi
}

# 安装依赖
install_dependencies() {
    print_info "安装 Python 依赖..."
    pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
    if [ $? -eq 0 ]; then
        print_success "依赖安装完成"
    else
        print_error "依赖安装失败"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    mkdir -p logs
    mkdir -p media/file_manager
    mkdir -p static/swagger-ui
    mkdir -p templates/ninja
    print_success "目录创建完成"
}

# 检查并下载 Swagger UI 静态文件
check_swagger_ui() {
    local swagger_css="$SCRIPT_DIR/static/swagger-ui/swagger-ui.css"
    local swagger_js="$SCRIPT_DIR/static/swagger-ui/swagger-ui-bundle.js"
    local download_script="$SCRIPT_DIR/../tools/download_swagger_ui.py"
    
    if [ -f "$swagger_css" ] && [ -f "$swagger_js" ]; then
        print_success "Swagger UI 静态文件已存在"
        return 0
    fi
    
    print_warning "Swagger UI 静态文件不存在，正在下载..."
    
    if [ -f "$download_script" ]; then
        python "$download_script" --target "$SCRIPT_DIR/static/swagger-ui"
        if [ $? -eq 0 ]; then
            print_success "Swagger UI 静态文件下载完成"
            return 0
        else
            print_error "Swagger UI 静态文件下载失败"
            print_warning "API 文档将使用 CDN 加载静态资源"
            return 1
        fi
    else
        print_warning "下载脚本不存在: $download_script"
        print_warning "API 文档将使用 CDN 加载静态资源"
        return 1
    fi
}

# 执行数据库迁移
run_migrate() {
    print_info "生成数据库迁移文件..."
    python manage.py makemigrations core scheduler
    
    print_info "执行数据库迁移..."
    python manage.py migrate
    
    if [ $? -eq 0 ]; then
        print_success "数据库迁移完成"
    else
        print_error "数据库迁移失败"
        exit 1
    fi
}

# 加载初始数据
load_data() {
    if [ -f "db_init.json" ]; then
        print_info "加载初始数据..."
        python manage.py loaddata db_init.json
        if [ $? -eq 0 ]; then
            print_success "初始数据加载完成"
        else
            print_error "初始数据加载失败"
            exit 1
        fi
    else
        print_warning "未找到 db_init.json 文件，跳过数据加载"
    fi
}

# 启动开发服务器
start_dev() {
    print_info "启动开发服务器..."
    print_info "地址: http://$HOST:$PORT"
    print_info "环境: $ENV"
    echo ""
    python manage.py runserver ${HOST}:${PORT}
}

# 启动 Uvicorn ASGI 服务器
start_uvicorn() {
    print_info "启动 Uvicorn ASGI 服务器..."
    print_info "地址: http://$HOST:$PORT"
    print_info "环境: $ENV"
    print_info "Workers: $WORKERS"
    echo ""
    uvicorn application.asgi:application \
        --host $HOST \
        --port $PORT \
        --workers $WORKERS \
        --log-level info \
        --access-log
}

# 启动生产服务器 (Gunicorn + Uvicorn Worker)
start_prod() {
    print_info "启动生产服务器 (Gunicorn + Uvicorn)..."
    print_info "地址: http://$HOST:$PORT"
    print_info "环境: $ENV"
    print_info "Workers: $WORKERS"
    echo ""
    gunicorn application.asgi:application \
        --bind ${HOST}:${PORT} \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --log-level info
}

# 启动任务调度器
start_scheduler() {
    print_info "启动任务调度器..."
    print_info "环境: $ENV"
    echo ""
    python start_scheduler.py
}

# 停止所有后台进程
stop_all() {
    print_info "停止所有后台进程..."
    
    # 停止 gunicorn
    pkill -f "gunicorn.*application.asgi" 2>/dev/null && print_success "Gunicorn 已停止" || print_warning "未找到 Gunicorn 进程"
    
    # 停止 uvicorn
    pkill -f "uvicorn.*application.asgi" 2>/dev/null && print_success "Uvicorn 已停止" || print_warning "未找到 Uvicorn 进程"
    
    # 停止 scheduler
    pkill -f "start_scheduler.py" 2>/dev/null && print_success "Scheduler 已停止" || print_warning "未找到 Scheduler 进程"
    
    # 停止 runserver
    pkill -f "manage.py runserver" 2>/dev/null && print_success "Django runserver 已停止" || print_warning "未找到 runserver 进程"
    
    print_success "停止操作完成"
}

# 查看运行状态
check_status() {
    print_info "检查服务运行状态..."
    echo ""
    
    # 检查 gunicorn
    if pgrep -f "gunicorn.*application.asgi" > /dev/null; then
        echo -e "${GREEN}[运行中]${NC} Gunicorn"
        pgrep -af "gunicorn.*application.asgi" | head -1
    else
        echo -e "${RED}[未运行]${NC} Gunicorn"
    fi
    
    # 检查 uvicorn
    if pgrep -f "uvicorn.*application.asgi" > /dev/null; then
        echo -e "${GREEN}[运行中]${NC} Uvicorn"
        pgrep -af "uvicorn.*application.asgi" | head -1
    else
        echo -e "${RED}[未运行]${NC} Uvicorn"
    fi
    
    # 检查 scheduler
    if pgrep -f "start_scheduler.py" > /dev/null; then
        echo -e "${GREEN}[运行中]${NC} Scheduler"
        pgrep -af "start_scheduler.py" | head -1
    else
        echo -e "${RED}[未运行]${NC} Scheduler"
    fi
    
    # 检查 runserver
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo -e "${GREEN}[运行中]${NC} Django runserver"
        pgrep -af "manage.py runserver" | head -1
    else
        echo -e "${RED}[未运行]${NC} Django runserver"
    fi
    
    echo ""
}

# 进入 Django Shell
django_shell() {
    print_info "进入 Django Shell..."
    python manage.py shell
}

# 初始化项目
init_project() {
    print_info "=========================================="
    print_info "  开始初始化项目"
    print_info "=========================================="
    echo ""
    
    activate_venv
    install_dependencies
    create_directories
    check_swagger_ui
    run_migrate
    load_data
    
    echo ""
    print_success "=========================================="
    print_success "  项目初始化完成!"
    print_success "=========================================="
    echo ""
    print_info "使用以下命令启动服务:"
    echo "  开发环境: $0 dev"
    echo "  生产环境: $0 prod"
    echo ""
}

# 解析命令行参数
parse_args() {
    HOST=$DEFAULT_HOST
    PORT=$DEFAULT_PORT
    WORKERS=$DEFAULT_WORKERS
    ENV=$DEFAULT_ENV
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--host)
                HOST="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -w|--workers)
                WORKERS="$2"
                shift 2
                ;;
            -e|--env)
                ENV="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # 设置环境变量
    export ZQ_ENV=$ENV
}

# 主函数
main() {
    # 获取命令
    COMMAND=${1:-help}
    shift 2>/dev/null || true
    
    # 解析参数
    parse_args "$@"
    
    # 非帮助命令时，激活虚拟环境并检查依赖
    if [[ "$COMMAND" != "help" && "$COMMAND" != "init" && "$COMMAND" != "install" ]]; then
        activate_venv
        check_dependencies
        create_directories
        check_swagger_ui
    fi
    
    # 执行命令
    case $COMMAND in
        dev)
            start_dev
            ;;
        prod)
            start_prod
            ;;
        uvicorn)
            start_uvicorn
            ;;
        scheduler)
            start_scheduler
            ;;
        migrate)
            run_migrate
            ;;
        init)
            init_project
            ;;
        install)
            activate_venv
            install_dependencies
            ;;
        loaddata)
            load_data
            ;;
        shell)
            django_shell
            ;;
        stop)
            stop_all
            ;;
        status)
            check_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"

