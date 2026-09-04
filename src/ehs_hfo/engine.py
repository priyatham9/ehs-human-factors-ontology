"""A stratified Datalog evaluator with full derivation provenance.

Naming, precisely
-----------------
This is a bottom-up Datalog evaluator with stratified negation as failure. It is
not "automated reasoning" in the sense that term carries in computer science:
there is no SMT or first-order decision procedure here, no proof certificate in
any standard format, and no soundness theorem relative to a formal semantics of
the domain. What it does have, and what the naming does buy, is a definite
semantics for the program it evaluates: for a stratified program the perfect
model is unique and independent of rule order, and because the language has no
function symbols the Herbrand base is finite so evaluation terminates.

The output that matters is not the conclusion set but the derivation trace. Every
derived fact records which rule fired and which facts satisfied its body, so any
conclusion can be unwound to the scenario inputs and the cited literature.

Complexity
----------
Evaluation is polynomial in the size of the fact base for a fixed program
(data complexity of Datalog is PTIME-complete). The implementation here is naive
iteration to a fixpoint per stratum, which is adequate at the scale of a single
scenario -- twenty factors, twenty-one rules, a few hundred derived facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .facts import Fact, Pattern, Rule, RuleError, Var

__all__ = [
    "Derivation",
    "EngineError",
    "Justification",
    "Program",
    "Result",
    "StratificationError",
]


class EngineError(RuntimeError):
    """Raised when a program cannot be evaluated."""


class StratificationError(EngineError):
    """Raised when negation appears inside a recursive cycle."""


@dataclass(frozen=True)
class Derivation:
    """One reason a fact holds: the rule that fired and the facts it consumed."""

    rule_id: str
    support: Tuple[Fact, ...]
    bindings: Tuple[Tuple[str, str], ...]


@dataclass
class Justification:
    """All recorded derivations for one fact."""

    fact: Fact
    derivations: List[Derivation] = field(default_factory=list)
    is_base: bool = False


# --------------------------------------------------------------------------- #
# Program
# --------------------------------------------------------------------------- #


class Program:
    """A set of rules, stratified once at construction time."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        seen: Set[str] = set()
        for rule in rules:
            if rule.rule_id in seen:
                raise RuleError(f"duplicate rule id {rule.rule_id!r}")
            seen.add(rule.rule_id)
        self.rules: Tuple[Rule, ...] = tuple(rules)
        self.strata: Tuple[Tuple[Rule, ...], ...] = self._stratify()

    # -- stratification ----------------------------------------------------- #

    def _stratify(self) -> Tuple[Tuple[Rule, ...], ...]:
        """Assign each intensional predicate a stratum, or fail loudly.

        The constraint is the standard one: for a positive body dependency the
        head's stratum must be at least the body's; for a negative dependency it
        must be strictly greater. Iterating the constraint to a fixpoint either
        converges or proves that a negative edge sits inside a cycle.
        """
        head_predicates = {rule.head.predicate for rule in self.rules}
        stratum: Dict[str, int] = {p: 0 for p in head_predicates}

        limit = len(head_predicates) + 1
        for _ in range(limit):
            changed = False
            for rule in self.rules:
                head = rule.head.predicate
                for literal in rule.body:
                    if literal.builtin:
                        continue
                    body = literal.predicate
                    if body not in stratum:
                        continue  # extensional predicate: always stratum 0
                    required = stratum[body] + (1 if literal.negated else 0)
                    if required > stratum[head]:
                        stratum[head] = required
                        changed = True
            if not changed:
                break
        else:
            offenders = self._negative_cycle_predicates()
            raise StratificationError(
                "program is not stratifiable; negation appears inside a recursive "
                f"cycle involving: {', '.join(sorted(offenders))}"
            )

        # Verify the assignment actually satisfies every constraint.
        for rule in self.rules:
            head = rule.head.predicate
            for literal in rule.body:
                if literal.builtin or literal.predicate not in stratum:
                    continue
                required = stratum[literal.predicate] + (1 if literal.negated else 0)
                if stratum[head] < required:
                    raise StratificationError(
                        f"rule {rule.rule_id} violates stratification: "
                        f"{head} must be above {literal.predicate}"
                    )

        depth = max(stratum.values()) + 1 if stratum else 1
        buckets: List[List[Rule]] = [[] for _ in range(depth)]
        for rule in self.rules:
            buckets[stratum[rule.head.predicate]].append(rule)
        return tuple(tuple(bucket) for bucket in buckets)

    def _negative_cycle_predicates(self) -> Set[str]:
        """Best-effort identification of predicates caught in a negative cycle."""
        edges: Dict[str, Set[str]] = {}
        negative: Set[Tuple[str, str]] = set()
        for rule in self.rules:
            head = rule.head.predicate
            for literal in rule.body:
                if literal.builtin:
                    continue
                edges.setdefault(literal.predicate, set()).add(head)
                if literal.negated:
                    negative.add((literal.predicate, head))

        def reaches(start: str, target: str) -> bool:
            seen: Set[str] = set()
            queue = [start]
            while queue:
                node = queue.pop()
                if node == target:
                    return True
                if node in seen:
                    continue
                seen.add(node)
                queue.extend(edges.get(node, ()))
            return False

        offenders: Set[str] = set()
        for body, head in negative:
            if reaches(head, body):
                offenders.update({body, head})
        return offenders or {r.head.predicate for r in self.rules}

    def rule(self, rule_id: str) -> Rule:
        """Look up a rule by identifier."""
        for candidate in self.rules:
            if candidate.rule_id == rule_id:
                return candidate
        raise KeyError(rule_id)

    # -- evaluation --------------------------------------------------------- #

    def evaluate(self, base_facts: Iterable[Fact]) -> "Result":
        """Run the program to a fixpoint and return the derived model."""
        facts: Set[Fact] = set(base_facts)
        # Seed the index from a sorted sequence, not from the set. Set iteration
        # order over Fact varies with PYTHONHASHSEED, and although the fixpoint
        # itself is order-independent, the order in which alternative
        # derivations are *discovered* is not. A trace that names a different
        # supporting fact from one run to the next is useless as an audit
        # record, so the traversal order is pinned here.
        ordered = sorted(facts, key=lambda f: (f.predicate, f.args))
        index: Dict[str, List[Fact]] = {}
        for fact in ordered:
            index.setdefault(fact.predicate, []).append(fact)
        justifications: Dict[Fact, Justification] = {
            fact: Justification(fact=fact, is_base=True) for fact in ordered
        }
        fired: List[Tuple[str, Fact]] = []

        for stratum in self.strata:
            while True:
                added = False
                for rule in stratum:
                    for bindings, support in self._match(rule.body, index):
                        head = _ground(rule.head, bindings)
                        derivation = Derivation(
                            rule_id=rule.rule_id,
                            support=tuple(support),
                            bindings=tuple(sorted(bindings.items())),
                        )
                        record = justifications.get(head)
                        if record is None:
                            record = Justification(fact=head)
                            justifications[head] = record
                            facts.add(head)
                            index.setdefault(head.predicate, []).append(head)
                            added = True
                        if derivation not in record.derivations:
                            record.derivations.append(derivation)
                            # A rule counts as fired when it contributes a
                            # derivation, not only when it is first to reach a
                            # conclusion. Recording only the winner would hide
                            # every independent route to the same finding, which
                            # is exactly what an auditor is looking for.
                            fired.append((rule.rule_id, head))
                if not added:
                    break

        # Canonicalise the alternatives recorded against each conclusion. The
        # seeded index above already makes discovery order reproducible; sorting
        # makes the printed trace independent of discovery order altogether, so
        # two runs of the same scenario produce byte-identical justifications.
        for record in justifications.values():
            record.derivations.sort(
                key=lambda d: (
                    d.rule_id,
                    tuple((f.predicate, f.args) for f in d.support),
                )
            )

        return Result(
            facts=frozenset(facts),
            justifications=justifications,
            program=self,
            firing_order=tuple(fired),
        )

    def _match(
        self, body: Sequence[Pattern], index: Mapping[str, List[Fact]]
    ) -> Iterable[Tuple[Dict[str, str], List[Fact]]]:
        """Yield every (bindings, support) pair satisfying the rule body.

        Candidate facts are drawn from a per-predicate index rather than the
        whole fact base. Without it, a four-literal body over a few hundred
        facts is slow enough to be noticeable.
        """

        def step(
            position: int, bindings: Dict[str, str], support: List[Fact]
        ) -> Iterable[Tuple[Dict[str, str], List[Fact]]]:
            if position == len(body):
                yield dict(bindings), list(support)
                return
            literal = body[position]

            if literal.builtin:
                if _eval_builtin(literal, bindings):
                    yield from step(position + 1, bindings, support)
                return

            candidates = index.get(literal.predicate, ())

            if literal.negated:
                probe = _ground_partial(literal, bindings)
                if not any(_fact_matches(probe, fact) for fact in candidates):
                    yield from step(position + 1, bindings, support)
                return

            # Iterate over a snapshot: the index grows while rules fire, and a
            # list mutated mid-iteration would raise or silently skip entries.
            for fact in tuple(candidates):
                extended = _unify(literal, fact, bindings)
                if extended is None:
                    continue
                support.append(fact)
                yield from step(position + 1, extended, support)
                support.pop()

        return step(0, {}, [])


