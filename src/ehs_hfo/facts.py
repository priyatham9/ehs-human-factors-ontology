"""Facts, patterns, rules and scenarios: the data the engine operates on.

The representation is deliberately plain. A fact is a predicate name and a tuple
of ground string terms. A pattern is the same thing with variables allowed, plus
a negation flag. There are no function symbols, so the Herbrand base of any
program is finite and bottom-up evaluation terminates. That property is the main
reason the representation is this restricted.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Set, Tuple, Union

__all__ = [
    "Var",
    "Fact",
    "Pattern",
    "Rule",
    "RuleError",
    "Scenario",
    "ScenarioError",
    "UNKNOWN_LEVEL",
]

UNKNOWN_LEVEL = "ehs:LevelUnknown"


@dataclass(frozen=True)
class Var:
    """A logic variable. Two variables with the same name are the same variable."""

    name: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"?{self.name}"


Term = Union[str, Var]


@dataclass(frozen=True)
class Fact:
    """A ground atom: a predicate name and constant arguments."""

    predicate: str
    args: Tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.predicate}({', '.join(self.args)})"


@dataclass(frozen=True)
class Pattern:
    """A body or head atom, possibly containing variables.

    ``negated`` marks a negative body literal, evaluated as negation as failure
    over strictly lower strata. ``builtin`` marks a guard evaluated during
    matching rather than looked up in the fact base. Two guards are supported:
    ``neq``, which succeeds when its two arguments differ, and ``lt``, which
    succeeds when the first argument sorts before the second. ``lt`` exists so a
    rule about an unordered pair can be written once rather than firing twice
    with the arguments swapped.
    """

    predicate: str
    args: Tuple[Term, ...]
    negated: bool = False
    builtin: bool = False

    def __str__(self) -> str:
        rendered = ", ".join(str(a) for a in self.args)
        prefix = "not " if self.negated else ""
        return f"{prefix}{self.predicate}({rendered})"

    @property
    def variables(self) -> Set[str]:
        """Names of the variables appearing in this pattern."""
        return {a.name for a in self.args if isinstance(a, Var)}


class RuleError(ValueError):
    """Raised when a rule is unsafe or otherwise malformed."""


BUILTIN_PREDICATES = frozenset({"neq", "lt"})


@dataclass(frozen=True)
class Rule:
    """A Datalog rule with a citation.

    ``basis`` records where the rule comes from and is printed in the derivation
    trace. Two values are used in this repository:

    ``literature``
        The rule states a proposition that appears in the cited source.
    ``convention``
        The rule encodes a threshold or banding decision chosen by the author of
        this repository. No source supports it and none is claimed.
    """

    rule_id: str
    description: str
    body: Tuple[Pattern, ...]
    head: Pattern
    source_refs: Tuple[str, ...] = ()
    basis: str = "literature"
    ontology_terms: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.basis not in ("literature", "convention"):
            raise RuleError(
                f"{self.rule_id}: basis must be 'literature' or 'convention', "
                f"got {self.basis!r}"
            )
        if self.basis == "literature" and not self.source_refs:
            raise RuleError(f"{self.rule_id}: a literature rule must cite a source")
        if self.head.negated:
            raise RuleError(f"{self.rule_id}: the head cannot be negated")
        if self.head.builtin:
            raise RuleError(f"{self.rule_id}: the head cannot be a builtin")

        positive_vars: Set[str] = set()
        for literal in self.body:
            if literal.builtin:
                if literal.predicate not in BUILTIN_PREDICATES:
                    raise RuleError(
                        f"{self.rule_id}: unknown builtin {literal.predicate!r}"
                    )
                continue
            if not literal.negated:
                positive_vars |= literal.variables

        unsafe_head = self.head.variables - positive_vars
        if unsafe_head:
            raise RuleError(
                f"{self.rule_id}: head variables {sorted(unsafe_head)} do not appear "
                "in a positive body literal"
            )
        for literal in self.body:
            if literal.negated or literal.builtin:
                unsafe = literal.variables - positive_vars
                if unsafe:
                    raise RuleError(
                        f"{self.rule_id}: variables {sorted(unsafe)} in {literal} are "
                        "not bound by a positive body literal"
                    )

    def __str__(self) -> str:
        body = ", ".join(str(literal) for literal in self.body)
        return f"{self.head} :- {body}."


class ScenarioError(ValueError):
    """Raised when a scenario description cannot be used."""


@dataclass
class Scenario:
    """A work scenario expressed as factor levels and optional mitigations.

    Attributes
 ----------
    scenario_id:
        Stable identifier used in reports and traces.
    description:
        Free text. Never parsed; carried through to the report.
    factor_levels:
        Map from factor CURIE to level CURIE. Factors omitted here are treated
        as ``ehs:LevelUnknown``, **not** as nominal. Treating an unassessed
        factor as satisfactory is the standard way a screening tool understates
        a hazard, so the default is the honest one and the report shows the
        resulting assessment coverage.
    mitigations:
        Map from factor CURIE to a list of identifiers for controls the site
        claims are in place. The engine uses their presence, never their
        content: it has no way to judge whether a control is effective.
    synthetic:
        True when the scenario was produced by ``synthetic/generate_scenarios.py``.
        Reports print this prominently.
    provenance:
        Free text saying where the scenario came from.
    """

    scenario_id: str
    description: str = ""
    factor_levels: Dict[str, str] = field(default_factory=dict)
    mitigations: Dict[str, List[str]] = field(default_factory=dict)
    synthetic: bool = False
    provenance: str = ""

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Scenario":
        """Build a scenario from a parsed JSON object, validating shapes."""
        if "scenario_id" not in payload:
            raise ScenarioError("scenario is missing 'scenario_id'")
        raw_levels = payload.get("factor_levels", {})
        if not isinstance(raw_levels, Mapping):
            raise ScenarioError("'factor_levels' must be an object")
        levels: Dict[str, str] = {}
        for key, value in raw_levels.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ScenarioError("'factor_levels' must map strings to strings")
            levels[key] = value

        raw_mitigations = payload.get("mitigations", {})
        if not isinstance(raw_mitigations, Mapping):
            raise ScenarioError("'mitigations' must be an object")
        mitigations: Dict[str, List[str]] = {}
        for key, value in raw_mitigations.items():
            if not isinstance(key, str):
                raise ScenarioError("'mitigations' keys must be strings")
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise ScenarioError(
                    f"'mitigations[{key}]' must be a list of control identifiers"
                )
            mitigations[key] = [str(item) for item in value]

        return cls(
            scenario_id=str(payload["scenario_id"]),
            description=str(payload.get("description", "")),
            factor_levels=levels,
            mitigations=mitigations,
            synthetic=bool(payload.get("synthetic", False)),
            provenance=str(payload.get("provenance", "")),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "Scenario":
        """Load a scenario from a JSON file on disk."""
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ScenarioError(f"{os.path.basename(path)} must contain a JSON object")
        return cls.from_dict(payload)

    def to_dict(self) -> Dict[str, object]:
        """Round-trippable dictionary form."""
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "synthetic": self.synthetic,
            "provenance": self.provenance,
            "factor_levels": dict(self.factor_levels),
            "mitigations": {k: list(v) for k, v in self.mitigations.items()},
        }

    def level_for(self, factor_curie: str) -> str:
        """The assessed level for a factor, or the explicit unknown level."""
        return self.factor_levels.get(factor_curie, UNKNOWN_LEVEL)
