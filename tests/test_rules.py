"""Tests on the rule base itself.

The rule base is where domain propositions live, so the checks here are about
discipline rather than logic: every rule declares where it comes from, every
term it mentions exists in the ontology, and the line between "the literature
says this" and "the author picked this threshold" is maintained and visible.
"""

from __future__ import annotations

import unittest

from tests import context

from ehs_hfo.assessment import assess
from ehs_hfo.facts import Scenario
from ehs_hfo.rules import BAND_ORDER, RULES, build_program


class TestRuleBaseIntegrity(unittest.TestCase):
    """Properties every rule must have."""

    def test_rule_ids_are_unique(self) -> None:
        ids = [rule.rule_id for rule in RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_rule_has_a_description(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.rule_id):
                self.assertTrue(
                    rule.description.strip(),
                    f"{rule.rule_id} has no description to print in a trace",
                )

    def test_every_literature_rule_cites_a_source(self) -> None:
        for rule in RULES:
            if rule.basis != "literature":
                continue
            with self.subTest(rule=rule.rule_id):
                self.assertTrue(rule.source_refs)

    def test_basis_is_one_of_the_two_declared_values(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.rule_id):
                self.assertIn(rule.basis, ("literature", "convention"))

    def test_banding_rules_are_all_convention(self) -> None:
        """No source anywhere supports these thresholds, and none is claimed."""
        for rule in RULES:
            if rule.head.predicate != "screeningBand":
                continue
            with self.subTest(rule=rule.rule_id):
                self.assertEqual(
                    rule.basis,
                    "convention",
                    f"{rule.rule_id} claims literature support for a threshold",
                )

    def test_some_rules_are_marked_convention(self) -> None:
        """If nothing were marked convention, the distinction would be decorative."""
        conventions = [r for r in RULES if r.basis == "convention"]
        self.assertGreater(len(conventions), 0)

    def test_ontology_terms_named_by_rules_exist(self) -> None:
        """A rule mentioning a term the ontology dropped would fire on nothing."""
        ont = context.ontology()
        known = (
            set(ont.factors)
            | set(ont.levels)
            | set(ont.error_modes)
            | set(ont.dimensions)
            | {
                m.control_level
                for m in ont.error_modes.values()
                if m.control_level
            }
        )
        for rule in RULES:
            for term in rule.ontology_terms:
                with self.subTest(rule=rule.rule_id, term=term):
                    self.assertIn(term, known)

    def test_program_stratifies(self) -> None:
        """Construction performs stratification; an unstratifiable base raises."""
        program = build_program()
        self.assertGreater(len(program.strata), 0)
        self.assertEqual(
            sum(len(s) for s in program.strata), len(program.rules)
        )


class TestBands(unittest.TestCase):
    """The ordinal screening bands."""

    def test_band_order_is_declared_and_distinct(self) -> None:
        self.assertGreater(len(BAND_ORDER), 1)
        self.assertEqual(len(BAND_ORDER), len(set(BAND_ORDER)))

    def test_every_band_rule_emits_a_declared_band(self) -> None:
        for rule in RULES:
            if rule.head.predicate != "screeningBand":
                continue
            emitted = rule.head.args[0]
            with self.subTest(rule=rule.rule_id):
                self.assertIn(emitted, BAND_ORDER)

    def test_nominal_scenario_gets_no_flag(self) -> None:
        ont = context.ontology()
        levels = {curie: "ehs:LevelNominal" for curie in ont.factors}
        result = assess(
            Scenario(scenario_id="all-nominal", factor_levels=levels),
            ont,
            context.program(),
        )
        self.assertEqual(result.screening_band, "no-flag")

    def test_degrading_a_factor_never_improves_the_band(self) -> None:
        """Monotonicity. Adding bad news must not make the screen look better."""
        ont = context.ontology()
        program = context.program()
        base = {curie: "ehs:LevelNominal" for curie in ont.factors}
        previous = BAND_ORDER.index(
            assess(
                Scenario(scenario_id="mono-0", factor_levels=dict(base)),
                ont,
                program,
            ).screening_band
        )
        for step, curie in enumerate(sorted(ont.factors), start=1):
            base[curie] = "ehs:LevelSeverelyDegraded"
            band = assess(
                Scenario(scenario_id=f"mono-{step}", factor_levels=dict(base)),
                ont,
                program,
            ).screening_band
            current = BAND_ORDER.index(band)
            with self.subTest(degraded=curie):
                self.assertGreaterEqual(
                    current,
                    previous,
                    f"degrading {curie} moved the band from "
                    f"{BAND_ORDER[previous]} to {band}",
                )
            previous = current


class TestUnassessedHandling(unittest.TestCase):
    """An unassessed factor must never be treated as a satisfactory one."""

    def test_omitted_factor_is_carried_as_unknown(self) -> None:
        ont = context.ontology()
        result = assess(
            Scenario(scenario_id="sparse", factor_levels={}), ont, context.program()
        )
        assessed, total = result.coverage
        self.assertEqual(assessed, 0)
        self.assertEqual(total, len(ont.factors))
        self.assertTrue(result.incomplete)

    def test_empty_scenario_raises_no_findings(self) -> None:
        """No data must produce no conclusions, not a clean bill of health."""
        result = assess(
            Scenario(scenario_id="sparse", factor_levels={}),
            context.ontology(),
            context.program(),
        )
        self.assertEqual(result.aggravated_error_modes, [])
        self.assertEqual(result.unmitigated, [])

    def test_incompleteness_is_reported(self) -> None:
        ont = context.ontology()
        levels = {curie: "ehs:LevelNominal" for curie in ont.factors}
        levels.pop(sorted(levels)[0])
        result = assess(
            Scenario(scenario_id="one-missing", factor_levels=levels),
            ont,
            context.program(),
        )
        self.assertTrue(result.incomplete)


class TestScenarioValidation(unittest.TestCase):
    """Unknown identifiers must be refused rather than ignored."""

    def test_unknown_factor_is_refused(self) -> None:
        from ehs_hfo.facts import ScenarioError

        with self.assertRaises(ScenarioError):
            assess(
                Scenario(
                    scenario_id="bad-factor",
                    factor_levels={"ehs:NotAFactor": "ehs:LevelNominal"},
                ),
                context.ontology(),
                context.program(),
            )

    def test_unknown_level_is_refused(self) -> None:
        from ehs_hfo.facts import ScenarioError

        with self.assertRaises(ScenarioError):
            assess(
                Scenario(
                    scenario_id="bad-level",
                    factor_levels={"ehs:Training": "ehs:LevelSplendid"},
                ),
                context.ontology(),
                context.program(),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
