# -*- coding: utf-8 -*-
"""
Pytest配置文件
"""

import pytest
import os
import tempfile
from pathlib import Path
import sys

# 确保测试环境可以同时 import `src.*` 与 `AIagent.src.*`
# 注意：不要把 `<project>/src` 直接插入 sys.path，否则会遮蔽标准库 `logging`（项目内也有 `logging/` 包）。
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_env_file(temp_dir):
    """创建示例.env文件"""
    env_file = temp_dir / ".env"
    env_file.write_text("""
TEST_VAR=test_value
INT_VAR=123
BOOL_VAR=true
""")
    return env_file


@pytest.fixture
def sample_yaml_config(temp_dir):
    """创建示例YAML配置文件"""
    config_file = temp_dir / "test.yaml"
    config_file.write_text("""
test_key: test_value
nested:
  key: nested_value
  number: 42
""")
    return config_file


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock环境变量"""
    env_vars = {
        "CLAUDE_CODE_PATH": "/usr/local/bin/claude",
        "CLAUDE_CODE_WORKING_DIR": "/tmp",
        "LLM_PROVIDER": "anthropic",
        "LLM_API_KEY": "test_api_key",
        "LLM_MODEL": "claude-sonnet-4-20250514",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars
