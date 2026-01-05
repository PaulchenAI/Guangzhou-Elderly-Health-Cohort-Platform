#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载 Swagger UI 静态文件到本地

使用方法:
    python tools/download_swagger_ui.py
    
    # 或指定目标目录
    python tools/download_swagger_ui.py --target /path/to/backend-django
"""

import argparse
import os
import sys
import urllib.request
import ssl

# Swagger UI 版本
SWAGGER_UI_VERSION = "5"

# 需要下载的文件
FILES = [
    f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css",
    f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js",
]


def get_default_target_dir():
    """获取默认目标目录（backend-django/static/swagger-ui）"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return os.path.join(project_root, "backend-django", "static", "swagger-ui")


def download_file(url: str, dest_dir: str) -> bool:
    """下载文件到指定目录"""
    filename = url.split("/")[-1]
    dest_path = os.path.join(dest_dir, filename)
    
    print(f"正在下载: {url}")
    print(f"保存到: {dest_path}")
    
    try:
        # 创建不验证 SSL 的上下文（某些环境可能需要）
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(url, context=context, timeout=30) as response:
            content = response.read()
            
        with open(dest_path, "wb") as f:
            f.write(content)
        
        file_size = len(content) / 1024
        print(f"✓ 下载成功! 文件大小: {file_size:.2f} KB\n")
        return True
        
    except Exception as e:
        print(f"✗ 下载失败: {e}\n")
        return False


def check_files_exist(dest_dir: str) -> bool:
    """检查所有文件是否已存在"""
    for url in FILES:
        filename = url.split("/")[-1]
        file_path = os.path.join(dest_dir, filename)
        if not os.path.exists(file_path):
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="下载 Swagger UI 静态文件到本地")
    parser.add_argument(
        "--target", "-t",
        default=get_default_target_dir(),
        help="目标目录路径 (默认: backend-django/static/swagger-ui)"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="仅检查文件是否存在，不下载"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制重新下载（即使文件已存在）"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="静默模式，减少输出"
    )
    
    args = parser.parse_args()
    dest_dir = args.target
    
    # 仅检查模式
    if args.check:
        if check_files_exist(dest_dir):
            if not args.quiet:
                print(f"✓ Swagger UI 静态文件已存在: {dest_dir}")
            sys.exit(0)
        else:
            if not args.quiet:
                print(f"✗ Swagger UI 静态文件不存在或不完整: {dest_dir}")
            sys.exit(1)
    
    # 如果文件已存在且不是强制模式，跳过下载
    if not args.force and check_files_exist(dest_dir):
        if not args.quiet:
            print(f"✓ Swagger UI 静态文件已存在，跳过下载: {dest_dir}")
            print("  使用 --force 参数强制重新下载")
        sys.exit(0)
    
    if not args.quiet:
        print("=" * 60)
        print("Swagger UI 静态文件下载工具")
        print("=" * 60)
        print()
    
    # 确保下载目录存在
    os.makedirs(dest_dir, exist_ok=True)
    if not args.quiet:
        print(f"下载目录: {dest_dir}\n")
    
    success_count = 0
    for url in FILES:
        if download_file(url, dest_dir):
            success_count += 1
    
    if not args.quiet:
        print("=" * 60)
        print(f"下载完成: {success_count}/{len(FILES)} 个文件成功")
        print("=" * 60)
    
    if success_count == len(FILES):
        if not args.quiet:
            print()
            print("Swagger UI 静态文件下载完成！")
            print()
        sys.exit(0)
    else:
        if not args.quiet:
            print()
            print("部分文件下载失败，请检查网络连接后重试")
            print("或手动下载以下文件:")
            for url in FILES:
                print(f"  - {url}")
        sys.exit(1)


if __name__ == "__main__":
    main()

