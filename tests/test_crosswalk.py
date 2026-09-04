"""Tests for the crosswalk.

The crosswalk is the part of this repository that carries the argument, so it is
tested harder than anything else. Three properties matter:

1. **Completeness.** Every external factor transcribed from a source framework is
   either crosswalked, recorded as a coverage gap, or marked out of scope with a
   reason. Nothing may be silently dropped, because a crosswalk that quietly
   omits its hard cases overstates the correspondence.
2. **Citation.** Every alignment names a source.
3. **Derivation.** The Markdown and CSV in ``crosswalk/`` are generated from the
   Turtle. If someone edits them by hand, these tests fail.
"""

from __future__ import annotations

import os
import unittest

from tests import context

from tools.build_crosswalk import FRAMEWORK_COLUMNS, build_csv, build_markdown


class TestCompleteness(unittest.TestCase):
    """Nothing transcribed from a source framework may be silently dropped."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.aligned = {a.external_factor for a in cls.ont.alignments.values()}
        cls.gapped = {g.uncovered_factor for g in cls.ont.coverage_gaps.values()}

    def test_every_external_factor_is_accounted_for(self) -> None:
        for curie, external in sorted(self.ont.external_factors.items()):
            with self.subTest(external=curie):
                accounted = (
                    curie in self.aligned
                    or curie in self.gapped
                    or external.out_of_scope_note is not None
                )
                self.assertTrue(
                    accounted,
                    f"{curie} ({external.label}) is neither crosswalked, "
                    f"recorded as a gap, nor marked out of scope",
                )

    def test_every_local_factor_appears_in_the_crosswalk(self) -> None:
        """A factor with no row at all would be an unexplained omission."""
        for curie in sorted(self.ont.factors):
            with self.subTest(factor=curie):
                has_alignment = bool(self.ont.alignments_for(curie))
                has_absence = bool(self.ont.no_counterpart.get(curie))
                self.assertTrue(
                    has_alignment or has_absence,
                    f"{curie} has no alignment and no asserted absence",
                )

    def test_every_factor_is_covered_against_every_framework(self) -> None:
        """For each factor and each framework: a match, or an asserted absence."""
        for factor_curie in sorted(self.ont.factors):
            aligned_frameworks = {
                self.ont.external_factors[a.external_factor].framework
                for a in self.ont.alignments_for(factor_curie)
            }
            absences = set(self.ont.no_counterpart.get(factor_curie, ()))
            for framework_curie, name in FRAMEWORK_COLUMNS:
                with self.subTest(factor=factor_curie, framework=name):
                    self.assertTrue(
                        framework_curie in aligned_frameworks
                        or framework_curie in absences,
                        f"{factor_curie} says nothing about {name}: it needs "
                        f"either an alignment or an ehs:noCounterpartIn assertion",
                    )

    def test_no_factor_both_matches_and_denies_a_framework(self) -> None:
        """An asserted absence must not sit alongside a match in the same framework."""
        for factor_curie in sorted(self.ont.factors):
            aligned = {
                self.ont.external_factors[a.external_factor].framework
                for a in self.ont.alignments_for(factor_curie)
            }
            for framework in self.ont.no_counterpart.get(factor_curie, ()):
                with self.subTest(factor=factor_curie, framework=framework):
                    self.assertNotIn(
                        framework,
                        aligned,
                        f"{factor_curie} claims no counterpart in {framework} "
                        f"while also aligning to one",
                    )


class TestIntegrity(unittest.TestCase):
    """Every alignment must be well-formed and cited."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_alignments_reference_known_terms(self) -> None:
        for curie, alignment in sorted(self.ont.alignments.items()):
            with self.subTest(alignment=curie):
                self.assertIn(alignment.local_factor, self.ont.factors)
                self.assertIn(
                    alignment.external_factor, self.ont.external_factors
                )

    def test_every_alignment_cites_a_source(self) -> None:
        for curie, alignment in sorted(self.ont.alignments.items()):
            with self.subTest(alignment=curie):
                self.assertTrue(
                    alignment.source_refs, f"{curie} carries no ehs:sourceRef"
                )

    def test_match_strength_is_one_of_the_declared_five(self) -> None:
        declared = {
            "ehs:MatchExact",
            "ehs:MatchClose",
            "ehs:MatchBroader",
            "ehs:MatchNarrower",
            "ehs:MatchPartial",
        }
        for curie, alignment in sorted(self.ont.alignments.items()):
            with self.subTest(alignment=curie):
                self.assertIn(alignment.match_strength, declared)

    def test_no_alignment_claims_exact(self) -> None:
        """No correspondence here is asserted identity, and none should be.

        The frameworks were written independently, decades apart, for different
        industries. Groth and Mosleh (2012) report that PIFs across methods are
        not defined specifically enough for consistent interpretation. A row
        marked 'exact' would be claiming more than the sources support.
        """
        exact = [
            curie
            for curie, a in self.ont.alignments.items()
            if a.match_strength == "ehs:MatchExact"
        ]
        self.assertEqual(exact, [])

    def test_external_factors_carry_source_wording(self) -> None:
        """A reader must be able to check a transcription against the source."""
        for curie, external in sorted(self.ont.external_factors.items()):
            if external.out_of_scope_note is not None:
                continue
            with self.subTest(external=curie):
                self.assertTrue(
                    external.verbatim_label,
                    f"{curie} has no ehs:verbatimLabel",
                )

    def test_every_framework_carries_a_bibliographic_citation(self) -> None:
        for curie, framework in sorted(self.ont.frameworks.items()):
            with self.subTest(framework=curie):
                self.assertTrue(framework.citation)
                self.assertTrue(framework.source_refs)

    def test_all_four_named_frameworks_are_present(self) -> None:
        for framework_curie, name in FRAMEWORK_COLUMNS:
            with self.subTest(framework=name):
                self.assertIn(framework_curie, self.ont.frameworks)


