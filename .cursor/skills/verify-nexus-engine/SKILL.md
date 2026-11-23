---
name: verify-nexus-engine
description: Drive the Nexus Engine Python library the way a user does, through examples/minimal_example.py and the public event API. Use when a change touches the example, event append, live state apply, or the jinyong setting pack and you need a transcript as proof.
---

# Verify Nexus Engine

Nexus Engine is a Python library. A user starts it by running `examples/minimal_example.py` or by calling `SQLiteEventStore`, `StateView`, and `Event.create` from Python. There is no web UI, port, or login.

Two processes can run at once. Give each one its own `--run-id`. The example keeps its database in memory. `apply-hp` writes `events.sqlite` under `/tmp/nexus-verify-runs/<run-id>/`. Do not point two drives at the same run id.

The helper is `.cursor/skills/verify-nexus-engine/scripts/verify_nexus.py`. Run it with the repository as the current directory. It puts `src` on `PYTHONPATH` itself.

## Launch

There is no long-lived server. Launch means one short process.

```bash
python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py example --run-id "$RUN_ID"
```

Ready means the process exits 0 and its stdout contains `ALL EXAMPLES COMPLETED!`. The transcript is `/tmp/nexus-verify-evidence/<run-id>/example.txt`. That line is the example's own completion print, after combat, the skill check, the 10-turn loop, and the setting-pack vocabulary print.

Empty data is the starting point. `SQLiteEventStore.initialize` creates the `events` table. The example then inserts players only in the `StateView` cache. No migration runner exists.

## Doctor

Run this before a drive when imports or the example path look wrong. It does not append events.

```bash
python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py doctor
```

Pass requires `doctor: ok`, `import: ok`, and `example: ... exists=True`. There is no port and no auth header to check.

## Drive

Read `.cursor/skills/verify-nexus-engine/features/README.md` and the feature file before driving. Commands:

```bash
python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py example --run-id "$RUN_ID"
python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py apply-hp --run-id "$RUN_ID"
```

`example` runs `examples/minimal_example.py`. `apply-hp` is the damage path. It creates Zhang Wuji at 100 hp, appends one combat event with `StateChange` path `hp`, operation `DELTA`, value `-10`, applies it, prints `live_hp`, then opens a new `StateView` on the same file and prints `replay_hp` or `replay_error`. Exit 0 requires `replay_hp: 90`. `replay_error` exits 1.

## Evidence

Proof is the transcript plus the side effect it names.

- `/tmp/nexus-verify-evidence/<run-id>/example.txt` holds the command stdout, stderr, and exit code.
- `/tmp/nexus-verify-evidence/<run-id>/apply-hp.txt` holds `live_hp`, `stored_events`, and either `replay_hp` or `replay_error`.
- The sqlite file for `apply-hp` is `/tmp/nexus-verify-runs/<run-id>/events.sqlite` until cleanup.

A passing example transcript shows `Player performed attack`, `Total events in store: 10`, the six vocabulary namespaces, and `ALL EXAMPLES COMPLETED!`. A live damage proof shows `live_hp: 90` and `stored_events: 1`. Replay is a second view of the same file. `replay_error` means the damage was not proved from the log. Do not treat `live_hp` alone as persistence.

The example and `apply-hp` call the library the README and the example call. They do not set private fields except by going through `add_entity`, `append`, `apply`, and `project_from`. No network is involved. A missing `OPENAI_API_KEY` does not change these drives. The example never calls LiteLLM.

## Cleanup

Cleanup deletes the run directory it created. It does not delete `/tmp/nexus-verify-evidence`.

```bash
python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py cleanup --run-id "$RUN_ID"
```

The example process has already exited, so there is no pid to kill. Do not kill by the name `python`.

## Helpers

The only helper is the script above. `doctor`, `example`, `apply-hp`, and `cleanup` are the subcommands. `--run-id` defaults to `NEXUS_VERIFY_RUN_ID` or `manual`.
