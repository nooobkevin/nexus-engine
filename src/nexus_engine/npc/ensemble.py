from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nexus_engine.agents.llm_interface import LLMInterface
from nexus_engine.core.entity import Entity, PersonaContract
from nexus_engine.core.event import Event, EventType, MechanicsResult
from nexus_engine.core.value_objects import EntityId, EntityRef, GameTime
from nexus_engine.npc.drives import NPCContext, get_default_drives
from nexus_engine.npc.goals import GoalGenerator, GoalPriorityQueue, SimplePlanner
from nexus_engine.validation.validator import Validator


@dataclass
class EnsembleBeat:
    speaker_index: int
    content: str
    action: str | None = None


@dataclass
class EnsembleScript:
    beats: list[EnsembleBeat]


async def npc_tick(
    npc: Entity,
    delta: int,
    context: NPCContext,
    goal_generator: GoalGenerator | None = None,
    planner: SimplePlanner | None = None,
    validator: Validator | None = None,
) -> list[Event]:
    events: list[Event] = []

    if goal_generator is None:
        goal_generator = GoalGenerator()
    if planner is None:
        planner = SimplePlanner()

    goals = await goal_generator.generate(npc, context)

    if not goals.goals:
        return events

    current_goal = goals.top()
    if not current_goal:
        return events

    action = await planner.plan_next(npc, current_goal, context)
    if not action:
        return events

    event = await execute_action(npc, action, context, validator)
    if event:
        events.append(event)

    return events


async def execute_action(
    npc: Entity,
    action: dict[str, Any],
    context: NPCContext,
    validator: Validator | None = None,
) -> Event | None:
    action_type = action.get("action", "unknown")
    target_id = action.get("target")

    mechanics = MechanicsResult(success=True, degree=0.5)

    target_ref = EntityRef(id=EntityId(target_id)) if target_id else None
    targets = [target_ref] if target_ref else []

    narrative = f"{npc.properties.get('name', 'Someone')} performed {action_type}"

    event = Event.create(
        game_time=context.world_time,
        event_type=action_type,
        actor=EntityRef(id=npc.id),
        location=EntityRef(id=context.current_location),
        mechanics=mechanics,
        effects=[],
        narrative_summary=narrative,
        targets=targets,
    )

    return event


async def ensemble_scene(
    npcs: list[Entity],
    context: NPCContext,
    llm: LLMInterface | None = None,
    validator: Validator | None = None,
) -> list[Event]:
    if not npcs:
        return []

    personas = []
    for npc in npcs:
        contract = getattr(npc, "persona_contract", None)
        if contract:
            personas.append(contract)
        else:
            personas.append(PersonaContract(
                persona_id=str(npc.id),
                core_traits=frozenset(),
                speech_pattern="",
                forbidden_behaviors=frozenset(),
                required_behaviors=frozenset(),
            ))

    if llm is None:
        llm = LLMInterface()

    internal_states = []
    for npc in npcs:
        goals = getattr(npc, "current_goals", GoalPriorityQueue())
        drives = getattr(npc, "drives", get_default_drives())
        internal_states.append({
            "goals": [g.id for g in goals.goals],
            "drives": {k: v.intensity for k, v in drives.items()} if isinstance(drives, dict) else {},
        })

    script = await llm.generate_ensemble(
        personas=personas,
        internal_states=internal_states,
        context=context,
    )

    events = []
    for beat in script.beats:
        if validator and beat.speaker_index < len(personas):
            validation = await validator.validate_persona(
                beat.content, personas[beat.speaker_index]
            )
            if validation.failed:
                beat.content = _rephrase_for_contract(
                    beat.content, personas[beat.speaker_index]
                )

        if beat.speaker_index < len(npcs):
            npc = npcs[beat.speaker_index]
            event = Event.create(
                game_time=context.world_time,
                event_type=EventType.CONVERSATION,
                actor=EntityRef(id=npc.id),
                location=EntityRef(id=context.current_location),
                mechanics=MechanicsResult(success=True, degree=0.5),
                effects=[],
                narrative_summary=beat.content,
            )
            events.append(event)

    return events


def _rephrase_for_contract(content: str, contract: PersonaContract) -> str:
    for forbidden in contract.forbidden_behaviors:
        if forbidden.lower() in content.lower():
            content = content.replace(forbidden, "[redacted]")
    return content


async def detect_reactive_triggers(npc: Entity, context: NPCContext) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []

    for event in context.recent_events:
        if event.actor and event.actor.id == npc.id:
            continue

        event_type = event.type.value
        if event_type == "threat_detected":
            triggers.append({
                "type": "defend",
                "source": event,
                "priority": 0.8,
            })
        elif event_type == "player_greeting":
            triggers.append({
                "type": "respond_greeting",
                "source": event,
                "priority": 0.6,
            })

    return triggers


async def execute_reactive_action(
    npc: Entity,
    triggers: list[dict[str, Any]],
    context: NPCContext,
) -> list[Event]:
    events: list[Event] = []

    if not triggers:
        return events

    top_trigger = max(triggers, key=lambda t: t.get("priority", 0))

    match top_trigger["type"]:
        case "defend":
            action = {"action": "defend"}
        case "respond_greeting":
            action = {"action": "greet_back"}
        case _:
            action = {"action": "observe"}

    event = await execute_action(npc, action, context)
    if event:
        events.append(event)

    return events


def can_follow_schedule(npc: Entity, current_time: GameTime, situation: Any) -> bool:
    schedule = getattr(npc, "schedule", None)
    if not schedule:
        return False

    if situation and situation.get("in_combat"):
        return False
    if situation and situation.get("in_conversation"):
        return False

    return True
