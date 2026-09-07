"""Typed access to the EHS human-factors ontology.

This module reads ``ontology/ehs-hfo.ttl`` with :mod:`ehs_hfo.turtle` and exposes
the parts the rule engine and the crosswalk builder need. It performs a small
amount of structural validation on load -- every factor must sit in a declared
dimension, every alignment must name a local factor, an external factor and a
match strength -- and raises :class:`OntologyError` when the file violates them.

It performs no OWL entailment. Subsumption, consistency and classification are
not computed anywhere in this repository, and no claim is made that the file is
consistent under OWL 2 Direct Semantics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .turtle import Graph, IRI, Literal, parse_file

__all__ = [
    "Ontology",
    "OntologyError",
    "Factor",
    "Dimension",
    "FactorLevel",
    "ErrorMode",
    "Alignment",
    "ExternalFactor",
    "Framework",
    "CoverageGap",
    "DEFAULT_ONTOLOGY_PATH",
]

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ONTOLOGY_PATH = os.path.normpath(
    os.path.join(_HERE, "..", "..", "ontology", "ehs-hfo.ttl")
)


class OntologyError(RuntimeError):
    """Raised when the ontology file is structurally unusable."""


# --------------------------------------------------------------------------- #
# Value objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Dimension:
    """One of the four context dimensions."""

    curie: str
    label: str
    definition: str
    idheas_category: Optional[str]
    comment: Optional[str]


@dataclass(frozen=True)
class FactorLevel:
    """An ordinal level a factor can be assigned in a scenario."""

    curie: str
    label: str
    rank: int
    definition: str

    @property
    def is_degraded(self) -> bool:
        """True when the level is worse than nominal but assessed."""
        return self.rank in (0, -1)

    @property
    def is_assessed(self) -> bool:
        """True unless the level is the explicit 'unknown' state."""
        return self.rank != -99


@dataclass(frozen=True)
class ErrorMode:
    """A human failure class, keyed to a cognitive control level."""

    curie: str
    label: str
    control_level: Optional[str]
    definition: str
    approximates: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MacrocognitiveFunction:
    """One of the five IDHEAS-G macrocognitive functions."""

    curie: str
    label: str
    definition: str


@dataclass(frozen=True)
class CognitiveFailureMode:
    """A failure mode of one macrocognitive function."""

    curie: str
    label: str
    function: str


@dataclass(frozen=True)
class Factor:
    """A performance-influencing factor."""

    curie: str
    label: str
    verbatim_label: Optional[str]
    dimension: str
    source_refs: Tuple[str, ...]
    predisposes_to: Tuple[str, ...]
    raises_demand_on: Tuple[str, ...]
    applies_to_functions: Tuple[str, ...]
    affects_failure_modes: Tuple[str, ...]
    observable_proxies: Tuple[str, ...]
    boundary_notes: Tuple[str, ...]
    comment: Optional[str]

    @property
    def local_name(self) -> str:
        """The part of the CURIE after the colon."""
        return self.curie.split(":", 1)[1]


@dataclass(frozen=True)
class Framework:
    """An external published framework."""

    curie: str
    label: str
    citation: Optional[str]
    source_refs: Tuple[str, ...]
    comment: Optional[str]


@dataclass(frozen=True)
class ExternalFactor:
    """A factor belonging to an external framework."""

    curie: str
    label: str
    verbatim_label: Optional[str]
    framework: Optional[str]
    parent: Optional[str]
    source_refs: Tuple[str, ...]
    out_of_scope_note: Optional[str]


@dataclass(frozen=True)
class Alignment:
    """A reified, cited correspondence between a local and an external factor."""

    curie: str
    local_factor: str
    external_factor: str
    match_strength: str
    source_refs: Tuple[str, ...]
    comment: Optional[str]


@dataclass(frozen=True)
class CoverageGap:
    """An external factor recorded as uncovered or only partially covered."""

    curie: str
    uncovered_factor: str
    comment: Optional[str]
    source_refs: Tuple[str, ...]


# --------------------------------------------------------------------------- #
# Ontology
# --------------------------------------------------------------------------- #


class Ontology:
    """A loaded, validated view of the ontology file."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.dimensions: Dict[str, Dimension] = {}
        self.levels: Dict[str, FactorLevel] = {}
        self.error_modes: Dict[str, ErrorMode] = {}
        self.functions: Dict[str, MacrocognitiveFunction] = {}
        self.failure_modes: Dict[str, CognitiveFailureMode] = {}
        self.factors: Dict[str, Factor] = {}
        self.frameworks: Dict[str, Framework] = {}
        self.external_factors: Dict[str, ExternalFactor] = {}
        self.alignments: Dict[str, Alignment] = {}
        self.coverage_gaps: Dict[str, CoverageGap] = {}
        self.no_counterpart: Dict[str, Tuple[str, ...]] = {}
        self._load()
        self._validate()

    # -- construction ------------------------------------------------------- #

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Ontology":
        """Parse and validate the ontology file."""
        return cls(parse_file(path or DEFAULT_ONTOLOGY_PATH))

    def _curie(self, term: object) -> str:
        if not isinstance(term, IRI):
            raise OntologyError(f"expected an IRI, found {term!r}")
        return self.graph.shorten(term)

    def _opt_curie(self, term: object) -> Optional[str]:
        return None if term is None else self._curie(term)

    def _lit(self, subject: object, predicate: str) -> Optional[str]:
        return self.graph.literal(subject, predicate)

    def _lits(self, subject: object, predicate: str) -> Tuple[str, ...]:
        return tuple(self.graph.literals(subject, predicate))

    def _label(self, subject: object) -> str:
        values = self.graph.literals(subject, "rdfs:label")
        if not values:
            raise OntologyError(f"{self._curie(subject)} has no rdfs:label")
        return values[0]

    def _load(self) -> None:
        g = self.graph

        for node in g.instances_of("ehs:ContextDimension"):
            curie = self._curie(node)
            self.dimensions[curie] = Dimension(
                curie=curie,
                label=self._label(node),
                definition=self._lit(node, "skos:definition") or "",
                idheas_category=self._opt_curie(
                    g.value(node, "ehs:correspondsToIdheasCategory")
                ),
                comment=self._lit(node, "rdfs:comment"),
            )

        for node in g.instances_of("ehs:FactorLevel"):
            curie = self._curie(node)
            rank_literal = g.value(node, "ehs:ordinalRank")
            if not isinstance(rank_literal, Literal):
                raise OntologyError(f"{curie} has no ehs:ordinalRank")
            self.levels[curie] = FactorLevel(
                curie=curie,
                label=self._label(node),
                rank=int(rank_literal.value),
                definition=self._lit(node, "skos:definition") or "",
            )

        for node in g.instances_of("ehs:ErrorMode"):
            curie = self._curie(node)
            self.error_modes[curie] = ErrorMode(
                curie=curie,
                label=self._label(node),
                control_level=self._opt_curie(g.value(node, "ehs:arisesAt")),
                definition=self._lit(node, "skos:definition") or "",
                approximates=tuple(
                    self._curie(o) for o in g.objects(node, "ehs:approximatesFailureMode")
                ),
            )

        for node in g.instances_of("ehs:MacrocognitiveFunction"):
            curie = self._curie(node)
            self.functions[curie] = MacrocognitiveFunction(
                curie=curie,
                label=self._label(node),
                definition=self._lit(node, "skos:definition") or "",
            )

        for node in g.instances_of("ehs:CognitiveFailureMode"):
            curie = self._curie(node)
            function = g.value(node, "ehs:failureOfFunction")
            if function is None:
                raise OntologyError(f"{curie} has no ehs:failureOfFunction")
            self.failure_modes[curie] = CognitiveFailureMode(
                curie=curie, label=self._label(node), function=self._curie(function)
            )

        for node in g.instances_of("ehs:PerformanceInfluencingFactor"):
            curie = self._curie(node)
            dimension = g.value(node, "ehs:inDimension")
            if dimension is None:
                raise OntologyError(f"{curie} has no ehs:inDimension")
            self.factors[curie] = Factor(
                curie=curie,
                label=self._label(node),
                verbatim_label=self._lit(node, "ehs:verbatimLabel"),
                dimension=self._curie(dimension),
                source_refs=self._lits(node, "ehs:sourceRef"),
                predisposes_to=tuple(
                    self._curie(o) for o in g.objects(node, "ehs:predisposesTo")
                ),
                raises_demand_on=tuple(
                    self._curie(o)
                    for o in g.objects(node, "ehs:degradationRaisesDemandOn")
                ),
                applies_to_functions=tuple(
                    self._curie(o) for o in g.objects(node, "ehs:appliesToFunction")
                ),
                affects_failure_modes=tuple(
                    self._curie(o) for o in g.objects(node, "ehs:affectsFailureMode")
                ),
                observable_proxies=self._lits(node, "ehs:observableProxy"),
                boundary_notes=self._lits(node, "ehs:boundaryNote"),
                comment=self._lit(node, "rdfs:comment"),
            )
            counterpart_gaps = tuple(
                self._curie(o) for o in g.objects(node, "ehs:noCounterpartIn")
            )
            if counterpart_gaps:
                self.no_counterpart[curie] = counterpart_gaps

        for node in g.instances_of("ehs:ExternalFramework"):
            curie = self._curie(node)
            self.frameworks[curie] = Framework(
                curie=curie,
                label=self._label(node),
                citation=self._lit(node, "dcterms:bibliographicCitation"),
                source_refs=self._lits(node, "ehs:sourceRef"),
                comment=self._lit(node, "rdfs:comment"),
            )

        for node in g.instances_of("ehs:ExternalFactor"):
            curie = self._curie(node)
            self.external_factors[curie] = ExternalFactor(
                curie=curie,
                label=self._label(node),
                verbatim_label=self._lit(node, "ehs:verbatimLabel"),
                framework=self._opt_curie(g.value(node, "ehs:definedIn")),
                parent=self._opt_curie(g.value(node, "ehs:externalParent")),
                source_refs=self._lits(node, "ehs:sourceRef"),
                out_of_scope_note=self._lit(node, "ehs:outOfScopeNote"),
            )

        for node in g.instances_of("ehs:Alignment"):
            curie = self._curie(node)
            local = g.value(node, "ehs:localFactor")
            external = g.value(node, "ehs:externalFactor")
            strength = g.value(node, "ehs:hasMatchStrength")
            if local is None or external is None or strength is None:
                raise OntologyError(
                    f"{curie} must have a local factor, an external factor and a strength"
                )
            self.alignments[curie] = Alignment(
                curie=curie,
                local_factor=self._curie(local),
                external_factor=self._curie(external),
                match_strength=self._curie(strength),
                source_refs=self._lits(node, "ehs:sourceRef"),
                comment=self._lit(node, "rdfs:comment"),
            )

        for node in g.instances_of("ehs:CoverageGap"):
            curie = self._curie(node)
            uncovered = g.value(node, "ehs:uncoveredFactor")
            if uncovered is None:
                raise OntologyError(f"{curie} has no ehs:uncoveredFactor")
            self.coverage_gaps[curie] = CoverageGap(
                curie=curie,
                uncovered_factor=self._curie(uncovered),
                comment=self._lit(node, "rdfs:comment"),
                source_refs=self._lits(node, "ehs:sourceRef"),
            )

    def _validate(self) -> None:
        """Check referential integrity of the loaded model."""
        problems: List[str] = []

        if not self.factors:
            problems.append("no performance-influencing factors were loaded")
        for factor in self.factors.values():
            if factor.dimension not in self.dimensions:
                problems.append(
                    f"{factor.curie} is in unknown dimension {factor.dimension}"
                )
            for mode in factor.predisposes_to:
                if mode not in self.error_modes:
                    problems.append(f"{factor.curie} predisposes to unknown {mode}")
            if not factor.applies_to_functions:
                problems.append(f"{factor.curie} applies to no macrocognitive function")
            for fn in factor.applies_to_functions:
                if fn not in self.functions:
                    problems.append(f"{factor.curie} applies to unknown function {fn}")
            for cfm in factor.affects_failure_modes:
                if cfm not in self.failure_modes:
                    problems.append(f"{factor.curie} affects unknown failure mode {cfm}")
                elif self.failure_modes[cfm].function not in factor.applies_to_functions:
                    problems.append(
                        f"{factor.curie} affects {cfm} but does not apply to its function"
                    )

        for cfm in self.failure_modes.values():
            if cfm.function not in self.functions:
                problems.append(f"{cfm.curie} is a failure of unknown function {cfm.function}")
        for mode in self.error_modes.values():
            for cfm in mode.approximates:
                if cfm not in self.failure_modes:
                    problems.append(f"{mode.curie} approximates unknown failure mode {cfm}")

        for alignment in self.alignments.values():
            if alignment.local_factor not in self.factors:
                problems.append(
                    f"{alignment.curie} names unknown local factor {alignment.local_factor}"
                )
            if alignment.external_factor not in self.external_factors:
                problems.append(
                    f"{alignment.curie} names unknown external factor "
                    f"{alignment.external_factor}"
                )
            if not alignment.source_refs:
                problems.append(f"{alignment.curie} has no ehs:sourceRef")

        for external in self.external_factors.values():
            if external.framework is not None and external.framework not in self.frameworks:
                problems.append(
                    f"{external.curie} names unknown framework {external.framework}"
                )
            if external.parent is not None and external.parent not in self.external_factors:
                problems.append(f"{external.curie} names unknown parent {external.parent}")

        for gap in self.coverage_gaps.values():
            if gap.uncovered_factor not in self.external_factors:
                problems.append(
                    f"{gap.curie} names unknown external factor {gap.uncovered_factor}"
                )

        for factor_curie, frameworks in self.no_counterpart.items():
            for framework in frameworks:
                if framework not in self.frameworks:
                    problems.append(
                        f"{factor_curie} claims no counterpart in unknown {framework}"
                    )

        if problems:
            raise OntologyError(
                "ontology failed structural validation:\n - "
                + "\n - ".join(problems)
            )

    # -- queries ------------------------------------------------------------ #

    def factors_in(self, dimension_curie: str) -> List[Factor]:
        """Factors assigned to a dimension, in label order."""
        return sorted(
            (f for f in self.factors.values() if f.dimension == dimension_curie),
            key=lambda f: f.label,
        )

    def alignments_for(self, factor_curie: str) -> List[Alignment]:
        """All alignments whose local factor is the one named."""
        return [a for a in self.alignments.values() if a.local_factor == factor_curie]

    def alignments_to(self, external_curie: str) -> List[Alignment]:
        """All alignments pointing at the named external factor."""
        return [a for a in self.alignments.values() if a.external_factor == external_curie]

    def external_factors_of(self, framework_curie: str) -> List[ExternalFactor]:
        """External factors belonging to one framework, in label order."""
        return sorted(
            (e for e in self.external_factors.values() if e.framework == framework_curie),
            key=lambda e: e.label,
        )

    def level(self, curie: str) -> FactorLevel:
        """Look up a factor level, raising a clear error if it is unknown."""
        try:
            return self.levels[curie]
        except KeyError:
            raise OntologyError(f"unknown factor level {curie!r}") from None

    def factor(self, curie: str) -> Factor:
        """Look up a factor, raising a clear error if it is unknown."""
        try:
            return self.factors[curie]
        except KeyError:
            raise OntologyError(f"unknown factor {curie!r}") from None

    def all_source_refs(self) -> List[str]:
        """Every distinct citation key referenced anywhere in the ontology."""
        keys = set()
        for triple in self.graph.triples:
            if triple[1] == self.graph.expand("ehs:sourceRef") and isinstance(
                triple[2], Literal
            ):
                keys.add(triple[2].value)
        return sorted(keys)
