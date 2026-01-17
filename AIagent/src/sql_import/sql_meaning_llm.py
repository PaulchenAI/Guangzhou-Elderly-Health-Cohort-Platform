# -*- coding: utf-8 -*-
"""
SQL 含义推断（简化版）
直接把 SQL 发给 LLM，让 LLM 解析并推断含义
"""

import json
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from ..llm.factory import LLMFactory
from ..utils.config_manager import ConfigManager
from ..utils.config_models import LLMConfig
from ..logging.logger import get_logger

logger = get_logger("sql_meaning_llm")

# 错误日志文件名
ERROR_LOG_FILENAME = "error_log.json"


# ============== JSON 格式验证模型 ==============

class MeaningInfo(BaseModel):
    """含义信息"""
    meaning: str = Field(..., description="推断的中文含义")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")
    reasoning: str = Field(..., description="推断理由")


class FieldInfo(BaseModel):
    """字段信息"""
    name: str = Field(..., description="字段名")
    type: str = Field(..., description="字段类型")
    comment: Optional[str] = Field(None, description="原始注释")
    meaning: str = Field(..., description="推断的中文含义")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reasoning: str = Field(..., description="推断理由")


class LLMOutputSchema(BaseModel):
    """LLM 输出格式验证模型"""
    table_name: str = Field(..., description="表名")
    table_comment: Optional[str] = Field(None, description="表注释")
    table_meaning: MeaningInfo = Field(..., description="表含义信息")
    fields: List[FieldInfo] = Field(..., min_length=1, description="字段列表")

# 默认输出目录
DEFAULT_OUTPUT_DIR = Path("docs/hospital/commentsql")

# 默认提示词模板
DEFAULT_PROMPT = """你是一个数据库专家，请分析以下 SQL CREATE TABLE 语句，提取表和字段信息，并推断中文含义。
这个数据库是一个养老机构的管理系统，请根据养老机构的管理需求，推断表和字段的中文含义。
## SQL 语句

```sql
{sql_content}
```

## 要求

1. 提取表名（忽略 {ignore_prefix} 前缀）
2. 提取表注释
3. 提取所有字段的名称、类型、注释
4. 对于没有注释或注释不清晰的，推断其中文含义
5. 字段名可能是拼音缩写（如 xh=序号, zyh=住院号, xm=姓名）或英文缩写

## 输出格式

请严格按以下 JSON 格式输出，不要包含其他文字：

```json
{{
  "table_name": "表名（不含前缀）",
  "table_comment": "原始表注释",
  "table_meaning": {{
    "meaning": "推断的中文含义",
    "confidence": 0.95,
    "reasoning": "推断理由"
  }},
  "fields": [
    {{
      "name": "字段名",
      "type": "字段类型",
      "comment": "原始注释（如果有）",
      "meaning": "推断的中文含义",
      "confidence": 0.95,
      "reasoning": "推断理由"
    }}
  ]
}}
```
"""

# 带上下文的提示词模板（用于重新推断）
CONTEXT_PROMPT = """你是一个数据库专家，请分析以下 SQL CREATE TABLE 语句，提取表和字段信息，并推断中文含义。
这个数据库是一个养老机构的管理系统。

## 重要上下文信息

**这个表是一个预设表单**，已知以下业务信息：
- **表单分类**: {form_category}
- **表单中文名称**: {form_name}

请基于上述业务上下文来推断字段含义，这将帮助你更准确地理解每个字段的用途。

## SQL 语句

```sql
{sql_content}
```

## 要求

1. 提取表名（忽略 {ignore_prefix} 前缀）
2. **表的中文含义应直接使用上面提供的"表单中文名称"**
3. 提取所有字段的名称、类型、注释
4. 对于没有注释或注释不清晰的，**结合表单的业务用途**推断其中文含义
5. 字段名可能是拼音缩写（如 xh=序号, zyh=住院号, xm=姓名）或英文缩写
6. 推断时要考虑这是"{form_category}"类型的表单

## 输出格式

请严格按以下 JSON 格式输出，不要包含其他文字：

```json
{{
  "table_name": "表名（不含前缀）",
  "table_comment": "原始表注释",
  "table_meaning": {{
    "meaning": "推断的中文含义（应使用表单中文名称）",
    "confidence": 0.98,
    "reasoning": "基于已知的表单名称和分类"
  }},
  "fields": [
    {{
      "name": "字段名",
      "type": "字段类型",
      "comment": "原始注释（如果有）",
      "meaning": "推断的中文含义",
      "confidence": 0.95,
      "reasoning": "推断理由（结合表单业务用途）"
    }}
  ]
}}
```
"""

