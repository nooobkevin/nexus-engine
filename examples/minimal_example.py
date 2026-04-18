from __future__ import annotations

import asyncio
from dataclasses import dataclass

from nexus_engine.core.value_objects import (
    EntityId,
    EntityRef,
    EventType,
    GameTime,
    Tag,
    new_entity_id,
)
from nexus_engine.core.entity import Entity, Location, Player
from nexus_engine.core.event import Event, MechanicsResult, StateChange, Operation
from nexus_engine.core.ability import Rule, MatchPattern, Outcome
from nexus_engine.store.event_store import EventFilter
from nexus_engine.store.sqlite_event_store import SQLiteEventStore
from nexus_engine.projection.state_view import StateView
from nexus_engine.rules.rule_engine import RuleEngine
from nexus_engine.rules.resolvers import DEFAULT_RESOLVERS
from nexus_engine.validation.validator import Validator
from nexus_engine.setting.setting_pack import SettingPack, create_minimal_setting_pack
from nexus_engine.setting.packs.jinyong import create_jinyong_setting_pack
from nexus_engine.npc.drives import DRIVE_SURVIVAL, DRIVE_SOCIAL, get_default_drives, NPCContext
from nexus_engine.npc.goals import GoalGenerator
from nexus_engine.npc.ensemble import npc_tick


@dataclass
class GameSession:
    event_store: SQLiteEventStore
    state_view: StateView
    rule_engine: RuleEngine
    validator: Validator
    setting: SettingPack
    player_id: EntityId
    current_time: GameTime

    @classmethod
    async def create(cls) -> "GameSession":
        event_store = SQLiteEventStore(":memory:")
        await event_store.initialize()

        state_view = StateView(event_store)

        rule_engine = RuleEngine()
        for name, resolver in DEFAULT_RESOLVERS.items():
            rule_engine.register_resolver(name, resolver)

        validator = Validator()
        setting = create_jinyong_setting_pack()

        player_id = new_entity_id()
        state_view.add_entity(Entity(
            id=player_id,
            archetype="swordsman",
            properties={
                "name": "Zhang Wuji",
                "hp": 100,
                "max_hp": 100,
                "qi": 100,
                "max_qi": 100,
                "skills": {"sword": 5, "internal_force": 3},
                "resources": {"qi": 100},
            },
        ))

        location_id = new_entity_id()
        state_view.add_entity(Location(
            id=location_id,
            archetype="wuxia_location",
            properties={
                "name": "Wudang Mountain",
                "description": "A misty mountain known for its sword techniques",
            },
        ))

        npc_id = new_entity_id()
        state_view.add_entity(Entity(
            id=npc_id,
            archetype="npc",
            properties={
                "name": "Zhang Cuishan",
                "hp": 80,
                "faction": "Wudang",
                "skills": {"sword": 6},
            },
        ))

        return cls(
            event_store=event_store,
            state_view=state_view,
            rule_engine=rule_engine,
            validator=validator,
            setting=setting,
            player_id=player_id,
            current_time=GameTime(0),
        )

    async def process_action(self, action_type: str, target_id: EntityId | None = None) -> Event:
        actor_ref = EntityRef(id=self.player_id)
        target_ref = EntityRef(id=target_id) if target_id else None
        targets = [target_ref] if target_ref else []

        mechanics = MechanicsResult(success=True, degree=0.5)

        event = Event.create(
            game_time=self.current_time,
            event_type=EventType.ACTION,
            actor=actor_ref,
            location=EntityRef(id=EntityId()),
            mechanics=mechanics,
            effects=[],
            narrative_summary=f"Player performed {action_type}",
            targets=[t.id for t in targets] if targets else [],
        )

        validation = await self.validator.validate_event(event)
        if not validation.failed:
            await self.event_store.append(event)
            await self.state_view.apply(event)
            self.current_time = self.current_time.advance(1)

        return event

    async def run_npc_turn(self, npc_id: EntityId) -> list[Event]:
        npc = await self.state_view.get_entity(npc_id)
        if not npc:
            return []

        context = NPCContext(
            world_time=self.current_time,
            current_location=EntityId(),
        )

        events = await npc_tick(npc, 1, context)
        for event in events:
            await self.event_store.append(event)
            await self.state_view.apply(event)

        return events


async def example_combat():
    print("=" * 50)
    print("Example: WUXIA COMBAT")
    print("=" * 50)

    session = await GameSession.create()

    print(f"\nPlayer: {session.player_id}")
    player = await session.state_view.get_entity(session.player_id)
    print(f"Player HP: {player.properties['hp']}/{player.properties['max_hp']}")
    print(f"Player Qi: {player.properties['qi']}/{player.properties['max_qi']}")

    print("\n--- Player attacks! ---")
    event = await session.process_action("attack")
    print(f"Action result: {event.narrative_summary}")

    print("\n--- NPC turn ---")
    events = await session.run_npc_turn(EntityId())
    for e in events:
        print(f"NPC action: {e.narrative_summary}")

    print("\n--- Query events ---")
    async for e in session.event_store.query(EventFilter(limit=5)):
        print(f"  [{e.game_time.ticks}] {e.type.value}: {e.narrative_summary}")


async def example_skill_check():
    print("\n" + "=" * 50)
    print("Example: SKILL CHECK")
    print("=" * 50)

    session = await GameSession.create()

    print("\n--- Player attempts to climb a mountain ---")
    event = await session.process_action("athletics_check")
    print(f"Action result: {event.narrative_summary}")

    print("\n--- Query player history ---")
    async for e in session.event_store.get_entity_history(str(session.player_id)):
        print(f"  [{e.game_time.ticks}] {e.narrative_summary}")


async def example_world_simulation():
    print("\n" + "=" * 50)
    print("Example: WORLD SIMULATION")
    print("=" * 50)

    session = await GameSession.create()

    print("\n--- Simulating 10 turns ---")
    for i in range(10):
        event = await session.process_action(f"turn_{i}")
        if i % 3 == 0:
            npc_events = await session.run_npc_turn(EntityId())
            for e in npc_events:
                print(f"  NPC: {e.narrative_summary}")

    print(f"\nTotal events in store: {await session.event_store.count()}")


async def example_validation():
    print("\n" + "=" * 50)
    print("Example: VALIDATION LAYER")
    print("=" * 50)

    session = await GameSession.create()

    print("\n--- Creating invalid event (missing required fields) ---")
    actor_ref = EntityRef(id=session.player_id)

    event = Event.create(
        game_time=GameTime(0),
        event_type=EventType.ACTION,
        actor=actor_ref,
        location=EntityRef(id=EntityId()),
        mechanics=MechanicsResult(success=True, degree=1.0),
        effects=[],
        narrative_summary="Test event",
    )

    print(f"\nEvent created: {event.id}")
    print(f"Event valid: {event is not None}")

    print("\n--- Setting Pack Vocabularies ---")
    vocab = session.setting.vocabulary
    if vocab:
        print(f"Namespaces: {list(vocab.namespaces)}")


async def main():
    await example_combat()
    await example_skill_check()
    await example_world_simulation()
    await example_validation()

    print("\n" + "=" * 50)
    print("ALL EXAMPLES COMPLETED!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
