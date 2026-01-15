# -*- coding: utf-8 -*-
"""
OpenSpec 验证器（最小可用版）

提供：
- 检查必需文件是否存在
- 可选调用 openspec-cn validate
- 基础 spec 格式检查（至少包含一个 #### 场景：）
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .client import OpenSpecClient, CommandResult
from ..logging.logger import get_logger

logger = get_logger("openspec.validator")


@dataclass(frozen=True)
class ValidationResult:
    success: bool
    errors: List[str]
    cli: Optional[CommandResult] = None


class OpenSpecValidator:
    def __init__(self, client: OpenSpecClient, openspec_root: str = "openspec") -> None:
        self.client = client
        self.openspec_root = Path(openspec_root)

    def check_required_files(self, change_id: str) -> List[str]:
        """
        检查变更目录下必需文件是否存在：
        - proposal.md
        - tasks.md
        - specs/ 下至少一个 .md
        """

        missing: List[str] = []
        change_dir = self.openspec_root / "changes" / change_id
        if not change_dir.exists():
            return [f"变更目录不存在: {change_dir}"]

        if not (change_dir / "proposal.md").exists():
            missing.append("proposal.md")
        if not (change_dir / "tasks.md").exists():
            missing.append("tasks.md")

        specs_dir = change_dir / "specs"
        spec_files = list(specs_dir.rglob("*.md")) if specs_dir.exists() else []
        if not spec_files:
            missing.append("specs/**/*.md")

        return missing

    async def validate_proposal(self, change_id: str, strict: bool = True) -> ValidationResult:
        errors: List[str] = []

        missing = self.check_required_files(change_id)
        if missing:
            errors.extend([f"缺少必需文件: {m}" for m in missing])

        cli_result: Optional[CommandResult] = None
        try:
            cli_result = await self.client.validate_change(change_id, strict=strict)
            if not cli_result.success:
                errors.append(cli_result.stderr.strip() or cli_result.stdout.strip() or "openspec-cn validate 失败")
        except Exception as e:
            errors.append(f"调用 openspec-cn validate 失败: {e}")

        return ValidationResult(success=(len(errors) == 0), errors=errors, cli=cli_result)

    def validate_spec_format(self, spec_path: str) -> bool:
        """
        基础格式校验：
        - 至少包含一个 '#### 场景：'
        """

        text = Path(spec_path).read_text(encoding="utf-8", errors="ignore")
        return "#### 场景：" in text

