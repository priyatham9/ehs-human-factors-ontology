"""Loss, provenance and a precisely scoped reconstruction contract.

The key counterexample: deleting an explicit absence changes source meaning
but leaves the standard SKOS export byte-identical. A decoder cannot recover
that distinction from SKOS alone. The independent sidecar retains it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests import context
from ehs_hfo.ontology import Ontology
from ehs_hfo.turtle import IRI, Literal, parse
from tools import build_skos
from tools import build_translation_audit as audit


class TranslationAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(context.ONTOLOGY_PATH).read_bytes()
        cls.ont = context.ontology()
        cls.files = audit.build_all(cls.source)
        cls.sidecar = audit.build_sidecar(cls.ont, cls.source)
        cls.report = json.loads(cls.files[audit.REPORT_NAME])

    def test_generated_files_current_and_byte_deterministic(self):
        self.assertEqual(self.files, audit.build_all(self.source))
        for name, text in self.files.items():
            self.assertEqual((audit.OUT / name).read_text(), text, name)
        self.assertEqual(audit.main(["--check"]), 0)

    def test_standard_skos_bytes_unchanged_and_hashes_match(self):
        for name, text in build_skos.build_all(self.ont).items():
            self.assertEqual((audit.OUT / name).read_text(), text)
            self.assertEqual(self.report["standardSkosSha256"][name], hashlib.sha256(text.encode()).hexdigest())

    def test_both_serializations_preserve_every_sidecar_triple(self):
        self.assertEqual(set(parse(self.files[audit.TTL_NAME]).triples), self.sidecar)
        self.assertEqual(audit.from_jsonld(self.files[audit.JSONLD_NAME]), self.sidecar)

    def test_skos_plus_sidecar_reconstructs_exact_contract_in_both_formats(self):
        original = audit.contract_projection(self.ont.graph.triples)
        skos = set(parse((audit.OUT / build_skos.TTL_NAME).read_text()).triples)
        self.assertNotEqual(audit.contract_projection(skos), original)
        for recovered in [set(parse(self.files[audit.TTL_NAME]).triples), audit.from_jsonld(self.files[audit.JSONLD_NAME])]:
            self.assertEqual(audit.contract_projection(skos | recovered), original)
        self.assertEqual(self.report["roundTrip"], {"contractTriples": 600, "recoveredTriples": 600, "missing": 0, "added": 0, "equal": True})

    def test_noninjectivity_absence_and_unknown_have_identical_skos(self):
        line = "ehs:WorkplaceVisibility ehs:noCounterpartIn xw:fw-SPARH ."
        original = self.source.decode()
        self.assertIn(line, original)
        altered = original.replace(line, "", 1).encode()
        other = Ontology(parse(altered.decode()))
        self.assertEqual(audit.cell_status(self.ont, "ehs:WorkplaceVisibility", "xw:fw-SPARH"), "asserted-no-counterpart")
        self.assertEqual(audit.cell_status(other, "ehs:WorkplaceVisibility", "xw:fw-SPARH"), "unasserted")
        self.assertEqual(build_skos.build_all(other), build_skos.build_all(self.ont))
        other_sidecar = audit.build_sidecar(other, altered)
        original_contract = audit.contract_projection(self.sidecar)
        other_contract = audit.contract_projection(other_sidecar)
        self.assertEqual(len(original_contract - other_contract), 1)
        self.assertEqual(len(other_contract - original_contract), 0)
        self.assertEqual(other_contract, audit.contract_projection(other.graph.triples))

    def test_alignment_rationale_can_change_without_any_skos_change(self):
        text = self.source.decode()
        old = "Weak. HFACS has no task-complexity category; the nearest is a supervisory failure to match task to crew."
        self.assertIn(old, text)
        altered = text.replace(old, "TEST FIXTURE: a different author rationale", 1).encode()
        other = Ontology(parse(altered.decode()))
        self.assertEqual(build_skos.build_all(other), build_skos.build_all(self.ont))
        self.assertNotEqual(audit.contract_projection(self.ont.graph.triples), audit.contract_projection(other.graph.triples))
        self.assertEqual(audit.contract_projection(audit.build_sidecar(other, altered)), audit.contract_projection(other.graph.triples))

    def test_gap_is_not_the_same_as_unmapped(self):
        gap = next(g for g in self.report["coverageGaps"] if g["externalFactor"] == "xw:cream-TimeOfDay")
        self.assertEqual(gap["coexistingAlignments"], ["xw:al-Fatigue-cream"])
        self.assertTrue(gap["skosConceptPresent"])
        row = next(a for a in self.report["alignments"] if a["id"] == "xw:al-Fatigue-cream")
        self.assertEqual(row["strength"], "ehs:MatchPartial")
        self.assertEqual(row["skosPredicate"], build_skos.SKOS + "relatedMatch")
        self.assertNotIn(IRI(audit.iri(gap["id"])), {s for s, _, _ in parse((audit.OUT / build_skos.TTL_NAME).read_text()).triples})

    def test_absence_provenance_is_source_snapshot_not_invented_evidence(self):
        snapshot = IRI("urn:sha256:" + hashlib.sha256(self.source).hexdigest())
        statements = {s for s, p, o in self.sidecar if p == audit.TYPE and o == IRI(audit.RDF + "Statement")}
        self.assertEqual(len(statements), 6)
        for s in statements:
            self.assertIn((s, IRI(audit.PROV + "wasDerivedFrom"), snapshot), self.sidecar)
            self.assertFalse(any(subject == s and p == IRI(audit.EHS + "sourceRef") for subject, p, _ in self.sidecar))
            self.assertIn((s, IRI(audit.RDF + "predicate"), audit.ABSENCE), self.sidecar)
        self.assertEqual(self.report["source"]["sha256"], hashlib.sha256(self.source).hexdigest())

    def test_missing_mapping_never_creates_an_absence(self):
        for f in self.ont.factors:
            self.assertEqual(audit.cell_status(self.ont, f, "xw:fw-IDHEAS-G"), "unasserted")
        with self.assertRaises(ValueError):
            audit.cell_status(self.ont, "ehs:Typo", "xw:fw-SPARH")

    def test_conflicting_assertions_are_reported_without_overwriting_either(self):
        modified = self.source + b"\nehs:Training ehs:noCounterpartIn xw:fw-SPARH .\n"
        other = Ontology(parse(modified.decode()))
        self.assertEqual(audit.cell_status(other, "ehs:Training", "xw:fw-SPARH"), "conflicting-assertions")
        self.assertEqual(audit.contract_projection(audit.build_sidecar(other, modified)), audit.contract_projection(other.graph.triples))

    def test_no_skos_negative_match_or_new_positive_mapping_is_invented(self):
        self.assertFalse(any(p.value.startswith(build_skos.SKOS) for _, p, _ in self.sidecar))
        source_absences = {t for t in self.ont.graph.triples if t[1] == audit.ABSENCE}
        self.assertEqual({t for t in self.sidecar if t[1] == audit.ABSENCE}, source_absences)

    def test_literals_preserve_language_datatype_and_escaping(self):
        sample = {(IRI("urn:test:s"), IRI("urn:test:p"), Literal('A "quote"\n\\slash', lang="en")),
                  (IRI("urn:test:s"), IRI("urn:test:q"), Literal("12", datatype="http://www.w3.org/2001/XMLSchema#integer"))}
        self.assertEqual(set(parse(audit.to_turtle(sample)).triples), sample)
        self.assertEqual(audit.from_jsonld(audit.to_jsonld(sample)), sample)

    def test_ledger_uses_distinct_units_and_keeps_dimension_mappings_separate(self):
        counts = self.report["counts"]
        self.assertEqual(counts["byStrength"], {"broader": 23, "close": 34, "partial": 33})
        self.assertEqual(counts["pifAlignments"], 90)
        self.assertEqual(counts["dimensionMappingsSeparate"], 4)
        self.assertEqual(counts["mappingCollisions"], 0)
        self.assertEqual(counts["sourceCellStatus"], {"asserted-no-counterpart": 6, "mapped": 74})
        self.assertEqual(counts["skosCellStatus"], {"mapped": 74, "unasserted": 6})


if __name__ == "__main__":
    unittest.main()
