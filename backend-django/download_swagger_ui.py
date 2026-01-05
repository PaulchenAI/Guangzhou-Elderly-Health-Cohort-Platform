#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载 Swagger UI 静态文件到本地

使用方法:
    python download_swagger_ui.py

下载后，在 settings.py 中添加:
    SWAGGER_CDN_URL = "/static/swagger-ui"
"""

import os
import urllib.request
import ssl

# Swagger UI 版本
SWAGGER_UI_VERSION = "5"

# 需要下载的文件
FILES = [
    f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css",
    f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js",
]

# 下载目录
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "swagger-ui")


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
        
        with urllib.request.urlopen(url, context=context) as response:
            content = response.read()
            
        with open(dest_path, "wb") as f:
            f.write(content)
        
        file_size = len(content) / 1024
        print(f"✓ 下载成功! 文件大小: {file_size:.2f} KB\n")
        return True
        
    except Exception as e:
        print(f"✗ 下载失败: {e}\n")
        return False


def main():
    print("=" * 60)
    print("Swagger UI 静态文件下载工具")
    print("=" * 60)
    print()
    
    # 确保下载目录存在
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"下载目录: {DOWNLOAD_DIR}\n")
    
    success_count = 0
    for url in FILES:
        if download_file(url, DOWNLOAD_DIR):
            success_count += 1
    
    print("=" * 60)
    print(f"下载完成: {success_count}/{len(FILES)} 个文件成功")
    print("=" * 60)
    
    if success_count == len(FILES):
        print()
        print("接下来请在 settings.py 中添加以下配置:")
        print()
        print('    # 使用本地 Swagger UI 静态文件')
        print('    SWAGGER_CDN_URL = "/static/swagger-ui"')
        print()
        print("并确保 Django 静态文件配置正确:")
        print()
        print('    STATIC_URL = "/static/"')
        print('    STATICFILES_DIRS = [BASE_DIR / "static"]')
        print()
    else:
        print()
        print("部分文件下载失败，请检查网络连接后重试")
        print("或手动下载以下文件:")
        for url in FILES:
            print(f"  - {url}")


if __name__ == "__main__":
    main()

