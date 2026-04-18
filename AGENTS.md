# AGENTS.md - Agent Workflow Instructions

## Overview

Nexus Engine is a universal text RPG framework that uses Event Sourcing for long-term consistency and separates "facts" (handled by code) from "expression" (handled by LLM).

## Core Principles

1. **Events are truth, state is projection** - All state changes are immutable events
2. **LLM proposes, code disposes** - LLM suggests, validator verifies, code commits
3. **Query by schema, not by prose** - Use structured queries, not prompt flooding
4. **Validate before commit** - All LLM output must pass validation
5. **Canon is sacred** - Canon facts cannot be violated
6. **Tiered simulation** - Full simulation only for active regions

## Project Structure

```
src/nexus_engine/
├── core/           # Data models (Entity, Event, Ability, Rule)
├── store/          # Event Store (SQLite/Postgres)
├── projection/     # State View (projections from events)
├── rules/          # Rule Engine (tiered resolution)
├── validation/     # Validator layer
├── memory/         # Memory System (Canon + Vector)
├── agents/         # LLM Agent Tools
├── npc/            # NPC Behavior (Drive-Goal-Plan)
├── world/          # World Simulator
├── crystallization/ # Pattern crystallization
├── setting/        # Setting Pack system
└── narrative/     # Narrative pipeline
```

## Development Commands

```bash
# Install in dev mode
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint & Format
ruff check .
ruff format .

# Type check
ty check .
```

## Key Invariants (Must Maintain)

- INV-1: All EntityRef must point to existing entities
- INV-2: Events are immutable once appended
- INV-3: StateView can be fully rebuilt from events
- INV-4: All LLM output must pass Validator before affecting state
- INV-5: Canon facts cannot be violated
- INV-6: All Tags must belong to SettingPack.vocabulary
- INV-7: Ability tier cannot exceed actor tier + allowed_stretch
- INV-8: PersonaContract.forbidden_behaviors cannot be violated
- INV-9: NPC decisions traceable to drives/goals/rules
- INV-10: New entity proposals must pass deduplication check

## LLM Integration Points

When adding LLM integration:

1. **Intent Parsing**: `agents/context_builder.py` - build_scene_context
2. **Ruling Generation**: `rules/rule_engine.py` - third-tier resolution
3. **Narrative Generation**: `narrative/pipeline.py` - narrate function
4. **NPC Ensemble**: `npc/ensemble.py` - ensemble_scene
5. **Director Planning**: `world/director.py` - Director.plan

## Testing Strategy

- **Unit tests**: Core data structures, rule matching, validation logic
- **Integration tests**: Event store, state projection, full pipeline
- **Invariant tests**: Must pass all 10 invariants

## Setting Pack Format

Setting Packs define world-specific rules, archetypes, vocabulary, and lore.
See `nexus_engine/setting/packs/jinyong.py` for a reference implementation.
