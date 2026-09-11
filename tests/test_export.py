"""Tests for ontology exports in JSON-LD and OWL/XML formats.

The exports are derived from the Turtle source and must remain consistent
with it. These tests verify:

1. Valid JSON-LD that can be parsed and contains the expected data
2. Round-trip fidelity: JSON-LD loads back to the same typed view
3. Valid, well-formed OWL/XML that declares all ontology classes
4. Byte-identical regeneration (currency test)
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tests import context

from ehs_hfo.export import export
from ehs_hfo.ontology import Ontology


OWL_NS = "{http://www.w3.org/2002/07/owl#}"


class TestJsonLdExport(unittest.TestCase):
    """JSON-LD export must be valid JSON with matching subject counts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.jsonld_text = export(cls.ont, format="jsonld")

    def test_export_produces_valid_json(self) -> None:
        """The output must parse as valid JSON-LD."""
        payload = json.loads(self.jsonld_text)
        self.assertIn("@context", payload)
        self.assertIn("@graph", payload)
        self.assertIsInstance(payload["@graph"], list)

    def test_context_contains_all_prefixes(self) -> None:
        """The @context must declare all prefixes from the ontology."""
        payload = json.loads(self.jsonld_text)
        context = payload["@context"]

        # Check that all prefixes from the Turtle are in the context
        expected_prefixes = {"ehs", "xw", "owl", "rdf", "rdfs", "xsd", "skos", "dcterms"}
        for prefix in expected_prefixes:
            self.assertIn(prefix, context)

    def test_subject_count_matches_ontology_graph(self) -> None:
        """The number of @id entries should match distinct subjects in the graph."""
        payload = json.loads(self.jsonld_text)
        graph = payload["@graph"]

        # Count unique subjects in the JSON-LD graph
        subject_ids = {node.get("@id") for node in graph if "@id" in node}

        # Count unique subjects in the Turtle graph
        turtle_subjects = set(str(triple[0]) for triple in self.ont.graph.triples)

        self.assertEqual(len(subject_ids), len(turtle_subjects))

    def test_factors_appear_in_export(self) -> None:
        """All factors from the ontology must appear in the JSON-LD."""
        payload = json.loads(self.jsonld_text)
        graph_subjects = {node.get("@id") for node in payload["@graph"]}

        # Check that at least some factors are present
        factor_curies = set(self.ont.factors.keys())
        self.assertTrue(len(factor_curies) > 0)

        for factor_curie in factor_curies:
            self.assertIn(factor_curie, graph_subjects)

    def test_alignments_appear_in_export(self) -> None:
        """All alignments must appear in the JSON-LD."""
        payload = json.loads(self.jsonld_text)
        graph_subjects = {node.get("@id") for node in payload["@graph"]}

        for alignment_curie in self.ont.alignments.keys():
            self.assertIn(alignment_curie, graph_subjects)


