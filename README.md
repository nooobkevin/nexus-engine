# Nexus Engine

**Universal Text RPG Framework with Event Sourcing**

A general-purpose framework for building text-based RPGs and interactive narratives. Nexus Engine uses Event Sourcing architecture to maintain long-term consistency, separating "facts" (handled by code) from "expression" (handled by LLM).

## Features

- **Event Sourcing Architecture** - Immutable event streams as source of truth, enabling perfect state reconstruction
- **Separation of Concerns** - Rules engine handles mechanics, LLM handles narrative
- **Tiered Simulation** - Full simulation for active regions, fast-forward for distant areas
- **NPC Behavior System** - Drive-Goal-Plan based autonomous NPCs
- **Crystallization** - Successful emergent patterns automatically become new rules
- **Setting Pack System** - Framework-agnostic world definitions (D&D, Wuxia, Cthulhu, etc.)
- **LLM Integration** - Structured queries instead of prompt flooding

## Architecture

```
nexus_engine/
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
└── narrative/      # Narrative pipeline
```

## Core Principles

1. **Events are truth, state is projection** - All state changes are immutable events
2. **LLM proposes, code disposes** - LLM suggests, validator verifies, code commits
3. **Query by schema, not by prose** - Use structured queries, not prompt flooding
4. **Validate before commit** - All LLM output must pass validation
5. **Canon is sacred** - Canon facts cannot be violated
6. **Tiered simulation** - Full simulation only for active regions

## Installation

```bash
# Clone the repository
git clone https://github.com/nooobkevin/nexus-engine.git
cd nexus-engine

# Install dependencies
uv pip install -e .
```

## Quick Start

```python
import asyncio
from nexus_engine.core.value_objects import EntityId, EntityRef, GameTime
from nexus_engine.store.sqlite_event_store import SQLiteEventStore
from nexus_engine.projection.state_view import StateView
from nexus_engine.rules.rule_engine import RuleEngine
from nexus_engine.validation.validator import Validator
from nexus_engine.setting.packs.jinyong import create_jinyong_setting_pack

async def main():
    # Initialize components
    event_store = SQLiteEventStore(":memory:")
    await event_store.initialize()
    state_view = StateView(event_store)
    rule_engine = RuleEngine()
    validator = Validator()
    setting = create_jinyong_setting_pack()

    # Create player
    from nexus_engine.core.entity import Entity
    player_id = EntityId()
    state_view.add_entity(Entity(
        id=player_id,
        archetype="swordsman",
        properties={"name": "Zhang Wuji", "hp": 100, "qi": 100},
    ))

    # Process actions and events
    from nexus_engine.core.event import Event, MechanicsResult, EventType
    event = Event.create(
        game_time=GameTime(0),
        event_type=EventType.ACTION,
        actor=EntityRef(id=player_id),
        location=EntityRef(id=EntityId()),
        mechanics=MechanicsResult(success=True, degree=1.0),
        effects=[],
        narrative_summary="Player attacks!",
    )

    await event_store.append(event)
    await state_view.apply(event)

    # Query events
    from nexus_engine.store.event_store import EventFilter
    async for e in event_store.query(EventFilter(limit=10)):
        print(f"[{e.game_time.ticks}] {e.narrative_summary}")

asyncio.run(main())
```

Run the full example:
```bash
cd examples
uv run python minimal_example.py
```

## Setting Packs

Nexus Engine is setting-agnostic. Create custom Setting Packs for any world:

```python
from nexus_engine.setting.setting_pack import (
    SettingPack, Archetype, ControlledVocabulary, PowerSystemSpec
)
from nexus_engine.core.value_objects import Tag, TierLevel

# Define vocabulary
vocab = ControlledVocabulary(
    namespaces={"material", "technique", "faction"},
    tags_by_namespace={
        "material": frozenset(["steel", "jade"]),
        "technique": frozenset(["sword", "palm"]),
        "faction": frozenset(["wudang", "shaolin"]),
    }
)

# Define archetypes
archetypes = {
    "swordsman": Archetype(
        id="swordsman",
        name="Swordsman",
        description="Sword combat specialist",
        base_tags=frozenset([Tag("technique", "sword")]),
        power_tier=TierLevel.MUNDANE,
    )
}

# Create setting pack
setting = SettingPack(
    id="my_setting",
    version="1.0.0",
    archetypes=archetypes,
    vocabulary=vocab,
)
```

## Development

```bash
# Install in dev mode
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check .
```

## Key Invariants

The framework maintains these invariants:

- **INV-1**: All EntityRef must point to existing entities
- **INV-2**: Events are immutable once appended
- **INV-3**: StateView can be fully rebuilt from events
- **INV-4**: All LLM output must pass Validator before affecting state
- **INV-5**: Canon facts cannot be violated
- **INV-6**: All Tags must belong to SettingPack.vocabulary
- **INV-7**: Ability tier cannot exceed actor tier + allowed_stretch
- **INV-8**: PersonaContract.forbidden_behaviors cannot be violated
- **INV-9**: NPC decisions traceable to drives/goals/rules
- **INV-10**: New entity proposals must pass deduplication check

## License

MIT
