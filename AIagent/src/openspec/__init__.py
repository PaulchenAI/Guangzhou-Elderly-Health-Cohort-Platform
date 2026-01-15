# -*- coding: utf-8 -*-
"""OpenSpec 集成模块"""

from .client import OpenSpecClient, CommandResult
from .parser import OpenSpecParser, ParsedTask
from .generator import OpenSpecGenerator, Conflict
from .validator import OpenSpecValidator, ValidationResult
from .manager import OpenSpecManager, ProposalStub, ProposalPlan

__all__ = [
    "OpenSpecClient",
    "CommandResult",
    "OpenSpecParser",
    "ParsedTask",
    "OpenSpecGenerator",
    "Conflict",
    "OpenSpecValidator",
    "ValidationResult",
    "OpenSpecManager",
    "ProposalStub",
    "ProposalPlan",
]

