#!/usr/bin/env python3
"""Drive Nexus Engine the way a user does, and keep proof after cleanup.

This is a library. There is no server. Each drive is one process with its own
data directory. Evidence is written under /tmp/nexus-verify-evidence and is
never deleted by cleanup.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_ROOT = Path("/tmp/nexus-verify-evidence")
RUN_ROOT = Path("/tmp/nexus-verify-runs")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not previous else src + os.pathsep + previous
    return env


def _run_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    return os.environ.get("NEXUS_VERIFY_RUN_ID", "manual")


def doctor() -> int:
    print(f"root: {ROOT}")
    print(f"python: {sys.version.split()[0]}")
    probe = textwrap.dedent(
        """
        import aiosqlite
        import nexus_engine
        from nexus_engine.store.sqlite_event_store import SQLiteEventStore
        from nexus_engine.projection.state_view import StateView
        print("import: ok")
        print("aiosqlite:", aiosqlite.__version__ if hasattr(aiosqlite, "__version__") else "present")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    example = ROOT / "examples" / "minimal_example.py"
    print(f"example: {example} exists={example.is_file()}")
    print("port: none")
    print("isolation: one sqlite file or :memory: per process")
    if result.returncode != 0 or not example.is_file():
        print("doctor: fail")
        return 1
    print("doctor: ok")
    return 0


def _write_transcript(evidence: Path, name: str, result: subprocess.CompletedProcess[str]) -> None:
    evidence.mkdir(parents=True, exist_ok=True)
    path = evidence / name
    path.write_text(
        f"exit: {result.returncode}\n\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
        encoding="utf-8",
    )
    print(f"evidence: {path}")
    print(f"exit: {result.returncode}")


def drive_example(run_id: str) -> int:
    evidence = EVIDENCE_ROOT / run_id
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "minimal_example.py")],
        cwd=ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )
    _write_transcript(evidence, "example.txt", result)
    ready = result.returncode == 0 and "ALL EXAMPLES COMPLETED!" in result.stdout
    print(f"ready: {ready}")
    return 0 if ready else 1


def drive_apply_hp(run_id: str) -> int:
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "events.sqlite"
    evidence = EVIDENCE_ROOT / run_id
    script = textwrap.dedent(
        f"""
        import asyncio
        from nexus_engine.core.entity import Entity
        from nexus_engine.core.event import Event, MechanicsResult, Operation, StateChange
        from nexus_engine.core.value_objects import EntityId, EntityRef, EventType, GameTime, new_entity_id
        from nexus_engine.projection.state_view import StateView
        from nexus_engine.store.sqlite_event_store import SQLiteEventStore

        async def main():
            store = SQLiteEventStore({str(db_path)!r})
            await store.initialize()
            view = StateView(store)
            player = new_entity_id()
            place = new_entity_id()
            view.add_entity(Entity(id=player, archetype="swordsman", properties={{"name": "Zhang Wuji", "hp": 100}}))
            view.add_entity(Entity(id=place, archetype="place", properties={{"name": "Wudang"}}))
            event = Event.create(
                game_time=GameTime(1),
                event_type=EventType.COMBAT,
                actor=EntityRef(id=player),
                location=EntityRef(id=place),
                mechanics=MechanicsResult(success=True, degree=1.0),
                effects=[StateChange(EntityRef(id=player), "hp", Operation.DELTA, -10)],
                narrative_summary="Player performed attack",
            )
            await store.append(event)
            await view.apply(event)
            live = (await view.get_entity(player)).properties["hp"]
            print(f"live_hp: {{live}}")
            print(f"stored_events: {{await store.count()}}")
            rebuilt = StateView(store)
            failed = False
            try:
                await rebuilt.project_from(store.get_since(GameTime(0)))
                again = await rebuilt.get_entity(player)
                replay_hp = None if again is None else again.properties.get("hp")
                print(f"replay_hp: {{replay_hp}}")
                failed = replay_hp != 90
            except Exception as exc:
                print(f"replay_error: {{type(exc).__name__}}: {{exc}}")
                failed = True
            await store.close()
            if failed:
                raise SystemExit(1)

        asyncio.run(main())
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=_env(),
        text=True,
        capture_output=True,
    )
    _write_transcript(evidence, "apply-hp.txt", result)
    print(f"run_dir: {run_dir}")
    return result.returncode


def cleanup(run_id: str) -> int:
    run_dir = RUN_ROOT / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
        print(f"removed: {run_dir}")
    else:
        print(f"absent: {run_dir}")
    evidence = EVIDENCE_ROOT / run_id
    print(f"evidence_kept: {evidence} exists={evidence.exists()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    example = sub.add_parser("example")
    example.add_argument("--run-id", default=None)
    apply_hp = sub.add_parser("apply-hp")
    apply_hp.add_argument("--run-id", default=None)
    clean = sub.add_parser("cleanup")
    clean.add_argument("--run-id", default=None)
    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    run_id = _run_id(getattr(args, "run_id", None))
    if args.command == "example":
        return drive_example(run_id)
    if args.command == "apply-hp":
        return drive_apply_hp(run_id)
    if args.command == "cleanup":
        return cleanup(run_id)
    return 2


if __name__ == "__main__":
    sys.exit(main())
