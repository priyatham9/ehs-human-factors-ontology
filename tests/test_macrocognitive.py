"""IDHEAS-G macrocognitive functions, cognitive failure modes, and the
function-specific rules that replaced the category-level roll-up."""

import unittest

from tests import context
from ehs_hfo.assessment import assess
from ehs_hfo.facts import Scenario
from ehs_hfo.rules import RULES

FUNCTIONS = {
    "ehs:Detection",
    "ehs:Understanding",
    "ehs:Decisionmaking",
    "ehs:ActionExecution",
    "ehs:InterteamCoordination",
}


class TestFunctionsInOntology(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_five_functions_are_present(self) -> None:
        self.assertEqual(set(self.ont.functions), FUNCTIONS)

    def test_each_function_has_exactly_one_failure_mode(self) -> None:
        by_function = {}
        for cfm in self.ont.failure_modes.values():
            by_function.setdefault(cfm.function, []).append(cfm.curie)
        self.assertEqual(set(by_function), FUNCTIONS)
        for fn, modes in by_function.items():
            with self.subTest(function=fn):
                self.assertEqual(len(modes), 1)

    def test_every_factor_applies_to_at_least_one_function(self) -> None:
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertTrue(factor.applies_to_functions)
                self.assertTrue(factor.affects_failure_modes)

    def test_no_factor_applies_to_every_function(self) -> None:
        """If a PIF applied to all five, applicability would be global again."""
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertLess(len(factor.applies_to_functions), len(FUNCTIONS))

    def test_affected_failure_modes_belong_to_applicable_functions(self) -> None:
        for curie, factor in self.ont.factors.items():
            for cfm in factor.affects_failure_modes:
                with self.subTest(factor=curie, failure_mode=cfm):
                    self.assertIn(
                        self.ont.failure_modes[cfm].function,
                        factor.applies_to_functions,
                    )

    def test_function_assignment_is_marked_as_interpretive(self) -> None:
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertTrue(
                    any("author" in note for note in factor.boundary_notes),
                    f"{curie} does not say its function assignment is interpretive",
                )

    def test_every_srk_error_mode_maps_to_a_failure_mode(self) -> None:
        for curie, mode in self.ont.error_modes.items():
            with self.subTest(mode=curie):
                self.assertTrue(mode.approximates)
                for cfm in mode.approximates:
                    self.assertIn(cfm, self.ont.failure_modes)


class TestFunctionSpecificRules(unittest.TestCase):
    def test_no_rule_rolls_up_by_context_dimension(self) -> None:
        """The reviewer's objection: aggregation across a category has no basis."""
        gone = {"degradedInDimension", "dimensionDegraded", "multiDimensionDegradation"}
        for rule in RULES:
            with self.subTest(rule=rule.rule_id):
                self.assertNotIn(rule.head.predicate, gone)
                for pattern in rule.body:
                    self.assertNotIn(pattern.predicate, gone)

    def test_band_rules_do_not_read_factorInDimension(self) -> None:
        for rule in RULES:
            if rule.head.predicate != "screeningBand":
                continue
            with self.subTest(rule=rule.rule_id):
                for pattern in rule.body:
                    self.assertNotEqual(pattern.predicate, "factorInDimension")

    def test_a_single_degraded_factor_challenges_only_its_functions(self) -> None:
        ont = context.ontology()
        levels = {c: "ehs:LevelNominal" for c in ont.factors}
        levels["ehs:WorkplaceVisibility"] = "ehs:LevelDegraded"
        a = assess(
            Scenario(scenario_id="one", description="", factor_levels=levels),
            ontology=ont,
        )
        self.assertEqual(a.challenged_functions, ["ehs:Detection"])
        self.assertEqual(
            a.elevated_failure_modes,
            [("ehs:Detection", "ehs:FailureOfDetection", "ehs:WorkplaceVisibility")],
        )
        self.assertEqual(a.aggravated_failure_modes, [])

    def test_two_factors_on_one_function_aggravate_it(self) -> None:
        ont = context.ontology()
        levels = {c: "ehs:LevelNominal" for c in ont.factors}
        levels["ehs:WorkplaceVisibility"] = "ehs:LevelDegraded"
        levels["ehs:MentalFatigue"] = "ehs:LevelDegraded"
        a = assess(
            Scenario(scenario_id="two", description="", factor_levels=levels),
            ontology=ont,
        )
        self.assertIn(("ehs:Detection", "ehs:FailureOfDetection"), a.aggravated_failure_modes)
        trace = "\n".join(
            a.explain("failureModeAggravated", "ehs:Detection", "ehs:FailureOfDetection")
        )
        self.assertIn("ehs:Detection", trace)
        self.assertIn("ehs:FailureOfDetection", trace)
        self.assertIn("nureg2198", trace)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
