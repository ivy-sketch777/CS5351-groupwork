from dataclasses import dataclass, field
from typing import List

from src.schemas import PolicyResult


@dataclass
class Rule:
    id: str
    priority: int
    description: str
    condition: str
    action: PolicyResult
    reason: str
    add_missing: List[str] = field(default_factory=list)
    set_overlap: bool = False


@dataclass
class RuleSet:
    version: str
    rules: List[Rule] = field(default_factory=list)
