#!/bin/bash
# 临时解决方案：跳过复杂文件，继续处理其他文件

echo "跳过 gzlry_BSE_EXCEL.sql，继续处理其他文件..."
echo ""
echo "方法 1：手动标记该文件为成功（如果不重要）"
echo "UPDATE import_status SET status='success' WHERE file_name='gzlry_BSE_EXCEL.sql' AND batch_id='1f5b4b14';"
echo ""
echo "方法 2：直接处理剩余文件"
echo "python manage.py import_oracle_sql --batch-id 1f5b4b14 --auto-fix --default-convertsql --continue-on-error"
echo ""
echo "当前待处理文件数: 93 个（除了 gzlry_BSE_EXCEL.sql）"
