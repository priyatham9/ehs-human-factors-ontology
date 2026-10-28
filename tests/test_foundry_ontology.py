"""Foundry-style ontology layer: spec, materialisation, links, actions, functions, export."""

from __future__ import annotations

import contextlib
import copy
import csv
import io
import json
import os
import sqlite3
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from tests import context

from ehs_hfo.foundry import ActionRejected, SpecError, load_spec
from ehs_hfo.foundry import functions as F
from ehs_hfo.foundry.__main__ import main as foundry_main
from ehs_hfo.foundry.export import export_json, export_sqlite
from ehs_hfo.foundry.materialise import build_store
from ehs_hfo.foundry.report import render_coverage_md
from ehs_hfo.foundry.runtime import ObjectValidationError
from ehs_hfo.foundry.spec import SPEC_PATH, validate

ROOT = Path(context.REPO_ROOT)
PINNED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def rows(rel):
    with open(ROOT / rel, encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


XW = rows("crosswalk/crosswalk.csv")
RULES = rows("crosswalk/pif_rules.csv")
INV = rows("incidents/csb_investigations.csv")
CODING = rows("incidents/csb_coding.csv")


def fresh():
    return build_store(clock=lambda: PINNED)


class Spec(unittest.TestCase):
    def test_bundled_spec_is_valid(self):
        spec = load_spec()
        self.assertEqual(len(spec.object_types), 9)
        self.assertEqual(len(spec.action_types), 4)

    def test_validation_reports_all_errors(self):
        raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        bad = copy.deepcopy(raw)
        bad["link_types"][0]["target"] = "Nope"
        bad["action_types"][0]["edits"][0]["set"]["match_strength"] = "close"
        bad["functions"][0]["reuses"] = "ehs_hfo.foundry.functions.missing"
        self.assertGreaterEqual(len(validate(bad)), 3)
        with self.assertRaises(SpecError):
            load_spec(bad)

    def test_cardinalities_are_declared(self):
        spec = load_spec()
        cards = Counter(lk["cardinality"] for lk in spec.link_types.values())
        self.assertEqual(cards["many_to_many"], 2)
        self.assertGreater(cards["many_to_one"], 0)


class Materialise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = fresh()

    def test_counts_match_committed_files(self):
        s = self.store
        self.assertEqual(len(s.objects("Rule")), len(RULES))
        self.assertEqual(len(s.objects("Investigation")), len(INV))
        self.assertEqual(len(s.objects("EvidenceExcerpt")), len(CODING))
        self.assertEqual(len(s.objects("CrosswalkEntry")),
                         sum(r["match_strength"] != "none" for r in XW))
        self.assertEqual(len(s.objects("AssertedAbsence")),
                         sum(r["match_strength"] == "none" for r in XW))
        self.assertEqual(len(s.objects("Pif")), len(context.ontology().factors))
        self.assertEqual(len(s.objects("CrosswalkEntry")), len(context.ontology().alignments))

    def test_no_dangling_links(self):
        for name, c in self.store.integrity_report().items():
            self.assertEqual(c.get("dangling", 0), 0, name)
            self.assertEqual(c.get("null", 0), 0, name)

    def test_traversal(self):
        pif = self.store.get("Pif", "ehs:Training")
        self.assertEqual(self.store.linked(pif, "dimension").one().primary_key, "ehs:HumanContext")
        n = sum(r["factor_curie"] == "ehs:Training" and r["match_strength"] != "none" for r in XW)
        self.assertEqual(len(self.store.linked(pif, "framework_items")), len(set(
            r["external_curie"] for r in XW
            if r["factor_curie"] == "ehs:Training" and r["match_strength"] != "none")))
        self.assertEqual(len(self.store.linked(pif, "crosswalk_entries")), n)
        props = {r["object"].primary_key: r["link_properties"]["match_strength"]
                 for r in self.store.link_rows(pif, "framework_items")}
        self.assertTrue(set(props.values()) <= {"close", "partial", "broader"})

    def test_investigation_to_pif(self):
        inv = self.store.get("Investigation", "bp-texas-city")
        want = {r["factor_curie"] for r in CODING if r["investigation_id"] == "bp-texas-city"}
        self.assertEqual({p.primary_key for p in self.store.linked(inv, "pifs")}, want)
        self.assertTrue(all(e["quoted_text"] for e in self.store.linked(inv, "excerpts")))

    def test_missing_foreign_key_is_rejected_on_load(self):
        s = fresh()
        s.add_objects("Rule", [{"rule_id": "RX", "factor_curie": "ehs:Nope", "external_curie": "xw:x",
                                "phrase": "p", "rationale": "r", "phrase_seen_in_incident_set": False,
                                "source": "t"}])
        self.assertEqual(s.integrity_report()["rule_pif"]["dangling"], 1)

    def test_duplicate_key_and_null_rejected(self):
        s = fresh()
        with self.assertRaises(ObjectValidationError):
            s.add_objects("Framework", [{"framework_curie": "xw:fw-CREAM", "label": "x", "source": "t"}])
        with self.assertRaises(ObjectValidationError):
            s.add_objects("Framework", [{"framework_curie": "xw:new", "label": None, "source": "t"}])


class Functions(unittest.TestCase):
    def test_framework_coverage_matches_csv(self):
        s = fresh()
        for fw in s.objects("Framework"):
            c = F.framework_coverage(s, fw.primary_key)
            ext = {r["external_curie"] for r in XW
                   if r["framework"] == fw.primary_key and r["match_strength"] != "none"}
            self.assertEqual(c["items_reached"], len(ext), fw.primary_key)
            self.assertEqual(c["entries"], sum(
                r["framework"] == fw.primary_key and r["match_strength"] != "none" for r in XW))
            self.assertEqual(c["pifs_asserted_absent"], sum(
                r["framework"] == fw.primary_key and r["match_strength"] == "none" for r in XW))
        idheas = F.framework_coverage(s, "xw:fw-IDHEAS-G")
        self.assertEqual((idheas["items_reached"], idheas["items_dimension_level"]), (0, 4))

    def test_coverage_of_a_pif_subset_and_strength_floor(self):
        s = fresh()
        sub = F.framework_coverage(s, "xw:fw-CREAM", ["ehs:Training"])
        self.assertEqual(sub["pifs_in_set"], 1)
        close = F.framework_coverage(s, "xw:fw-CREAM", min_strength="close")
        self.assertEqual(close["entries_by_strength"], {"close": close["entries"]})
        self.assertLess(close["entries"], F.framework_coverage(s, "xw:fw-CREAM")["entries"])
        with self.assertRaises(KeyError):
            F.framework_coverage(s, "xw:fw-CREAM", ["ehs:Nope"])
        with self.assertRaises(ValueError):
            F.framework_coverage(s, "xw:fw-CREAM", min_strength="none")

    def test_rules_triggered_by_factor_set(self):
        s = fresh()
        got = F.rules_triggered(s, ["ehs:Training", "ehs:Staffing"])
        want = sorted(r["rule_id"] for r in RULES if r["factor_curie"] in ("ehs:Training", "ehs:Staffing"))
        self.assertEqual([r.primary_key for r in got], want)
        self.assertEqual(F.rules_triggered(s, []), [])

    def test_rules_triggered_by_text_agrees_with_suggester(self):
        from ehs_hfo import suggest
        s = fresh()
        text = "The procedures were not followed and operators had too little training."
        mine = F.rules_triggered_by_text(s, text)
        theirs = suggest.suggest(text, suggest.load_curated())
        self.assertEqual(set(mine), set(theirs))
        self.assertIn("ehs:ProceduresGuidanceAndInstructions", mine)

    def test_pif_evidence(self):
        s = fresh()
        ev = F.pif_evidence(s, "ehs:Training")
        want = [r for r in CODING if r["factor_curie"] == "ehs:Training"]
        self.assertEqual(ev["excerpts"], len(want))
        self.assertEqual(ev["findings"] + ev["recommendations"], len(want))
        self.assertEqual(len(ev["investigations"]), len({r["investigation_id"] for r in want}))

    def test_coverage_table_totals(self):
        t = F.coverage_table(fresh())
        self.assertEqual(sum(f["rules"] for f in t["frameworks"]), len(RULES))
        self.assertEqual(sum(p["excerpts"] for p in t["pifs"]), len(CODING))
        self.assertEqual(sum(f["entries"] for f in t["frameworks"]),
                         sum(r["match_strength"] != "none" for r in XW))


class Actions(unittest.TestCase):
    def test_reject_entry_changes_traversal_coverage_and_logs(self):
        s = fresh()
        key = "ehs:Training|" + next(r["external_curie"] for r in XW if r["factor_curie"] == "ehs:Training"
                                     and r["match_strength"] != "none" and r["framework"] == "xw:fw-CREAM")
        before = F.framework_coverage(s, "xw:fw-CREAM")["entries"]
        n_links = len(s.link_pairs("pif_framework_item"))
        entry = s.apply("reject_crosswalk_entry", {"entry": key, "reason": "wrong_counterpart"}, "tester")
        self.assertEqual(entry.timestamp, PINNED.isoformat())
        self.assertEqual(F.framework_coverage(s, "xw:fw-CREAM")["entries"], before - 1)
        self.assertEqual(len(s.link_pairs("pif_framework_item")), n_links - 1)
        h = s.edit_history("CrosswalkEntry", key)
        self.assertEqual([(e["property"], e["before"], e["after"]) for e in h][0],
                         ("review_status", "active", "rejected"))
        with self.assertRaises(ActionRejected):
            s.apply("reject_crosswalk_entry", {"entry": key, "reason": "wrong_counterpart"}, "tester")
        self.assertEqual(len(s.action_log), 1)

    def test_rejected_action_changes_nothing(self):
        s = fresh()
        with self.assertRaises(ActionRejected) as cm:
            s.apply("flag_crosswalk_entry", {"entry": "nope", "reason": "other"}, " ")
        self.assertGreaterEqual(len(cm.exception.errors), 2)
        self.assertEqual(s.action_log, [])
        key = next(iter(s.objects("CrosswalkEntry").primary_keys()))
        with self.assertRaises(ActionRejected):  # note required when reason is other
            s.apply("flag_crosswalk_entry", {"entry": key, "reason": "other"}, "t")
        s.apply("flag_crosswalk_entry", {"entry": key, "reason": "other", "note": "check"}, "t")
        self.assertEqual(s.get("CrosswalkEntry", key)["review_status"], "under_review")

    def test_reject_excerpt_hides_investigation_link(self):
        s = fresh()
        ex = next(e for e in s.objects("EvidenceExcerpt") if e["factor_curie"] == "ehs:Staffing")
        inv = s.get("Investigation", ex["investigation_id"])
        self.assertIn("ehs:Staffing", [p.primary_key for p in s.linked(inv, "pifs")])
        s.apply("reject_evidence_excerpt", {"excerpt": ex, "reason": "quote_not_in_source"}, "t")
        self.assertNotIn("ehs:Staffing", [p.primary_key for p in s.linked(inv, "pifs")])
        self.assertEqual(F.pif_evidence(s, "ehs:Staffing")["excerpts"], 0)

    def test_retire_rule(self):
        s = fresh()
        s.apply("retire_rule", {"rule": "R01", "reason": "phrase too generic"}, "t")
        self.assertNotIn("R01", [r.primary_key for r in F.rules_triggered(s, ["ehs:ProceduresGuidanceAndInstructions"])])
        with self.assertRaises(ActionRejected):
            s.apply("retire_rule", {"rule": "R01", "reason": "phrase too generic"}, "t")
        with self.assertRaises(ActionRejected):
            s.apply("retire_rule", {"rule": "R02", "reason": "short"}, "t")


class Export(unittest.TestCase):
    def test_sqlite_and_json_roundtrip(self):
        s = fresh()
        s.apply("retire_rule", {"rule": "R01", "reason": "phrase too generic"}, "t")
        with tempfile.TemporaryDirectory() as d:
            db = export_sqlite(s, Path(d) / "o.sqlite")
            js = export_json(s, Path(d) / "o.json")
            con = sqlite3.connect(str(db))
            try:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM Rule").fetchone()[0], len(RULES))
                self.assertEqual(con.execute("SELECT COUNT(*) FROM link_pif_framework_item").fetchone()[0],
                                 sum(r["match_strength"] != "none" for r in XW))
                self.assertEqual(con.execute("SELECT COUNT(*) FROM action_log").fetchone()[0], 1)
                self.assertEqual(con.execute("SELECT status FROM Rule WHERE rule_id='R01'").fetchone()[0], "retired")
                self.assertIsNotNone(con.execute("SELECT spec_json FROM ontology_spec").fetchone())
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute("INSERT INTO Framework (framework_curie, label, source) VALUES ('xw:fw-CREAM','x','y')")
            finally:
                con.close()
            data = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(len(data["objects"]["Pif"]), len(context.ontology().factors))
            self.assertEqual(len(data["action_log"]), 1)

    def test_cli_writes_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "c.md"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(foundry_main(["--out", d, "--coverage-md", str(md)]), 0)
            self.assertTrue((Path(d) / "ontology.sqlite").exists())
            self.assertTrue(md.read_text(encoding="utf-8").startswith("# What the crosswalk covers"))


class CoverageDoc(unittest.TestCase):
    def test_committed_coverage_page_is_current(self):
        committed = (ROOT / "docs" / "ontology-coverage.md").read_text(encoding="utf-8")
        self.assertEqual(committed, render_coverage_md(fresh()),
                         "run: python3 -m ehs_hfo.foundry --coverage-md docs/ontology-coverage.md")

    def test_no_stray_environment_dependence(self):
        self.assertTrue(os.path.exists(SPEC_PATH))


if __name__ == "__main__":
    unittest.main()
