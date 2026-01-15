# -*- coding: utf-8 -*-
"""
OpenSpec CLI 客户端封装

封装 openspec-cn 命令调用，提供 list/show/validate/archive 等能力。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logging.logger import get_logger

logger = get_logger("openspec.client")


@dataclass(frozen=True)
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


class OpenSpecClient:
    """OpenSpec CLI 客户端封装"""

    def __init__(
        self,
        openspec_dir: str = "openspec",
        cli_path: str = "openspec-cn",
        working_dir: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.openspec_dir = openspec_dir
        self.cli_path = cli_path
        self.timeout = timeout
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    async def _run(self, args: List[str]) -> CommandResult:
        cmd = [self.cli_path, *args]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.working_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"OpenSpec CLI 不可用: {self.cli_path}") from e

        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"OpenSpec CLI 执行超时（{self.timeout}s）：{' '.join(cmd)}")

        stdout = (stdout_b or b"").decode("utf-8", errors="ignore")
        stderr = (stderr_b or b"").decode("utf-8", errors="ignore")
        rc = proc.returncode or 0
        return CommandResult(success=(rc == 0), stdout=stdout, stderr=stderr, return_code=rc)

    def _parse_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except Exception:
            return None

    async def list_changes(self) -> List[Dict[str, Any]]:
        """列出活动变更（尽量使用 --json 输出）。"""

        # 兼容旧版本 openspec-cn：可能不支持 --json
        result = await self._run(["list", "--json"])
        if result.success:
            data = self._parse_json(result.stdout.strip())
            return data if isinstance(data, list) else []

        if "unknown option '--json'" in (result.stderr or ""):
            fallback = await self._run(["list"])
            if not fallback.success:
                logger.warning(f"list_changes 失败: {fallback.stderr.strip()}")
                return []
            lines = [ln.strip() for ln in fallback.stdout.splitlines() if ln.strip()]
            return [{"raw": ln} for ln in lines]

        logger.warning(f"list_changes 失败: {result.stderr.strip()}")
        return []

    async def list_specs(self) -> List[Dict[str, Any]]:
        """列出规范（尽量使用 --json 输出）。"""

        result = await self._run(["list", "--specs", "--json"])
        if result.success:
            data = self._parse_json(result.stdout.strip())
            return data if isinstance(data, list) else []

        if "unknown option '--json'" in (result.stderr or ""):
            fallback = await self._run(["list", "--specs"])
            if not fallback.success:
                logger.warning(f"list_specs 失败: {fallback.stderr.strip()}")
                return []
            lines = [ln.strip() for ln in fallback.stdout.splitlines() if ln.strip()]
            return [{"raw": ln} for ln in lines]

        logger.warning(f"list_specs 失败: {result.stderr.strip()}")
        return []

    async def show_change(self, change_id: str, deltas_only: bool = False) -> Dict[str, Any]:
        """显示变更详情。"""

        args = ["show", change_id, "--json"]
        if deltas_only:
            args.append("--deltas-only")

        result = await self._run(args)
        if not result.success:
            raise RuntimeError(f"show_change 失败: {result.stderr.strip() or result.stdout.strip()}")

        data = self._parse_json(result.stdout.strip())
        return data if isinstance(data, dict) else {}

    async def validate_change(self, change_id: str, strict: bool = True) -> CommandResult:
        """验证变更提案（返回原始命令结果）。"""

        args = ["validate", change_id]
        if strict:
            args.append("--strict")
        return await self._run(args)

    async def archive_change(self, change_id: str, skip_specs: bool = False) -> CommandResult:
        """归档变更（默认带 --yes，避免交互）。"""

        args = ["archive", change_id, "--yes"]
        if skip_specs:
            args.append("--skip-specs")
        return await self._run(args)

