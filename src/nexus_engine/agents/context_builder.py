from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nexus_engine.core.event import Event
from nexus_engine.core.value_objects import EntityId


@dataclass
class SceneContext:
    location: LocationView
    player: EntityView
    recent_events: list[EventSummary]
    relevant_memories: list[MemoryHit]
    available_abilities: list[AbilityDescriptor]
    vocabulary: VocabularyDescriptor


@dataclass
class LocationView:
    id: str
    name: str
    entities: list[EntitySummary]
    conditions: list[str]
    properties: dict[str, Any]


@dataclass
class EntityView:
    id: str
    archetype: str
    name: str
    tags: list[str]
    properties: dict[str, Any]
    resources: dict[str, int]


@dataclass
class EntitySummary:
    id: str
    archetype: str
    name: str


@dataclass
class EventSummary:
    id: str
    type: str
    game_time: int
    summary: str


@dataclass
class MemoryHit:
    content: str
    relevance: float
    source: str


@dataclass
class AbilityDescriptor:
    id: str
    name: str
    costs: dict[str, int]
    tier: int


@dataclass
class VocabularyDescriptor:
    namespaces: list[str]
    tags_by_namespace: dict[str, list[str]]


class ContextBuilder:
    def __init__(
        self,
        state_view: Any,
        memory_system: Any | None = None,
        setting_pack: Any | None = None,
    ):
        self.state_view = state_view
        self.memory_system = memory_system
        self.setting_pack = setting_pack

    async def build_scene_context(
        self,
        player_id: EntityId,
        location_id: EntityId,
        recent_events: list[Event] | None = None,
    ) -> SceneContext:
        location = await self._build_location_view(location_id)
        player = await self._build_entity_view(player_id)
        recent = await self._build_recent_events(player_id, recent_events)
        memories = await self._build_relevant_memories(player_id, location_id)
        abilities = await self._build_available_abilities(player)
        vocabulary = self._build_vocabulary()

        return SceneContext(
            location=location,
            player=player,
            recent_events=recent,
            relevant_memories=memories,
            available_abilities=abilities,
            vocabulary=vocabulary,
        )

    async def _build_location_view(self, location_id: EntityId) -> LocationView:
        snapshot = await self.state_view.get_location_snapshot(
            location_id, aspects=["entities", "conditions"]
        )
        if not snapshot:
            return LocationView(
                id=str(location_id),
                name="Unknown",
                entities=[],
                conditions=[],
                properties={},
            )

        entities = []
        for entity_id in snapshot.entities:
            entity = await self.state_view.get_entity(entity_id)
            if entity:
                entities.append(EntitySummary(
                    id=str(entity.id),
                    archetype=entity.archetype,
                    name=entity.properties.get("name", "Unnamed"),
                ))

        return LocationView(
            id=str(snapshot.id),
            name=snapshot.name,
            entities=entities,
            conditions=snapshot.conditions,
            properties=snapshot.properties,
        )

    async def _build_entity_view(self, entity_id: EntityId) -> EntityView:
        entity = await self.state_view.get_entity(entity_id)
        if not entity:
            return EntityView(
                id=str(entity_id),
                archetype="unknown",
                name="Unknown",
                tags=[],
                properties={},
                resources={},
            )

        return EntityView(
            id=str(entity.id),
            archetype=entity.archetype,
            name=entity.properties.get("name", "Unnamed"),
            tags=[str(t) for t in entity.tags],
            properties=entity.properties,
            resources=entity.properties.get("resources", {}),
        )

    async def _build_recent_events(
        self,
        player_id: EntityId,
        provided_events: list[Event] | None = None,
    ) -> list[EventSummary]:
        if provided_events:
            return [
                EventSummary(
                    id=str(e.id),
                    type=e.type.value,
                    game_time=e.game_time.ticks,
                    summary=e.narrative_summary,
                )
                for e in provided_events[-10:]
            ]

        from nexus_engine.store.event_store import EventFilter

        filter_obj = EventFilter()
        filter_obj.actor = str(player_id)
        filter_obj.limit = 10

        events = []
        async for event in self.state_view.event_store.query(filter_obj):
            events.append(EventSummary(
                id=str(event.id),
                type=event.type.value,
                game_time=event.game_time.ticks,
                summary=event.narrative_summary,
            ))

        return events

    async def _build_relevant_memories(
        self, player_id: EntityId, location_id: EntityId
    ) -> list[MemoryHit]:
        if not self.memory_system:
            return []

        return await self.memory_system.recall_relevant_to(
            entities=[str(player_id), str(location_id)],
            limit=5,
        )

    async def _build_available_abilities(self, player: EntityView) -> list[AbilityDescriptor]:
        if not self.setting_pack:
            return []

        archetypes = getattr(self.setting_pack, "archetypes", {})
        archetype = archetypes.get(player.archetype)
        if not archetype:
            return []

        abilities = getattr(archetype, "default_abilities", [])
        return [
            AbilityDescriptor(
                id=str(a.id) if hasattr(a, "id") else str(a),
                name=getattr(a, "name", "Unknown"),
                costs={},
                tier=getattr(a, "tier", 0),
            )
            for a in abilities
        ]

    def _build_vocabulary(self) -> VocabularyDescriptor:
        if not self.setting_pack:
            return VocabularyDescriptor(namespaces=[], tags_by_namespace={})

        vocab = getattr(self.setting_pack, "vocabulary", None)
        if not vocab:
            return VocabularyDescriptor(namespaces=[], tags_by_namespace={})

        namespaces = list(getattr(vocab, "namespaces", []))
        tags_by_ns = {}
        for ns in namespaces:
            tags = list(getattr(vocab, "tags_by_namespace", {}).get(ns, []))
            tags_by_ns[ns] = tags

        return VocabularyDescriptor(
            namespaces=namespaces,
            tags_by_namespace=tags_by_ns,
        )
