from __future__ import annotations

from typing import Any

from nexus_engine.core.ability import Predicate
from nexus_engine.core.value_objects import Tag


class PredicateEvaluator:
    def __init__(self):
        self._handlers: dict[str, Any] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        self._handlers["has_tag"] = self._pred_has_tag
        self._handlers["has_resource"] = self._pred_has_resource
        self._handlers["in_location"] = self._pred_in_location
        self._handlers["entity_has_property"] = self._pred_entity_property
        self._handlers["time_elapsed"] = self._pred_time_elapsed
        self._handlers["relationship_above"] = self._pred_relationship
        self._handlers["and"] = self._pred_and
        self._handlers["or"] = self._pred_or
        self._handlers["not"] = self._pred_not
        self._handlers["compare_property"] = self._pred_compare_property

    def evaluate(
        self, predicate: Predicate, world_state: Any, context: dict[str, Any]
    ) -> bool:
        handler = self._handlers.get(predicate.type)
        if not handler:
            raise ValueError(f"Unknown predicate type: {predicate.type}")
        return handler(predicate.params, world_state, context)

    def _pred_has_tag(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity = context.get("entity")
        if not entity:
            return False
        tag = Tag(namespace=params["namespace"], value=params["value"])
        return entity.has_tag(tag)

    def _pred_has_resource(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity = context.get("entity")
        if not entity:
            return False
        pool_id = params["pool_id"]
        required = params.get("amount", 1)
        current = entity.properties.get("resources", {}).get(pool_id, 0)
        return current >= required

    def _pred_in_location(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity = context.get("entity")
        if not entity:
            return False
        current_location = context.get("location_id")
        required_location = params["location_id"]
        return str(current_location) == str(required_location)

    def _pred_entity_property(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity = context.get("entity")
        if not entity:
            return False
        prop_path = params["path"]
        expected = params["value"]
        actual = entity.get_property(prop_path)
        return actual == expected

    def _pred_time_elapsed(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        game_time = context.get("game_time")
        if not game_time:
            return False
        min_ticks = params.get("min_ticks", 0)
        return game_time.ticks >= min_ticks

    def _pred_relationship(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity_a = context.get("entity")
        entity_b_id = params.get("entity_b_id")
        min_value = params.get("min_value", 0)
        relationship_type = params.get("type", "trust")

        if not entity_a or not entity_b_id:
            return False

        relationship = world_state.get_relationship(entity_a.id, entity_b_id)
        if not relationship:
            return False

        value = getattr(relationship, relationship_type, 0)
        return value >= min_value

    def _pred_and(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        predicates = params.get("predicates", [])
        return all(self.evaluate(p, world_state, context) for p in predicates)

    def _pred_or(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        predicates = params.get("predicates", [])
        return any(self.evaluate(p, world_state, context) for p in predicates)

    def _pred_not(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        predicate = params.get("predicate")
        if not predicate:
            return True
        return not self.evaluate(predicate, world_state, context)

    def _pred_compare_property(
        self, params: dict[str, Any], world_state: Any, context: dict[str, Any]
    ) -> bool:
        entity = context.get("entity")
        if not entity:
            return False

        prop_path = params["path"]
        operator = params.get("operator", "eq")
        value = params.get("value")

        actual = entity.get_property(prop_path)
        if actual is None:
            return False

        match operator:
            case "eq":
                return actual == value
            case "ne":
                return actual != value
            case "gt":
                return actual > value
            case "gte":
                return actual >= value
            case "lt":
                return actual < value
            case "lte":
                return actual <= value
            case _:
                return False


_default_evaluator: PredicateEvaluator | None = None


def get_default_evaluator() -> PredicateEvaluator:
    global _default_evaluator
    if _default_evaluator is None:
        _default_evaluator = PredicateEvaluator()
    return _default_evaluator
