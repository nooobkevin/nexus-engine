#!/usr/bin/env python3
"""Check that StateView hp survives discarding the cache.

Exit 0 only when every generated integer DELTA replays and a dict SET can be
stored. Exit 1 prints each finding in library terms. The temp database is removed.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from nexus_engine.core.entity import Entity
from nexus_engine.core.event import Event, MechanicsResult, Operation, StateChange
from nexus_engine.core.value_objects import EntityRef, EventType, GameTime, new_entity_id
from nexus_engine.projection.state_view import StateView
from nexus_engine.store.sqlite_event_store import SQLiteEventStore

SYNC_COMMIT = "dedb626af41f01ca30d7ce909aaa336e7ed015e5"
DELTAS = [value for value in range(-5, 6) if value != 0]


async def check_delta(root: Path, delta: int) -> str | None:
    db_path = root / f"delta-{delta}.sqlite"
    store = SQLiteEventStore(str(db_path))
    await store.initialize()
    try:
        view = StateView(store)
        player = new_entity_id()
        place = new_entity_id()
        view.add_entity(Entity(id=player, archetype="swordsman", properties={"hp": 100}))
        view.add_entity(Entity(id=place, archetype="place", properties={"name": "Wudang"}))
        event = Event.create(
            game_time=GameTime(1),
            event_type=EventType.COMBAT,
            actor=EntityRef(id=player),
            location=EntityRef(id=place),
            mechanics=MechanicsResult(success=True, degree=1.0),
            effects=[StateChange(EntityRef(id=player), "hp", Operation.DELTA, delta)],
            narrative_summary="hit",
        )
        await store.append(event)
        await view.apply(event)
        live = (await view.get_entity(player)).properties["hp"]
        expected = 100 + delta
        if live != expected:
            return f"live apply: DELTA {delta} left hp {live}, expected {expected}"
        rebuilt = StateView(store)
        try:
            await rebuilt.project_from(store.get_since(GameTime(0)))
        except Exception as exc:
            return (
                f"replay: DELTA {delta} live hp {live}, then "
                f"{type(exc).__name__}: {exc} in SQLiteEventStore._deserialize_event"
            )
        again = await rebuilt.get_entity(player)
        if again is None:
            return f"replay: DELTA {delta} live hp {live}, rebuilt StateView has no player"
        replay_hp = again.properties.get("hp")
        if replay_hp != expected:
            return f"replay: DELTA {delta} live hp {live}, rebuilt hp {replay_hp}, expected {expected}"
        return None
    finally:
        await store.close()


async def check_dict() -> str | None:
    player = new_entity_id()
    place = new_entity_id()
    try:
        Event.create(
            game_time=GameTime(1),
            event_type=EventType.COMBAT,
            actor=EntityRef(id=player),
            location=EntityRef(id=place),
            mechanics=MechanicsResult(success=True, degree=1.0),
            effects=[StateChange(EntityRef(id=player), "stats", Operation.SET, {"hp": 90})],
            narrative_summary="set",
        )
    except TypeError as exc:
        return f"dict effect: Event.create raised TypeError: {exc}"
    return None


async def main() -> int:
    print(f"sync_commit: {SYNC_COMMIT}")
    print("property: rebuilt hp equals live hp after an integer DELTA")
    findings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="nexus-inv3-") as tmp:
        for delta in DELTAS:
            finding = await check_delta(Path(tmp), delta)
            if finding:
                findings.append(finding)
                break
    dict_finding = await check_dict()
    if dict_finding:
        findings.append(dict_finding)
    if not findings:
        print("findings: none")
        return 0
    print(f"findings: {len(findings)}")
    for item in findings:
        print(f"- {item}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