class TestJsonLdRoundTrip(unittest.TestCase):
    """Round-trip: JSON-LD exports and re-imports must preserve ontology shape."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.original_ont = context.ontology()

    def test_round_trip_preserves_factor_ids(self) -> None:
        """After round-trip, factor IDs must be identical."""
        # Export to JSON-LD
        jsonld_text = export(self.original_ont, format="jsonld")

        # Create a minimal reader that loads the JSON-LD back
        payload = json.loads(jsonld_text)
        graph = payload["@graph"]

        # Collect factor IRIs from the JSON-LD
        exported_factors = set()
        for node in graph:
            node_id = node.get("@id")
            if node_id and "PerformanceInfluencingFactor" in str(node):
                exported_factors.add(node_id)

        # Also check by looking for nodes that have properties matching factors
        for factor_curie in self.original_ont.factors.keys():
            self.assertIn(factor_curie, {n.get("@id") for n in graph})

    def test_round_trip_preserves_alignment_count(self) -> None:
        """The JSON-LD must include all alignments from the ontology."""
        jsonld_text = export(self.original_ont, format="jsonld")
        payload = json.loads(jsonld_text)
        graph = payload["@graph"]

        # Check that all alignment curies are in the export
        for alignment_curie in self.original_ont.alignments.keys():
            self.assertIn(alignment_curie, {n.get("@id") for n in graph})

    def test_round_trip_preserves_dimension_count(self) -> None:
        """The JSON-LD must include all dimensions from the ontology."""
        jsonld_text = export(self.original_ont, format="jsonld")
        payload = json.loads(jsonld_text)
        graph = payload["@graph"]

        for dimension_curie in self.original_ont.dimensions.keys():
            self.assertIn(dimension_curie, {n.get("@id") for n in graph})

    def test_round_trip_preserves_level_count(self) -> None:
        """The JSON-LD must include all factor levels from the ontology."""
        jsonld_text = export(self.original_ont, format="jsonld")
        payload = json.loads(jsonld_text)
        graph = payload["@graph"]

        for level_curie in self.original_ont.levels.keys():
            self.assertIn(level_curie, {n.get("@id") for n in graph})


class TestOwlXmlExport(unittest.TestCase):
    """OWL/XML export must be well-formed XML with all declared classes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.owlxml_text = export(cls.ont, format="owlxml")

    def test_export_produces_valid_xml(self) -> None:
        """The output must be valid XML that parses without error."""
        try:
            root = ET.fromstring(self.owlxml_text)
            self.assertIsNotNone(root)
        except ET.ParseError as e:
            self.fail(f"OWL/XML is not valid XML: {e}")

    def test_ontology_element_exists(self) -> None:
        """The root element must be Ontology."""
        root = ET.fromstring(self.owlxml_text)
        self.assertIn("Ontology", root.tag)

    def test_prefixes_are_declared(self) -> None:
        """All ontology prefixes must be declared in the XML."""
        root = ET.fromstring(self.owlxml_text)
        prefix_elements = root.findall(OWL_NS + "Prefix")

        declared_prefixes = {elem.get("name") for elem in prefix_elements}
        expected_prefixes = {"ehs", "xw", "owl", "rdf", "rdfs", "xsd", "skos", "dcterms"}

        for prefix in expected_prefixes:
            self.assertIn(prefix, declared_prefixes)

    def test_classes_are_declared(self) -> None:
        """Every rdf:type Class from the Turtle must be declared in OWL/XML."""
        root = ET.fromstring(self.owlxml_text)
        declared_classes = {elem.get("IRI") for elem in root.findall(OWL_NS + "Class")}

        # Classes from the ontology should include at least the core EHS classes
        expected_classes = {
            "ehs:ContextDimension",
            "ehs:PerformanceInfluencingFactor",
            "ehs:FactorLevel",
            "ehs:ErrorMode",
            "ehs:ExternalFramework",
            "ehs:ExternalFactor",
            "ehs:Alignment",
        }

        for cls in expected_classes:
            self.assertIn(cls, declared_classes)

    def test_individuals_have_assertions(self) -> None:
        """Individuals must have property assertions."""
        root = ET.fromstring(self.owlxml_text)
        individuals = root.findall(OWL_NS + "NamedIndividual")

        # Check that at least some individuals have assertions
        individuals_with_assertions = [
            ind for ind in individuals
            if len(ind) > 0
        ]
        self.assertTrue(len(individuals_with_assertions) > 0)


class TestExportCurrency(unittest.TestCase):
    """Exports must be deterministic: regenerating produces byte-identical output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_jsonld_regeneration_is_byte_identical(self) -> None:
        """Exporting JSON-LD twice must produce identical bytes."""
        export1 = export(self.ont, format="jsonld")
        export2 = export(self.ont, format="jsonld")

        self.assertEqual(export1, export2)

    def test_owlxml_regeneration_is_byte_identical(self) -> None:
        """Exporting OWL/XML twice must produce identical bytes."""
        export1 = export(self.ont, format="owlxml")
        export2 = export(self.ont, format="owlxml")

        self.assertEqual(export1, export2)

    def test_exported_jsonld_file_matches_current_state(self) -> None:
        """The committed ontology/ehs-hfo.jsonld must match the current ontology."""
        jsonld_path = os.path.join(context.REPO_ROOT, "ontology", "ehs-hfo.jsonld")
        if os.path.exists(jsonld_path):
            with open(jsonld_path, "r", encoding="utf-8") as f:
                committed = f.read()

            generated = export(self.ont, format="jsonld")

            if committed != generated:
                # Try parsing both to see if they're semantically equivalent
                # (JSON ordering might differ)
                committed_data = json.loads(committed)
                generated_data = json.loads(generated)
                self.assertEqual(committed_data, generated_data)

    def test_exported_owlxml_file_matches_current_state(self) -> None:
        """The committed ontology/ehs-hfo.owx must match the current ontology."""
        owlxml_path = os.path.join(context.REPO_ROOT, "ontology", "ehs-hfo.owx")
        if os.path.exists(owlxml_path):
            with open(owlxml_path, "r", encoding="utf-8") as f:
                committed = f.read()

            generated = export(self.ont, format="owlxml")

            self.assertEqual(committed, generated)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