# --------------------------------------------------------------------------- #
# Result
# --------------------------------------------------------------------------- #


@dataclass
class Result:
    """The model produced by one evaluation, with its provenance."""

    facts: FrozenSet[Fact]
    justifications: Dict[Fact, Justification]
    program: Program
    firing_order: Tuple[Tuple[str, Fact], ...] = ()

    def query(self, predicate: str, arity: Optional[int] = None) -> List[Fact]:
        """All derived or base facts for a predicate, sorted for stable output."""
        found = [
            f
            for f in self.facts
            if f.predicate == predicate and (arity is None or len(f.args) == arity)
        ]
        return sorted(found, key=lambda f: f.args)

    def holds(self, predicate: str, *args: str) -> bool:
        """True when the exact ground fact is in the model."""
        return Fact(predicate, tuple(args)) in self.facts

    def base_facts(self) -> List[Fact]:
        """The facts supplied as input rather than derived."""
        return sorted(
            (j.fact for j in self.justifications.values() if j.is_base),
            key=lambda f: (f.predicate, f.args),
        )

    def derived_facts(self) -> List[Fact]:
        """The facts produced by rule firing."""
        return sorted(
            (j.fact for j in self.justifications.values() if not j.is_base),
            key=lambda f: (f.predicate, f.args),
        )

    # -- tracing ------------------------------------------------------------ #

    def explain(
        self, fact: Fact, max_depth: int = 12, max_alternatives: int = 1
    ) -> List[str]:
        """Render a derivation tree for one fact as indented lines.

        Every leaf is either a base fact or a note saying why the branch stops,
        so a reader can always tell the difference between "this came from the
        input" and "this trace was cut short".

        ``max_alternatives`` bounds how many independent derivations of the same
        fact are expanded. A fact with several supports is common and expanding
        all of them makes the output unreadable, so the default shows one and
        counts the rest. Pass a larger number, or ``0`` for all of them, when the
        alternatives are the thing being audited.
        """
        if fact not in self.justifications:
            return [f"{fact}  [NOT DERIVED]"]
        lines: List[str] = []
        self._explain_into(fact, 0, lines, set(), max_depth, max_alternatives)
        return lines

    def _explain_into(
        self,
        fact: Fact,
        depth: int,
        lines: List[str],
        seen: Set[Fact],
        max_depth: int,
        max_alternatives: int,
    ) -> None:
        indent = "  " * depth
        record = self.justifications.get(fact)
        if record is None:
            lines.append(f"{indent}{fact}  [unknown]")
            return
        if record.is_base:
            lines.append(f"{indent}{fact}  [given]")
            return
        if fact in seen:
            lines.append(f"{indent}{fact}  [already shown above]")
            return
        if depth >= max_depth:
            lines.append(f"{indent}{fact}  [trace truncated at depth {max_depth}]")
            return

        seen = seen | {fact}
        shown = (
            record.derivations
            if max_alternatives <= 0
            else record.derivations[:max_alternatives]
        )
        for derivation in shown:
            rule = self.program.rule(derivation.rule_id)
            citation = ", ".join(rule.source_refs) if rule.source_refs else "no source"
            lines.append(
                f"{indent}{fact}"
                f"  <- {derivation.rule_id} [{rule.basis}; {citation}]"
            )
            lines.append(f"{indent}  rule: {rule}")
            lines.append(f"{indent}  because: {rule.description}")
            for supporting in derivation.support:
                self._explain_into(
                    supporting, depth + 2, lines, seen, max_depth, max_alternatives
                )
        remaining = len(record.derivations) - len(shown)
        if remaining > 0:
            lines.append(
                f"{indent}  ({remaining} further derivation"
                f"{'s' if remaining != 1 else ''} recorded and not expanded here)"
            )

    def rules_fired(self) -> List[str]:
        """Identifiers of every rule that contributed at least one derivation."""
        return sorted({rule_id for rule_id, _ in self.firing_order})


