from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from nexus_engine.core.entity import Entity
from nexus_engine.core.event import Event, StateChange
from nexus_engine.core.tag_index import TagInvertedIndex
from nexus_engine.core.value_objects import EntityId, GameTime, Tag
from nexus_engine.store.event_store import EventStore
from nexus_engine.store.snapshot_store import Snapshot, SnapshotStore


@dataclass
class EntitySnapshot:
    id: EntityId
    archetype: str
    tags: frozenset[Tag]
    properties: dict[str, Any]
    created_at: GameTime
    canon_locked: bool


@dataclass
class LocationSnapshot:
    id: EntityId
    name: str
    entities: list[EntityId]
    conditions: list[str]
    properties: dict[str, Any]


@dataclass
class Relationship:
    entity_a: EntityId
    entity_b: EntityId
    trust: float = 0.0
    affinity: float = 0.0
    debts: dict[str, Any] = field(default_factory=dict)


class StateView:
    def __init__(
        self,
        event_store: EventStore,
        snapshot_store: SnapshotStore | None = None,
    ):
        self.event_store = event_store
        self.snapshot_store = snapshot_store
        self._entity_cache: dict[EntityId, Entity] = {}
        self._tag_index = TagInvertedIndex()
        self._current_time: GameTime = GameTime(0)

    async def get_entity(self, id: EntityId, depth: int = 1) -> Entity | None:
        if id in self._entity_cache:
            return self._entity_cache[id]
        return None

    async def entity_exists(self, id: EntityId) -> bool:
        if id in self._entity_cache:
            return True
        return False

    def find_by_tag(self, tag: str) -> list[Entity]:
        entity_ids = self._tag_index.get_entities_with_tag(tag)
        return [self._entity_cache[EntityId(eid)] for eid in entity_ids if EntityId(eid) in self._entity_cache]

    def find_by_tags_and(self, tags: list[str]) -> list[Entity]:
        entity_ids = self._tag_index.get_entities_with_tags_and(tags)
        return [self._entity_cache[EntityId(eid)] for eid in entity_ids if EntityId(eid) in self._entity_cache]

    def find_by_tags_or(self, tags: list[str]) -> list[Entity]:
        entity_ids = self._tag_index.get_entities_with_tags_or(tags)
        return [self._entity_cache[EntityId(eid)] for eid in entity_ids if EntityId(eid) in self._entity_cache]

    async def get_location_snapshot(
        self, loc: EntityId, aspects: list[str]
    ) -> LocationSnapshot | None:
        entity = await self.get_entity(loc)
        if not entity:
            return None
        return LocationSnapshot(
            id=entity.id,
            name=entity.properties.get("name", "Unknown"),
            entities=[],
            conditions=[],
            properties=entity.properties,
        )

    async def get_relationship(self, a: EntityId, b: EntityId) -> Relationship | None:
        return None

    async def get_inventory(self, holder: EntityId) -> list[EntityId]:
        return []

    async def apply(self, event: Event) -> None:
        self._current_time = event.game_time
        for effect in event.effects:
            await self._apply_effect(effect)

    async def _apply_effect(self, effect: StateChange) -> None:
        target_id = effect.target.id
        if target_id not in self._entity_cache:
            return
        entity = self._entity_cache[target_id]
        new_properties = effect.apply(entity.properties)
        self._entity_cache[target_id] = Entity(
            id=entity.id,
            archetype=entity.archetype,
            tags=entity.tags,
            properties=new_properties,
            observations=entity.observations,
            created_at=entity.created_at,
            canon_locked=entity.canon_locked,
        )

    async def project_from(
        self,
        events: AsyncIterator[Event],
        base_snapshot: Snapshot | None = None,
    ) -> None:
        if base_snapshot:
            self._current_time = base_snapshot.game_time
            for entity_data in base_snapshot.state.get("entities", {}).values():
                entity = Entity(
                    id=EntityId(entity_data["id"]),
                    archetype=entity_data["archetype"],
                    tags=frozenset(Tag(**t) for t in entity_data.get("tags", [])),
                    properties=entity_data.get("properties", {}),
                    created_at=GameTime(entity_data.get("created_at", 0)),
                    canon_locked=entity_data.get("canon_locked", False),
                )
                self._entity_cache[entity.id] = entity

        async for event in events:
            await self.apply(event)

    async def snapshot_at(self, time: GameTime) -> Snapshot:
        if self.snapshot_store:
            cached = await self.snapshot_store.load_nearest(time)
            if cached:
                self._current_time = cached.game_time
                for entity_data in cached.state.get("entities", {}).values():
                    entity = Entity(
                        id=EntityId(entity_data["id"]),
                        archetype=entity_data["archetype"],
                        tags=frozenset(Tag(**t) for t in entity_data.get("tags", [])),
                        properties=entity_data.get("properties", {}),
                        created_at=GameTime(entity_data.get("created_at", 0)),
                        canon_locked=entity_data.get("canon_locked", False),
                    )
                    self._entity_cache[entity.id] = entity

        events = self.event_store.get_since(self._current_time)
        async for event in events:
            if event.game_time.ticks <= time.ticks:
                await self.apply(event)
                self._current_time = event.game_time

        return self._create_snapshot(time)

    def _create_snapshot(self, time: GameTime) -> Snapshot:
        from nexus_engine.core.value_objects import new_event_id

        entities_state = {}
        for entity_id, entity in self._entity_cache.items():
            entities_state[str(entity_id)] = {
                "id": str(entity.id),
                "archetype": entity.archetype,
                "tags": [
                    {"namespace": t.namespace, "value": t.value} for t in entity.tags
                ],
                "properties": entity.properties,
                "created_at": entity.created_at.ticks,
                "canon_locked": entity.canon_locked,
            }

        return Snapshot(
            game_time=time,
            event_id=new_event_id(),
            state={"entities": entities_state, "current_time": time.ticks},
        )

    def add_entity(self, entity: Entity) -> None:
        self._entity_cache[entity.id] = entity
        tag_strs = [str(t) for t in entity.tags]
        self._tag_index.add_entity(str(entity.id), frozenset(tag_strs))

    def update_entity_tags(self, entity_id: EntityId, tags: frozenset[Tag]) -> None:
        if entity_id in self._entity_cache:
            entity = self._entity_cache[entity_id]
            new_entity = Entity(
                id=entity.id,
                archetype=entity.archetype,
                tags=tags,
                properties=entity.properties,
                observations=entity.observations,
                created_at=entity.created_at,
                canon_locked=entity.canon_locked,
            )
            self._entity_cache[entity_id] = new_entity
            tag_strs = [str(t) for t in tags]
            self._tag_index.update_entity_tags(str(entity_id), frozenset(tag_strs))

    @property
    def current_time(self) -> GameTime:
        return self._current_time
