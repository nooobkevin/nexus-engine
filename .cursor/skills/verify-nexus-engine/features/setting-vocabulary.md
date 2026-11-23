# Read the setting vocabulary

Read the setting vocabulary shows the namespaces shipped by `create_jinyong_setting_pack`.

## Sub-features

- `vocab-print` prints the namespace list from the bundled example.
- `vocab-membership` answers whether a tag namespace is in that list.

## How to get to it (user POV)

- Run `examples/minimal_example.py` and read the `Namespaces:` line in the validation section.
- Call `create_jinyong_setting_pack().vocabulary.namespaces` from Python.

## Driving it with verify_nexus.py

Preconditions:

- `doctor` prints `doctor: ok`.
- `RUN_ID` is set and unused.

- **Print namespaces.** Run `python3 .cursor/skills/verify-nexus-engine/scripts/verify_nexus.py example --run-id "$RUN_ID"`. Stdout contains `Namespaces: ['school', 'element', 'technique', 'body_part', 'rank', 'material']` and exit code 0.
- **Proof.** `/tmp/nexus-verify-evidence/$RUN_ID/example.txt` contains that list. The list is the second view of `SettingPack.vocabulary`. No sqlite row stores it.

## Gotchas

- The example prints `Event valid: True` for an event it only checks with `event is not None`. That line does not prove vocabulary enforcement.
- Order in the printed list follows dict order from `create_jinyong_setting_pack`. Compare the six names, not a sorted string, unless the pack starts sorting them.
- This drive does not create a tag or reject an unknown namespace.
