# -*- coding: utf-8 -*-
"""
OpenSpec 集成模块测试（单元测试为主，避免依赖本机 openspec-cn）。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from src.openspec.client import OpenSpecClient, CommandResult
from src.openspec.parser import OpenSpecParser
from src.openspec.generator import OpenSpecGenerator
from src.openspec.validator import OpenSpecValidator
from src.openspec.manager import OpenSpecManager, ProposalStub


class TestOpenSpecParser:
    def test_parse_tasks(self, temp_dir):
        tasks = temp_dir / "tasks.md"
        tasks.write_text(
            "\n".join(
                [
                    "# tasks",
                    "- [x] 1.1 done",
                    "- [ ] 1.2 todo",
                    "  - [ ] 1.2.1 sub",
                ]
            ),
            encoding="utf-8",
        )

        parser = OpenSpecParser()
        parsed = parser.parse_tasks(str(tasks))
        assert len(parsed) == 3
        assert parsed[0].checked is True
        assert parsed[1].checked is False


class TestOpenSpecGenerator:
    def test_check_conflicts(self, temp_dir):
        # 构造 openspec root
        root = temp_dir / "openspec"
        (root / "changes").mkdir(parents=True)

        # other change has specs/auth/spec.md
        other = root / "changes" / "other-change"
        (other / "specs" / "auth").mkdir(parents=True)
        (other / "specs" / "auth" / "spec.md").write_text("## 新增需求\n", encoding="utf-8")

        gen = OpenSpecGenerator(openspec_root=str(root))
        conflicts = gen.check_conflicts("new-change", ["specs/auth/spec.md"])
        assert len(conflicts) == 1
        assert conflicts[0].other_change_id == "other-change"


class TestOpenSpecValidator:
    @pytest.mark.asyncio
    async def test_validate_proposal_without_cli(self, temp_dir, mocker):
        root = temp_dir / "openspec"
        change_id = "c1"
        change_dir = root / "changes" / change_id
        (change_dir / "specs" / "x").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# p\n", encoding="utf-8")
        (change_dir / "tasks.md").write_text("- [ ] 1.1 a\n", encoding="utf-8")
        (change_dir / "specs" / "x" / "spec.md").write_text("#### 场景：a\n", encoding="utf-8")

        client = OpenSpecClient(working_dir=str(temp_dir))
        mocker.patch.object(
            client,
            "validate_change",
            new=mocker.AsyncMock(return_value=CommandResult(True, "", "", 0)),
        )

        v = OpenSpecValidator(client=client, openspec_root=str(root))
        res = await v.validate_proposal(change_id, strict=True)
        assert res.success is True
        assert res.errors == []


class TestOpenSpecManager:
    def test_track_progress(self, temp_dir):
        root = temp_dir / "openspec"
        change_id = "c2"
        change_dir = root / "changes" / change_id
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text("- [x] a\n- [ ] b\n", encoding="utf-8")

        m = OpenSpecManager(openspec_root=str(root))
        info = m.track_progress(change_id)
        assert info["total"] == 2
        assert info["done"] == 1

    def test_create_proposal_plan(self):
        m = OpenSpecManager(openspec_root="openspec")
        a = ProposalStub(change_id="a", description="a")
        b = ProposalStub(change_id="b", description="b", depends_on=["a"])
        plan = m.create_proposal_plan([b, a])
        assert [p.change_id for p in plan.ordered][:2] == ["a", "b"]

