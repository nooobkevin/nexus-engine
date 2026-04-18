from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nexus_engine.core.ability import Predicate
from nexus_engine.core.value_objects import GameTime


class GoalSource(str, Enum):
    DRIVE_DERIVED = "drive_derived"
    REACTIVE = "reactive"
    DIRECTOR_ASSIGNED = "director_assigned"


@dataclass
class Goal:
    id: str
    priority: float
    prerequisites: list[Predicate]
    target_state: dict[str, Any]
    deadline: GameTime | None = None
    source: GoalSource = GoalSource.DRIVE_DERIVED
    plan: list[dict[str, Any]] = field(default_factory=list)
    completed: bool = False

    def is_expired(self, current_time: GameTime) -> bool:
        if self.deadline and current_time > self.deadline:
            return True
        return False


@dataclass
class GoalPriorityQueue:
    goals: list[Goal] = field(default_factory=list)

    def add(self, goal: Goal) -> None:
        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority, reverse=True)

    def pop(self) -> Goal | None:
        if not self.goals:
            return None
        return self.goals.pop(0)

    def top(self) -> Goal | None:
        if not self.goals:
            return None
        return self.goals[0]

    def remove(self, goal_id: str) -> None:
        self.goals = [g for g in self.goals if g.id != goal_id]

    def clear_completed(self) -> None:
        self.goals = [g for g in self.goals if not g.completed]


class GoalGenerator:
    def __init__(self, llm_interface: Any | None = None):
        self.llm_interface = llm_interface

    async def generate(
        self,
        npc: Any,
        context: Any,
    ) -> GoalPriorityQueue:
        queue = GoalPriorityQueue()

        from nexus_engine.npc.drives import select_dominant_drive, get_default_drives, DriveState

        drive_state = DriveState(drives=get_default_drives())
        dominant = select_dominant_drive(drive_state)

        if dominant:
            goal = self._drive_to_goal(dominant, npc)
            queue.add(goal)

        return queue

    def _drive_to_goal(self, drive: Any, npc: Any) -> Goal:
        drive_goal_map = {
            "survival": ("stay_alive", {"health": ("gt", 0)}),
            "social": ("build_relationships", {"relationships": ("gt", 0)}),
            "prestige": ("gain_recognition", {"reputation": ("gt", 0)}),
            "knowledge": ("learn_secrets", {"knowledge": ("gt", 0)}),
            "goods": ("accumulate_wealth", {"wealth": ("gt", 0)}),
            "freedom": ("maintain_independence", {"captivity": ("eq", False)}),
        }

        goal_type, target = drive_goal_map.get(drive.drive_id, ("explore", {}))
        goal_id = f"{npc.id}_{drive.drive_id}_{drive.intensity}"

        return Goal(
            id=goal_id,
            priority=drive.intensity * (1 - drive.saturation),
            prerequisites=[],
            target_state={goal_type: target},
            source=GoalSource.DRIVE_DERIVED,
        )


class SimplePlanner:
    def __init__(self):
        self._action_map: dict[str, list[dict[str, Any]]] = {
            "explore": [
                {"action": "move", "direction": "random"},
                {"action": "look_around"},
            ],
            "talk": [
                {"action": "approach", "target": None},
                {"action": "speak", "topic": None},
            ],
            "fight": [
                {"action": "approach", "target": None},
                {"action": "attack"},
            ],
            "flee": [
                {"action": "retreat"},
                {"action": "hide"},
            ],
        }

    async def plan_next(
        self,
        npc: Any,
        goal: Goal,
        context: Any,
    ) -> dict[str, Any] | None:
        goal_action = list(goal.target_state.keys())[0] if goal.target_state else "explore"
        actions = self._action_map.get(goal_action, self._action_map["explore"])
        return actions[0] if actions else None

    def validate_plan(self, plan: list[dict[str, Any]], goal: Goal) -> bool:
        return len(plan) > 0
