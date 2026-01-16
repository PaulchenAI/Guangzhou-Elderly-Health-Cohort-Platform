# -*- coding: utf-8 -*-
"""
策略缓存管理系统
管理 LLM 生成的提取脚本缓存
"""

import os
import json
import hashlib
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path


class StrategyCache:
    """策略缓存管理器"""
    
    def __init__(self, cache_dir: str = "docs/hospital/foreignkey/generated_strategies"):
        """
        初始化策略缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.test_cases_file = self.cache_dir / "test_cases.json"
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载元数据
        self.metadata = self._load_metadata()
        self.test_cases = self._load_test_cases()
    
    def _load_metadata(self) -> Dict:
        """加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告：加载元数据失败 - {e}")
        
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"错误：保存元数据失败 - {e}")
    
    def _load_test_cases(self) -> Dict:
        """加载测试用例"""
        if self.test_cases_file.exists():
            try:
                with open(self.test_cases_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告：加载测试用例失败 - {e}")
        
        return {}
    
    def _save_test_cases(self):
        """保存测试用例"""
        try:
            with open(self.test_cases_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_cases, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"错误：保存测试用例失败 - {e}")
    
    def compute_format_fingerprint(
        self,
        fk_statements: List[str]
    ) -> str:
        """
        计算格式指纹
        
        Args:
            fk_statements: 外键语句列表
            
        Returns:
            8位哈希指纹
        """
        # 提取格式特征
        features = {
            'has_alter_table': any('alter table' in stmt.lower() for stmt in fk_statements),
            'has_constraint': any('constraint' in stmt.lower() for stmt in fk_statements),
            'avg_length': sum(len(stmt) for stmt in fk_statements) / max(len(fk_statements), 1),
            'has_newlines': any('\n' in stmt for stmt in fk_statements),
            'statement_count': len(fk_statements),
        }
        
        # 生成哈希指纹
        features_str = json.dumps(features, sort_keys=True)
        fingerprint = hashlib.md5(features_str.encode()).hexdigest()[:8]
        
        return fingerprint
    
    def get_cached_script(self, fingerprint: str) -> Optional[str]:
        """
        获取缓存的脚本
        
        Args:
            fingerprint: 格式指纹
            
        Returns:
            脚本代码，如果不存在则返回 None
        """
        if fingerprint not in self.metadata:
            return None
        
        script_file = self.cache_dir / f"{fingerprint}.py"
        
        if not script_file.exists():
            return None
        
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"错误：读取缓存脚本失败 - {e}")
            return None
    
    def save_strategy(
        self,
        fingerprint: str,
        script_code: str,
        description: str,
        sample_file: str,
        test_statements: List[str]
    ):
        """
        保存策略到缓存
        
        Args:
            fingerprint: 格式指纹
            script_code: 脚本代码
            description: 格式描述
            sample_file: 样本文件名
            test_statements: 测试语句
        """
        # 保存脚本文件
        script_file = self.cache_dir / f"{fingerprint}.py"
        try:
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_code)
        except Exception as e:
            print(f"错误：保存脚本文件失败 - {e}")
            return
        
        # 更新元数据
        self.metadata[fingerprint] = {
            'script_file': f"{fingerprint}.py",
            'format_description': description,
            'success_count': 0,
            'created_at': datetime.now().isoformat(),
            'last_used_at': None,
            'sample_file': sample_file
        }
        self._save_metadata()
        
        # 保存测试用例
        self.test_cases[fingerprint] = test_statements
        self._save_test_cases()
        
        print(f"✓ 策略已缓存: {fingerprint}")
    
    def update_usage(self, fingerprint: str):
        """
        更新策略使用统计
        
        Args:
            fingerprint: 格式指纹
        """
        if fingerprint in self.metadata:
            self.metadata[fingerprint]['success_count'] += 1
            self.metadata[fingerprint]['last_used_at'] = datetime.now().isoformat()
            self._save_metadata()
    
    def get_strategy_info(self, fingerprint: str) -> Optional[Dict]:
        """获取策略信息"""
        return self.metadata.get(fingerprint)
    
    def list_all_strategies(self) -> List[Dict]:
        """列出所有策略"""
        strategies = []
        for fingerprint, info in self.metadata.items():
            strategies.append({
                'fingerprint': fingerprint,
                **info
            })
        
        # 按成功次数排序
        strategies.sort(key=lambda x: x.get('success_count', 0), reverse=True)
        
        return strategies
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_strategies = len(self.metadata)
        total_usage = sum(info.get('success_count', 0) for info in self.metadata.values())
        
        return {
            'total_strategies': total_strategies,
            'total_usage_count': total_usage,
            'cache_directory': str(self.cache_dir),
            'strategies': list(self.metadata.keys())
        }
