from __future__ import annotations

import json
from typing import Any, AsyncIterator

import aiosqlite

from nexus_engine.core.event import Event, MechanicsResult, StateChange, Operation
from nexus_engine.core.value_objects import (
    EntityRef,
    EventId,
    EventType,
    GameTime,
)
from nexus_engine.store.event_store import EventFilter, EventStore


class SQLiteEventStore(EventStore):
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                game_time INTEGER NOT NULL,
                type TEXT NOT NULL,
                actor_id TEXT,
                targets TEXT,
                location_id TEXT,
                mechanics TEXT,
                effects TEXT,
                witnesses TEXT,
                narrative_summary TEXT,
                narrative_full TEXT,
                parent_event_id TEXT,
                canon INTEGER DEFAULT 0,
                tags TEXT,
                raw TEXT NOT NULL
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_game_time ON events(game_time)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_location ON events(location_id)"
        )

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _serialize_event(self, event: Event) -> dict[str, Any]:
        return {
            "id": str(event.id),
            "game_time": event.game_time.ticks,
            "type": event.type.value,
            "actor": str(event.actor.id) if event.actor else None,
            "targets": [str(t.id) for t in event.targets],
            "location": str(event.location.id),
            "mechanics": {
                "success": event.mechanics.success,
                "degree": event.mechanics.degree,
                "values": event.mechanics.values,
                "roll": event.mechanics.roll,
                "difficulty": event.mechanics.difficulty,
            },
            "effects": [
                {
                    "target": str(e.target.id),
                    "path": e.path,
                    "operation": e.operation.value,
                    "value": e.value,
                }
                for e in event.effects
            ],
            "witnesses": [str(w.id) for w in event.witnesses],
            "narrative_summary": event.narrative_summary,
            "narrative_full": event.narrative_full,
            "parent_event": str(event.parent_event) if event.parent_event else None,
            "canon": event.canon,
            "tags": [str(t) for t in event.tags],
        }

    def _deserialize_event(self, data: dict[str, Any]) -> Event:
        mechanics = MechanicsResult(
            success=data["mechanics"]["success"],
            degree=data["mechanics"]["degree"],
            values=data["mechanics"].get("values", {}),
            roll=data["mechanics"].get("roll"),
            difficulty=data["mechanics"].get("difficulty"),
        )

        effects = [
            StateChange(
                target=EntityRef(id=data["target"]),
                path=e["path"],
                operation=Operation(e["operation"]),
                value=e["value"],
            )
            for e in data["effects"]
        ]

        from uuid import UUID

        return Event(
            id=UUID(data["id"]),
            game_time=GameTime(data["game_time"]),
            type=EventType(data["type"]),
            actor=EntityRef(id=UUID(data["actor"])) if data["actor"] else None,
            targets=frozenset(EntityRef(id=UUID(t)) for t in data["targets"]),
            location=EntityRef(id=UUID(data["location"])),
            mechanics=mechanics,
            effects=frozenset(effects),
            witnesses=frozenset(EntityRef(id=UUID(w)) for w in data["witnesses"]),
            narrative_summary=data["narrative_summary"],
            narrative_full=data.get("narrative_full"),
            parent_event=UUID(data["parent_event"])
            if data.get("parent_event")
            else None,
            canon=bool(data.get("canon", False)),
            tags=frozenset(),
        )

    async def append(self, event: Event) -> EventId:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        raw = self._serialize_event(event)
        raw_json = json.dumps(raw)
        await self._conn.execute(
            """
            INSERT INTO events (
                id, game_time, type, actor_id, targets, location_id,
                mechanics, effects, witnesses, narrative_summary, narrative_full,
                parent_event_id, canon, tags, raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(event.id),
                event.game_time.ticks,
                event.type.value,
                str(event.actor.id) if event.actor else None,
                json.dumps([str(t.id) for t in event.targets]),
                str(event.location.id),
                json.dumps(raw["mechanics"]),
                json.dumps(raw["effects"]),
                json.dumps([str(w.id) for w in event.witnesses]),
                event.narrative_summary,
                event.narrative_full,
                str(event.parent_event) if event.parent_event else None,
                1 if event.canon else 0,
                json.dumps([str(t) for t in event.tags]),
                raw_json,
            ),
        )
        await self._conn.commit()
        return event.id

    async def get(self, id: EventId) -> Event | None:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        async with self._conn.execute(
            "SELECT raw FROM events WHERE id = ?", (str(id),)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._deserialize_event(json.loads(row[0]))
        return None

    def query(self, filter: EventFilter) -> AsyncIterator[Event]:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        conn = self._conn

        async def _query() -> AsyncIterator[Event]:
            query = "SELECT raw FROM events WHERE 1=1"
            params: list[Any] = []

            if filter.actor:
                query += " AND actor_id = ?"
                params.append(filter.actor)
            if filter.location:
                query += " AND location_id = ?"
                params.append(filter.location)
            if filter.types:
                placeholders = ",".join("?" * len(filter.types))
                query += f" AND type IN ({placeholders})"
                params.extend(filter.types)
            if filter.time_range:
                query += " AND game_time >= ? AND game_time <= ?"
                params.extend([filter.time_range[0].ticks, filter.time_range[1].ticks])
            if filter.involves_entity:
                query += " AND (actor_id = ? OR targets LIKE ?)"
                params.append(filter.involves_entity)
                params.append(f"%{filter.involves_entity}%")

            query += " ORDER BY game_time LIMIT ?"
            params.append(filter.limit)

            async with conn.execute(query, params) as cursor:
                async for row in cursor:
                    yield self._deserialize_event(json.loads(row[0]))

        return _query()

    def get_since(self, time: GameTime) -> AsyncIterator[Event]:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        conn = self._conn

        async def _get_since() -> AsyncIterator[Event]:
            async with conn.execute(
                "SELECT raw FROM events WHERE game_time >= ? ORDER BY game_time",
                (time.ticks,),
            ) as cursor:
                async for row in cursor:
                    yield self._deserialize_event(json.loads(row[0]))

        return _get_since()

    def get_entity_history(
        self, entity_id: str, since: GameTime | None = None
    ) -> AsyncIterator[Event]:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        conn = self._conn

        async def _get_history() -> AsyncIterator[Event]:
            query = "SELECT raw FROM events WHERE actor_id = ? OR targets LIKE ?"
            params: list[Any] = [entity_id, f"%{entity_id}%"]
            if since:
                query += " AND game_time >= ?"
                params.append(since.ticks)
            query += " ORDER BY game_time"
            async with conn.execute(query, params) as cursor:
                async for row in cursor:
                    yield self._deserialize_event(json.loads(row[0]))

        return _get_history()

    async def count(self) -> int:
        if not self._conn:
            raise RuntimeError("EventStore not initialized")
        conn = self._conn
        async with conn.execute("SELECT COUNT(*) FROM events") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
