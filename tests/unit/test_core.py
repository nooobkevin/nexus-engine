from __future__ import annotations

import pytest

from nexus_engine.core.value_objects import GameTime, EntityId, Tag, EventType, EntityRef
from nexus_engine.core.entity import Entity, Observation, PersonaContract
from nexus_engine.core.event import Event, StateChange, MechanicsResult, Operation
from nexus_engine.core.ability import Rule, MatchPattern, Outcome, Ability, TargetingRule


def test_game_time_basics():
    t1 = GameTime(100)
    t2 = t1 + 50
    assert t2.ticks == 150
    assert t1.ticks == 100
    assert t2 - t1 == 50


def test_entity_creation():
    entity = Entity(
        id=EntityId(),
        archetype="test_archetype",
        properties={"name": "Test Entity", "hp": 100},
    )
    assert entity.properties["name"] == "Test Entity"
    assert entity.properties["hp"] == 100


def test_entity_property_access():
    entity = Entity(
        id=EntityId(),
        archetype="test",
        properties={"stats": {"strength": 15, "dexterity": 12}},
    )
    assert entity.get_property("stats.strength") == 15
    assert entity.get_property("stats.dexterity") == 12
    assert entity.get_property("stats.missing", 0) == 0


def test_entity_with_property():
    entity = Entity(
        id=EntityId(),
        archetype="test",
        properties={"hp": 100},
    )
    updated = entity.with_property("hp", 80)
    assert updated.properties["hp"] == 80
    assert entity.properties["hp"] == 100


def test_tag_creation():
    tag = Tag(namespace="material", value="steel")
    assert str(tag) == "material:steel"
    assert tag.namespace == "material"
    assert tag.value == "steel"


def test_state_change_apply():
    target = EntityRef(id=EntityId())
    state = {"hp": 100, "name": "Test"}

    change = StateChange(target=target, path="hp", operation=Operation.SET, value=50)
    new_state = change.apply(state)
    assert new_state["hp"] == 50

    change_delta = StateChange(target=target, path="hp", operation=Operation.DELTA, value=10)
    new_state = change_delta.apply(new_state)
    assert new_state["hp"] == 60


def test_mechanics_result():
    result = MechanicsResult(success=True, degree=0.75, roll=15, difficulty=10)
    assert result.success is True
    assert result.degree == 0.75
    assert result.is_critical_success is False
    assert result.is_critical_failure is False

    crit_success = MechanicsResult(success=True, roll=20)
    assert crit_success.is_critical_success is True

    crit_fail = MechanicsResult(success=False, roll=1)
    assert crit_fail.is_critical_failure is True


def test_event_creation():
    event = Event.create(
        game_time=GameTime(0),
        event_type=EventType.ACTION,
        actor=EntityRef(id=EntityId()),
        location=EntityRef(id=EntityId()),
        mechanics=MechanicsResult(success=True, degree=1.0),
        effects=[],
        narrative_summary="Test event",
    )
    assert event.narrative_summary == "Test event"
    assert event.canon is False


def test_event_narrative_summary_truncation():
    long_summary = "x" * 200
    event = Event.create(
        game_time=GameTime(0),
        event_type=EventType.NARRATIVE,
        actor=None,
        location=EntityRef(id=EntityId()),
        mechanics=MechanicsResult(success=True),
        effects=[],
        narrative_summary=long_summary,
    )
    assert len(event.narrative_summary) <= 150


def test_frozen_entity_immutability():
    entity = Entity(
        id=EntityId(),
        archetype="test",
        properties={"hp": 100},
    )
    updated = entity.with_property("hp", 50)
    assert entity.properties["hp"] == 100
    assert updated.properties["hp"] == 50
