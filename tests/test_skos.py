"""SKOS export: regenerate-and-diff, parse-back validity and mapping fidelity.

No network is used. The Turtle is read back with the repository's own parser and
the JSON-LD with a minimal expander written for the flat shape the exporter
emits; the two must yield the same triples as the in-memory model.
"""

from __future__ import annotations

import json
import os
import unittest

from tests import context
from tools import build_skos
from ehs_hfo import turtle

SKOS = "http://www.w3.org/2004/02/skos/core#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _read(name: str) -> str:
    with open(os.path.join(build_skos.SKOS_DIR, name), encoding="utf-8", newline="") as fh:
        return fh.read()


def _model(triples):
    out = set()
    for s, p, o in triples:
        out.add((s, p, o if o[0] == "iri" else ("lit", o[1], o[2])))
    return out


def _from_turtle(text):
    g = turtle.parse(text)
    out = set()
    for s, p, o in g.triples:
        if isinstance(o, turtle.IRI):
            out.add((s.value, p.value, ("iri", o.value)))
        else:
            assert isinstance(o, turtle.Literal) and o.datatype is None
            out.add((s.value, p.value, ("lit", o.value, o.lang or "")))
    return out


def _from_jsonld(text):
    doc = json.loads(text)
    ctx = doc["@context"]

    def exp(term):
        if term == "@type":
            return RDF_TYPE
        if "://" in term:  # absolute IRI
            return term
        prefix, _, local = term.partition(":")
        return ctx[prefix] + local

    out = set()
    for node in doc["@graph"]:
        s = exp(node["@id"])
        for key, values in node.items():
            if key == "@id":
                continue
            for v in values:
                if key == "@type":
                    out.add((s, RDF_TYPE, ("iri", exp(v))))
                elif "@id" in v:
                    out.add((s, exp(key), ("iri", exp(v["@id"]))))
                else:
                    out.add((s, exp(key), ("lit", v["@value"], v.get("@language", ""))))
    return out


class TestSkosExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.triples = build_skos.build_triples(cls.ont)
        cls.model = _model(cls.triples)

    def test_files_are_current(self) -> None:
        for name, expected in build_skos.build_all(self.ont).items():
            self.assertEqual(
                _read(name), expected, f"{name} is stale; run python3 tools/build_skos.py"
            )

    def test_check_flag_passes(self) -> None:
        self.assertEqual(build_skos.main(["--check"]), 0)

    def test_turtle_parses_back_to_the_model(self) -> None:
        self.assertEqual(_from_turtle(_read(build_skos.TTL_NAME)), self.model)

    def test_jsonld_parses_back_to_the_model(self) -> None:
        self.assertEqual(_from_jsonld(_read(build_skos.JSONLD_NAME)), self.model)

    def test_every_concept_is_well_formed(self) -> None:
        subjects = {}
        for s, p, o in self.model:
            subjects.setdefault(s, []).append((p, o))
        concepts = {s for s, po in subjects.items() if (RDF_TYPE, ("iri", SKOS + "Concept")) in po}
        schemes = {
            s for s, po in subjects.items() if (RDF_TYPE, ("iri", SKOS + "ConceptScheme")) in po
        }
        self.assertEqual(len(schemes), 1 + len(self.ont.frameworks))
        for c in concepts:
            po = subjects[c]
            self.assertTrue([o for p, o in po if p == SKOS + "prefLabel"], c)
            ins = [o[1] for p, o in po if p == SKOS + "inScheme"]
            self.assertEqual(len(ins), 1, c)
            self.assertIn(ins[0], schemes)
        # Every SKOS relation must point at a declared concept or scheme.
        for s, p, o in self.model:
            if o[0] == "iri" and p.startswith(SKOS) and p.split("#")[1] not in (
                "ConceptScheme", "Concept",
            ):
                self.assertTrue(o[1] in concepts or o[1] in schemes, (s, p, o))

    def test_counts_match_the_ontology(self) -> None:
        in_hfo = (SKOS + "inScheme", ("iri", build_skos.HFO_SCHEME))
        hfo = {s for s, p, o in self.model if (p, o) == in_hfo}
        self.assertEqual(len(hfo), len(self.ont.dimensions) + len(self.ont.factors))
        self.assertEqual(len(self.ont.factors), 20)
        self.assertEqual(len(self.ont.dimensions), 4)
        mapping = set(build_skos.MATCH_PROPERTY.values())
        pifs = {build_skos._iri(f) for f in self.ont.factors}
        n = sum(1 for s, p, o in self.model if p in mapping and s in pifs)
        self.assertEqual(n, len(self.ont.alignments))

    def test_every_alignment_has_its_mapping_triple(self) -> None:
        for a in self.ont.alignments.values():
            triple = (
                build_skos._iri(a.local_factor),
                build_skos.MATCH_PROPERTY[a.match_strength],
                ("iri", build_skos._iri(a.external_factor)),
            )
            self.assertIn(triple, self.model, a.curie)

    def test_no_exact_match_is_invented(self) -> None:
        exact = sum(
            1 for a in self.ont.alignments.values() if a.match_strength == "ehs:MatchExact"
        )
        got = sum(1 for s, p, o in self.model if p == SKOS + "exactMatch")
        self.assertEqual(got, exact)

    def test_dimensions_are_top_concepts_of_the_pif_scheme(self) -> None:
        tops = {
            o[1]
            for s, p, o in self.model
            if s == build_skos.HFO_SCHEME and p == SKOS + "hasTopConcept"
        }
        self.assertEqual(tops, {build_skos._iri(d) for d in self.ont.dimensions})

    def test_docs_page_counts_match_the_export(self) -> None:
        from collections import Counter

        with open(os.path.join(context.REPO_ROOT, "docs", "skos.md"), encoding="utf-8") as fh:
            page = fh.read()
        counts = Counter(a.match_strength for a in self.ont.alignments.values())
        for strength, prop in (
            ("ehs:MatchClose", "closeMatch"),
            ("ehs:MatchBroader", "broadMatch"),
            ("ehs:MatchPartial", "relatedMatch"),
        ):
            row = [ln for ln in page.splitlines() if f"`skos:{prop}`" in ln and ln.startswith("|")][0]
            self.assertTrue(row.rstrip().endswith(f"| {counts[strength]} |"), row)
        self.assertEqual(counts["ehs:MatchExact"] + counts["ehs:MatchNarrower"], 0)
        self.assertIn(f"{len(self.ont.alignments)} alignments", page)

    def test_does_not_claim_endorsement(self) -> None:
        self.assertIn("Not endorsed by any standards body", _read(build_skos.TTL_NAME))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
