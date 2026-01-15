# -*- coding: utf-8 -*-
"""
AIagent - 多智能体AI框架
基于LangChain + LangGraph + Claude Code CLI
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aiagent",
    version="0.1.0",
    author="ZQ Platform Team",
    author_email="dev@zq-platform.com",
    description="多智能体AI框架 - 集成Claude Code CLI和OpenSpec",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zq-platform/AIagent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aiagent=src.main:main",
        ],
    },
)
