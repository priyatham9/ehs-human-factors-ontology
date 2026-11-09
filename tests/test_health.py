"""Data expectations and lineage: the checks must hold, seeded breakages must be caught, outputs must not drift."""

from __future__ import annotations

import copy
import os
import unittest

from tests import context

from tools import health


class TestHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = health.load()
        cls.checks = health.run_checks(cls.data)
        cls.spec = health.load_spec()

    def test_no_error_severity_failures(self) -> None:
        failed = [c for c in self.checks if c["status"] == "fail"]
        self.assertEqual(failed, [])

    def test_headline_counts_recomputed(self) -> None:
        n = len(self.checks)
        self.assertEqual(n, 71)
        warns = sorted(c["rule"] for c in self.checks if c["status"] == "warn")
        self.assertEqual(len(warns), 2)
        d = self.data
        self.assertEqual(len(d["crosswalk"]), 96)
        self.assertEqual(len(d["coding"]), 67)
        self.assertEqual(sum(1 for r in d["investigations"] if not r["fatalities"]), 9)
        uncoded = set(d["ont"].factors) - {r["factor_curie"] for r in d["coding"]}
        warn = [c for c in self.checks if c["rule"].startswith("factors never coded")][0]
        self.assertEqual(warn["observed"], len(uncoded))

    def test_check_ids_unique_and_sequential(self) -> None:
        ids = [c["id"] for c in self.checks]
        self.assertEqual(ids, ["H%02d" % (i + 1) for i in range(len(ids))])

    def _failing(self, data):
        return {c["rule"] for c in health.run_checks(data) if c["status"] == "fail"}

    def test_seeded_breakages_are_caught(self) -> None:
        d = copy.deepcopy({k: v for k, v in self.data.items() if k != "ont"})
        d["ont"] = self.data["ont"]
        d["coding"][0]["factor_curie"] = "ehs:NotAFactor"
        d["rules"][0]["external_curie"] = "xw:missing"
        d["crosswalk"][0]["match_strength"] = "exact"
        d["investigations"][0]["incident_date"] = "2031-01-01"
        d["pairs"][0]["observed"] = str(int(d["pairs"][0]["observed"]) + 1)
        failing = self._failing(d)
        for rule in ("factor_curie is a factor in the ontology", "external_curie is an external factor",
                     "match_strength is close, partial, broader or none", "no date after " + health.LAST_PLAUSIBLE_DATE,
                     "observed pair counts equal a recount from csb_coding.csv"):
            self.assertIn(rule, failing)

    def test_orphan_coding_row_is_caught(self) -> None:
        d = {k: copy.deepcopy(v) for k, v in self.data.items() if k != "ont"}
        d["ont"] = self.data["ont"]
        d["coding"].append(dict(d["coding"][0], investigation_id="ghost-investigation", quoted_text="x" * 40))
        self.assertIn("every coding row points at an investigation marked coded", self._failing(d))

    def test_lineage_valid_and_breakages_caught(self) -> None:
        self.assertEqual(health.validate_lineage(self.spec), [])
        bad = copy.deepcopy(self.spec)
        bad["stages"][0]["function"] = "no_such_function"
        bad["stages"][1]["outputs"] = bad["stages"][0]["outputs"]
        bad["stages"][2]["inputs"].append("health_doc")
        bad["stages"][-1]["inputs"].append("health_doc")
        text = " | ".join(health.validate_lineage(bad))
        self.assertIn("not defined", text)
        self.assertIn("produced by both", text)
        self.assertIn("cycle", text)

    def test_undeclared_output_is_caught(self) -> None:
        bad = copy.deepcopy(self.spec)
        bad["artifacts"]["crosswalk"]["paths"] = ["crosswalk/crosswalk.csv"]
        self.assertIn("committed file not declared in lineage: crosswalk/crosswalk.md", health.validate_lineage(bad))

    def test_outputs_match_generator(self) -> None:
        outs, _checks, problems = health.outputs()
        self.assertEqual(problems, [])
        for path, text in outs.items():
            with open(path, encoding="utf-8", newline="") as fh:
                self.assertEqual(fh.read(), text, os.path.relpath(path, context.REPO_ROOT) + " is stale; run make health")

    def test_doc_numbers_match_checks(self) -> None:
        with open(health.DOC, encoding="utf-8") as fh:
            doc = fh.read()
        npass = sum(1 for c in self.checks if c["status"] == "pass")
        self.assertIn("%d expectations: %d pass, 2 warn, 0 fail" % (len(self.checks), npass), doc)


if __name__ == "__main__":
    unittest.main()
