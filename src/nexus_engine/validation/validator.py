from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from nexus_engine.core.ability import RulingDraft
from nexus_engine.core.entity import Entity, PersonaContract
from nexus_engine.core.event import EventDraft
from nexus_engine.core.value_objects import EntityId


@dataclass
class ValidationViolation:
    code: str
    message: str
    severity: Literal["error", "warning"]
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    valid: bool
    violations: list[ValidationViolation] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return len(self.violations) > 0

    @property
    def errors(self) -> list[ValidationViolation]:
        return [v for v in self.violations if v.severity == "error"]

    @property
    def warnings(self) -> list[ValidationViolation]:
        return [v for v in self.violations if v.severity == "warning"]


POWER_TOLERANCE = 1.5


class Validator:
    def __init__(
        self,
        canon_store: Any | None = None,
        rule_engine: Any | None = None,
        setting_pack: Any | None = None,
    ):
        self.canon_store = canon_store
        self.rule_engine = rule_engine
        self.setting_pack = setting_pack
        self._power_tiers = {
            0: 10,
            1: 25,
            2: 50,
            3: 100,
            4: 200,
        }

    async def validate_event(self, event: EventDraft) -> ValidationResult:
        violations: list[ValidationViolation] = []

        if event.actor:
            actor_exists = await self._entity_exists(event.actor.id)
            if not actor_exists:
                violations.append(
                    ValidationViolation(
                        code="DANGLING_REF",
                        message=f"Actor {event.actor} does not exist",
                        severity="error",
                        context={"actor": str(event.actor.id)},
                    )
                )

        for target in event.targets:
            if not await self._entity_exists(target.id):
                violations.append(
                    ValidationViolation(
                        code="DANGLING_REF",
                        message=f"Target {target} does not exist",
                        severity="error",
                        context={"target": str(target.id)},
                    )
                )

        if event.actor:
            power = self._estimate_power(event)
            actor_tier = await self._get_entity_tier(event.actor.id)
            max_power = self._power_tiers.get(actor_tier, 10) * POWER_TOLERANCE
            if power > max_power:
                violations.append(
                    ValidationViolation(
                        code="POWER_EXCEEDS_TIER",
                        message=f"Event power {power} exceeds tier limit {max_power}",
                        severity="error",
                        context={"power": power, "tier": actor_tier, "max": max_power},
                    )
                )

        if self.setting_pack:
            tag_violations = self._validate_tags(event)
            violations.extend(tag_violations)

        return ValidationResult(valid=len(violations) == 0, violations=violations)

    async def validate_ruling(
        self, ruling: RulingDraft, actor: Entity
    ) -> ValidationResult:
        violations: list[ValidationViolation] = []

        power = self._estimate_ruling_power(ruling)
        actor_tier = getattr(actor, "tier", 0)
        max_power = self._power_tiers.get(actor_tier, 10) * POWER_TOLERANCE
        if power > max_power:
            violations.append(
                ValidationViolation(
                    code="POWER_EXCEEDS_TIER",
                    message=f"Ruling power {power} exceeds actor tier limit",
                    severity="error",
                    context={"power": power, "tier": actor_tier},
                )
            )

        if ruling.difficulty_tier.value != "trivial":
            if not ruling.resource_costs:
                violations.append(
                    ValidationViolation(
                        code="MISSING_COST",
                        message="Non-trivial action should have resource costs",
                        severity="warning",
                        context={},
                    )
                )

        for ref in ruling.referenced_entities:
            if not await self._entity_exists(EntityId(ref)):
                violations.append(
                    ValidationViolation(
                        code="DANGLING_REF",
                        message=f"Referenced entity {ref} does not exist",
                        severity="error",
                        context={"ref": ref},
                    )
                )

        if self.canon_store:
            canon_violations = await self._check_canon_violations(ruling)
            violations.extend(canon_violations)

        return ValidationResult(valid=len(violations) == 0, violations=violations)

    async def validate_persona(
        self, output: str, contract: PersonaContract
    ) -> ValidationResult:
        violations: list[ValidationViolation] = []

        for forbidden in contract.forbidden_behaviors:
            if forbidden.lower() in output.lower():
                violations.append(
                    ValidationViolation(
                        code="FORBIDDEN_BEHAVIOR",
                        message=f"Output contains forbidden behavior: {forbidden}",
                        severity="error",
                        context={"forbidden": forbidden},
                    )
                )

        return ValidationResult(valid=len(violations) == 0, violations=violations)

    async def _entity_exists(self, entity_id: EntityId) -> bool:
        return True

    async def _get_entity_tier(self, entity_id: EntityId) -> int:
        return 0

    def _estimate_power(self, event: EventDraft) -> float:
        base_power = 0.0
        for effect in event.effects:
            if effect.operation.value in ("SET", "DELTA"):
                base_power += abs(effect.value.get("amount", 0)) * 0.1
        return base_power

    def _estimate_ruling_power(self, ruling: RulingDraft) -> float:
        return ruling.plausibility * 10

    def _validate_tags(self, event: EventDraft) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        if not self.setting_pack:
            return violations

        allowed_namespaces = getattr(self.setting_pack, "allowed_tag_namespaces", set())
        if not allowed_namespaces:
            return violations

        for tag in event.tags:
            if tag.namespace not in allowed_namespaces:
                violations.append(
                    ValidationViolation(
                        code="INVALID_TAG",
                        message=f"Tag namespace '{tag.namespace}' not in vocabulary",
                        severity="warning",
                        context={"tag": str(tag)},
                    )
                )
        return violations

    async def _check_canon_violations(
        self, ruling: RulingDraft
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        if not self.canon_store:
            return violations

        for effect in ruling.success_effects:
            contradiction = await self.canon_store.contradicts(effect)
            if contradiction:
                violations.append(
                    ValidationViolation(
                        code="CANON_VIOLATION",
                        message=f"Effect contradicts canon fact: {contradiction}",
                        severity="error",
                        context={"effect": effect, "canon": contradiction},
                    )
                )
        return violations
