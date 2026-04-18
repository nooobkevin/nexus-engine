from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nexus_engine.core.ability import RulingDraft, Rule
from nexus_engine.core.value_objects import GameTime


@dataclass
class RulingObservation:
    ruling: RulingDraft
    outcome: Any
    timestamp: GameTime


@dataclass
class CrystallizationCandidate:
    pattern_description: str
    occurrences: int
    consistency_score: float
    sample_rulings: list[RulingObservation]


@dataclass
class CrystallizerConfig:
    threshold: int = 10
    min_consistency: float = 0.8


class Crystallizer:
    def __init__(self, config: CrystallizerConfig | None = None):
        self.config = config or CrystallizerConfig()
        self._observations: list[RulingObservation] = []
        self._pattern_groups: dict[str, list[RulingObservation]] = {}

    def observe(
        self,
        ruling: RulingDraft,
        outcome: Any,
        game_time: GameTime,
    ) -> None:
        observation = RulingObservation(ruling, outcome, game_time)
        self._observations.append(observation)

        pattern_key = self._extract_pattern_key(ruling)
        if pattern_key:
            if pattern_key not in self._pattern_groups:
                self._pattern_groups[pattern_key] = []
            self._pattern_groups[pattern_key].append(observation)

    def _extract_pattern_key(self, ruling: RulingDraft) -> str:
        return f"{ruling.difficulty_tier.value}_{ruling.plausibility:.1f}"

    def extract_candidates(self) -> list[CrystallizationCandidate]:
        candidates = []

        for pattern_key, observations in self._pattern_groups.items():
            if len(observations) >= self.config.threshold:
                consistency = self._calculate_consistency(observations)
                if consistency > self.config.min_consistency:
                    candidates.append(CrystallizationCandidate(
                        pattern_description=pattern_key,
                        occurrences=len(observations),
                        consistency_score=consistency,
                        sample_rulings=observations[-10:],
                    ))

        return candidates

    def _calculate_consistency(self, observations: list[RulingObservation]) -> float:
        if not observations:
            return 0.0

        outcomes = [o.outcome.success if hasattr(o.outcome, 'success') else True for o in observations]
        if not outcomes:
            return 0.0

        success_count = sum(1 for o in outcomes if o)
        return success_count / len(outcomes)

    async def crystallize(
        self,
        candidate: CrystallizationCandidate,
        validator: Any | None = None,
        rule_engine: Any | None = None,
    ) -> Rule | None:

        generalized = self._generalize_pattern(candidate)

        if validator:
            result = await validator.validate_rule(generalized)
            if result.failed:
                return None

        if rule_engine:
            rule_engine.register_rule(generalized)

        return generalized

    def _generalize_pattern(self, candidate: CrystallizationCandidate) -> Rule:
        common_tags = set()
        common_action_types = set()

        for obs in candidate.sample_rulings:
            ruling = obs.ruling
            common_action_types.add(ruling.difficulty_tier.value)

        from nexus_engine.core.ability import MatchPattern

        pattern = MatchPattern(
            action_types=frozenset(common_action_types),
            tags=frozenset(),
            context_conditions=frozenset(),
        )

        return Rule.create(
            pattern=pattern,
            resolver="crystallized_effect",
            priority=50,
            source="CRYSTALLIZED",
            params={"candidate": candidate.pattern_description},
        )