# 默认 SQL 文件目录
DEFAULT_SQL_DIR = Path("docs/hospital/convertsql/create")


class SQLMeaningInferencer:
    """SQL 含义推断器（简化版）"""
    
    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        ignore_prefix: str = "gzlry_",
        prompt_template: Optional[str] = None,
        skip_existing: bool = False,
        concurrency: int = 1
    ):
        """
        初始化推断器
        
        Args:
            llm_config: LLM 配置
            ignore_prefix: 要忽略的表名前缀
            prompt_template: 自定义提示词模板
            skip_existing: 是否跳过已存在结果的文件
            concurrency: 并发数量（默认 1，即顺序处理）
        """
        if llm_config is None:
            config_manager = ConfigManager()
            llm_config = config_manager.get_llm_config()
        
        self.llm_client = LLMFactory.create_llm(llm_config)
        self.llm_config = llm_config
        self.ignore_prefix = ignore_prefix
        self.prompt_template = prompt_template or DEFAULT_PROMPT
        self.skip_existing = skip_existing
        self.concurrency = max(1, concurrency)  # 至少为 1
    
    async def infer_file(
        self,
        sql_file: str,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        推断单个 SQL 文件的含义
        
        Args:
            sql_file: SQL 文件路径
            output_path: 输出路径（可选）
            
        Returns:
            推断结果
        """
        sql_path = Path(sql_file)
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL 文件不存在: {sql_file}")
        
        # 读取 SQL 内容
        sql_content = sql_path.read_text(encoding='utf-8')
        
        # 调用 LLM 推断
        result = await self._infer_with_llm(sql_content)
        
        # 构建完整结果
        full_result = {
            "file_path": str(sql_path),
            "table": {
                "table_name": result.get("table_name", ""),
                "original_comment": result.get("table_comment"),
                "inferred_meaning": result.get("table_meaning", {}).get("meaning"),
                "confidence": result.get("table_meaning", {}).get("confidence"),
                "reasoning": result.get("table_meaning", {}).get("reasoning"),
                "fields": [
                    {
                        "field_name": f.get("name", ""),
                        "field_type": f.get("type", ""),
                        "original_comment": f.get("comment"),
                        "inferred_meaning": f.get("meaning"),
                        "confidence": f.get("confidence"),
                        "reasoning": f.get("reasoning")
                    }
                    for f in result.get("fields", [])
                ]
            },
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "llm_model": self.llm_config.model,
                "llm_provider": self.llm_config.provider
            }
        }
        
        # 确定输出路径
        if output_path is None:
            output_path = DEFAULT_OUTPUT_DIR / f"{sql_path.stem}_meaning.json"
        else:
            output_path = Path(output_path)
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已保存到: {output_path}")
        return full_result
    
    async def infer_directory(
        self,
        sql_dir: str,
        output_dir: Optional[str] = None,
        retry_failed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量推断目录中的 SQL 文件（支持并发处理）
        
        Args:
            sql_dir: SQL 文件目录
            output_dir: 输出目录（可选）
            retry_failed: 是否只重试之前失败的任务
            
        Returns:
            推断结果列表
        """
        dir_path = Path(sql_dir)
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {sql_dir}")
        
        output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 如果是重试模式，只处理错误日志中的文件
        if retry_failed:
            sql_files = self._get_failed_files(output_path, dir_path)
            if not sql_files:
                logger.info("没有需要重试的失败任务")
                return []
            logger.info(f"重试模式：找到 {len(sql_files)} 个失败任务")
        else:
            sql_files = list(dir_path.glob("*.sql"))
            if not sql_files:
                logger.warning(f"目录中没有 SQL 文件: {sql_dir}")
                return []
        
        # 过滤已存在的文件
        tasks_to_process = []
        skipped_count = 0
        
        for sql_file in sql_files:
            out_file = output_path / f"{sql_file.stem}_meaning.json"
            
            # 检查是否跳过已存在的结果
            if self.skip_existing and out_file.exists():
                logger.info(f"跳过（已存在）: {sql_file.name}")
                skipped_count += 1
                continue
            
            tasks_to_process.append((sql_file, out_file))
        
        if not tasks_to_process:
            logger.info(f"没有需要处理的文件（跳过 {skipped_count} 个）")
            return []
        
        # 并发处理
        logger.info(f"开始处理 {len(tasks_to_process)} 个文件，并发数: {self.concurrency}")
        
        semaphore = asyncio.Semaphore(self.concurrency)
        task_results = await asyncio.gather(
            *[self._process_file_with_semaphore(semaphore, sql_file, out_file) 
              for sql_file, out_file in tasks_to_process],
            return_exceptions=False  # 我们在内部处理异常
        )
        
        # 分离成功和失败的结果
        results = []
        failed_tasks = []
        
        for result, error_info in task_results:
            if error_info:
                failed_tasks.append(error_info)
            elif result:
                results.append(result)
        
        # 保存错误日志
        self._save_error_log(output_path, failed_tasks)
        
        # 保存汇总文件
        if results:
            summary_file = output_path / "all_meanings.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(
            f"批量处理完成: 成功 {len(results)} 个, "
            f"失败 {len(failed_tasks)} 个, "
            f"跳过 {skipped_count} 个"
        )
        return results
    
    async def _process_file_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        sql_file: Path,
        out_file: Path
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        使用信号量控制的单文件处理
        
        Args:
            semaphore: 并发控制信号量
            sql_file: SQL 文件路径
            out_file: 输出文件路径
            
        Returns:
            (推断结果, 错误信息) 元组，成功时错误信息为 None
        """
        async with semaphore:
            try:
                result = await self.infer_file(str(sql_file), str(out_file))
                
                # 检查是否有错误
                if "error" in result.get("table", {}):
                    raise Exception(result["table"]["error"])
                
                logger.info(f"完成: {sql_file.name}")
                return (result, None)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"处理 {sql_file.name} 失败: {error_msg}")
                error_info = {
                    "file": str(sql_file),
                    "file_name": sql_file.name,
                    "error": error_msg,
                    "failed_at": datetime.now().isoformat()
                }
                return (None, error_info)
    
    def _save_error_log(self, output_dir: Path, failed_tasks: List[Dict[str, Any]]) -> None:
        """
        保存错误日志
        
        Args:
            output_dir: 输出目录
            failed_tasks: 失败任务列表
        """
        error_log_path = output_dir / ERROR_LOG_FILENAME
        
        # 读取现有的错误日志
        existing_errors = []
        if error_log_path.exists():
            try:
                with open(error_log_path, 'r', encoding='utf-8') as f:
                    existing_errors = json.load(f)
            except Exception:
                existing_errors = []
        
        # 合并错误日志（移除已成功的，添加新失败的）
        # 获取当前成功的文件名集合
        if failed_tasks:
            # 更新错误日志：保留未重试的旧错误，添加新错误
            failed_file_names = {t["file_name"] for t in failed_tasks}
            # 移除已经重试过的旧错误记录
            existing_errors = [
                e for e in existing_errors 
                if e.get("file_name") not in failed_file_names
            ]
            # 添加新的失败记录
            existing_errors.extend(failed_tasks)
        
        # 保存错误日志
        error_log = {
            "updated_at": datetime.now().isoformat(),
            "total_failed": len(existing_errors),
            "failed_tasks": existing_errors
        }
        
        with open(error_log_path, 'w', encoding='utf-8') as f:
            json.dump(error_log, f, ensure_ascii=False, indent=2)
        
        if existing_errors:
            logger.info(f"错误日志已保存到: {error_log_path}")
    
    def _get_failed_files(self, output_dir: Path, sql_dir: Path) -> List[Path]:
        """
        从错误日志中获取失败的文件列表
        
        Args:
            output_dir: 输出目录（包含错误日志）
            sql_dir: SQL 文件目录
            
        Returns:
            失败的 SQL 文件路径列表
        """
        error_log_path = output_dir / ERROR_LOG_FILENAME
        
        if not error_log_path.exists():
            logger.warning(f"错误日志不存在: {error_log_path}")
            return []
        
        try:
            with open(error_log_path, 'r', encoding='utf-8') as f:
                error_log = json.load(f)
        except Exception as e:
            logger.error(f"读取错误日志失败: {e}")
            return []
        
        failed_tasks = error_log.get("failed_tasks", [])
        failed_files = []
        
        for task in failed_tasks:
            file_path = Path(task.get("file", ""))
            # 如果原始路径存在，使用原始路径
            if file_path.exists():
                failed_files.append(file_path)
            else:
                # 否则尝试在 sql_dir 中查找
                file_name = task.get("file_name", "")
                if file_name:
                    alt_path = sql_dir / file_name
                    if alt_path.exists():
                        failed_files.append(alt_path)
                    else:
                        logger.warning(f"找不到失败的文件: {file_name}")
        
        return failed_files
    
    def clear_error_log(self, output_dir: Optional[str] = None) -> bool:
        """
        清除错误日志
        
        Args:
            output_dir: 输出目录
            
        Returns:
            是否成功清除
        """
        output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        error_log_path = output_path / ERROR_LOG_FILENAME
        
        if error_log_path.exists():
            error_log_path.unlink()
            logger.info(f"错误日志已清除: {error_log_path}")
            return True
        else:
            logger.info("没有错误日志需要清除")
            return False
    
    async def _infer_with_llm(self, sql_content: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        调用 LLM 进行推断，带格式验证和重试（使用上下文修正）
        
        Args:
            sql_content: SQL 内容
            max_retries: 最大重试次数
            
        Returns:
            验证通过的推断结果
        """
        base_prompt = self.prompt_template.format(
            sql_content=sql_content,
            ignore_prefix=self.ignore_prefix
        )
        
        last_error = None
        last_response = None
        validation_errors = []
        
        for attempt in range(max_retries + 1):
            try:
                # 构建带上下文的 prompt
                if attempt == 0:
                    prompt = base_prompt
                else:
                    prompt = self._build_retry_prompt(
                        base_prompt, 
                        last_response, 
                        validation_errors
                    )
                
                response = await self.llm_client.invoke_prompt(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=4000
                )
                last_response = response
                
                # 提取 JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = json.loads(response)
                
                # 验证 JSON 格式
                validation_errors = self._get_validation_errors(data)
                if not validation_errors:
                    logger.info(f"JSON 格式验证通过（第 {attempt + 1} 次尝试）")
                    return data
                else:
                    last_error = f"格式验证失败: {validation_errors}"
                    logger.warning(f"第 {attempt + 1} 次尝试：{last_error}")
            
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {e}"
                validation_errors = [f"返回内容不是有效的 JSON 格式: {e}"]
                logger.warning(f"第 {attempt + 1} 次尝试：{last_error}")
            except Exception as e:
                last_error = f"LLM 调用失败: {e}"
                logger.error(f"第 {attempt + 1} 次尝试：{last_error}")
                break  # 网络错误等不重试
        
        logger.error(f"推断失败，已重试 {max_retries} 次: {last_error}")
        return {"error": last_error}
    
    def _build_retry_prompt(
        self, 
        base_prompt: str, 
        last_response: str, 
        errors: List[str]
    ) -> str:
        """
        构建带上下文的重试 prompt
        
        Args:
            base_prompt: 原始 prompt
            last_response: 上一次的 LLM 响应
            errors: 验证错误列表
            
        Returns:
            包含上下文的重试 prompt
        """
        error_list = "\n".join(f"  - {e}" for e in errors)
        
        retry_context = f"""
## ⚠️ 上次输出格式有误，请修正

### 上次的输出
```
{last_response[:1500] if last_response else "无"}
```

### 格式错误
{error_list}

### 修正要求
请严格按照要求的 JSON 格式重新输出，确保：
1. 所有必填字段都有值（table_name, table_meaning, fields）
2. confidence 必须是 0-1 之间的数字
3. fields 数组不能为空
4. 只输出 JSON，不要包含其他文字

---

"""
        return retry_context + base_prompt
    
    def _get_validation_errors(self, data: Dict[str, Any]) -> List[str]:
        """
        获取 JSON 格式验证错误列表
        
        Args:
            data: LLM 输出的 JSON 数据
            
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        try:
            # 使用 Pydantic 模型验证
            LLMOutputSchema(**data)
            return []  # 验证通过
        except ValidationError as e:
            # 收集详细的验证错误
            for err in e.errors():
                field = '.'.join(str(x) for x in err['loc'])
                msg = err['msg']
                errors.append(f"字段 '{field}': {msg}")
            return errors
        except Exception as e:
            return [f"验证异常: {e}"]
    
    def _validate_output(self, data: Dict[str, Any]) -> bool:
        """
        验证 LLM 输出的 JSON 格式是否符合预期
        
        Args:
            data: LLM 输出的 JSON 数据
            
        Returns:
            是否验证通过
        """
        errors = self._get_validation_errors(data)
        if errors:
            for e in errors:
                logger.warning(e)
            return False
        return True
    
    # ============== Excel 元数据重新推断功能 ==============
    
    def _read_excel_metadata(self, excel_file: str) -> List[Dict[str, Any]]:
        """
        读取 Excel 文件中的表单元数据
        
        Args:
            excel_file: Excel 文件路径
            
        Returns:
            表单元数据列表，每个元素包含 table_name, form_category, form_name
        """
        excel_path = Path(excel_file)
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel 文件不存在: {excel_file}")
        
        # 读取 Excel
        df = pd.read_excel(excel_path)
        
        # 检查必需的列
        required_cols = ['TABLENAME', 'FORMDES', 'NAMELABEL']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Excel 文件缺少必需的列: {missing_cols}")
        
        # 转换为列表
        metadata_list = []
        for _, row in df.iterrows():
            table_name = str(row['TABLENAME']).strip().upper()
            form_category = str(row['FORMDES']).strip() if pd.notna(row['FORMDES']) else ""
            form_name = str(row['NAMELABEL']).strip() if pd.notna(row['NAMELABEL']) else ""
            
            if table_name and table_name != 'NAN':
                metadata_list.append({
                    'table_name': table_name,
                    'form_category': form_category,
                    'form_name': form_name
                })
        
        logger.info(f"从 Excel 读取了 {len(metadata_list)} 条表单元数据")
        return metadata_list
    
    async def infer_with_context(
        self,
        sql_content: str,
        form_category: str,
        form_name: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        带上下文的 LLM 推断
        
        Args:
            sql_content: SQL 内容
            form_category: 表单分类（如 "院前评估"）
            form_name: 表单中文名称（如 "社会参与评估表"）
            max_retries: 最大重试次数
            
        Returns:
            验证通过的推断结果
        """
        # 使用带上下文的提示词模板
        base_prompt = CONTEXT_PROMPT.format(
            sql_content=sql_content,
            ignore_prefix=self.ignore_prefix,
            form_category=form_category or "未分类",
            form_name=form_name or "未命名表单"
        )
        
        last_error = None
        last_response = None
        validation_errors = []
        
        for attempt in range(max_retries + 1):
            try:
                # 构建带上下文的 prompt
                if attempt == 0:
                    prompt = base_prompt
                else:
                    prompt = self._build_retry_prompt(
                        base_prompt, 
                        last_response, 
                        validation_errors
                    )
                
                response = await self.llm_client.invoke_prompt(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=4000
                )
                last_response = response
                
                # 提取 JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = json.loads(response)
                
                # 验证 JSON 格式
                validation_errors = self._get_validation_errors(data)
                if not validation_errors:
                    logger.info(f"JSON 格式验证通过（第 {attempt + 1} 次尝试）")
                    return data
                else:
                    last_error = f"格式验证失败: {validation_errors}"
                    logger.warning(f"第 {attempt + 1} 次尝试：{last_error}")
            
            except json.JSONDecodeError as e:
                last_error = f"JSON 解析失败: {e}"
                validation_errors = [f"返回内容不是有效的 JSON 格式: {e}"]
                logger.warning(f"第 {attempt + 1} 次尝试：{last_error}")
            except Exception as e:
                last_error = f"LLM 调用失败: {e}"
                logger.error(f"第 {attempt + 1} 次尝试：{last_error}")
                break  # 网络错误等不重试
        
        logger.error(f"推断失败，已重试 {max_retries} 次: {last_error}")
        return {"error": last_error}
    
    async def reinfer_from_excel(
        self,
        excel_file: str,
        output_dir: Optional[str] = None,
        sql_dir: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        基于 Excel 元数据批量重新推断表含义
        
        Args:
            excel_file: Excel 文件路径
            output_dir: 输出目录（也是查找现有 JSON 的目录）
            sql_dir: SQL 文件目录
            dry_run: 是否为预览模式（不实际执行）
            
        Returns:
            处理结果统计
        """
        output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        sql_path = Path(sql_dir) if sql_dir else DEFAULT_SQL_DIR
        
        # 读取 Excel 元数据
        metadata_list = self._read_excel_metadata(excel_file)
        
        # 分类统计
        to_process = []
        skipped_no_json = []
        skipped_existing = []
        
        for meta in metadata_list:
            table_name = meta['table_name']
            json_file = output_path / f"{table_name}_meaning.json"
            
            # 检查 JSON 是否存在
            if not json_file.exists():
                skipped_no_json.append(table_name)
                continue
            
            # 检查是否跳过已存在（基于元数据中是否有 form_context 标记）
            if self.skip_existing:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    # 如果已有 form_context 标记，说明已重新推断过
                    if existing_data.get('metadata', {}).get('form_context'):
                        skipped_existing.append(table_name)
                        continue
                except Exception:
                    pass
            
            # 获取 SQL 文件路径
            sql_file = None
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                sql_file_path = existing_data.get('file_path')
                if sql_file_path and Path(sql_file_path).exists():
                    sql_file = Path(sql_file_path)
            except Exception:
                pass
            
            # 如果从 JSON 中没找到，尝试在 sql_dir 中查找
            if not sql_file:
                possible_sql = sql_path / f"{table_name}.sql"
                if possible_sql.exists():
                    sql_file = possible_sql
            
            if sql_file:
                to_process.append({
                    **meta,
                    'json_file': json_file,
                    'sql_file': sql_file
                })
            else:
                logger.warning(f"找不到 SQL 文件: {table_name}")
                skipped_no_json.append(table_name)
        
        # 预览模式
        if dry_run:
            print(f"\n=== 预览模式 ===")
            print(f"总行数: {len(metadata_list)}")
            print(f"将处理: {len(to_process)} 个表")
            print(f"跳过（JSON 不存在）: {len(skipped_no_json)} 个")
            print(f"跳过（已重新推断）: {len(skipped_existing)} 个")
            
            if to_process:
                print(f"\n将处理的表:")
                for item in to_process[:20]:
                    print(f"  - {item['table_name']}: {item['form_name']}")
                if len(to_process) > 20:
                    print(f"  ... 还有 {len(to_process) - 20} 个")
            
            if skipped_no_json:
                print(f"\n跳过的表（JSON 不存在）:")
                for name in skipped_no_json[:10]:
                    print(f"  - {name}")
                if len(skipped_no_json) > 10:
                    print(f"  ... 还有 {len(skipped_no_json) - 10} 个")
            
            return {
                'total': len(metadata_list),
                'to_process': len(to_process),
                'skipped_no_json': len(skipped_no_json),
                'skipped_existing': len(skipped_existing),
                'dry_run': True
            }
        
        # 实际处理
        if not to_process:
            logger.info("没有需要处理的表")
            return {
                'total': len(metadata_list),
                'success': 0,
                'failed': 0,
                'skipped_no_json': len(skipped_no_json),
                'skipped_existing': len(skipped_existing)
            }
        
        logger.info(f"开始处理 {len(to_process)} 个表，并发数: {self.concurrency}")
        
        # 并发处理
        semaphore = asyncio.Semaphore(self.concurrency)
        task_results = await asyncio.gather(
            *[self._process_reinfer_with_semaphore(semaphore, item, output_path)
              for item in to_process],
            return_exceptions=False
        )
        
        # 统计结果
        success_count = 0
        failed_count = 0
        failed_tables = []
        
        for result, error_info in task_results:
            if error_info:
                failed_count += 1
                failed_tables.append(error_info)
            elif result:
                success_count += 1
        
        # 输出报告
        print(f"\n=== 处理完成 ===")
        print(f"总行数: {len(metadata_list)}")
        print(f"成功: {success_count} 个")
        print(f"失败: {failed_count} 个")
        print(f"跳过（JSON 不存在）: {len(skipped_no_json)} 个")
        print(f"跳过（已重新推断）: {len(skipped_existing)} 个")
        
        if failed_tables:
            print(f"\n失败的表:")
            for item in failed_tables[:10]:
                print(f"  - {item['table_name']}: {item['error']}")
        
        if skipped_no_json:
            print(f"\n跳过的表（JSON 不存在）:")
            for name in skipped_no_json[:10]:
                print(f"  - {name}")
            if len(skipped_no_json) > 10:
                print(f"  ... 还有 {len(skipped_no_json) - 10} 个")
        
        return {
            'total': len(metadata_list),
            'success': success_count,
            'failed': failed_count,
            'skipped_no_json': len(skipped_no_json),
            'skipped_existing': len(skipped_existing),
            'failed_tables': failed_tables
        }
    
    async def _process_reinfer_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        item: Dict[str, Any],
        output_path: Path
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        使用信号量控制的单表重新推断
        
        Args:
            semaphore: 并发控制信号量
            item: 包含表信息的字典
            output_path: 输出目录
            
        Returns:
            (推断结果, 错误信息) 元组
        """
        async with semaphore:
            table_name = item['table_name']
            form_category = item['form_category']
            form_name = item['form_name']
            sql_file = item['sql_file']
            json_file = item['json_file']
            
            try:
                # 读取 SQL 内容
                sql_content = sql_file.read_text(encoding='utf-8')
                
                # 带上下文推断
                result = await self.infer_with_context(
                    sql_content=sql_content,
                    form_category=form_category,
                    form_name=form_name
                )
                
                if "error" in result:
                    raise Exception(result["error"])
                
                # 构建完整结果
                full_result = {
                    "file_path": str(sql_file),
                    "table": {
                        "table_name": result.get("table_name", ""),
                        "original_comment": result.get("table_comment"),
                        "inferred_meaning": result.get("table_meaning", {}).get("meaning"),
                        "confidence": result.get("table_meaning", {}).get("confidence"),
                        "reasoning": result.get("table_meaning", {}).get("reasoning"),
                        "fields": [
                            {
                                "field_name": f.get("name", ""),
                                "field_type": f.get("type", ""),
                                "original_comment": f.get("comment"),
                                "inferred_meaning": f.get("meaning"),
                                "confidence": f.get("confidence"),
                                "reasoning": f.get("reasoning")
                            }
                            for f in result.get("fields", [])
                        ]
                    },
                    "metadata": {
                        "processed_at": datetime.now().isoformat(),
                        "llm_model": self.llm_config.model,
                        "llm_provider": self.llm_config.provider,
                        "form_context": {
                            "form_category": form_category,
                            "form_name": form_name
                        }
                    }
                }
                
                # 保存结果
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(full_result, f, ensure_ascii=False, indent=2)
                
                logger.info(f"完成: {table_name} ({form_name})")
                return (full_result, None)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"处理 {table_name} 失败: {error_msg}")
                return (None, {
                    'table_name': table_name,
                    'error': error_msg,
                    'failed_at': datetime.now().isoformat()
                })