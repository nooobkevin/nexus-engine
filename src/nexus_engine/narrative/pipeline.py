from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nexus_engine.agents.context_builder import SceneContext
from nexus_engine.agents.llm_interface import ChatMessage, LLMInterface
from nexus_engine.core.entity import Entity
from nexus_engine.core.event import Event, EventDraft, EventType
from nexus_engine.core.value_objects import EntityId, EntityRef, GameTime, Tag
from nexus_engine.memory.memory_system import MemorySystem
from nexus_engine.rules.rule_engine import resolve_action
from nexus_engine.validation.validator import Validator


@dataclass
class Intent:
    action_type: str
    actor_ref: EntityRef
    targets: list[EntityRef]
    tags: list[Tag]
    parameters: dict[str, Any] = field(default_factory=dict)
    implied_location: EntityRef | None = None


@dataclass
class WorkingContext:
    scene: SceneContext
    player_id: EntityId
    current_time: GameTime
    relevant_entities: list[Entity] = field(default_factory=list)


@dataclass
class NarrativeOutput:
    narrative: str
    events: list[Event]
    game_time: GameTime


async def process_player_action(
    input_text: str,
    player_id: EntityId,
    context: WorkingContext,
    llm: LLMInterface,
    state_view: Any,
    event_store: Any,
    validator: Validator,
    memory_system: MemorySystem,
) -> NarrativeOutput:
    intent = await _parse_intent(input_text, context, llm)

    working_context = await _gather_context(intent, context, state_view)

    outcome = await _resolve_action(intent, working_context, state_view)

    drafts = _outcome_to_events(outcome, intent, context.current_time)

    for draft in drafts:
        validation = await validator.validate_event(draft)
        if validation.failed:
            drafts = _rebalance_events(drafts, validation.violations)
            break

    events = [draft.to_event(context.current_time) for draft in drafts]

    for event in events:
        await event_store.append(event)
        await state_view.apply(event)

    narrative = await _generate_narrative(events, working_context, llm)

    await memory_system.ingest(events, narrative)

    return NarrativeOutput(
        narrative=narrative,
        events=events,
        game_time=context.current_time,
    )


async def _parse_intent(
    input_text: str,
    context: WorkingContext,
    llm: LLMInterface,
) -> Intent:
    scene_desc = f"Player {context.player_id} at location"

    prompt = f"""
Player input: {input_text}

Current scene: {scene_desc}

Parse the player's intent and return a structured action.
"""

    schema = {
        "type": "object",
        "properties": {
            "action_type": {"type": "string"},
            "targets": {"type": "array", "items": {"type": "string"}},
            "parameters": {"type": "object"},
        },
    }

    result = await llm.structured_completion(
        messages=[ChatMessage(role="user", content=prompt)],
        response_schema=schema,
    )

    return Intent(
        action_type=result.get("action_type", "unknown"),
        actor_ref=EntityRef(id=context.player_id),
        targets=[EntityRef(id=t) for t in result.get("targets", [])],
        tags=[],
        parameters=result.get("parameters", {}),
    )


async def _gather_context(
    intent: Intent,
    context: WorkingContext,
    state_view: Any,
) -> WorkingContext:
    relevant_entities = []

    for target in intent.targets:
        entity = await state_view.get_entity(target.id)
        if entity:
            relevant_entities.append(entity)

    return WorkingContext(
        scene=context.scene,
        player_id=context.player_id,
        current_time=context.current_time,
        relevant_entities=relevant_entities,
    )


async def _resolve_action(
    intent: Intent,
    context: WorkingContext,
    state_view: Any,
) -> Any:
    actor = context.relevant_entities[0] if context.relevant_entities else None
    if actor is None:
        from nexus_engine.core.ability import Outcome
        from nexus_engine.core.ability import EffectTemplate
        return Outcome(success=False, degree=0.0, mechanics=None, effects=frozenset())
    return await resolve_action(
        state_view.rule_engine,
        intent.action_type,
        actor,
        None,
        {"tags": intent.tags, "parameters": intent.parameters},
    )


def _outcome_to_events(outcome: Any, intent: Intent, game_time: GameTime, working_context: WorkingContext | None = None) -> list[EventDraft]:
    if not outcome or not outcome.success:
        return []

    location_ref = intent.implied_location
    if not location_ref and working_context:
        location_ref = EntityRef(id=EntityId(working_context.scene.location.id))
    if not location_ref:
        location_ref = intent.actor_ref

    draft = EventDraft(
        type=EventType(intent.action_type),
        actor=intent.actor_ref,
        targets=[t for t in intent.targets],
        location=location_ref,
        mechanics=outcome.mechanics,
        effects=[],
        narrative_summary=outcome.narrative or "Action performed",
    )

    return [draft]


def _rebalance_events(
    drafts: list[EventDraft],
    violations: list[Any],
) -> list[EventDraft]:
    return drafts


async def _generate_narrative(
    events: list[Event],
    context: WorkingContext,
    llm: LLMInterface,
) -> str:
    if not events:
        return "Nothing happened."

    facts = [e.narrative_summary for e in events]
    prompt = "Events:\n" + "\n".join(f"  - {f}" for f in facts)
    prompt += "\n\nGenerate a narrative description."

    return await llm.chat(prompt)
