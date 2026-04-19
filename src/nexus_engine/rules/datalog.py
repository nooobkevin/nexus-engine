from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DatalogFact:
    predicate: str
    args: tuple[str, ...]

    def __hash__(self) -> int:
        return hash((self.predicate, self.args))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DatalogFact):
            return False
        return self.predicate == other.predicate and self.args == other.args


@dataclass
class DatalogRule:
    head: DatalogFact
    body: list[DatalogFact | DatalogCondition]


@dataclass
class DatalogCondition:
    predicate: str
    args: tuple[str, ...]
    negated: bool = False


class DatalogEngine:
    def __init__(self):
        self._facts: set[DatalogFact] = set()
        self._rules: list[DatalogRule] = []
        self._predicates: dict[str, set[DatalogFact]] = {}

    def add_fact(self, predicate: str, *args: str) -> None:
        fact = DatalogFact(predicate, tuple(args))
        self._facts.add(fact)
        if predicate not in self._predicates:
            self._predicates[predicate] = set()
        self._predicates[predicate].add(fact)

    def add_rule(self, rule: DatalogRule) -> None:
        self._rules.append(rule)

    def query(self, predicate: str, *args: str) -> list[tuple[str, ...]]:
        target = DatalogFact(predicate, tuple(args))
        results = set()

        if target in self._facts:
            results.add(target.args)

        for rule in self._rules:
            if rule.head == target:
                bindings = self._evaluate_rule_body(rule.body, {})
                for binding in bindings:
                    results.add(tuple(binding.get(arg, arg) for arg in args))

        return list(results)

    def _evaluate_rule_body(
        self,
        body: list[DatalogFact | DatalogCondition],
        bindings: dict[str, str],
    ) -> list[dict[str, str]]:
        if not body:
            return [bindings]

        first = body[0]
        rest = body[1:]

        if isinstance(first, DatalogCondition):
            matching_facts = self._get_matching_facts(
                first.predicate, first.args, bindings, first.negated
            )
            results = []
            for binding in matching_facts:
                new_bindings = {**bindings, **binding}
                results.extend(self._evaluate_rule_body(rest, new_bindings))
            return results

        return []

    def _get_matching_facts(
        self,
        predicate: str,
        args: tuple[str, ...],
        bindings: dict[str, str],
        negated: bool,
    ) -> list[dict[str, str]]:
        if negated:
            return [{}]

        resolved_args = tuple(bindings.get(arg, arg) for arg in args)
        fact = DatalogFact(predicate, resolved_args)

        if fact in self._facts:
            return [{}]

        results = []
        if predicate in self._predicates:
            for existing_fact in self._predicates[predicate]:
                new_bindings = dict(bindings)
                match = True
                for i, arg in enumerate(args):
                    if arg in bindings:
                        if bindings[arg] != existing_fact.args[i]:
                            match = False
                            break
                    else:
                        new_bindings[arg] = existing_fact.args[i]
                if match:
                    results.append(new_bindings)

        return results

    def evaluate(self) -> None:
        changed = True
        while changed:
            changed = False
            for rule in self._rules:
                bindings = self._evaluate_rule_body(rule.body, {})
                for binding in bindings:
                    head_args = tuple(binding.get(arg, arg) for arg in rule.head.args)
                    new_fact = DatalogFact(rule.head.predicate, head_args)
                    if new_fact not in self._facts:
                        self._facts.add(new_fact)
                        if rule.head.predicate not in self._predicates:
                            self._predicates[rule.head.predicate] = set()
                        self._predicates[rule.head.predicate].add(new_fact)
                        changed = True

    def get_all_facts(self) -> set[DatalogFact]:
        return self._facts.copy()

    def __contains__(self, fact: DatalogFact) -> bool:
        return fact in self._facts


def create_knowledge_base() -> DatalogEngine:
    kb = DatalogEngine()

    kb.add_fact("element", "fire")
    kb.add_fact("element", "water")
    kb.add_fact("element", "earth")
    kb.add_fact("element", "ice")

    kb.add_fact("material", "wood")
    kb.add_fact("material", "stone")
    kb.add_fact("material", "metal")

    kb.add_fact("social", "hostile")
    kb.add_fact("social", "friendly")
    kb.add_fact("social", "neutral")

    return kb


def add_elemental_rules(kb: DatalogEngine) -> None:

    kb.add_rule(
        DatalogRule(
            head=DatalogFact("overcomes", ("ice", "fire")),
            body=[],
        )
    )
    kb.add_rule(
        DatalogRule(
            head=DatalogFact("overcomes", ("fire", "wood")),
            body=[],
        )
    )
    kb.add_rule(
        DatalogRule(
            head=DatalogFact("overcomes", ("water", "fire")),
            body=[],
        )
    )
