from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet

from nexus_engine.core.ability import Rule
from nexus_engine.core.value_objects import ArchetypeId, Tag, TierLevel


@dataclass
class Archetype:
    id: ArchetypeId
    name: str
    description: str
    base_tags: FrozenSet[Tag] = field(default_factory=frozenset)
    base_properties: dict[str, Any] = field(default_factory=dict)
    default_abilities: list[str] = field(default_factory=list)
    power_tier: TierLevel = TierLevel.MUNDANE


@dataclass
class ResourcePoolDef:
    id: str
    name: str
    max_at_tier: list[int] = field(default_factory=list)


@dataclass
class TierDef:
    level: int
    name: str
    abilities: list[str] = field(default_factory=list)


@dataclass
class PowerSystemSpec:
    resource_pools: list[ResourcePoolDef] = field(default_factory=list)
    tier_levels: list[TierDef] = field(default_factory=list)
    advancement_rules: list[dict[str, Any]] = field(default_factory=list)
    ability_taxonomy: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlledVocabulary:
    namespaces: FrozenSet[str] = field(default_factory=frozenset)
    tags_by_namespace: dict[str, FrozenSet[str]] = field(default_factory=dict)

    def is_valid_tag(self, tag: Tag) -> bool:
        return (
            tag.namespace in self.namespaces
            and tag.value in self.tags_by_namespace.get(tag.namespace, frozenset())
        )


@dataclass
class StyleGuide:
    tone: str = "neutral"
    perspective: str = "third_person_limited"
    prose_style: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoreEntry:
    id: str
    content: str
    source: str
    vector_embedding: list[float] | None = None


@dataclass
class SettingPack:
    id: str
    version: str
    archetypes: dict[ArchetypeId, Archetype] = field(default_factory=dict)
    power_system: PowerSystemSpec | None = None
    vocabulary: ControlledVocabulary | None = None
    common_sense_rules: list[Rule] = field(default_factory=list)
    narrative_style: StyleGuide = field(default_factory=StyleGuide)
    lore_corpus: list[LoreEntry] = field(default_factory=list)
    canon_facts: list[Any] = field(default_factory=list)

    def validate_entity(self, entity: Any) -> bool:
        if not self.vocabulary:
            return True

        for tag in entity.tags:
            if not self.vocabulary.is_valid_tag(tag):
                return False
        return True

    def get_abilities_for_archetype(self, archetype_id: ArchetypeId) -> list[Any]:
        archetype = self.archetypes.get(archetype_id)
        if not archetype:
            return []
        return archetype.default_abilities


def create_minimal_setting_pack() -> SettingPack:
    return SettingPack(
        id="minimal",
        version="1.0.0",
        archetypes={},
        power_system=None,
        vocabulary=ControlledVocabulary(
            namespaces=frozenset(["material", "technique", "element"]),
            tags_by_namespace={
                "material": frozenset(["steel", "wood", "stone"]),
                "technique": frozenset(["sword", "spear", "bow"]),
                "element": frozenset(["fire", "water", "earth", "wind"]),
            },
        ),
        narrative_style=StyleGuide(),
    )
