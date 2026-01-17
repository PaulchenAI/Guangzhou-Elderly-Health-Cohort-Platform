# -*- coding: utf-8 -*-
"""
Django API 命令行工具入口

使用方法:
    python -m src.django_api info              # 显示 API 信息
    python -m src.django_api login             # 测试登录
    python -m src.django_api search <keyword>  # 搜索 API 端点
    python -m src.django_api call <intent>     # 根据意图调用 API
    python -m src.django_api summary           # 生成 AI 摘要
    python -m src.django_api list-tags         # 列出所有 Tag
    python -m src.django_api list-endpoints    # 列出所有端点
"""

from .cli import main

if __name__ == '__main__':
    main()
