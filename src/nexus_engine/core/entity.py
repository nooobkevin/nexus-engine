from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, List, Optional

from nexus_engine.core.value_objects import (
    ArchetypeId,
    EntityId,
    GameTime,
    SourceRef,
    Tag,
)


@dataclass(frozen=True)
class Observation:
    content: str
    source: SourceRef
    confidence: float
    timestamp: GameTime


@dataclass(frozen=True)
class Entity:
    id: EntityId
    archetype: ArchetypeId
    tags: FrozenSet[Tag] = field(default_factory=frozenset)
    properties: dict[str, Any] = field(default_factory=dict)
    observations: List["Observation"] = field(default_factory=list)
    created_at: GameTime = field(default_factory=lambda: GameTime(0))
    canon_locked: bool = False

    def add_observation(self, observation: Observation) -> Entity:
        if self.canon_locked:
            raise ValueError("Cannot add observation to canon-locked entity")
        return Entity(
            id=self.id,
            archetype=self.archetype,
            tags=self.tags,
            properties=self.properties,
            observations=[*self.observations, observation],
            created_at=self.created_at,
            canon_locked=self.canon_locked,
        )

    def get_property(self, path: str, default: Any = None) -> Any:
        keys = path.split(".")
        value = self.properties
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def with_property(self, path: str, value: Any) -> Entity:
        keys = path.split(".")
        new_props = dict(self.properties)
        current = new_props
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        return Entity(
            id=self.id,
            archetype=self.archetype,
            tags=self.tags,
            properties=new_props,
            observations=self.observations,
            created_at=self.created_at,
            canon_locked=self.canon_locked,
        )

    def has_tag(self, tag: Tag) -> bool:
        return tag in self.tags

    def has_tag_namespace(self, namespace: str) -> bool:
        return any(t.namespace == namespace for t in self.tags)


@dataclass(frozen=True)
class NPC(Entity):
    drives: dict[str, float] = field(default_factory=dict)
    current_goals: tuple = field(default_factory=tuple)
    persona_contract: Optional[PersonaContract] = None
    schedule: Optional[Any] = None

    def update_drive(self, drive_id: str, intensity: float) -> NPC:
        new_drives = dict(self.drives)
        new_drives[drive_id] = max(0.0, min(1.0, intensity))
        return NPC(
            id=self.id,
            archetype=self.archetype,
            tags=self.tags,
            properties=self.properties,
            observations=self.observations,
            created_at=self.created_at,
            canon_locked=self.canon_locked,
            drives=new_drives,
            current_goals=self.current_goals,
            persona_contract=self.persona_contract,
            schedule=self.schedule,
        )


@dataclass(frozen=True)
class PersonaContract:
    persona_id: str
    core_traits: FrozenSet[str] = field(default_factory=frozenset)
    speech_pattern: str = ""
    forbidden_behaviors: FrozenSet[str] = field(default_factory=frozenset)
    required_behaviors: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Item(Entity):
    pass


@dataclass(frozen=True)
class Location(Entity):
    pass


@dataclass(frozen=True)
class Player(Entity):
    pass
