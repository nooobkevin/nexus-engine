# Apply damage

Apply damage lowers the player hp by 10 in the live session and, on a second view, shows the same hp after the live cache is discarded.

## Sub-features

- `damage-live` shows hp 90 after one delta of -10.
- `damage-replay` opens a new `StateView` on the same sqlite file and shows hp 90.

## How to get to it (user POV)

- Build a player with `properties["hp"] == 100`, append a combat `Event` whose effect is `StateChange` path `hp`, operation `DELTA`, value `-10`, then call `StateView.apply`.
- Read hp from `StateView.get_entity`.
- Discard the cache. Construct another `StateView` with the same `SQLiteEventStore` and call `project_from` on `get_since(GameTime(0))`.

The bundled example never takes this path. Its events use `effects=[]`.

## Driving it with verify_nexus.py

Preconditions:

- `doctor` prints `doctor: ok`.
- `RUN_ID` is set and unused.
- `/tmp/nexus-verify-runs/$RUN_ID/` does not already exist.

- **Live damage.** Run `python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py apply-hp --run-id "$RUN_ID"`. Stdout contains `live_hp: 90` and `stored_events: 1`.
- **Replay.** The same command continues. The proof line is `replay_hp: 90` and the process exits 0. The current code prints `replay_error: KeyError: 'target'` and exits 1. The journey fails there.
- **Proof.** `/tmp/nexus-verify-evidence/$RUN_ID/apply-hp.txt` must contain `live_hp: 90`, `stored_events: 1`, and `replay_hp: 90` before this feature is called verified. `replay_error` is a failed journey. The sqlite file is `/tmp/nexus-verify-runs/$RUN_ID/events.sqlite`.

## Gotchas

- `StateView.add_entity` writes only the cache. A replay that never sees a birth event cannot restore the player even after deserialize is fixed. Report that if `replay_error` disappears and `replay_hp` is `None`.
- `Event.effects` is a `frozenset`. A `StateChange` whose value is a dict raises `TypeError: unhashable type: 'dict'` inside `Event.create`, before `append`. This drive uses an int and does not cover that case.
- `Validator.validate_event` is not on this path. The example's validator does not check hp.
- Cleanup removes the sqlite file and keeps `apply-hp.txt`.
