# Run the bundled session

The bundled session prints a wuxia combat beat, a skill check, a 10-turn loop, and the setting vocabulary, then exits.

## Sub-features

- `session-combat` prints the player hp line and one attack summary.
- `session-check` prints an athletics check and one history line.
- `session-world` prints the stored event count after ten turns.
- `session-vocab` prints the setting namespaces.

## How to get to it (user POV)

- From the repository root, run `python3 examples/minimal_example.py` with `PYTHONPATH=src`.
- The same process is what `verify_nexus.py example` launches. There is no other menu or flag.

## Driving it with verify_nexus.py

Preconditions:

- `doctor` prints `doctor: ok`.
- `RUN_ID` is set and unused.

- **Run the session.** Run `python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py example --run-id "$RUN_ID"`. Exit code is 0. Stdout contains `Player HP: 100/100`, `Action result: Player performed attack`, `Total events in store: 10`, `Namespaces:`, and `ALL EXAMPLES COMPLETED!`.
- **Proof.** Read `/tmp/nexus-verify-evidence/$RUN_ID/example.txt`. It records the exit code and the full stdout. The file remains after `cleanup --run-id "$RUN_ID"`.

## Gotchas

- The attack in this example passes no target. A transcript of this entry does not prove `process_action` with a target id. That entry is in `record-action.md` and fails.
- The printed events have no `StateChange`. A completed example does not prove hp can be rebuilt from the log. That entry is in `apply-damage.md` and the replay step fails.
- `Total events in store: 10` counts the world-simulation session only. It is not the combat session and not a rebuilt `StateView`.
- NPC lines are absent. `run_npc_turn` is called with a new `EntityId()` that is not in the cache, so the turn returns no events. Do not invent an NPC line to make the transcript look busy.
