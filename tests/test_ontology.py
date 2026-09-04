"""Structural tests on the ontology.

These check the properties the rule engine and the crosswalk depend on. They do
not check OWL consistency: nothing in this repository computes entailments, and
no claim is made that the file is consistent under OWL 2 Direct Semantics.
"""

from __future__ import annotations

import unittest

from tests import context

from ehs_hfo.ontology import Ontology, OntologyError


class TestStructure(unittest.TestCase):
    """The shape the rest of the code assumes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_exactly_four_dimensions(self) -> None:
        """Four context dimensions, no more. The whole claim rests on this."""
        self.assertEqual(len(self.ont.dimensions), 4)

    def test_every_dimension_binds_an_idheas_category(self) -> None:
        """The binding to IDHEAS-G is what stops this reading as a new taxonomy."""
        for curie, dimension in self.ont.dimensions.items():
            with self.subTest(dimension=curie):
                self.assertIsNotNone(
                    dimension.idheas_category,
                    f"{curie} does not name the IDHEAS-G category it renames",
                )
                self.assertIn(
                    dimension.idheas_category, self.ont.external_factors
                )

    def test_idheas_bindings_are_a_bijection(self) -> None:
        """Four dimensions onto four distinct categories: a 1:1 correspondence."""
        bound = [d.idheas_category for d in self.ont.dimensions.values()]
        self.assertEqual(len(set(bound)), 4)

    def test_twenty_factors(self) -> None:
        """IDHEAS-G's twenty PIFs, adopted without addition or deletion."""
        self.assertEqual(len(self.ont.factors), 20)

    def test_every_factor_sits_in_a_declared_dimension(self) -> None:
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertIn(factor.dimension, self.ont.dimensions)

    def test_every_factor_cites_a_source(self) -> None:
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertTrue(
                    factor.source_refs, f"{curie} carries no ehs:sourceRef"
                )

    def test_every_factor_carries_the_source_wording(self) -> None:
        """verbatimLabel is how a reader checks the adoption claim against NUREG-2198."""
        for curie, factor in self.ont.factors.items():
            with self.subTest(factor=curie):
                self.assertTrue(
                    factor.verbatim_label,
                    f"{curie} has no ehs:verbatimLabel to check against the source",
                )

    def test_dimension_factor_counts_partition_the_twenty(self) -> None:
        total = sum(
            len(self.ont.factors_in(curie)) for curie in self.ont.dimensions
        )
        self.assertEqual(total, 20)


class TestLevels(unittest.TestCase):
    """The ordinal level scheme the engine reasons over."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_five_levels(self) -> None:
        self.assertEqual(len(self.ont.levels), 5)

    def test_ranks_are_unique(self) -> None:
        """The generator resolves weights by rank, so ranks must not collide."""
        ranks = [level.rank for level in self.ont.levels.values()]
        self.assertEqual(len(ranks), len(set(ranks)))

    def test_unknown_is_not_degraded_and_not_assessed(self) -> None:
        """'Not assessed' must never be silently equivalent to 'nominal'."""
        unknown = self.ont.level("ehs:LevelUnknown")
        self.assertFalse(unknown.is_assessed)
        self.assertFalse(unknown.is_degraded)

    def test_nominal_is_assessed_and_not_degraded(self) -> None:
        nominal = self.ont.level("ehs:LevelNominal")
        self.assertTrue(nominal.is_assessed)
        self.assertFalse(nominal.is_degraded)

    def test_degraded_levels_are_the_two_below_nominal(self) -> None:
        degraded = {c for c, lv in self.ont.levels.items() if lv.is_degraded}
        self.assertEqual(
            degraded, {"ehs:LevelDegraded", "ehs:LevelSeverelyDegraded"}
        )


class TestErrorModes(unittest.TestCase):
    """Rasmussen's control levels and Reason's error modes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_error_modes_declared(self) -> None:
        self.assertGreaterEqual(len(self.ont.error_modes), 3)

    def test_knowledge_based_mistake_exists_and_is_bound_to_a_control_level(
        self,
    ) -> None:
        mode = self.ont.error_modes["ehs:KnowledgeBasedMistake"]
        self.assertEqual(mode.control_level, "ehs:KnowledgeBasedControl")

    def test_every_error_mode_names_a_control_level(self) -> None:
        for curie, mode in self.ont.error_modes.items():
            with self.subTest(mode=curie):
                self.assertIsNotNone(mode.control_level)


class TestValidation(unittest.TestCase):
    """The loader must reject structurally broken files rather than limp on."""

    def _load(self, text: str) -> Ontology:
        from ehs_hfo.turtle import parse

        return Ontology(parse(text))

    def test_rejects_factor_in_undeclared_dimension(self) -> None:
        text = """
        @prefix ehs: <https://example.org/ehs#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ehs:F a owl:NamedIndividual , ehs:PerformanceInfluencingFactor ;
            rdfs:label "F"@en ;
            ehs:inContextDimension ehs:NoSuchDimension ;
            ehs:sourceRef "x" .
        """
        with self.assertRaises(OntologyError):
            self._load(text)

    def test_rejects_individual_without_a_label(self) -> None:
        text = """
        @prefix ehs: <https://example.org/ehs#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        ehs:D a owl:NamedIndividual , ehs:ContextDimension .
        """
        with self.assertRaises(OntologyError):
            self._load(text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
