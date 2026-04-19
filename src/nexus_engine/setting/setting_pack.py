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
    synonyms: dict[str, str] = field(default_factory=dict)
    isa_hierarchy: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self):
        self._canonical_cache: dict[str, str] = {}
        self._build_canonical_cache()

    def _build_canonical_cache(self) -> None:
        for tag in self._all_tags():
            self._canonical_cache[tag] = self._to_canonical(tag)

    def _all_tags(self) -> set[str]:
        tags = set()
        for ns_tags in self.tags_by_namespace.values():
            tags.update(ns_tags)
        return tags

    def _to_canonical(self, tag_str: str) -> str:
        if tag_str in self.synonyms:
            return self.synonyms[tag_str]
        return tag_str

    def resolve_tag(self, tag: Tag) -> Tag:
        canonical_value = self._to_canonical(tag.value)
        if canonical_value != tag.value:
            return Tag(namespace=tag.namespace, value=canonical_value)
        return tag

    def is_valid_tag(self, tag: Tag) -> bool:
        canonical = self.resolve_tag(tag)
        return (
            canonical.namespace in self.namespaces
            and canonical.value in self.tags_by_namespace.get(canonical.namespace, frozenset())
        )

    def get_parent_tags(self, tag: Tag) -> list[Tag]:
        canonical = self.resolve_tag(tag)
        parents = self.isa_hierarchy.get(canonical.value, [])
        return [Tag(namespace=canonical.namespace, value=p) for p in parents]

    def is_a(self, tag: Tag, parent_tag: Tag) -> bool:
        canonical = self.resolve_tag(tag)
        parent_canonical = self.resolve_tag(parent_tag)

        if canonical == parent_canonical:
            return True

        def check_ancestors(current: str, target: str) -> bool:
            parents = self.isa_hierarchy.get(current, [])
            if target in parents:
                return True
            for p in parents:
                if check_ancestors(p, target):
                    return True
            return False

        return check_ancestors(canonical.value, parent_canonical.value)

    def matches_tag(self, entity_tags: frozenset[Tag], pattern_tag: Tag) -> bool:
        for entity_tag in entity_tags:
            if entity_tag.namespace != pattern_tag.namespace:
                continue
            resolved_entity = self.resolve_tag(entity_tag)
            resolved_pattern = self.resolve_tag(pattern_tag)
            if resolved_entity == resolved_pattern:
                return True
            if self.is_a(entity_tag, pattern_tag):
                return True
        return False


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