class TestCoverageGaps(unittest.TestCase):
    """Gaps are assertions and must be as well-formed as matches."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_gaps_are_recorded(self) -> None:
        """A crosswalk claiming complete coverage of four frameworks is suspect."""
        self.assertGreater(len(self.ont.coverage_gaps), 0)

    def test_gaps_name_a_known_external_factor_and_explain_themselves(
        self,
    ) -> None:
        for curie, gap in sorted(self.ont.coverage_gaps.items()):
            with self.subTest(gap=curie):
                self.assertIn(gap.uncovered_factor, self.ont.external_factors)
                self.assertTrue(gap.comment, f"{curie} has no explanation")

    def test_time_of_day_is_recorded_as_a_gap(self) -> None:
        """CREAM has a circadian CPC; IDHEAS-G has no counterpart, so neither does this."""
        gapped = {g.uncovered_factor for g in self.ont.coverage_gaps.values()}
        self.assertIn("xw:cream-TimeOfDay", gapped)

    def test_a_gapped_factor_is_aligned_at_most_partially(self) -> None:
        """A gap may coexist with a partial match, and with nothing stronger.

        ``ehs:CoverageGap`` covers factors this ontology does not cover *or
        covers only at partial strength*. Partial overlap is not coverage:
        ``xw:cream-TimeOfDay`` clips ``ehs:MentalFatigue`` at the edges and is
        still a gap, because neither represents circadian phase. A gap sitting
        alongside a close, broader or narrower match would be a contradiction.
        """
        gapped = {g.uncovered_factor: c for c, g in self.ont.coverage_gaps.items()}
        for alignment in self.ont.alignments.values():
            if alignment.external_factor not in gapped:
                continue
            with self.subTest(
                gap=gapped[alignment.external_factor], alignment=alignment.curie
            ):
                self.assertEqual(
                    alignment.match_strength,
                    "ehs:MatchPartial",
                    f"{alignment.external_factor} is recorded as a coverage gap "
                    f"but {alignment.curie} aligns to it at "
                    f"{alignment.match_strength}, which asserts coverage",
                )


class TestGeneratedArtefacts(unittest.TestCase):
    """``crosswalk/`` is derived. Hand edits must not survive."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def _assert_matches(self, filename: str, expected: str) -> None:
        path = os.path.join(context.CROSSWALK_DIR, filename)
        self.assertTrue(
            os.path.exists(path),
            f"{filename} is missing; run python3 tools/build_crosswalk.py",
        )
        with open(path, encoding="utf-8") as handle:
            actual = handle.read()
        self.assertEqual(
            actual,
            expected,
            f"{filename} is out of date or was hand-edited; "
            f"run python3 tools/build_crosswalk.py",
        )

    def test_markdown_is_current(self) -> None:
        self._assert_matches("crosswalk.md", build_markdown(self.ont))

    def test_csv_is_current(self) -> None:
        self._assert_matches("crosswalk.csv", build_csv(self.ont))

    def test_csv_row_count_matches_the_ontology(self) -> None:
        import csv
        import io

        rows = list(csv.DictReader(io.StringIO(build_csv(self.ont))))
        absences = sum(len(v) for v in self.ont.no_counterpart.values())
        self.assertEqual(len(rows), len(self.ont.alignments) + absences)

    def test_markdown_states_that_it_is_generated(self) -> None:
        self.assertIn("generated", build_markdown(self.ont).lower())

    def test_markdown_names_idheas_as_the_source_of_the_structure(self) -> None:
        """The adoption claim must survive into the rendered artefact."""
        text = build_markdown(self.ont)
        self.assertIn("IDHEAS-G", text)
        self.assertIn("NUREG-2198", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
