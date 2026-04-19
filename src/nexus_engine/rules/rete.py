from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AlphaNode:
    pattern: str
    condition: Callable[[dict[str, Any]], bool]
    matched_entities: set[str] = field(default_factory=set)


@dataclass
class BetaNode:
    left_input: AlphaNode | BetaNode
    right_input: AlphaNode | BetaNode
    join_condition: Callable[[set[str], set[str]], set[str]]
    joined_entities: set[str] = field(default_factory=set)


@dataclass
class ProductionRule:
    id: str
    name: str
    alpha_nodes: list[AlphaNode]
    beta_nodes: list[BetaNode]
    action: Callable[[dict[str, Any]], Any]
    priority: int = 50


@dataclass
class ReteNetwork:
    alpha_nodes: dict[str, AlphaNode] = field(default_factory=dict)
    beta_nodes: dict[str, BetaNode] = field(default_factory=dict)
    production_rules: list[ProductionRule] = field(default_factory=list)
    terminal_nodes: list[tuple[ProductionRule, set[str]]] = field(default_factory=list)

    _fact_store: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_production(self, rule: ProductionRule) -> None:
        self.production_rules.append(rule)
        for alpha in rule.alpha_nodes:
            if alpha.pattern not in self.alpha_nodes:
                self.alpha_nodes[alpha.pattern] = alpha
            else:
                existing = self.alpha_nodes[alpha.pattern]
                existing.matched_entities |= alpha.matched_entities

    def assert_fact(self, entity_id: str, fact: dict[str, Any]) -> list[Any]:
        self._fact_store[entity_id] = fact
        return self._propagate_assertion(entity_id, fact)

    def retract_fact(self, entity_id: str) -> list[Any]:
        if entity_id in self._fact_store:
            del self._fact_store[entity_id]
        return self._propagate_retraction(entity_id)

    def modify_fact(self, entity_id: str, fact: dict[str, Any]) -> list[Any]:
        self._fact_store[entity_id] = fact
        return self._propagate_modification(entity_id, fact)

    def _propagate_assertion(self, entity_id: str, fact: dict[str, Any]) -> list[Any]:
        triggered = []

        for rule in self.production_rules:
            if self._matches_rule(rule, entity_id, fact):
                result = rule.action(
                    {"entity_id": entity_id, "fact": fact, "store": self._fact_store}
                )
                if result:
                    triggered.append(result)

        return triggered

    def _propagate_retraction(self, entity_id: str) -> list[Any]:
        return []

    def _propagate_modification(
        self, entity_id: str, fact: dict[str, Any]
    ) -> list[Any]:
        return self._propagate_assertion(entity_id, fact)

    def _matches_rule(
        self, rule: ProductionRule, entity_id: str, fact: dict[str, Any]
    ) -> bool:
        for alpha in rule.alpha_nodes:
            if not alpha.condition(fact):
                return False
        return True

    def fire_rules(self) -> list[Any]:
        results = []
        for rule in self.production_rules:
            for entity_id, fact in self._fact_store.items():
                if self._matches_rule(rule, entity_id, fact):
                    result = rule.action(
                        {
                            "entity_id": entity_id,
                            "fact": fact,
                            "store": self._fact_store,
                        }
                    )
                    if result:
                        results.append(result)
        return results


class ReteBuilder:
    def __init__(self):
        self._alpha_patterns: dict[str, Callable[[dict[str, Any]], bool]] = {}

    def register_alpha_pattern(
        self,
        pattern_name: str,
        condition: Callable[[dict[str, Any]], bool],
    ) -> None:
        self._alpha_patterns[pattern_name] = condition

    def build_rule(
        self,
        rule_id: str,
        name: str,
        patterns: list[str],
        action: Callable[[dict[str, Any]], Any],
        priority: int = 50,
    ) -> ProductionRule:
        alpha_nodes = []
        for pattern_name in patterns:
            if pattern_name in self._alpha_patterns:
                alpha_nodes.append(
                    AlphaNode(
                        pattern=pattern_name,
                        condition=self._alpha_patterns[pattern_name],
                    )
                )

        return ProductionRule(
            id=rule_id,
            name=name,
            alpha_nodes=alpha_nodes,
            beta_nodes=[],
            action=action,
            priority=priority,
        )

    def build_network(self) -> ReteNetwork:
        return ReteNetwork()


STANDARD_PATTERNS: dict[str, Callable[[dict[str, Any]], bool]] = {}


def register_pattern(name: str, condition: Callable[[dict[str, Any]], bool]) -> None:
    STANDARD_PATTERNS[name] = condition


register_pattern("has_tag_fire", lambda f: f.get("tags", {}).get("element") == "fire")
register_pattern("has_tag_water", lambda f: f.get("tags", {}).get("element") == "water")
register_pattern(
    "has_tag_hostile", lambda f: f.get("tags", {}).get("social") == "hostile"
)
register_pattern(
    "has_tag_friendly", lambda f: f.get("tags", {}).get("social") == "friendly"
)
register_pattern("is_alive", lambda f: f.get("properties", {}).get("hp", 0) > 0)
register_pattern("is_dead", lambda f: f.get("properties", {}).get("hp", 0) <= 0)
register_pattern("has_resource", lambda f: f.get("resources", {}).get("qi", 0) > 0)
