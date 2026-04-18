from __future__ import annotations

from typing import Any

from nexus_engine.core.ability import (
    CheckFormula,
    Outcome,
    Rule,
)
from nexus_engine.core.entity import Entity
from nexus_engine.core.value_objects import Tag


class RuleEngine:
    def __init__(self):
        self._exact_rules: dict[str, Rule] = {}
        self._tag_rules: list[Rule] = []
        self._setting_rules: list[Rule] = []
        self._resolvers: dict[str, Any] = {}

    def register_resolver(self, name: str, resolver: Any) -> None:
        self._resolvers[name] = resolver

    def register_rule(self, rule: Rule) -> None:
        if rule.source == "CORE" and not rule.pattern.tags:
            for action_type in rule.pattern.action_types:
                self._exact_rules[action_type] = rule
        elif rule.source == "SETTING_PACK":
            self._setting_rules.append(rule)
        else:
            self._tag_rules.append(rule)
        self._tag_rules.sort(key=lambda r: r.priority, reverse=True)

    def match_exact(self, action_type: str) -> Rule | None:
        return self._exact_rules.get(action_type)

    def match_by_tags(self, tags: frozenset[Tag]) -> Rule | None:
        best_match: Rule | None = None
        best_score = 0

        for rule in self._tag_rules:
            score = self._calculate_tag_affinity(tags, rule.pattern.tags)
            if score > best_score and score > 0.5:
                best_score = score
                best_match = rule

        return best_match

    def _calculate_tag_affinity(
        self, entity_tags: frozenset[Tag], rule_tags: frozenset[Tag]
    ) -> float:
        if not rule_tags:
            return 0.0
        matches = sum(1 for tag in entity_tags if tag in rule_tags)
        return matches / len(rule_tags)

    def resolve(
        self,
        rule: Rule,
        actor: Entity,
        target: Entity | None,
        context: dict[str, Any],
    ) -> Outcome:
        resolver = self._resolvers.get(rule.resolver)
        if not resolver:
            return Outcome(
                success=False,
                degree=0.0,
                mechanics=None,
                effects=frozenset(),
                narrative=f"No resolver found for rule: {rule.resolver}",
            )
        return resolver(actor, target, context, rule.params)

    def get_applicable_rules(
        self,
        actor: Entity,
        action_tags: list[Tag],
    ) -> list[Rule]:
        applicable = []
        action_tag_set = frozenset(action_tags)

        for rule in self._tag_rules:
            if self._calculate_tag_affinity(action_tag_set, rule.pattern.tags) > 0.3:
                applicable.append(rule)

        for rule in self._setting_rules:
            if self._calculate_tag_affinity(action_tag_set, rule.pattern.tags) > 0.3:
                applicable.append(rule)

        return sorted(applicable, key=lambda r: r.priority, reverse=True)


async def resolve_action(
    engine: RuleEngine,
    action_type: str,
    actor: Entity,
    target: Entity | None,
    context: dict[str, Any],
) -> Outcome:
    rule = engine.match_exact(action_type)
    if not rule:
        rule = engine.match_by_tags(frozenset(context.get("tags", [])))
    if not rule:
        return Outcome(
            success=False,
            degree=0.0,
            mechanics=None,
            effects=frozenset(),
            narrative="No applicable rule found for this action.",
        )
    return engine.resolve(rule, actor, target, context)


async def resolve_check(
    actor: Entity,
    formula: CheckFormula,
    context: dict[str, Any],
) -> Outcome:
    import random

    roll = random.randint(1, 20)
    modifier = formula.roll_modifier + context.get("modifier", 0)
    total = roll + modifier
    dc = formula.dc()
    success = total >= dc
    degree = max(0.0, min(1.0, (total - dc + 5) / 10))

    from nexus_engine.core.event import MechanicsResult

    mechanics = MechanicsResult(
        success=success,
        degree=degree,
        roll=roll,
        difficulty=dc,
        values={"modifier": modifier, "total": total, "dc": dc},
    )

    return Outcome(
        success=success,
        degree=degree,
        mechanics=mechanics,
        effects=frozenset(),
        narrative=f"Roll: {roll} + {modifier} = {total} vs DC {dc} ({'Success' if success else 'Failure'})",
    )
