from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, FrozenSet, Optional

from nexus_engine.core.value_objects import (
    AbilityId,
    RuleId,
    Tag,
    TierLevel,
    new_rule_id,
)


@dataclass(frozen=True)
class ResourceCost:
    pool_id: str
    amount: int


@dataclass(frozen=True)
class Predicate:
    type: str
    params: dict[str, Any]

    def evaluate(self, world_state: Any, context: Any) -> bool:
        return True


@dataclass(frozen=True)
class TargetingRule:
    range: str
    constraints: FrozenSet[Predicate] = field(default_factory=frozenset)


@dataclass(frozen=True)
class EffectTemplate:
    effect_type: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class Ability:
    id: AbilityId
    archetype: str
    targeting: TargetingRule
    costs: FrozenSet[ResourceCost] = field(default_factory=frozenset)
    requirements: FrozenSet[Predicate] = field(default_factory=frozenset)
    effect_chain: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    failure_branch: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    tier: TierLevel = TierLevel.MUNDANE

    def meets_requirements(self, actor: Any, world_state: Any) -> bool:
        for req in self.requirements:
            if not req.evaluate(world_state, {"actor": actor}):
                return False
        return True

    def can_afford(self, entity: Any) -> bool:
        for cost in self.costs:
            pool_value = entity.properties.get("resources", {}).get(cost.pool_id, 0)
            if pool_value < cost.amount:
                return False
        return True


@dataclass(frozen=True)
class MatchPattern:
    action_types: FrozenSet[str] = field(default_factory=frozenset)
    tags: FrozenSet[Tag] = field(default_factory=frozenset)
    context_conditions: FrozenSet[Predicate] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Rule:
    id: RuleId
    pattern: MatchPattern
    resolver: str
    priority: int = 50
    source: str = "CORE"
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        pattern: MatchPattern,
        resolver: str,
        priority: int = 50,
        source: str = "CORE",
        params: Optional[dict[str, Any]] = None,
    ) -> Rule:
        return cls(
            id=new_rule_id(),
            pattern=pattern,
            resolver=resolver,
            priority=priority,
            source=source,
            params=params or {},
        )


class DifficultyTier(str, Enum):
    TRIVIAL = "trivial"
    EASY = "easy"
    AVERAGE = "average"
    HARD = "hard"
    EXTREME = "extreme"
    HEROIC = "heroic"

    @classmethod
    def from_dc(cls, dc: int) -> DifficultyTier:
        if dc <= 5:
            return cls.TRIVIAL
        elif dc <= 10:
            return cls.EASY
        elif dc <= 15:
            return cls.AVERAGE
        elif dc <= 20:
            return cls.HARD
        elif dc <= 30:
            return cls.EXTREME
        else:
            return cls.HEROIC


@dataclass(frozen=True)
class CheckFormula:
    attribute: str
    skill: Optional[str] = None
    difficulty: DifficultyTier = DifficultyTier.AVERAGE
    roll_modifier: int = 0

    def dc(self) -> int:
        dc_map = {
            DifficultyTier.TRIVIAL: 5,
            DifficultyTier.EASY: 10,
            DifficultyTier.AVERAGE: 15,
            DifficultyTier.HARD: 20,
            DifficultyTier.EXTREME: 25,
            DifficultyTier.HEROIC: 30,
        }
        return dc_map.get(self.difficulty, 15)


@dataclass(frozen=True)
class RulingDraft:
    plausibility: float
    reasoning: str
    difficulty_tier: DifficultyTier
    resource_costs: dict[str, int] = field(default_factory=dict)
    prerequisites: FrozenSet[Predicate] = field(default_factory=frozenset)
    check_formula: Optional[CheckFormula] = None
    success_effects: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    failure_effects: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    side_effects: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    novelty_score: float = 0.0
    referenced_entities: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Outcome:
    success: bool
    degree: float
    mechanics: Any
    effects: FrozenSet[EffectTemplate] = field(default_factory=frozenset)
    narrative: str = ""
