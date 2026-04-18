from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nexus_engine.agents.llm_interface import LLMInterface
from nexus_engine.core.value_objects import GameTime


@dataclass
class WorldConfig:
    proximity_config: Any = None
    tick_interval: int = 1
    director_interval: int = 100


@dataclass
class NarrativeBlueprint:
    pacing_adjustments: dict[str, Any] = field(default_factory=dict)
    recommended_encounters: list[dict[str, Any]] = field(default_factory=list)
    foreshadowing_hooks: list[str] = field(default_factory=list)
    schedule_modifications: dict[str, Any] = field(default_factory=dict)


class Director:
    def __init__(self, llm: LLMInterface | None = None):
        self.llm = llm
        self._ticks_since_plan = 0
        self._current_blueprint: NarrativeBlueprint | None = None

    async def plan(
        self,
        world_state: Any,
        player_arc: dict[str, Any] | None = None,
    ) -> NarrativeBlueprint:
        if self._ticks_since_plan < 100:
            return self._current_blueprint or NarrativeBlueprint()

        self._ticks_since_plan = 0

        if self.llm is None:
            self._current_blueprint = NarrativeBlueprint()
            return self._current_blueprint

        self._current_blueprint = NarrativeBlueprint(
            pacing_adjustments={"current": "normal"},
            recommended_encounters=[],
            foreshadowing_hooks=[],
            schedule_modifications={},
        )

        return self._current_blueprint

    def should_invoke(self, tick_count: int) -> bool:
        return tick_count - self._ticks_since_plan >= 100


@dataclass
class Scheduler:
    events: list[dict[str, Any]] = field(default_factory=list)

    def ingest(self, blueprint: NarrativeBlueprint) -> None:
        for encounter in blueprint.recommended_encounters:
            self.events.append({
                "type": "encounter",
                "data": encounter,
                "scheduled_tick": 0,
            })

    def get_due_events(self, current_time: GameTime) -> list[dict[str, Any]]:
        due = [e for e in self.events if e.get("scheduled_tick", 0) <= current_time.ticks]
        return due
