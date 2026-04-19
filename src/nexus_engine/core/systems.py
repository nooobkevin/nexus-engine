from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator, TypeVar

from nexus_engine.core.entity import Entity
from nexus_engine.core.tag_index import TagInvertedIndex


T = TypeVar("T")


@dataclass
class ComponentQuery:
    required_tags: list[str] | None = None
    excluded_tags: list[str] | None = None
    property_conditions: dict[str, Any] | None = None


class WorldState:
    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.tag_index = TagInvertedIndex()
        self._archetypes: dict[str, list[str]] = {}

    def add_entity(self, entity: Entity) -> None:
        self.entities[str(entity.id)] = entity
        tag_strs = [str(t) for t in entity.tags]
        self.tag_index.add_entity(str(entity.id), frozenset(tag_strs))

    def remove_entity(self, entity_id: str) -> None:
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.tag_index.remove_entity(entity_id)

    def get_entity(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def query(self, query: ComponentQuery) -> Iterator[Entity]:
        entity_ids = self.tag_index.search(
            tags_and=query.required_tags,
            tags_none=query.excluded_tags,
        )

        for entity_id in entity_ids:
            entity = self.entities.get(entity_id)
            if entity is None:
                continue

            if query.property_conditions:
                if not self._check_property_conditions(
                    entity, query.property_conditions
                ):
                    continue

            yield entity

    def _check_property_conditions(
        self, entity: Entity, conditions: dict[str, Any]
    ) -> bool:
        for path, expected in conditions.items():
            actual = entity.get_property(path)
            if isinstance(expected, str) and expected.startswith(">="):
                if not (actual is not None and actual >= float(expected[2:])):
                    return False
            elif isinstance(expected, str) and expected.startswith("<="):
                if not (actual is not None and actual <= float(expected[2:])):
                    return False
            elif isinstance(expected, str) and expected.startswith(">"):
                if not (actual is not None and actual > float(expected[1:])):
                    return False
            elif isinstance(expected, str) and expected.startswith("<"):
                if not (actual is not None and actual < float(expected[1:])):
                    return False
            elif isinstance(expected, str) and expected.startswith("!="):
                if actual == expected[2:]:
                    return False
            elif actual != expected:
                return False
        return True

    def query_by_archetype(self, archetype_id: str) -> Iterator[Entity]:
        required = self._archetypes.get(archetype_id, [])
        query = ComponentQuery(required_tags=required if required else None)
        yield from self.query(query)

    def register_archetype(self, archetype_id: str, required_tags: list[str]) -> None:
        self._archetypes[archetype_id] = required_tags

    def update_entity_tags(self, entity_id: str, tags: frozenset[str]) -> None:
        if entity_id in self.entities:
            self.tag_index.update_entity_tags(entity_id, tags)


class System(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def query(self) -> ComponentQuery:
        return ComponentQuery()

    @abstractmethod
    def update(self, world: WorldState, dt: float) -> list[Any]:
        pass


class MovementSystem(System):
    name = "movement"

    @property
    def query(self) -> ComponentQuery:
        return ComponentQuery(
            required_tags=["position", "velocity"],
        )

    def update(self, world: WorldState, dt: float) -> list[Any]:
        events = []
        for entity in world.query(self.query):
            pos = entity.get_property("position", {"x": 0, "y": 0, "z": 0})
            vel = entity.get_property("velocity", {"x": 0, "y": 0, "z": 0})

            new_pos = {
                "x": pos.get("x", 0) + vel.get("x", 0) * dt,
                "y": pos.get("y", 0) + vel.get("y", 0) * dt,
                "z": pos.get("z", 0) + vel.get("z", 0) * dt,
            }

            world.entities[str(entity.id)].properties["position"] = new_pos
            events.append(
                {"type": "moved", "entity": str(entity.id), "position": new_pos}
            )

        return events


class HealthSystem(System):
    name = "health"

    @property
    def query(self) -> ComponentQuery:
        return ComponentQuery(required_tags=["health"])

    def update(self, world: WorldState, dt: float) -> list[Any]:
        events = []
        for entity in world.query(self.query):
            hp = entity.get_property("hp", 0)
            max_hp = entity.get_property("max_hp", 100)

            if hp <= 0 and not entity.has_tag_namespace("dead"):
                world.update_entity_tags(
                    str(entity.id), frozenset(str(t) for t in entity.tags) | frozenset(["dead"])
                )
                events.append({"type": "died", "entity": str(entity.id)})

            if hp > max_hp:
                world.entities[str(entity.id)].properties["hp"] = max_hp

        return events


class ResourceSystem(System):
    name = "resource"

    @property
    def query(self) -> ComponentQuery:
        return ComponentQuery(required_tags=["resource_pool"])

    def update(self, world: WorldState, dt: float) -> list[Any]:
        events = []
        for entity in world.query(self.query):
            resources = entity.get_property("resources", {})
            for resource_id, amount in resources.items():
                max_amount = entity.get_property(f"max_{resource_id}", 100)
                if amount > max_amount:
                    resources[resource_id] = max_amount
                    events.append(
                        {
                            "type": "resource_capped",
                            "entity": str(entity.id),
                            "resource": resource_id,
                        }
                    )
        return events


class SystemManager:
    def __init__(self, world: WorldState):
        self.world = world
        self.systems: list[System] = []
        self._system_by_name: dict[str, System] = {}

    def register_system(self, system: System) -> None:
        self.systems.append(system)
        self._system_by_name[system.name] = system

    def get_system(self, name: str) -> System | None:
        return self._system_by_name.get(name)

    def tick(self, dt: float) -> list[Any]:
        all_events = []
        for system in self.systems:
            events = system.update(self.world, dt)
            all_events.extend(events)
        return all_events
