from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, FrozenSet, List, Optional

from nexus_engine.core.value_objects import (
    EntityRef,
    EventId,
    EventType,
    GameTime,
    Tag,
    new_event_id,
)


class Operation(str, Enum):
    SET = "SET"
    DELTA = "DELTA"
    APPEND = "APPEND"
    REMOVE = "REMOVE"


@dataclass(frozen=True)
class StateChange:
    target: EntityRef
    path: str
    operation: Operation
    value: Any

    def apply(self, current_state: dict[str, Any]) -> dict[str, Any]:
        new_state = dict(current_state)
        keys = self.path.split(".")
        current = new_state
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        match self.operation:
            case Operation.SET:
                current[keys[-1]] = self.value
            case Operation.DELTA:
                if isinstance(current.get(keys[-1]), (int, float)):
                    current[keys[-1]] = current[keys[-1]] + self.value
                else:
                    current[keys[-1]] = self.value
            case Operation.APPEND:
                if isinstance(current.get(keys[-1]), list):
                    current[keys[-1]] = [*current[keys[-1]], self.value]
                else:
                    current[keys[-1]] = [self.value]
            case Operation.REMOVE:
                if isinstance(current.get(keys[-1]), list):
                    current[keys[-1]] = [
                        x for x in current[keys[-1]] if x != self.value
                    ]
                else:
                    if keys[-1] in current:
                        del current[keys[-1]]

        return new_state


@dataclass(frozen=True)
class MechanicsResult:
    success: bool
    degree: float = 0.0
    values: dict[str, Any] = field(default_factory=dict)
    roll: Optional[int] = None
    difficulty: Optional[int] = None

    @property
    def is_critical_success(self) -> bool:
        return self.roll is not None and self.roll == 20

    @property
    def is_critical_failure(self) -> bool:
        return self.roll is not None and self.roll == 1


@dataclass(frozen=True)
class Event:
    id: EventId
    game_time: GameTime
    type: EventType
    actor: Optional[EntityRef]
    targets: FrozenSet[EntityRef]
    location: EntityRef
    mechanics: MechanicsResult
    effects: FrozenSet[StateChange]
    witnesses: FrozenSet[EntityRef]
    narrative_summary: str
    narrative_full: Optional[str] = None
    parent_event: Optional[EventId] = None
    canon: bool = False
    tags: FrozenSet[Tag] = field(default_factory=frozenset)

    @classmethod
    def create(
        cls,
        game_time: GameTime,
        event_type: EventType,
        actor: Optional[EntityRef],
        location: EntityRef,
        mechanics: MechanicsResult,
        effects: List[StateChange],
        narrative_summary: str,
        targets: Optional[List[EntityRef]] = None,
        witnesses: Optional[List[EntityRef]] = None,
        parent_event: Optional[EventId] = None,
        canon: bool = False,
        tags: Optional[List[Tag]] = None,
    ) -> Event:
        return cls(
            id=new_event_id(),
            game_time=game_time,
            type=event_type,
            actor=actor,
            targets=frozenset(targets or []),
            location=location,
            mechanics=mechanics,
            effects=frozenset(effects),
            witnesses=frozenset(witnesses or []),
            narrative_summary=narrative_summary[:150],
            parent_event=parent_event,
            canon=canon,
            tags=frozenset(tags or []),
        )

    def with_full_narrative(self, narrative: str) -> Event:
        return Event(
            id=self.id,
            game_time=self.game_time,
            type=self.type,
            actor=self.actor,
            targets=self.targets,
            location=self.location,
            mechanics=self.mechanics,
            effects=self.effects,
            witnesses=self.witnesses,
            narrative_summary=self.narrative_summary,
            narrative_full=narrative,
            parent_event=self.parent_event,
            canon=self.canon,
            tags=self.tags,
        )


@dataclass(frozen=True)
class EventDraft:
    type: EventType
    actor: Optional[EntityRef]
    targets: List[EntityRef]
    location: EntityRef
    mechanics: MechanicsResult
    effects: List[StateChange]
    narrative_summary: str
    parent_event: Optional[EventId] = None
    tags: List[Tag] = field(default_factory=list)

    def to_event(self, game_time: GameTime) -> Event:
        return Event.create(
            game_time=game_time,
            event_type=self.type,
            actor=self.actor,
            location=self.location,
            mechanics=self.mechanics,
            effects=self.effects,
            narrative_summary=self.narrative_summary,
            targets=self.targets,
            parent_event=self.parent_event,
            tags=self.tags,
        )