# --------------------------------------------------------------------------- #
# Matching helpers
# --------------------------------------------------------------------------- #


def _unify(
    pattern: Pattern, fact: Fact, bindings: Mapping[str, str]
) -> Optional[Dict[str, str]]:
    """Extend ``bindings`` so ``pattern`` matches ``fact``, or return None."""
    if len(pattern.args) != len(fact.args):
        return None
    extended = dict(bindings)
    for term, value in zip(pattern.args, fact.args):
        if isinstance(term, Var):
            bound = extended.get(term.name)
            if bound is None:
                extended[term.name] = value
            elif bound != value:
                return None
        elif term != value:
            return None
    return extended


def _ground(pattern: Pattern, bindings: Mapping[str, str]) -> Fact:
    """Instantiate a fully bound pattern into a fact."""
    args: List[str] = []
    for term in pattern.args:
        if isinstance(term, Var):
            if term.name not in bindings:
                raise EngineError(f"unbound variable {term} while grounding {pattern}")
            args.append(bindings[term.name])
        else:
            args.append(term)
    return Fact(pattern.predicate, tuple(args))


def _ground_partial(pattern: Pattern, bindings: Mapping[str, str]) -> Pattern:
    """Substitute known bindings, leaving unbound variables in place."""
    args: List[object] = []
    for term in pattern.args:
        if isinstance(term, Var) and term.name in bindings:
            args.append(bindings[term.name])
        else:
            args.append(term)
    return Pattern(pattern.predicate, tuple(args), pattern.negated, pattern.builtin)


def _fact_matches(pattern: Pattern, fact: Fact) -> bool:
    """True when a (possibly partially ground) pattern matches a fact."""
    if pattern.predicate != fact.predicate or len(pattern.args) != len(fact.args):
        return False
    for term, value in zip(pattern.args, fact.args):
        if isinstance(term, Var):
            continue
        if term != value:
            return False
    return True


def _eval_builtin(pattern: Pattern, bindings: Mapping[str, str]) -> bool:
    """Evaluate a guard. ``neq`` and ``lt`` are the only ones supported."""
    if pattern.predicate not in ("neq", "lt"):
        raise EngineError(f"unsupported builtin {pattern.predicate!r}")
    if len(pattern.args) != 2:
        raise EngineError(f"{pattern.predicate} takes exactly two arguments")
    resolved: List[str] = []
    for term in pattern.args:
        if isinstance(term, Var):
            if term.name not in bindings:
                raise EngineError(f"{pattern.predicate} called with unbound {term}")
            resolved.append(bindings[term.name])
        else:
            resolved.append(term)
    if pattern.predicate == "neq":
        return resolved[0] != resolved[1]
    return resolved[0] < resolved[1]
