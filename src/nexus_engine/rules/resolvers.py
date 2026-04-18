from __future__ import annotations

import random
from typing import Any

from nexus_engine.core.ability import EffectTemplate, Outcome
from nexus_engine.core.entity import Entity
from nexus_engine.core.event import MechanicsResult


async def resolve_ability_check(
    actor: Entity,
    target: Entity | None,
    context: dict[str, Any],
    params: dict[str, Any],
) -> Outcome:
    ability_id = params.get("ability_id", "")
    difficulty = params.get("difficulty", 15)
    modifier = params.get("modifier", 0)

    roll = random.randint(1, 20)
    total = roll + modifier
    success = total >= difficulty
    degree = max(0.0, min(1.0, (total - difficulty + 5) / 10))

    mechanics = MechanicsResult(
        success=success,
        degree=degree,
        roll=roll,
        difficulty=difficulty,
        values={"ability_id": ability_id, "modifier": modifier, "total": total},
    )

    effects: list[EffectTemplate] = []
    if success:
        effects = params.get("success_effects", [])
    else:
        effects = params.get("failure_effects", [])

    return Outcome(
        success=success,
        degree=degree,
        mechanics=mechanics,
        effects=frozenset(effects),
        narrative=f"Ability check: {roll} + {modifier} = {total} vs DC {difficulty}",
    )


async def resolve_damage(
    actor: Entity,
    target: Entity | None,
    context: dict[str, Any],
    params: dict[str, Any],
) -> Outcome:
    if not target:
        return Outcome(
            success=False,
            degree=0.0,
            mechanics=None,
            effects=frozenset(),
            narrative="No target specified for damage.",
        )

    base_damage = params.get("base_damage", 0)
    damage_type = params.get("damage_type", "physical")
    multiplier = params.get("multiplier", 1.0)

    roll = random.randint(1, 6)
    total_damage = int((base_damage + roll) * multiplier)

    mechanics = MechanicsResult(
        success=True,
        degree=min(1.0, total_damage / 50),
        roll=roll,
        values={
            "base_damage": base_damage,
            "damage_type": damage_type,
            "total_damage": total_damage,
        },
    )

    effect = EffectTemplate(
        effect_type="apply_damage",
        parameters={
            "target": str(target.id),
            "amount": total_damage,
            "type": damage_type,
        },
    )

    return Outcome(
        success=True,
        degree=min(1.0, total_damage / 50),
        mechanics=mechanics,
        effects=frozenset([effect]),
        narrative=f"Dealt {total_damage} {damage_type} damage.",
    )


async def resolve_healing(
    actor: Entity,
    target: Entity | None,
    context: dict[str, Any],
    params: dict[str, Any],
) -> Outcome:
    if not target:
        target = actor

    base_healing = params.get("base_healing", 0)
    roll = random.randint(1, 4)
    total_healing = base_healing + roll

    mechanics = MechanicsResult(
        success=True,
        degree=min(1.0, total_healing / 30),
        roll=roll,
        values={"base_healing": base_healing, "total_healing": total_healing},
    )

    effect = EffectTemplate(
        effect_type="apply_healing",
        parameters={
            "target": str(target.id),
            "amount": total_healing,
        },
    )

    return Outcome(
        success=True,
        degree=min(1.0, total_healing / 30),
        mechanics=mechanics,
        effects=frozenset([effect]),
        narrative=f"Healed {target.properties.get('name', 'target')} for {total_healing} HP.",
    )


async def resolve_skill_check(
    actor: Entity,
    target: Entity | None,
    context: dict[str, Any],
    params: dict[str, Any],
) -> Outcome:
    skill = params.get("skill", "unknown")
    difficulty = params.get("difficulty", 15)
    modifier = params.get("modifier", 0)

    actor_skill_bonus = actor.properties.get("skills", {}).get(skill, 0)
    roll = random.randint(1, 20)
    total = roll + actor_skill_bonus + modifier
    success = total >= difficulty
    degree = max(0.0, min(1.0, (total - difficulty + 5) / 10))

    mechanics = MechanicsResult(
        success=success,
        degree=degree,
        roll=roll,
        difficulty=difficulty,
        values={
            "skill": skill,
            "actor_bonus": actor_skill_bonus,
            "modifier": modifier,
            "total": total,
        },
    )

    narrative = f"{skill.capitalize()} check: {roll} (roll) + {actor_skill_bonus} (skill) + {modifier} (mod) = {total} vs DC {difficulty}"

    return Outcome(
        success=success,
        degree=degree,
        mechanics=mechanics,
        effects=frozenset(),
        narrative=narrative,
    )


DEFAULT_RESOLVERS = {
    "ability_check": resolve_ability_check,
    "damage": resolve_damage,
    "healing": resolve_healing,
    "skill_check": resolve_skill_check,
}
