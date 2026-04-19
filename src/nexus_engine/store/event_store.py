from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator

from nexus_engine.core.event import Event
from nexus_engine.core.value_objects import EventId, GameTime


class EventStore(ABC):
    @abstractmethod
    async def append(self, event: Event) -> EventId: ...

    @abstractmethod
    async def get(self, id: EventId) -> Event | None: ...

    @abstractmethod
    def query(self, filter: EventFilter) -> AsyncIterator[Event]: ...

    @abstractmethod
    def get_since(self, time: GameTime) -> AsyncIterator[Event]: ...

    @abstractmethod
    def get_entity_history(
        self, entity_id: str, since: GameTime | None = None
    ) -> AsyncIterator[Event]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def close(self) -> None: ...


class EventFilter:
    actor: str | None = None
    target: str | None = None
    location: str | None = None
    types: list[str] | None = None
    time_range: tuple[GameTime, GameTime] | None = None
    involves_entity: str | None = None
    limit: int = 100

    def __init__(
        self,
        actor: str | None = None,
        target: str | None = None,
        location: str | None = None,
        types: list[str] | None = None,
        time_range: tuple[GameTime, GameTime] | None = None,
        involves_entity: str | None = None,
        limit: int = 100,
    ):
        self.actor = actor
        self.target = target
        self.location = location
        self.types = types
        self.time_range = time_range
        self.involves_entity = involves_entity
        self.limit = limit
