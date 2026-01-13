#!/bin/bash
# -*- coding: utf-8 -*-
#
# 分阶段导入脚本
# 用于将 DDL/DML 分离后的 SQL 文件分阶段导入到 MySQL 数据库
#
# 使用方法：
#   ./tools/import_ddl_dml.sh [选项]
#
# 选项：
#   --sql-dir DIR       SQL 文件目录（默认: docs/hospital/convertsql）
#   --batch-id ID       批次 ID（默认: 自动生成）
#   --ddl-only          仅导入 DDL（表结构）
#   --dml-only          仅导入 DML（数据）
#   --continue-on-error 遇到错误继续执行
#   --dry-run           仅显示将要执行的命令，不实际执行
#   -h, --help          显示帮助信息
#

set -e

# 默认值
SQL_DIR="docs/hospital/convertsql"
BATCH_ID=""
DDL_ONLY=false
DML_ONLY=false
CONTINUE_ON_ERROR=false
DRY_RUN=false

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    echo "分阶段导入脚本 - 用于导入 DDL/DML 分离后的 SQL 文件"
    echo ""
    echo "使用方法："
    echo "  ./tools/import_ddl_dml.sh [选项]"
    echo ""
    echo "选项："
    echo "  --sql-dir DIR       SQL 文件目录（默认: docs/hospital/convertsql）"
    echo "  --batch-id ID       批次 ID（默认: 自动生成）"
    echo "  --ddl-only          仅导入 DDL（表结构）"
    echo "  --dml-only          仅导入 DML（数据）"
    echo "  --continue-on-error 遇到错误继续执行"
    echo "  --dry-run           仅显示将要执行的命令，不实际执行"
    echo "  -h, --help          显示帮助信息"
    echo ""
    echo "示例："
    echo "  # 导入所有（先 DDL，后 DML）"
    echo "  ./tools/import_ddl_dml.sh --sql-dir docs/hospital/convertsql"
    echo ""
    echo "  # 仅导入表结构"
    echo "  ./tools/import_ddl_dml.sh --ddl-only"
    echo ""
    echo "  # 仅导入数据"
    echo "  ./tools/import_ddl_dml.sh --dml-only"
    echo ""
    echo "  # 指定批次 ID"
    echo "  ./tools/import_ddl_dml.sh --batch-id prod_20260113"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --sql-dir)
            SQL_DIR="$2"
            shift 2
            ;;
        --batch-id)
            BATCH_ID="$2"
            shift 2
            ;;
        --ddl-only)
            DDL_ONLY=true
            shift
            ;;
        --dml-only)
            DML_ONLY=true
            shift
            ;;
        --continue-on-error)
            CONTINUE_ON_ERROR=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            echo -e "${RED}错误：未知选项 $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

# 生成批次 ID（如果未指定）
if [ -z "$BATCH_ID" ]; then
    BATCH_ID="import_$(date +%Y%m%d_%H%M%S)"
fi

# 检查目录
CREATE_DIR="$SQL_DIR/create"
INSERT_DIR="$SQL_DIR/insert"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}     分阶段导入脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "SQL 目录: ${GREEN}$SQL_DIR${NC}"
echo -e "批次 ID:  ${GREEN}$BATCH_ID${NC}"
echo ""

# 检查 create 目录
if [ ! -d "$CREATE_DIR" ]; then
    echo -e "${YELLOW}警告：DDL 目录不存在: $CREATE_DIR${NC}"
    DDL_EXISTS=false
