# Record an action

Record an action stores one player attack in the event log and reads that summary back.

## Sub-features

- `record-untargeted` stores an attack with no target and queries it.
- `record-targeted` stores an attack aimed at an existing entity.

## How to get to it (user POV)

- Run the combat section of `examples/minimal_example.py`. The attack has no target. The query prints `[0] action: Player performed attack`.
- Call `GameSession.process_action("attack", target_id=<an entity id>)` in `examples/minimal_example.py`.

## Driving it with verify_nexus.py

Preconditions:

- `doctor` prints `doctor: ok`.
- `RUN_ID` is set and unused.

- **Untargeted attack.** Run `python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py example --run-id "$RUN_ID"`. The transcript contains `[0] action: Player performed attack` and exit code 0.
- **Proof for the untargeted attack.** `/tmp/nexus-verify-evidence/$RUN_ID/example.txt` contains that query line. The example's query is the second view. It reads the in-memory store, not the `StateView` cache.
- **Targeted attack.** This entry has no helper subcommand. Run `GameSession.process_action("attack", target_id=npc_id)` from a Python process with `PYTHONPATH=src`. The journey fails. `process_action` puts the raw id into `Event.create(..., targets=)`. `SQLiteEventStore.append` then raises `AttributeError: 'UUID' object has no attribute 'id'`.

## Gotchas

- Do not mark `record-targeted` verified because `record-untargeted` printed an attack line.
- The example constructs a fresh `EntityId()` as the event location. Querying by the player's location id does not find the attack.
- `get_entity_history` in the skill-check section prints the athletics line only because the actor id matches. It is not proof that a target id round-trips.
