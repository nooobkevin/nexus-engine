from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

if TYPE_CHECKING:
    EntityId = UUID
    EventId = UUID
    RuleId = UUID
    AbilityId = UUID
else:
    def EntityId(x=None):
        if x is None:
            return uuid4()
        return UUID(x) if isinstance(x, str) else x
    
    def EventId(x=None):
        if x is None:
            return uuid4()
        return UUID(x) if isinstance(x, str) else x
    
    def RuleId(x=None):
        if x is None:
            return uuid4()
        return UUID(x) if isinstance(x, str) else x
    
    def AbilityId(x=None):
        if x is None:
            return uuid4()
        return UUID(x) if isinstance(x, str) else x


ArchetypeId = str
DriveId = str
GoalId = str
TagId = str


@dataclass(frozen=True, order=True)
class GameTime:
    ticks: int = field(compare=True)

    def __add__(self, other: int) -> GameTime:
        return GameTime(self.ticks + other)

    def __sub__(self, other: GameTime) -> int:
        return self.ticks - other.ticks

    def advance(self, delta: int) -> GameTime:
        return GameTime(self.ticks + delta)

    @property
    def wall_time(self) -> datetime:
        return datetime.now()

    def to_int(self) -> int:
        return self.ticks


@dataclass(frozen=True)
class EntityRef:
    id: EntityId

    def __str__(self) -> str:
        return f"EntityRef({self.id})"


@dataclass(frozen=True)
class SourceRef:
    source_type: Literal["event", "npc", "player", "setting_pack"]
    ref_id: str
    quote: str | None = None


@dataclass(frozen=True, order=True)
class Tag:
    namespace: str
    value: str

    def __str__(self) -> str:
        return f"{self.namespace}:{self.value}"

    def matches(self, other: Tag) -> bool:
        return self.namespace == other.namespace and self.value == other.value


class TierLevel(int, Enum):
    MUNDANE = 0
    HEROIC = 1
    LEGENDARY = 2
    MYTHIC = 3
    DIVINE = 4

    @classmethod
    def from_int(cls, value: int) -> TierLevel:
        return cls(max(0, min(4, value)))


class EventType(str, Enum):
    ACTION = "action"
    PERCEPTION = "perception"
    NARRATIVE = "narrative"
    COMBAT = "combat"
    SOCIAL = "social"
    MOVEMENT = "movement"
    ABILITY_USE = "ability_use"
    ITEM_USE = "item_use"
    CONVERSATION = "conversation"
    WORLD_STATE_CHANGE = "world_state_change"
    SYSTEM = "system"


def new_entity_id() -> EntityId:
    return uuid4()  # type: ignore[return-value]


def new_event_id() -> EventId:
    return uuid4()  # type: ignore[return-value]


def new_rule_id() -> RuleId:
    return uuid4()  # type: ignore[return-value]


def new_ability_id() -> AbilityId:
    return uuid4()  # type: ignore[return-value]


def new_goal_id() -> GoalId:
    return uuid4()  # type: ignore[return-value]


def new_drive_id() -> DriveId:
    return uuid4()  # type: ignore[return-value]
