"""The rule base, and the translation from ontology and scenario into facts.

Every rule carries a ``basis``. ``literature`` means the proposition appears in
the cited source; ``convention`` means the threshold was chosen by the author of
this repository and no source supports it. The distinction is printed in every
derivation trace, because the difference between "Rasmussen says so" and "I
picked two" is the difference a reviewer will want to see.

Predicate vocabulary
--------------------
Extensional (supplied as input):

===========================  =============================================
``factorInDimension(F, D)``  from the ontology
``factorPredisposesTo(F,M)`` from the ontology
``factorRaisesDemandOn(F,C)`` from the ontology
``errorModeAtControl(M, C)`` from the ontology
``levelDegraded(L)``         ontology level with ordinal rank 0 or -1
``levelSeverelyDegraded(L)`` ontology level with ordinal rank -1
``levelUnassessed(L)``       ontology level with ordinal rank -99
``factorLevel(F, L)``        from the scenario
``mitigation(F, C)``         from the scenario
===========================  =============================================

Intensional (derived):

==================================  =========================================
``degradedFactor(F)``               factor assessed below nominal
``severelyDegradedFactor(F)``       factor assessed at the lowest level
``unassessedFactor(F)``             factor with no assessment recorded
``mitigatedFactor(F)``              a control is claimed against the factor
``unmitigatedDegradation(F)``       degraded and no control claimed
``degradedForFunction(N, F)``       a degraded factor, with a function it applies to
``functionChallenged(N)``           at least one applicable degraded factor for N
``failureModeElevated(N, K, F)``    factor F raises failure mode K of function N
``failureModeAggravated(N, K)``     two distinct degraded factors raise K of N
``multiFunctionChallenge()``        two or more functions challenged
``controlDemand(C)``                the task is pushed to a control level
``unsupportedControlDemand(C)``     that demand is not backed by training
``elevatedErrorMode(M)``            an error mode flagged by a degraded factor
``aggravatedErrorMode(M)``          flagged and made worse by a second factor
``assessmentIncomplete()``          at least one factor is unassessed
``screeningBand(B)``                a qualitative screening outcome
==================================  =========================================

``screeningBand`` is an ordinal label. It is not a probability, not a rate, and
not calibrated against any outcome data. See the README section "What this does
not buy you".
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .engine import Program
from .facts import Fact, Pattern, Rule, Scenario, ScenarioError, UNKNOWN_LEVEL, Var
from .ontology import Ontology

__all__ = [
    "RULES",
    "BAND_ORDER",
    "build_program",
    "ontology_facts",
    "scenario_facts",
    "base_facts",
]

_F = Var("F")
_G = Var("G")
_D = Var("D")
_E = Var("E")
_L = Var("L")
_M = Var("M")
_C = Var("C")
_N = Var("N")
_O = Var("O")
_K = Var("K")

KNOWLEDGE_BASED = "ehs:KnowledgeBasedControl"
KB_MISTAKE = "ehs:KnowledgeBasedMistake"
TRAINING = "ehs:Training"
TIME_PRESSURE = "ehs:TimePressureAndStress"
PROCEDURES = "ehs:ProceduresGuidanceAndInstructions"

#: Screening bands from least to most serious. Used only for ordering output.
BAND_ORDER: Tuple[str, ...] = (
    "no-flag",
    "review",
    "elevated",
    "stop-and-review",
)


def _p(predicate: str, *args: object) -> Pattern:
    return Pattern(predicate, tuple(args))  # type: ignore[arg-type]


def _not(predicate: str, *args: object) -> Pattern:
    return Pattern(predicate, tuple(args), negated=True)  # type: ignore[arg-type]


def _neq(left: object, right: object) -> Pattern:
    return Pattern("neq", (left, right), builtin=True)  # type: ignore[arg-type]


def _lt(left: object, right: object) -> Pattern:
    return Pattern("lt", (left, right), builtin=True)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Rule base
# --------------------------------------------------------------------------- #

RULES: Tuple[Rule, ...] = (
    # -- levels to factor states ------------------------------------------- #
    Rule(
        rule_id="R01-degraded",
        description=(
            "A factor assessed below the nominal condition is a degraded factor. "
            "Levels and their ordinal ranks come from the ontology, not from here."
        ),
        body=(_p("factorLevel", _F, _L), _p("levelDegraded", _L)),
        head=_p("degradedFactor", _F),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R02-severely-degraded",
        description="A factor at the lowest assessed level is severely degraded.",
        body=(_p("factorLevel", _F, _L), _p("levelSeverelyDegraded", _L)),
        head=_p("severelyDegradedFactor", _F),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R03-unassessed",
        description=(
            "A factor carrying the explicit unknown level is unassessed. It is not "
            "treated as nominal anywhere in this program."
        ),
        body=(_p("factorLevel", _F, _L), _p("levelUnassessed", _L)),
        head=_p("unassessedFactor", _F),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R04-incomplete",
        description="An assessment with any unassessed factor is incomplete.",
        body=(_p("unassessedFactor", _F),),
        head=_p("assessmentIncomplete"),
        source_refs=("groth2012",),
    ),
    # -- mitigation, the one negative dependency in the program ------------- #
    Rule(
        rule_id="R05-mitigated",
        description=(
            "A factor against which the site claims a control is a mitigated factor. "
            "The engine records that a control was claimed. It cannot and does not "
            "judge whether the control works."
        ),
        body=(_p("mitigation", _F, _C),),
        head=_p("mitigatedFactor", _F),
        source_refs=("hse_pifs",),
    ),
    Rule(
        rule_id="R06-unmitigated",
        description="A degraded factor with no claimed control is an unmitigated degradation.",
        body=(_p("degradedFactor", _F), _not("mitigatedFactor", _F)),
        head=_p("unmitigatedDegradation", _F),
        source_refs=("hse_pifs",),
    ),
    # -- function-specific roll-up (IDHEAS-G structure) -------------------- #
    Rule(
        rule_id="R07-degraded-for-function",
        description=(
            "Attach each degraded factor to every macrocognitive function the "
            "ontology says it applies to. A PIF has no effect outside the functions "
            "it applies to, so nothing is rolled up across a whole context category."
        ),
        body=(_p("degradedFactor", _F), _p("factorAppliesToFunction", _F, _N)),
        head=_p("degradedForFunction", _N, _F),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R08-function-challenged",
        description="A function with any applicable degraded factor is challenged.",
        body=(_p("degradedForFunction", _N, _F),),
        head=_p("functionChallenged", _N),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R09-failure-mode-elevated",
        description=(
            "A degraded factor raises the cognitive failure mode of the function it "
            "affects. The function is carried in the conclusion so the trace shows "
            "which function and which failure mode the finding belongs to."
        ),
        body=(
            _p("degradedFactor", _F),
            _p("factorAffectsFailureMode", _F, _K),
            _p("failureModeOfFunction", _K, _N),
        ),
        head=_p("failureModeElevated", _N, _K, _F),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R12-failure-mode-aggravated",
        description=(
            "Two distinct degraded factors raising the same failure mode of the same "
            "function. Two routes to one failure mode are open; no multiplicative "
            "claim is made."
        ),
        body=(
            _p("failureModeElevated", _N, _K, _F),
            _p("failureModeElevated", _N, _K, _G),
            _lt(_F, _G),
        ),
        head=_p("failureModeAggravated", _N, _K),
        source_refs=("nureg2198",),
    ),
    Rule(
        rule_id="R13-multi-function",
        description=(
            "Two or more distinct macrocognitive functions are challenged. This "
            "replaces the earlier multi-dimension rule: IDHEAS-G structures PIF "
            "effects by function, not by context category."
        ),
        body=(
            _p("functionChallenged", _N),
            _p("functionChallenged", _O),
            _lt(_N, _O),
        ),
        head=_p("multiFunctionChallenge"),
        source_refs=("nureg2198",),
    ),
    # -- cognitive control demand ------------------------------------------ #
    Rule(
        rule_id="R10-control-demand",
        description=(
            "Degrading a factor that the ontology marks as raising demand on a "
            "control level creates that demand. Scenario familiarity is the "
            "principal case: a situation for which no stored rule applies must be "
            "handled by reasoning from a model of the system."
        ),
        body=(_p("degradedFactor", _F), _p("factorRaisesDemandOn", _F, _C)),
        head=_p("controlDemand", _C),
        source_refs=("rasmussen1983",),
    ),
    Rule(
        rule_id="R11-unsupported-demand",
        description=(
            "A demand for a given control level is unsupported when the operator's "
            "training is itself degraded. Knowledge-based performance depends on the "
            "quality of the mental model training is supposed to have built."
        ),
        body=(_p("controlDemand", _C), _p("degradedFactor", TRAINING)),
        head=_p("unsupportedControlDemand", _C),
        source_refs=("rasmussen1983", "reason1990"),
    ),
    # -- error modes -------------------------------------------------------- #
    Rule(
        rule_id="R20-elevated-from-factor",
        description=(
            "A degraded factor flags the error modes the ontology associates with "
            "it. The association is a theoretical claim from the cited source; no "
            "effect size is attached to it."
        ),
        body=(_p("degradedFactor", _F), _p("factorPredisposesTo", _F, _M)),
        head=_p("elevatedErrorMode", _M),
        source_refs=("reason1990",),
    ),
    Rule(
        rule_id="R21-elevated-from-unsupported-demand",
        description=(
            "An unsupported demand for a control level flags the error mode that "
            "arises at that level."
        ),
        body=(_p("unsupportedControlDemand", _C), _p("errorModeAtControl", _M, _C)),
        head=_p("elevatedErrorMode", _M),
        source_refs=("rasmussen1983", "reason1990"),
    ),
    Rule(
        rule_id="R22-aggravated-by-second-factor",
        description=(
            "An error mode flagged by one degraded factor and flagged again by a "
            "second, distinct degraded factor is recorded as aggravated. This says "
            "two independent routes to the same failure class are open. It does not "
            "say the risk has doubled; nothing here supports a multiplicative claim."
        ),
        body=(
            _p("degradedFactor", _F),
            _p("factorPredisposesTo", _F, _M),
            _p("degradedFactor", _G),
            _p("factorPredisposesTo", _G, _M),
            _lt(_F, _G),
        ),
        head=_p("aggravatedErrorMode", _M),
        source_refs=("groth2012",),
    ),
    Rule(
        rule_id="R23-time-pressure-on-knowledge-based",
        description=(
            "Knowledge-based performance is slow and effortful, so time pressure "
            "bears on it more heavily than on rule-based or skill-based performance. "
            "Where a knowledge-based demand is already unsupported and time pressure "
            "is degraded, the knowledge-based mistake mode is recorded as aggravated."
        ),
        body=(
            _p("unsupportedControlDemand", KNOWLEDGE_BASED),
            _p("degradedFactor", TIME_PRESSURE),
        ),
        head=_p("aggravatedErrorMode", KB_MISTAKE),
        source_refs=("rasmussen1983", "reason1990"),
    ),
    Rule(
        rule_id="R24-procedure-substitution",
        description=(
            "Adequate procedures can carry an unfamiliar task at the rule-based "
            "level. Where scenario familiarity is degraded and procedures are also "
            "degraded, the fallback is gone; this records that condition explicitly "
            "so it appears in the trace rather than being inferred by the reader."
        ),
        body=(
            _p("degradedFactor", "ehs:ScenarioFamiliarity"),
            _p("degradedFactor", PROCEDURES),
        ),
        head=_p("noRuleBasedFallback"),
        source_refs=("rasmussen1983", "hollnagel1998"),
    ),
    # -- screening bands: conventions, not findings ------------------------- #
    Rule(
        rule_id="R30-band-review",
        description=(
            "Any unmitigated degradation puts the scenario in the review band. "
            "Threshold chosen by the author; no source supports it."
        ),
        body=(_p("unmitigatedDegradation", _F),),
        head=_p("screeningBand", "review"),
        basis="convention",
    ),
    Rule(
        rule_id="R31-band-elevated-multi-function",
        description=(
            "Unmitigated degradation bearing on two or more distinct macrocognitive "
            "functions raises the band to elevated. Threshold chosen by the author; "
            "no source supports it."
        ),
        body=(
            _p("unmitigatedDegradation", _F),
            _p("factorAppliesToFunction", _F, _N),
            _p("unmitigatedDegradation", _G),
            _p("factorAppliesToFunction", _G, _O),
            _lt(_N, _O),
        ),
        head=_p("screeningBand", "elevated"),
        basis="convention",
    ),
    Rule(
        rule_id="R35-band-elevated-failure-mode-aggravated",
        description=(
            "An aggravated cognitive failure mode of any function raises the band to "
            "elevated. Threshold chosen by the author; no source supports it."
        ),
        body=(_p("failureModeAggravated", _N, _K),),
        head=_p("screeningBand", "elevated"),
        basis="convention",
    ),
    Rule(
        rule_id="R32-band-elevated-aggravated",
        description=(
            "Any aggravated error mode raises the band to elevated. Threshold "
            "chosen by the author; no source supports it."
        ),
        body=(_p("aggravatedErrorMode", _M),),
        head=_p("screeningBand", "elevated"),
        basis="convention",
    ),
    Rule(
        rule_id="R33-band-stop-and-review",
        description=(
            "A severely degraded factor occurring alongside an aggravated error mode "
            "puts the scenario in the stop-and-review band. Threshold chosen by the "
            "author; no source supports it."
        ),
        body=(
            _p("severelyDegradedFactor", _F),
            _not("mitigatedFactor", _F),
            _p("aggravatedErrorMode", _M),
        ),
        head=_p("screeningBand", "stop-and-review"),
        basis="convention",
    ),
    Rule(
        rule_id="R34-band-stop-and-review-no-fallback",
        description=(
            "An unsupported knowledge-based demand with no rule-based fallback puts "
            "the scenario in the stop-and-review band. Threshold chosen by the "
            "author; no source supports it."
        ),
        body=(
            _p("unsupportedControlDemand", KNOWLEDGE_BASED),
            _p("noRuleBasedFallback"),
        ),
        head=_p("screeningBand", "stop-and-review"),
        basis="convention",
    ),
)


def build_program() -> Program:
    """Construct and stratify the rule base."""
    return Program(RULES)


# --------------------------------------------------------------------------- #
# Fact construction
# --------------------------------------------------------------------------- #


def ontology_facts(ontology: Ontology) -> List[Fact]:
    """Translate the ontology into the extensional facts the rules read.

    Nothing is invented here. Each fact restates an assertion already present in
    ``ontology/ehs-hfo.ttl``.
    """
    facts: List[Fact] = []
    for factor in ontology.factors.values():
        facts.append(Fact("factorInDimension", (factor.curie, factor.dimension)))
        for mode in factor.predisposes_to:
            facts.append(Fact("factorPredisposesTo", (factor.curie, mode)))
        for control in factor.raises_demand_on:
            facts.append(Fact("factorRaisesDemandOn", (factor.curie, control)))
        for function in factor.applies_to_functions:
            facts.append(Fact("factorAppliesToFunction", (factor.curie, function)))
        for cfm in factor.affects_failure_modes:
            facts.append(Fact("factorAffectsFailureMode", (factor.curie, cfm)))
    for mode in ontology.error_modes.values():
        if mode.control_level is not None:
            facts.append(Fact("errorModeAtControl", (mode.curie, mode.control_level)))
    for cfm in ontology.failure_modes.values():
        facts.append(Fact("failureModeOfFunction", (cfm.curie, cfm.function)))
    for level in ontology.levels.values():
        if level.is_degraded:
            facts.append(Fact("levelDegraded", (level.curie,)))
        if level.rank == -1:
            facts.append(Fact("levelSeverelyDegraded", (level.curie,)))
        if not level.is_assessed:
            facts.append(Fact("levelUnassessed", (level.curie,)))
    return facts


def scenario_facts(scenario: Scenario, ontology: Ontology) -> List[Fact]:
    """Translate a scenario into facts, validating every identifier it uses.

    Factors the scenario does not mention are emitted at the explicit unknown
    level, so an incomplete assessment shows up as incomplete rather than as a
    clean one.
    """
    unknown_factors = sorted(set(scenario.factor_levels) - set(ontology.factors))
    if unknown_factors:
        raise ScenarioError(
            f"scenario {scenario.scenario_id!r} references factors that are not in "
            f"the ontology: {', '.join(unknown_factors)}"
        )
    unknown_levels = sorted(set(scenario.factor_levels.values()) - set(ontology.levels))
    if unknown_levels:
        raise ScenarioError(
            f"scenario {scenario.scenario_id!r} uses levels that are not in the "
            f"ontology: {', '.join(unknown_levels)}"
        )
    unknown_mitigated = sorted(set(scenario.mitigations) - set(ontology.factors))
    if unknown_mitigated:
        raise ScenarioError(
            f"scenario {scenario.scenario_id!r} claims controls against factors that "
            f"are not in the ontology: {', '.join(unknown_mitigated)}"
        )

    facts: List[Fact] = []
    for factor_curie in sorted(ontology.factors):
        facts.append(
            Fact("factorLevel", (factor_curie, scenario.level_for(factor_curie)))
        )
    for factor_curie, controls in sorted(scenario.mitigations.items()):
        for control in controls:
            facts.append(Fact("mitigation", (factor_curie, control)))
    return facts


def base_facts(scenario: Scenario, ontology: Ontology) -> List[Fact]:
    """All extensional facts for one evaluation."""
    return ontology_facts(ontology) + scenario_facts(scenario, ontology)