else
    DDL_COUNT=$(ls -1 "$CREATE_DIR"/*.sql 2>/dev/null | wc -l)
    echo -e "DDL 文件: ${GREEN}$DDL_COUNT 个${NC} ($CREATE_DIR)"
    DDL_EXISTS=true
fi

# 检查 insert 目录
if [ ! -d "$INSERT_DIR" ]; then
    echo -e "${YELLOW}警告：DML 目录不存在: $INSERT_DIR${NC}"
    DML_EXISTS=false
else
    DML_COUNT=$(ls -1 "$INSERT_DIR"/*.sql 2>/dev/null | wc -l)
    echo -e "DML 文件: ${GREEN}$DML_COUNT 个${NC} ($INSERT_DIR)"
    DML_EXISTS=true
fi

echo ""

# 构建导入命令的公共参数
COMMON_ARGS=""
if [ "$CONTINUE_ON_ERROR" = true ]; then
    COMMON_ARGS="$COMMON_ARGS --continue-on-error"
fi

# 切换到 backend-django 目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend-django"

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}错误：后端目录不存在: $BACKEND_DIR${NC}"
    exit 1
fi

cd "$BACKEND_DIR"
echo -e "工作目录: ${GREEN}$(pwd)${NC}"
echo ""

# 导入 DDL
import_ddl() {
    if [ "$DDL_EXISTS" = false ]; then
        echo -e "${YELLOW}跳过 DDL 导入（目录不存在）${NC}"
        return 0
    fi

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  阶段 1：导入表结构（DDL）${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    DDL_BATCH="${BATCH_ID}_ddl"
    CMD="python manage.py import_oracle_sql --batch-id $DDL_BATCH --sql-dir ../$CREATE_DIR $COMMON_ARGS"

    echo -e "执行命令："
    echo -e "${GREEN}$CMD${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] 跳过实际执行${NC}"
    else
        eval $CMD
        DDL_RESULT=$?

        if [ $DDL_RESULT -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✓ DDL 导入完成${NC}"
        else
            echo ""
            echo -e "${RED}✗ DDL 导入失败（退出码: $DDL_RESULT）${NC}"
            if [ "$CONTINUE_ON_ERROR" = false ]; then
                exit $DDL_RESULT
            fi
        fi
    fi

    echo ""
}

# 导入 DML
import_dml() {
    if [ "$DML_EXISTS" = false ]; then
        echo -e "${YELLOW}跳过 DML 导入（目录不存在）${NC}"
        return 0
    fi

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  阶段 2：导入数据（DML）${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    DML_BATCH="${BATCH_ID}_dml"
    CMD="python manage.py import_oracle_sql --batch-id $DML_BATCH --sql-dir ../$INSERT_DIR $COMMON_ARGS"

    echo -e "执行命令："
    echo -e "${GREEN}$CMD${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] 跳过实际执行${NC}"
    else
        eval $CMD
        DML_RESULT=$?

        if [ $DML_RESULT -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✓ DML 导入完成${NC}"
        else
            echo ""
            echo -e "${RED}✗ DML 导入失败（退出码: $DML_RESULT）${NC}"
            if [ "$CONTINUE_ON_ERROR" = false ]; then
                exit $DML_RESULT
            fi
        fi
    fi

    echo ""
}

# 执行导入
if [ "$DDL_ONLY" = true ]; then
    import_ddl
elif [ "$DML_ONLY" = true ]; then
    import_dml
else
    import_ddl
    import_dml
fi

# 显示总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  导入完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "查看导入状态："
echo -e "  ${GREEN}python manage.py import_oracle_sql --show-status --batch-id ${BATCH_ID}_ddl${NC}"
echo -e "  ${GREEN}python manage.py import_oracle_sql --show-status --batch-id ${BATCH_ID}_dml${NC}"
echo ""
echo -e "查看日志："
echo -e "  ${GREEN}cat logs/import_${BATCH_ID}_ddl.log${NC}"
echo -e "  ${GREEN}cat logs/import_${BATCH_ID}_dml.log${NC}"
echo ""
echo -e "重试失败的文件："
echo -e "  ${GREEN}python manage.py import_oracle_sql --retry-failed --batch-id ${BATCH_ID}_ddl${NC}"
echo -e "  ${GREEN}python manage.py import_oracle_sql --retry-failed --batch-id ${BATCH_ID}_dml${NC}"
echo ""
