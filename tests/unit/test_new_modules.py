from __future__ import annotations

from nexus_engine.core.tag_index import TagInvertedIndex
from nexus_engine.core.systems import (
    WorldState,
    ComponentQuery,
    SystemManager,
    MovementSystem,
)
from nexus_engine.core.entity import Entity
from nexus_engine.core.value_objects import Tag
from nexus_engine.rules.rete import ReteBuilder
from nexus_engine.rules.datalog import DatalogEngine, create_knowledge_base, DatalogFact
from nexus_engine.setting.setting_pack import ControlledVocabulary
from uuid import uuid4


def test_tag_inverted_index_basic():
    index = TagInvertedIndex()

    index.add_entity("entity1", frozenset(["fire", "weapon", "rare"]))
    index.add_entity("entity2", frozenset(["fire", "consumable"]))
    index.add_entity("entity3", frozenset(["water", "weapon"]))

    assert "entity1" in index.get_entities_with_tag("fire")
    assert "entity2" in index.get_entities_with_tag("fire")
    assert "entity3" not in index.get_entities_with_tag("fire")

    and_result = index.get_entities_with_tags_and(["fire", "weapon"])
    assert "entity1" in and_result
    assert "entity3" not in and_result

    or_result = index.get_entities_with_tags_or(["fire", "water"])
    assert "entity1" in or_result
    assert "entity2" in or_result
    assert "entity3" in or_result


def test_tag_inverted_index_search():
    index = TagInvertedIndex()

    index.add_entity("e1", frozenset(["a", "b", "c"]))
    index.add_entity("e2", frozenset(["a", "b"]))
    index.add_entity("e3", frozenset(["b", "c"]))
    index.add_entity("e4", frozenset(["c"]))

    result = index.search(tags_and=["a", "b"])
    assert result == {"e1", "e2"}

    result = index.search(tags_or=["a"])
    assert result == {"e1", "e2"}

    result = index.search(tags_none=["a"])
    assert "e1" not in result
    assert "e2" not in result
    assert "e3" in result


def test_controlled_vocabulary_synonyms():
    vocab = ControlledVocabulary(
        namespaces=frozenset(["element"]),
        tags_by_namespace={
            "element": frozenset(["fire", "water", "earth"]),
        },
        synonyms={
            "burning": "fire",
            "flaming": "fire",
            "hot": "fire",
        },
    )

    tag = Tag(namespace="element", value="burning")
    resolved = vocab.resolve_tag(tag)
    assert resolved.value == "fire"

    assert vocab.is_valid_tag(Tag(namespace="element", value="fire"))
    assert vocab.is_valid_tag(Tag(namespace="element", value="burning"))


def test_controlled_vocabulary_hierarchy():
    vocab = ControlledVocabulary(
        namespaces=frozenset(["element"]),
        tags_by_namespace={
            "element": frozenset(["fire", "mundane_fire", "spiritual_fire"]),
        },
        isa_hierarchy={
            "mundane_fire": ["fire"],
            "spiritual_fire": ["fire"],
            "fire": [],
        },
    )

    assert vocab.is_a(
        Tag(namespace="element", value="mundane_fire"),
        Tag(namespace="element", value="fire"),
    )
    assert vocab.is_a(
        Tag(namespace="element", value="spiritual_fire"),
        Tag(namespace="element", value="fire"),
    )
    assert vocab.is_a(
        Tag(namespace="element", value="fire"), Tag(namespace="element", value="fire")
    )


def test_world_state_query():
    world = WorldState()

    entity1 = Entity(
        id=uuid4(),
        archetype="test",
        properties={"hp": 100, "name": "Entity 1"},
        tags=frozenset([Tag(namespace="element", value="fire")]),
    )

    entity2 = Entity(
        id=uuid4(),
        archetype="test",
        properties={"hp": 50, "name": "Entity 2"},
        tags=frozenset([Tag(namespace="element", value="water")]),
    )

    world.add_entity(entity1)
    world.add_entity(entity2)

    fire_entities = list(world.query(ComponentQuery(required_tags=["element:fire"])))
    assert len(fire_entities) == 1

    water_entities = list(world.query(ComponentQuery(required_tags=["element:water"])))
    assert len(water_entities) == 1


def test_datalog_engine_basic():
    kb = DatalogEngine()

    kb.add_fact("element", "fire")
    kb.add_fact("element", "water")
    kb.add_fact("material", "wood")

    assert DatalogFact("element", ("fire",)) in kb
    assert DatalogFact("element", ("water",)) in kb
    assert DatalogFact("material", ("wood",)) in kb

    results = kb.query("element", "fire")
    assert ("fire",) in results


def test_datalog_engine_rules():
    kb = create_knowledge_base()

    results = kb.query("element", "fire")
    assert ("fire",) in results


def test_rete_network():
    builder = ReteBuilder()

    builder.register_alpha_pattern(
        "has_fire", lambda f: f.get("tags", {}).get("element") == "fire"
    )

    rule = builder.build_rule(
        rule_id="r1",
        name="Fire Rule",
        patterns=["has_fire"],
        action=lambda ctx: {"triggered": True, "entity": ctx["entity_id"]},
    )

    network = builder.build_network()
    network.add_production(rule)

    results = network.assert_fact(
        "entity1", {"tags": {"element": "fire"}, "name": "Test"}
    )
    assert len(results) > 0


def test_system_manager():
    world = WorldState()
    manager = SystemManager(world)

    manager.register_system(MovementSystem())

    entity = Entity(
        id=uuid4(),
        archetype="test",
        properties={
            "hp": 100,
            "max_hp": 100,
            "position": {"x": 0, "y": 0, "z": 0},
            "velocity": {"x": 1, "y": 0, "z": 0},
        },
        tags=frozenset(
            [
                Tag(namespace="game", value="position"),
                Tag(namespace="game", value="velocity"),
            ]
        ),
    )

    world.add_entity(entity)

    found = list(
        world.query(ComponentQuery(required_tags=["game:position", "game:velocity"]))
    )
    assert len(found) > 0
