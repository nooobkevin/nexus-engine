---
name: verify-event-replay
description: Re-check the Nexus Engine promise that a discarded StateView can be rebuilt from SQLiteEventStore. Use when a change touches Event.create, StateChange, SQLiteEventStore append or deserialize, or StateView.apply and project_from.
---

# Verify event replay

Property: after `StateView.apply` commits an integer `DELTA` on `hp`, a new `StateView` built with `project_from(store.get_since(GameTime(0)))` shows the same `hp`.

Harm: a saved session loads the log and shows the hp from before the blow, or it crashes while reading the row it just wrote.

The check runs the real `Event.create`, `SQLiteEventStore.append`, `StateView.apply`, and `StateView.project_from`. It is not a separate model of those functions. TLA+ would hide the deserialize bug behind a hand-written step. CrossHair does not drive `aiosqlite`. A seeded loop over the real functions is the check.

## When a change needs this

Run it when the diff touches any of these:

- `src/nexus_engine/core/event.py`, functions `Event.create` and `StateChange.apply`
- `src/nexus_engine/store/sqlite_event_store.py`, functions `_serialize_event`, `_deserialize_event`, `append`, `get_since`
- `src/nexus_engine/projection/state_view.py`, functions `StateView.apply`, `StateView._apply_effect`, `StateView.project_from`, `StateView.add_entity`

If those files match commit `dedb626af41f01ca30d7ce909aaa336e7ed015e5` and this script is unchanged, the recorded findings below are the expected result. If those files differ from that commit, the findings are stale until you run the check and read the new transcript. Move the sync commit forward only after you confirm the script still describes the code at the new commit. Record the new sha in this section and in the transcript header the script prints.

## Run

From the repository root:

```bash
python3 .cursor/skills/verify-event-replay/check_replay.py
```

The script sets `PYTHONPATH` to `src` when it is launched as a file. Python 3.11 or newer and `aiosqlite` are required. No network. The database is a temp directory the script deletes.

Exit 0 means every integer delta from -5 through 5, excluding 0, replays to `100 + delta`, and `Event.create` accepts a `SET` whose value is a dict.

Exit 1 means at least one finding. The baseline at the sync commit is exit 1 with both findings below and no others.

- Integer deltas: live `hp` is `100 + delta`, then replay raises `KeyError: 'target'` in `SQLiteEventStore._deserialize_event`. The reader uses `data["target"]` on the event dict. The writer stored the id on each effect as `e["target"]`.
- Dict value: `Event.create` raises `TypeError: unhashable type: 'dict'` because `Event.effects` is a `frozenset` and `StateChange.value` is unhashable. `StateChange.apply` itself can `SET` a dict.

A transcript that adds a `live apply` finding, an `ImportError`, or a `KeyError` on a different key is a new break or a modeling error. A modeling error is an exception before `Event.create`, or a stack that does not mention `event.py`, `sqlite_event_store.py`, or `state_view.py`. Do not delete a finding to make the exit code 0. A product fix is the only way the two baseline findings disappear.

## Bounds

- One entity, one path `hp`, start value 100.
- Deltas are the eleven integers from -5 to 5 except 0.
- One dict case, `SET` of `{"hp": 90}` on path `stats`.
- Single-threaded. One connection. No snapshot store. No validator. No second effect on the same event.

Left out: concurrent appends, tags, canon, nested property paths, `APPEND` and `REMOVE`, and entity birth as an event. `add_entity` is cache-only, so a green replay still has to be read against that limit. If deserialize starts succeeding and `replay hp` is missing, that is the birth gap, not a pass.

## Update

When the covered functions change on purpose, run the script, replace the finding text in this file with the new transcript, and set the sync commit to the commit you just ran against. Keep the property sentence. Do not narrow the delta set or skip the dict case to obtain exit 0.
