"""Running a scenario and rendering the result with its derivation trace.

The report is deliberately unglamorous. It reports what was assessed, what was
not, which rules fired, and what each conclusion rests on. It reports no
probability, no score and no index, because nothing in this repository is
calibrated against outcome data and a number would imply otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .engine import Program, Result
from .facts import Fact, Scenario
from .ontology import Ontology
from .rules import BAND_ORDER, base_facts, build_program

__all__ = ["Assessment", "assess", "render_text"]

CAVEATS: Tuple[str, ...] = (
    "The four context dimensions are the four PIF context categories of IDHEAS-G "
    "(NUREG-2198, 2021), relabelled. They are not original to this tool.",
    "No human error probability is computed. The screening band is an ordinal "
    "label produced by rules marked 'convention', not a rate and not a "
    "probability.",
    "Factor levels are analyst judgements supplied as input. This tool does not "
    "derive them from data and does not check them.",
    "The links from factors to error modes are theoretical propositions taken "
    "from the cited literature. No effect size is attached to any of them, and "
    "none has been validated against injury or incident outcomes.",
    "SPAR-H multipliers are not used. They were estimated for at-power nuclear "
    "power plant operations, and NUREG-2198 states that existing methods are not "
    "necessarily adequate outside that context.",
)


@dataclass
class DimensionSummary:
    """Per-dimension roll-up of the factor levels supplied."""

    dimension: str
    label: str
    idheas_category: Optional[str]
    assessed: int
    total: int
    degraded: List[str] = field(default_factory=list)
    severely_degraded: List[str] = field(default_factory=list)
    unassessed: List[str] = field(default_factory=list)


@dataclass
class Assessment:
    """The structured result of evaluating one scenario."""

    scenario: Scenario
    ontology: Ontology
    program: Program
    result: Result
    dimensions: List[DimensionSummary]
    elevated_error_modes: List[str]
    aggravated_error_modes: List[str]
    challenged_functions: List[str]
    elevated_failure_modes: List[Tuple[str, str, str]]
    aggravated_failure_modes: List[Tuple[str, str]]
    unsupported_demands: List[str]
    unmitigated: List[str]
    screening_band: str
    incomplete: bool

    @property
    def coverage(self) -> Tuple[int, int]:
        """Number of factors assessed, and the number in the ontology."""
        assessed = sum(d.assessed for d in self.dimensions)
        total = sum(d.total for d in self.dimensions)
        return assessed, total

    def explain(self, predicate: str, *args: str) -> List[str]:
        """Derivation trace lines for one conclusion."""
        return self.result.explain(Fact(predicate, tuple(args)))

    def band_trace(self) -> List[str]:
        """Derivation trace for the screening band that was reported."""
        if self.screening_band == "no-flag":
            return ["screeningBand(no-flag)  [no band rule fired]"]
        return self.explain("screeningBand", self.screening_band)


def assess(
    scenario: Scenario,
    ontology: Optional[Ontology] = None,
    program: Optional[Program] = None,
) -> Assessment:
    """Evaluate a scenario against the ontology and the rule base."""
    ontology = ontology or Ontology.load()
    program = program or build_program()
    result = program.evaluate(base_facts(scenario, ontology))

    dimensions: List[DimensionSummary] = []
    for dim_curie in sorted(ontology.dimensions):
        dimension = ontology.dimensions[dim_curie]
        factors = ontology.factors_in(dim_curie)
        degraded = [
            f.curie
            for f in factors
            if result.holds("degradedFactor", f.curie)
            and not result.holds("severelyDegradedFactor", f.curie)
        ]
        severe = [
            f.curie for f in factors if result.holds("severelyDegradedFactor", f.curie)
        ]
        unassessed = [
            f.curie for f in factors if result.holds("unassessedFactor", f.curie)
        ]
        dimensions.append(
            DimensionSummary(
                dimension=dim_curie,
                label=dimension.label,
                idheas_category=dimension.idheas_category,
                assessed=len(factors) - len(unassessed),
                total=len(factors),
                degraded=sorted(degraded),
                severely_degraded=sorted(severe),
                unassessed=sorted(unassessed),
            )
        )

    bands = {f.args[0] for f in result.query("screeningBand", arity=1)}
    band = "no-flag"
    for candidate in BAND_ORDER:
        if candidate in bands:
            band = candidate

    return Assessment(
        scenario=scenario,
        ontology=ontology,
        program=program,
        result=result,
        dimensions=dimensions,
        elevated_error_modes=[f.args[0] for f in result.query("elevatedErrorMode", 1)],
        aggravated_error_modes=[
            f.args[0] for f in result.query("aggravatedErrorMode", 1)
        ],
        challenged_functions=sorted(
            f.args[0] for f in result.query("functionChallenged", 1)
        ),
        elevated_failure_modes=sorted(
            (f.args[0], f.args[1], f.args[2])
            for f in result.query("failureModeElevated", 3)
        ),
        aggravated_failure_modes=sorted(
            (f.args[0], f.args[1]) for f in result.query("failureModeAggravated", 2)
        ),
        unsupported_demands=[
            f.args[0] for f in result.query("unsupportedControlDemand", 1)
        ],
        unmitigated=[f.args[0] for f in result.query("unmitigatedDegradation", 1)],
        screening_band=band,
        incomplete=result.holds("assessmentIncomplete"),
    )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _rule(width: int = 78) -> str:
    return "-" * width


def render_text(assessment: Assessment, show_traces: bool = True) -> str:
    """Render a plain-text report, optionally including full derivation traces."""
    ontology = assessment.ontology
    scenario = assessment.scenario
    out: List[str] = []

    out.append("EHS human-factors context screening")
    out.append(_rule())
    out.append(f"Scenario:    {scenario.scenario_id}")
    if scenario.description:
        out.append(f"Description: {scenario.description}")
    if scenario.provenance:
        out.append(f"Provenance:  {scenario.provenance}")
    if scenario.synthetic:
        out.append("")
        out.append(
            "*** SYNTHETIC SCENARIO. Generated to exercise the engine. It describes "
            "no real site, ***"
        )
        out.append(
            "*** no real crew and no real event, and supports no empirical claim.   "
            "            ***"
        )
    out.append("")

    assessed, total = assessment.coverage
    out.append(f"Assessment coverage: {assessed} of {total} factors assessed")
    if assessment.incomplete:
        out.append(
            "  Unassessed factors are carried as 'unknown', never as 'nominal'. "
            "Read the band accordingly."
        )
    out.append("")

    out.append("Context dimensions")
    out.append(_rule())
    for summary in assessment.dimensions:
        idheas = summary.idheas_category or "(unbound)"
        out.append(
            f"{summary.label}  [IDHEAS-G category: {idheas}]  "
            f"{summary.assessed}/{summary.total} assessed"
        )
        for curie in summary.severely_degraded:
            out.append(f"    severely degraded  {ontology.factor(curie).label}")
        for curie in summary.degraded:
            out.append(f"    degraded           {ontology.factor(curie).label}")
        if summary.unassessed:
            names = ", ".join(ontology.factor(c).label for c in summary.unassessed)
            out.append(f"    unassessed         {names}")
    out.append("")

    out.append("Macrocognitive functions (IDHEAS-G)")
    out.append(_rule())
    if assessment.challenged_functions:
        for fn in assessment.challenged_functions:
            out.append(f"  Challenged: {ontology.functions[fn].label}")
            for n, k, f in assessment.elevated_failure_modes:
                if n == fn:
                    tag = "aggravated" if (n, k) in assessment.aggravated_failure_modes else "elevated"
                    out.append(
                        f"    {tag:10} {ontology.failure_modes[k].label}  "
                        f"<- {ontology.factor(f).label}"
                    )
    else:
        out.append("  No function challenged by the supplied levels.")
    out.append("")

    out.append("Findings")
    out.append(_rule())
    if assessment.unsupported_demands:
        for curie in assessment.unsupported_demands:
            out.append(f"  Unsupported control demand: {curie}")
    if assessment.aggravated_error_modes:
        for curie in assessment.aggravated_error_modes:
            out.append(f"  Aggravated error mode:      {ontology.error_modes[curie].label}")
    for curie in assessment.elevated_error_modes:
        if curie not in assessment.aggravated_error_modes:
            out.append(f"  Elevated error mode:        {ontology.error_modes[curie].label}")
    if assessment.unmitigated:
        names = ", ".join(ontology.factor(c).label for c in assessment.unmitigated)
        out.append(f"  Degraded with no control claimed: {names}")
    if not (
        assessment.unsupported_demands
        or assessment.elevated_error_modes
        or assessment.unmitigated
    ):
        out.append("  No findings from the supplied levels.")
    out.append("")

    out.append(f"Screening band: {assessment.screening_band}")
    out.append(
        "  Ordinal label only. Produced by rules marked 'convention'. Not a "
        "probability, not a rate."
    )
    out.append("")

    if show_traces:
        out.append("Derivation trace: screening band")
        out.append(_rule())
        out.extend("  " + line for line in assessment.band_trace())
        out.append("")

        for n, k in assessment.aggravated_failure_modes:
            out.append(f"Derivation trace: failureModeAggravated({n}, {k})")
            out.extend("  " + line for line in assessment.explain("failureModeAggravated", n, k))
            out.append("")
        for curie in assessment.aggravated_error_modes:
            out.append(f"Derivation trace: aggravatedErrorMode({curie})")
            out.append(_rule())
            out.extend(
                "  " + line for line in assessment.explain("aggravatedErrorMode", curie)
            )
            out.append("")

        for curie in assessment.elevated_error_modes:
            if curie in assessment.aggravated_error_modes:
                continue
            out.append(f"Derivation trace: elevatedErrorMode({curie})")
            out.append(_rule())
            out.extend(
                "  " + line for line in assessment.explain("elevatedErrorMode", curie)
            )
            out.append("")

    out.append("Rules that fired")
    out.append(_rule())
    for rule_id in assessment.result.rules_fired():
        rule = assessment.program.rule(rule_id)
        refs = ", ".join(rule.source_refs) if rule.source_refs else "no source"
        out.append(f"  {rule_id}  [{rule.basis}; {refs}]")
    out.append("")

    out.append("Standing caveats")
    out.append(_rule())
    for caveat in CAVEATS:
        out.append(f" - {caveat}")
    return "\n".join(out)
