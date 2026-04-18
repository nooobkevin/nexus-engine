from __future__ import annotations

import json
from typing import Any

import aiosqlite

from nexus_engine.core.value_objects import EventId, GameTime


class Snapshot:
    def __init__(self, game_time: GameTime, event_id: EventId, state: dict[str, Any]):
        self.game_time = game_time
        self.event_id = event_id
        self.state = state

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_time": self.game_time.ticks,
            "event_id": str(self.event_id),
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        return cls(
            game_time=GameTime(data["game_time"]),
            event_id=EventId(data["event_id"]),
            state=data["state"],
        )


class SnapshotStore:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_time INTEGER NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL
            )
            """
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_game_time ON snapshots(game_time)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_event_id ON snapshots(event_id)"
        )

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def save(self, snapshot: Snapshot) -> None:
        if not self._conn:
            raise RuntimeError("SnapshotStore not initialized")
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO snapshots (game_time, event_id, state)
            VALUES (?, ?, ?)
            """,
            (
                snapshot.game_time.ticks,
                str(snapshot.event_id),
                json.dumps(snapshot.state),
            ),
        )
        await self._conn.commit()

    async def load(self, event_id: EventId) -> Snapshot | None:
        if not self._conn:
            raise RuntimeError("SnapshotStore not initialized")
        async with self._conn.execute(
            "SELECT state FROM snapshots WHERE event_id = ?", (str(event_id),)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Snapshot.from_dict(json.loads(row[0]))
        return None

    async def load_nearest(self, game_time: GameTime) -> Snapshot | None:
        if not self._conn:
            raise RuntimeError("SnapshotStore not initialized")
        async with self._conn.execute(
            """
            SELECT state FROM snapshots 
            WHERE game_time <= ? 
            ORDER BY game_time DESC 
            LIMIT 1
            """,
            (game_time.ticks,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Snapshot.from_dict(json.loads(row[0]))
        return None

    async def load_latest(self) -> Snapshot | None:
        if not self._conn:
            raise RuntimeError("SnapshotStore not initialized")
        async with self._conn.execute(
            "SELECT state FROM snapshots ORDER BY game_time DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Snapshot.from_dict(json.loads(row[0]))
        return None

    async def delete_after(self, game_time: GameTime) -> int:
        if not self._conn:
            raise RuntimeError("SnapshotStore not initialized")
        cursor = await self._conn.execute(
            "DELETE FROM snapshots WHERE game_time > ?", (game_time.ticks,)
        )
        await self._conn.commit()
        return cursor.rowcount
