# -*- coding: utf-8 -*-
"""
配置系统测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from src.utils.env_loader import EnvLoader
from src.utils.config_loader import ConfigLoader
from src.utils.config_models import Settings, ClaudeCodeConfig, LLMConfig
from src.utils.config_manager import ConfigManager


class TestEnvLoader:
    """环境变量加载器测试"""
    
    def test_get_existing_env_var(self):
        """测试获取存在的环境变量"""
        os.environ['TEST_VAR'] = 'test_value'
        loader = EnvLoader()
        assert loader.get('TEST_VAR') == 'test_value'
        del os.environ['TEST_VAR']
    
    def test_get_nonexistent_env_var(self):
        """测试获取不存在的环境变量"""
        loader = EnvLoader()
        assert loader.get('NONEXISTENT_VAR') is None
        assert loader.get('NONEXISTENT_VAR', 'default') == 'default'
    
    def test_get_bool(self):
        """测试获取布尔类型环境变量"""
        loader = EnvLoader()
        os.environ['BOOL_TRUE'] = 'true'
        os.environ['BOOL_FALSE'] = 'false'
        assert loader.get_bool('BOOL_TRUE') is True
        assert loader.get_bool('BOOL_FALSE') is False
        assert loader.get_bool('NONEXISTENT', True) is True
        del os.environ['BOOL_TRUE']
        del os.environ['BOOL_FALSE']
    
    def test_get_int(self):
        """测试获取整数类型环境变量"""
        loader = EnvLoader()
        os.environ['INT_VAR'] = '123'
        assert loader.get_int('INT_VAR') == 123
        assert loader.get_int('NONEXISTENT', 456) == 456
        del os.environ['INT_VAR']
    
    def test_require(self):
        """测试获取必需的环境变量"""
        loader = EnvLoader()
        os.environ['REQUIRED_VAR'] = 'required_value'
        assert loader.require('REQUIRED_VAR') == 'required_value'
        del os.environ['REQUIRED_VAR']
        
        with pytest.raises(ValueError):
            loader.require('NONEXISTENT_VAR')


class TestConfigLoader:
    """YAML配置加载器测试"""
    
    def test_load_yaml(self):
        """测试加载YAML文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("""
test_key: test_value
nested:
  key: nested_value
""")
            
            loader = ConfigLoader(config_dir=tmpdir)
            config = loader.load_yaml("test.yaml")
            
            assert config['test_key'] == 'test_value'
            assert config['nested']['key'] == 'nested_value'
    
    def test_get_nested_key(self):
        """测试获取嵌套配置键"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("""
section:
  key: value
""")
            
            loader = ConfigLoader(config_dir=tmpdir)
            assert loader.get("test.yaml", "section.key") == 'value'
            assert loader.get("test.yaml", "nonexistent.key") is None


class TestConfigModels:
    """配置模型测试"""
    
    def test_claude_code_config(self):
        """测试Claude Code配置模型"""
        config = ClaudeCodeConfig(
            path="/usr/local/bin/claude",
            timeout=300,
            max_concurrent=2,
            working_dir="/tmp"
        )
        
        assert config.path == "/usr/local/bin/claude"
        assert config.timeout == 300
        assert config.max_concurrent == 2
    
    def test_llm_config(self):
        """测试LLM配置模型"""
        config = LLMConfig(
            provider="anthropic",
            api_key="test_key",
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7
        )
        
        assert config.provider == "anthropic"
        assert config.api_key == "test_key"
        assert config.temperature == 0.7
    
    def test_llm_config_validation(self):
        """测试LLM配置验证"""
        # local提供商不需要api_key
        config = LLMConfig(
            provider="local",
            model="local-model"
        )
        assert config.provider == "local"
        
        # 其他提供商需要api_key
        with pytest.raises(ValueError):
            LLMConfig(
                provider="anthropic",
                api_key=None,
                model="claude-sonnet-4-20250514"
            )


class TestConfigManager:
    """配置管理器测试"""
    
    def test_config_manager_singleton(self, monkeypatch):
        """测试配置管理器单例模式"""
        # 设置必需的环境变量
        monkeypatch.setenv("CLAUDE_CODE_PATH", "/usr/local/bin/claude")
        monkeypatch.setenv("CLAUDE_CODE_WORKING_DIR", "/tmp")
        
        # 清除单例实例
        from src.utils.config_manager import ConfigManager
        ConfigManager._instance = None
        
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        assert manager1 is manager2
    
    def test_get_configs(self, monkeypatch):
        """测试获取各种配置"""
        # 设置必需的环境变量
        monkeypatch.setenv("CLAUDE_CODE_PATH", "/usr/local/bin/claude")
        monkeypatch.setenv("CLAUDE_CODE_WORKING_DIR", "/tmp")
        monkeypatch.setenv("LLM_PROVIDER", "local")  # local不需要api_key
        
        # 清除单例实例
        from src.utils.config_manager import ConfigManager
        ConfigManager._instance = None
        
        manager = ConfigManager()
        claude_config = manager.get_claude_code_config()
        
        assert claude_config.path == "/usr/local/bin/claude"
        assert claude_config.timeout == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
