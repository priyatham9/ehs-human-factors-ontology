"""Tests on the synthetic corpus and the guardrails around it.

Two jobs. First, use the corpus for what it is for: exercising the engine over
structurally varied input. Second, and more importantly, enforce the labelling.
Synthetic data that loses its label is the mechanism by which a made-up number
ends up in a paper, so the label is tested as hard as the behaviour.
"""

from __future__ import annotations

import json
import os
import unittest
from typing import Dict, List

from tests import context

from ehs_hfo.assessment import assess, render_text
from ehs_hfo.facts import Scenario
from ehs_hfo.rules import BAND_ORDER

from synthetic.generate_scenarios import (
    DEFAULT_COUNT,
    DEFAULT_SEED,
    SYNTHETIC_HEADER,
    generate_corpus,
)


def _scenario_paths() -> List[str]:
    """Every JSON file in the committed corpus."""
    return sorted(
        os.path.join(context.SYNTHETIC_SCENARIO_DIR, name)
        for name in os.listdir(context.SYNTHETIC_SCENARIO_DIR)
        if name.endswith(".json")
    )


class TestCorpusPresence(unittest.TestCase):
    """The corpus exists and is where the documentation says it is."""

    def test_corpus_directory_exists(self) -> None:
        self.assertTrue(os.path.isdir(context.SYNTHETIC_SCENARIO_DIR))

    def test_corpus_is_not_empty(self) -> None:
        self.assertGreater(len(_scenario_paths()), 0)

    def test_corpus_has_a_generator(self) -> None:
        self.assertTrue(
            os.path.exists(
                os.path.join(context.SYNTHETIC_DIR, "generate_scenarios.py")
            )
        )

    def test_corpus_has_a_readme(self) -> None:
        self.assertTrue(
            os.path.exists(os.path.join(context.SYNTHETIC_DIR, "README.md"))
        )


