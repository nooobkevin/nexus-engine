# Nexus Engine verification map

This directory is the maintained source for verifying the user-facing behavior of Nexus Engine. Read the index before driving the library, then use the matching feature file as the recipe.

## Baseline preconditions

- Current directory is the repository root.
- `python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py doctor` prints `doctor: ok`.
- Set `RUN_ID` to a new token per run. Two runs must not share a run id.
- The example starts from an empty in-memory store. `apply-hp` starts from an empty sqlite file under `/tmp/nexus-verify-runs/$RUN_ID/`.
- Never inspect or delete a sqlite file this run did not create.

## Driving conventions

- Start every recipe from the baseline unless its preconditions say otherwise.
- Treat every command as literal. Keep the `--run-id` flag.
- Run library actions through `verify_nexus.py`.
- Restore nothing in the example. It exits when `main` finishes.
- Do not remove proof artifacts during cleanup.

## Proof and skip reporting

- Capture the command, the transcript, and the stored side effect the feature names.
- Record the feature file and the entry point with the artifact path.
- Report an unreachable path with the command and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.
- `live_hp` without `replay_hp` does not prove the event log.

## Feature entry contract

Each feature file starts with an H1 and one paragraph, then four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with verify_nexus.py`, `Gotchas`.

## Features

- [Run the bundled session](./session-example.md) covers the four sections of `examples/minimal_example.py`.
- [Record an action](./record-action.md) covers appending an attack and reading it back. Passing a target id is a separate entry and fails.
- [Apply damage](./apply-damage.md) covers a live hp change and a second view rebuilt from the sqlite file. The rebuild entry fails.
- [Read the setting vocabulary](./setting-vocabulary.md) covers the jinyong namespaces printed by the example.
