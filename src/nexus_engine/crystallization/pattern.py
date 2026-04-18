from __future__ import annotations

from typing import Any

from nexus_engine.core.ability import Rule


def generalize_pattern(candidate: Any) -> Rule:
    common_effects = _find_common_effects(candidate.sample_rulings)

    generalized_effects = []
    for effect in common_effects:
        gen_effect = _replace_specific_with_placeholder(effect)
        generalized_effects.append(gen_effect)

    return Rule.create(
        pattern=candidate.pattern,
        resolver="crystallized_effect",
        priority=50,
        source="CRYSTALLIZED",
        params={"effects": generalized_effects},
    )


def _find_common_effects(rulings: list[Any]) -> list[Any]:
    if not rulings:
        return []

    first_effects = rulings[0].success_effects if rulings else []
    common = list(first_effects)

    for ruling in rulings[1:]:
        effects = ruling.success_effects
        common = [e for e in common if e in effects]

    return common


def _replace_specific_with_placeholder(effect: Any) -> Any:
    from nexus_engine.core.ability import EffectTemplate

    if hasattr(effect, 'parameters'):
        params = dict(effect.parameters)
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 10:
                params[key] = "{{entity}}"

        return EffectTemplate(
            effect_type=effect.effect_type,
            parameters=params,
        )

    return effect
