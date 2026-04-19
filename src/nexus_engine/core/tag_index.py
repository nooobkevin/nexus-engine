from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TagInvertedIndex:
    _index: dict[str, set[str]] = field(default_factory=dict)
    _entity_tags: dict[str, set[str]] = field(default_factory=dict)

    def add_entity(self, entity_id: str, tags: frozenset[str]) -> None:
        if entity_id in self._entity_tags:
            self._remove_entity_from_index(entity_id, self._entity_tags[entity_id])

        self._entity_tags[entity_id] = set(tags)

        for tag in tags:
            if tag not in self._index:
                self._index[tag] = set()
            self._index[tag].add(entity_id)

    def remove_entity(self, entity_id: str) -> None:
        if entity_id in self._entity_tags:
            self._remove_entity_from_index(entity_id, self._entity_tags[entity_id])
            del self._entity_tags[entity_id]

    def _remove_entity_from_index(self, entity_id: str, tags: set[str]) -> None:
        for tag in tags:
            if tag in self._index:
                self._index[tag].discard(entity_id)
                if not self._index[tag]:
                    del self._index[tag]

    def update_entity_tags(self, entity_id: str, new_tags: frozenset[str]) -> None:
        self.add_entity(entity_id, new_tags)

    def get_entities_with_tag(self, tag: str) -> set[str]:
        return self._index.get(tag, set()).copy()

    def get_entities_with_tags_and(self, tags: list[str]) -> set[str]:
        if not tags:
            return set(self._entity_tags.keys())

        result = self._index.get(tags[0], set()).copy()
        for tag in tags[1:]:
            result &= self._index.get(tag, set())
        return result

    def get_entities_with_tags_or(self, tags: list[str]) -> set[str]:
        result = set()
        for tag in tags:
            result |= self._index.get(tag, set())
        return result

    def get_entities_with_tags_none(self, tags: list[str]) -> set[str]:
        all_entities = set(self._entity_tags.keys())
        excluded = self.get_entities_with_tags_or(tags)
        return all_entities - excluded

    def search(
        self,
        tags_and: list[str] | None = None,
        tags_or: list[str] | None = None,
        tags_none: list[str] | None = None,
    ) -> set[str]:
        if tags_and:
            result = self.get_entities_with_tags_and(tags_and)
        elif tags_or:
            result = self.get_entities_with_tags_or(tags_or)
        else:
            result = set(self._entity_tags.keys())

        if tags_and and tags_or:
            result |= self.get_entities_with_tags_or(tags_or)
        if tags_none:
            result -= self.get_entities_with_tags_or(tags_none)

        return result

    def get_entity_tags(self, entity_id: str) -> set[str]:
        return self._entity_tags.get(entity_id, set()).copy()

    def has_tag(self, entity_id: str, tag: str) -> bool:
        return tag in self._entity_tags.get(entity_id, set())

    def has_any_tag(self, entity_id: str, tags: list[str]) -> bool:
        entity_tags = self._entity_tags.get(entity_id, set())
        return any(tag in entity_tags for tag in tags)

    def has_all_tags(self, entity_id: str, tags: list[str]) -> bool:
        entity_tags = self._entity_tags.get(entity_id, set())
        return all(tag in entity_tags for tag in tags)

    def get_tag_counts(self) -> dict[str, int]:
        return {tag: len(entities) for tag, entities in self._index.items()}

    def get_all_tags(self) -> set[str]:
        return set(self._index.keys())

    def __len__(self) -> int:
        return len(self._entity_tags)

    def __contains__(self, entity_id: str) -> bool:
        return entity_id in self._entity_tags
