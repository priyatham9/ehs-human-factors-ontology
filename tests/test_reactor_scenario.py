"""The worked chemical-reactor scenario.

The scenario is the one the README walks through: an inexperienced operator, a
non-routine plant condition with no covering procedure, and a fixed time window.
The expected conclusion is that the task is displaced from rule-based to
knowledge-based control while the training to support that control level is
degraded, so knowledge-based mistake risk is elevated.

What these tests check is that **the engine derives that conclusion from the
stated facts and rules, and can show its working**. They are not evidence that
the conclusion is true of any real reactor. The scenario is hand-written, the
chain is Rasmussen's and Reason's rather than this repository's, and no
probability is computed anywhere.
"""

from __future__ import annotations

import os
import unittest

from tests import context

from ehs_hfo.assessment import assess, render_text
from ehs_hfo.facts import Scenario

SCENARIO_PATH = os.path.join(
    context.EXAMPLES_DIR, "reactor_startup_nonroutine.json"
)


class TestReactorScenario(unittest.TestCase):
    """Inexperienced operator + non-routine conditions + time pressure."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = Scenario.from_json_file(SCENARIO_PATH)
        cls.assessment = assess(
            cls.scenario, context.ontology(), context.program()
        )
        cls.result = cls.assessment.result

    # -- the inputs are what the docstring says they are ------------------- #

    def test_the_three_stated_conditions_are_present(self) -> None:
        levels = self.scenario.factor_levels
        degraded = {"ehs:LevelDegraded", "ehs:LevelSeverelyDegraded"}
        self.assertIn(levels["ehs:Training"], degraded, "inexperienced operator")
        self.assertIn(
            levels["ehs:ScenarioFamiliarity"], degraded, "non-routine conditions"
        )
        self.assertIn(
            levels["ehs:TimePressureAndStress"], degraded, "time pressure"
        )

    def test_scenario_is_fully_assessed(self) -> None:
        """All twenty factors are supplied, so the band is not weakened by gaps."""
        assessed, total = self.assessment.coverage
        self.assertEqual(assessed, total)
        self.assertEqual(total, 20)
        self.assertFalse(self.assessment.incomplete)

    def test_scenario_is_not_labelled_synthetic(self) -> None:
        """A hand-written illustration, not generator output."""
        self.assertFalse(self.scenario.synthetic)

    # -- the expected conclusion -------------------------------------------- #

    def test_knowledge_based_control_is_demanded(self) -> None:
        """An unfamiliar situation with no covering procedure forces the shift."""
        self.assertTrue(
            self.result.holds("controlDemand", "ehs:KnowledgeBasedControl")
        )

    def test_the_knowledge_based_demand_is_unsupported(self) -> None:
        """Demand for knowledge-based control, with training degraded."""
        self.assertTrue(
            self.result.holds(
                "unsupportedControlDemand", "ehs:KnowledgeBasedControl"
            )
        )
        self.assertIn(
            "ehs:KnowledgeBasedControl", self.assessment.unsupported_demands
        )

    def test_knowledge_based_mistake_risk_is_elevated(self) -> None:
        """The headline conclusion the scenario exists to demonstrate."""
        self.assertTrue(
            self.result.holds("elevatedErrorMode", "ehs:KnowledgeBasedMistake")
        )

    def test_knowledge_based_mistake_risk_is_aggravated(self) -> None:
        """Two distinct degraded factors bear on the same error mode."""
        self.assertTrue(
            self.result.holds("aggravatedErrorMode", "ehs:KnowledgeBasedMistake")
        )
        self.assertIn(
            "ehs:KnowledgeBasedMistake", self.assessment.aggravated_error_modes
        )

    def test_the_flagged_factors_are_left_unmitigated(self) -> None:
        """No controls are claimed, so each degraded factor stands unmitigated."""
        for factor in (
            "ehs:Training",
            "ehs:ScenarioFamiliarity",
            "ehs:TimePressureAndStress",
        ):
            with self.subTest(factor=factor):
                self.assertTrue(
                    self.result.holds("unmitigatedDegradation", factor)
                )

    def test_band_is_the_most_severe(self) -> None:
        from ehs_hfo.rules import BAND_ORDER

        self.assertEqual(self.assessment.screening_band, BAND_ORDER[-1])

    # -- the derivation must be inspectable --------------------------------- #

    def test_the_conclusion_traces_back_to_the_stated_inputs(self) -> None:
        """Every leaf of the trace is a fact the scenario or ontology supplied."""
        trace = "\n".join(
            self.result.explain(
                self._fact("aggravatedErrorMode", "ehs:KnowledgeBasedMistake")
            )
        )
        self.assertIn("ehs:ScenarioFamiliarity", trace)
        self.assertIn("ehs:TimePressureAndStress", trace)
        self.assertIn("given", trace)

    def test_every_degraded_input_appears_in_some_derivation(self) -> None:
        """The default trace shows one derivation; all of them are recorded.

        ``explain`` prints a single derivation per fact by default and says how
        many it withheld. The support is still there, so widening the trace has
        to surface the training route as well.
        """
        trace = "\n".join(
            self.result.explain(
                self._fact("aggravatedErrorMode", "ehs:KnowledgeBasedMistake"),
                max_alternatives=8,
            )
        )
        self.assertIn("ehs:Training", trace)

    def test_the_report_is_byte_identical_across_runs(self) -> None:
        """An audit record that changes between runs is not an audit record.

        Regression test. The fact index was once seeded by iterating a set, so
        which of several equally valid derivations got printed depended on
        ``PYTHONHASHSEED``. The conclusions were stable; the stated reasons were
        not, which is worse than it sounds for a tool sold on traceability.
        """
        first = render_text(
            assess(self.scenario, context.ontology(), context.program())
        )
        for _ in range(3):
            again = render_text(
                assess(self.scenario, context.ontology(), context.program())
            )
            self.assertEqual(first, again)

    def test_the_trace_names_its_rules_and_sources(self) -> None:
        trace = "\n".join(
            self.result.explain(
                self._fact("unsupportedControlDemand", "ehs:KnowledgeBasedControl")
            )
        )
        self.assertIn("rule:", trace)
        self.assertIn("because:", trace)

    def test_the_band_trace_declares_its_basis_as_convention(self) -> None:
        """The band is a chosen threshold and the trace must say so."""
        trace = "\n".join(self.assessment.band_trace())
        self.assertIn("convention", trace)

    def test_the_report_emits_no_number_that_could_pass_for_a_rate(self) -> None:
        """No decimal appears in the report, so nothing reads as a probability.

        The word "probability" *does* appear, in the standing caveats, where it
        is disclaimed. What must never appear is a number that a reader could
        lift out and quote as a rate.
        """
        import re

        text = render_text(self.assessment)
        decimals = re.findall(r"\d+\.\d+", text)
        self.assertEqual(
            decimals, [], f"report contains decimal figures: {decimals}"
        )
        self.assertNotIn("%", text)

    def test_the_report_disclaims_being_a_probability(self) -> None:
        """The disclaimer is part of the output, not just the documentation."""
        text = render_text(self.assessment).lower()
        self.assertIn("not a probability", text)
        self.assertIn("no human error probability is computed", text)

    def test_the_report_states_the_idheas_provenance(self) -> None:
        """A reader of the output alone must learn the structure is adopted."""
        text = render_text(self.assessment)
        self.assertIn("IDHEAS-G", text)
        self.assertIn("NUREG-2198", text)

    def test_understanding_and_decisionmaking_are_the_challenged_functions(self) -> None:
        """The three stated conditions bear on understanding and decisionmaking;
        procedures also apply to action execution. Detection and interteam
        coordination are untouched, and the report must say so by omission."""
        self.assertEqual(
            self.assessment.challenged_functions,
            ["ehs:ActionExecution", "ehs:Decisionmaking", "ehs:Understanding"],
        )
        self.assertIn(
            ("ehs:Decisionmaking", "ehs:FailureOfDecisionmaking"),
            self.assessment.aggravated_failure_modes,
        )
        self.assertIn(
            ("ehs:Understanding", "ehs:FailureOfUnderstanding"),
            self.assessment.aggravated_failure_modes,
        )
        self.assertNotIn(
            ("ehs:ActionExecution", "ehs:FailureOfActionExecution"),
            self.assessment.aggravated_failure_modes,
        )

    def test_the_report_names_function_and_failure_mode(self) -> None:
        text = render_text(self.assessment)
        self.assertIn("Macrocognitive functions (IDHEAS-G)", text)
        self.assertIn("failure of decisionmaking", text)
        self.assertIn("failureModeAggravated(ehs:Understanding, ehs:FailureOfUnderstanding)", text)

    # -- counterfactuals: the conclusion must depend on the inputs ---------- #

    def test_removing_the_training_deficit_removes_the_unsupported_demand(
        self,
    ) -> None:
        """If training is adequate, the knowledge-based demand is supported."""
        levels = dict(self.scenario.factor_levels)
        levels["ehs:Training"] = "ehs:LevelNominal"
        relaxed = assess(
            Scenario(scenario_id="reactor-training-ok", factor_levels=levels),
            context.ontology(),
            context.program(),
        )
        self.assertFalse(
            relaxed.result.holds(
                "unsupportedControlDemand", "ehs:KnowledgeBasedControl"
            )
        )

    def test_a_fully_nominal_scenario_raises_nothing(self) -> None:
        """The rules must not fire on their own; a clean input yields a clean band."""
        levels = {c: "ehs:LevelNominal" for c in context.ontology().factors}
        clean = assess(
            Scenario(scenario_id="reactor-all-nominal", factor_levels=levels),
            context.ontology(),
            context.program(),
        )
        self.assertEqual(clean.screening_band, "no-flag")
        self.assertEqual(clean.aggravated_error_modes, [])
        self.assertEqual(clean.unmitigated, [])

    def test_claiming_a_control_marks_the_factor_mitigated(self) -> None:
        """Mitigation is recorded from its presence; the engine cannot judge it."""
        mitigated = assess(
            Scenario(
                scenario_id="reactor-with-controls",
                factor_levels=dict(self.scenario.factor_levels),
                mitigations={"ehs:Training": ["CTRL-supervised-restart"]},
            ),
            context.ontology(),
            context.program(),
        )
        self.assertTrue(
            mitigated.result.holds("mitigatedFactor", "ehs:Training")
        )
        self.assertFalse(
            mitigated.result.holds("unmitigatedDegradation", "ehs:Training")
        )

    @staticmethod
    def _fact(predicate: str, *args: str):
        from ehs_hfo.facts import Fact

        return Fact(predicate, tuple(args))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
