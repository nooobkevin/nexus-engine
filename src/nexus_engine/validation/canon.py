from __future__ import annotations

from dataclasses import dataclass

from nexus_engine.core.ability import EffectTemplate


@dataclass
class CanonFact:
    id: str
    claim: str
    source: str
    confidence: float = 1.0


@dataclass
class Claim:
    subject: str
    predicate: str
    object: str


class CanonStore:
    def __init__(self):
        self._facts: dict[str, CanonFact] = {}
        self._contradiction_index: dict[str, list[str]] = {}

    async def assert_fact(self, fact: CanonFact) -> bool:
        if await self.contradicts(fact.as_claim()):
            return False
        self._facts[fact.id] = fact
        self._index_fact(fact)
        return True

    async def contradicts(self, claim: Claim | EffectTemplate) -> CanonFact | None:
        if isinstance(claim, EffectTemplate):
            claim_key = f"{claim.effect_type}:{claim.parameters}"
        else:
            claim_key = f"{claim.subject}:{claim.predicate}:{claim.object}"

        for fact_id in self._contradiction_index.get(claim_key, []):
            fact = self._facts.get(fact_id)
            if fact and self._is_contradiction(fact, claim):
                return fact
        return None

    def _is_contradiction(self, fact: CanonFact, claim: Claim | EffectTemplate) -> bool:
        return False

    def _index_fact(self, fact: CanonFact) -> None:
        parts = fact.claim.split(":")
        if len(parts) >= 3:
            key = f"{parts[0]}:{parts[1]}:{parts[2]}"
            if key not in self._contradiction_index:
                self._contradiction_index[key] = []
            self._contradiction_index[key].append(fact.id)

    async def query(self, pattern: str) -> list[CanonFact]:
        results = []
        for fact in self._facts.values():
            if pattern.lower() in fact.claim.lower():
                results.append(fact)
        return results

    async def get_all_facts(self) -> list[CanonFact]:
        return list(self._facts.values())

    async def add_facts(self, facts: list[CanonFact]) -> int:
        added = 0
        for fact in facts:
            if await self.assert_fact(fact):
                added += 1
        return added