class TestLabelling(unittest.TestCase):
    """Every file must announce that it is fabricated. No exceptions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.payloads: Dict[str, dict] = {}
        for path in _scenario_paths():
            with open(path, encoding="utf-8") as handle:
                cls.payloads[os.path.basename(path)] = json.load(handle)

    def test_every_file_is_flagged_synthetic(self) -> None:
        for name, payload in sorted(self.payloads.items()):
            with self.subTest(file=name):
                self.assertIs(payload.get("synthetic"), True)

    def test_every_file_carries_the_provenance_header_verbatim(self) -> None:
        for name, payload in sorted(self.payloads.items()):
            with self.subTest(file=name):
                self.assertEqual(payload.get("provenance"), SYNTHETIC_HEADER)

    def test_the_header_says_what_matters(self) -> None:
        lowered = SYNTHETIC_HEADER.lower()
        self.assertIn("synthetic", lowered)
        self.assertIn("not an observation", lowered)
        self.assertIn("no establishment", lowered)
        self.assertIn("is an empirical finding", lowered)  # "...no number ... is an empirical finding"

    def test_every_file_names_its_generator(self) -> None:
        for name, payload in sorted(self.payloads.items()):
            with self.subTest(file=name):
                generator = payload.get("generator")
                self.assertIsInstance(generator, dict)
                self.assertEqual(
                    generator.get("script"), "synthetic/generate_scenarios.py"
                )

    def test_the_label_survives_loading(self) -> None:
        for path in _scenario_paths():
            with self.subTest(file=os.path.basename(path)):
                self.assertTrue(Scenario.from_json_file(path).synthetic)

    def test_the_label_reaches_the_rendered_report(self) -> None:
        """A reader of the output alone must be told the input was fabricated."""
        scenario = Scenario.from_json_file(_scenario_paths()[0])
        text = render_text(
            assess(scenario, context.ontology(), context.program())
        ).upper()
        self.assertIn("SYNTHETIC", text)

    def test_the_example_scenario_is_not_in_this_directory(self) -> None:
        """The hand-written illustration must not be filed as generated data."""
        names = {os.path.basename(p) for p in _scenario_paths()}
        self.assertNotIn("reactor_startup_nonroutine.json", names)


class TestReproducibility(unittest.TestCase):
    """The committed corpus must be regenerable, so it can be checked."""

    def test_generation_is_deterministic(self) -> None:
        first = generate_corpus(count=8, seed=1234, ontology=context.ontology())
        second = generate_corpus(count=8, seed=1234, ontology=context.ontology())
        self.assertEqual(first, second)

    def test_different_seeds_give_different_corpora(self) -> None:
        a = generate_corpus(count=8, seed=1, ontology=context.ontology())
        b = generate_corpus(count=8, seed=2, ontology=context.ontology())
        self.assertNotEqual(a, b)

    def test_committed_corpus_matches_the_generator(self) -> None:
        """Hand-edited scenarios must not survive."""
        expected = generate_corpus(
            count=DEFAULT_COUNT, seed=DEFAULT_SEED, ontology=context.ontology()
        )
        expected_by_id = {s["scenario_id"]: s for s in expected}
        actual_by_id = {}
        for path in _scenario_paths():
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            actual_by_id[payload["scenario_id"]] = payload

        self.assertEqual(
            set(expected_by_id),
            set(actual_by_id),
            "corpus on disk does not match the generator; "
            "run python3 synthetic/generate_scenarios.py",
        )
        for scenario_id, payload in sorted(expected_by_id.items()):
            with self.subTest(scenario=scenario_id):
                self.assertEqual(actual_by_id[scenario_id], payload)

    def test_generator_only_emits_levels_the_ontology_declares(self) -> None:
        """The weight table is keyed by rank; this proves the resolution works."""
        ont = context.ontology()
        for scenario in generate_corpus(count=24, seed=99, ontology=ont):
            for factor, level in scenario["factor_levels"].items():
                with self.subTest(scenario=scenario["scenario_id"]):
                    self.assertIn(factor, ont.factors)
                    self.assertIn(level, ont.levels)

    def test_generator_never_emits_the_unknown_level(self) -> None:
        """Absence is expressed by omitting a factor, not by naming 'unknown'."""
        for scenario in generate_corpus(
            count=24, seed=99, ontology=context.ontology()
        ):
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertNotIn(
                    "ehs:LevelUnknown", scenario["factor_levels"].values()
                )


class TestEngineExercise(unittest.TestCase):
    """What the corpus is actually for."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.program = context.program()
        cls.assessments = [
            assess(Scenario.from_json_file(p), cls.ont, cls.program)
            for p in _scenario_paths()
        ]

    def test_every_scenario_evaluates(self) -> None:
        self.assertEqual(len(self.assessments), len(_scenario_paths()))

    def test_every_scenario_yields_a_declared_band(self) -> None:
        for assessment in self.assessments:
            with self.subTest(scenario=assessment.scenario.scenario_id):
                self.assertIn(assessment.screening_band, BAND_ORDER)

    def test_every_derived_fact_has_a_justification(self) -> None:
        for assessment in self.assessments:
            result = assessment.result
            with self.subTest(scenario=assessment.scenario.scenario_id):
                for fact in result.derived_facts():
                    self.assertTrue(result.justifications[fact].derivations)

    def test_every_report_renders(self) -> None:
        for assessment in self.assessments:
            with self.subTest(scenario=assessment.scenario.scenario_id):
                self.assertTrue(render_text(assessment).strip())

    def test_the_corpus_exercises_more_than_one_band(self) -> None:
        """A corpus that always lands in one band tests nothing about banding."""
        bands = {a.screening_band for a in self.assessments}
        self.assertGreater(len(bands), 1, f"corpus only produced {bands}")

    def test_the_corpus_exercises_the_unassessed_path(self) -> None:
        incomplete = [a for a in self.assessments if a.incomplete]
        self.assertGreater(len(incomplete), 0)

    def test_the_corpus_exercises_mitigations(self) -> None:
        mitigated = [
            a for a in self.assessments if a.scenario.mitigations
        ]
        self.assertGreater(len(mitigated), 0)

    def test_most_rules_are_reachable_from_the_corpus(self) -> None:
        """A rule no input can reach is either dead or untested; say which."""
        fired = set()
        for assessment in self.assessments:
            fired.update(rule_id for rule_id, _ in assessment.result.firing_order)
        all_ids = {rule.rule_id for rule in self.program.rules}
        unreached = sorted(all_ids - fired)
        self.assertLessEqual(
            len(unreached),
            2,
            f"rules never reached by the synthetic corpus: {unreached}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
