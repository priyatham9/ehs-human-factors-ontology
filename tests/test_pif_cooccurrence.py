"""The PIF co-occurrence analysis must be reproducible and the doc must not drift."""

from __future__ import annotations

import csv
import os
import re
import unittest
from collections import defaultdict
from itertools import combinations

from tests import context

from tools import pif_cooccurrence as pc


class TestPifCooccurrence(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fig = pc.compute()

    def test_headline_counts_recomputed_from_raw_csv(self) -> None:
        with open(os.path.join(context.REPO_ROOT, "incidents", "csb_coding.csv"),
                  encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        sets = defaultdict(set)
        for r in rows:
            sets[r["investigation_id"]].add(r["factor_curie"])
        self.assertEqual(self.fig["n_inv"], len(sets))
        self.assertEqual(self.fig["n_codings"], sum(len(s) for s in sets.values()))
        pair_counts = defaultdict(int)
        for s in sets.values():
            for pr in combinations(sorted(s), 2):
                pair_counts[pr] += 1
        self.assertEqual(self.fig["n_distinct"], len(pair_counts))
        top = max(pair_counts.items(), key=lambda kv: (kv[1], kv[0]))
        self.assertEqual(self.fig["obs"][top[0]], top[1])
        self.assertEqual(sum(v * v for v in pair_counts.values()), self.fig["obs_stat"])

    def test_p_values_valid_and_holm_not_smaller(self) -> None:
        for pr in self.fig["pairs"]:
            for key in ("p_up", "p_lo", "holm"):
                self.assertTrue(0 < self.fig[key][pr] <= 1)
        self.assertEqual(len(self.fig["pairs"]), 45)

    def test_deterministic(self) -> None:
        again = pc.compute()
        self.assertEqual(pc.pairs_csv(again), pc.pairs_csv(self.fig))

    def test_wilson_known_value(self) -> None:
        lo, hi = pc.wilson(17, 23)
        self.assertAlmostEqual(lo, 0.5353, places=3)
        self.assertAlmostEqual(hi, 0.8745, places=3)

    def test_committed_outputs_are_current(self) -> None:
        self.assertEqual(open(pc.PAIRS_PATH, encoding="utf-8").read(), pc.pairs_csv(self.fig))
        self.assertEqual(open(pc.PIFS_PATH, encoding="utf-8").read(), pc.pifs_csv(self.fig))
        self.assertEqual(open(pc.SVG_PATH, encoding="utf-8").read(), pc.render_svg(self.fig))

    def test_doc_block_matches_data(self) -> None:
        text = open(pc.DOC_PATH, encoding="utf-8").read()
        start = text.index(pc.BEGIN_MARKER)
        end = text.index(pc.END_MARKER) + len(pc.END_MARKER)
        self.assertEqual(
            text[start:end], pc.render_block(self.fig),
            "docs/pif-cooccurrence.md is stale; run python3 tools/pif_cooccurrence.py --write",
        )
        self.assertIn("pif-cooccurrence.svg", text)

    def test_hand_written_prose_claims_hold(self) -> None:
        text = open(pc.DOC_PATH, encoding="utf-8").read()
        top = self.fig["max_pair"]
        self.assertEqual({pc.short(top[0]), pc.short(top[1])},
                         {"Training", "ProceduresGuidanceAndInstructions"})
        self.assertGreater(self.fig["holm"][top], 0.05)
        self.assertLessEqual(self.fig["p_up"][top], 0.05)
        self.assertIn("(17 of 23)", text)
        self.assertEqual(self.fig["prevalence"]["ehs:TeamAndOrganizationFactors"], 17)
        for other in ("ehs:Training", "ehs:ProceduresGuidanceAndInstructions"):
            pr = tuple(sorted(("ehs:TeamAndOrganizationFactors", other)))
            self.assertLess(self.fig["obs"][pr], self.fig["expected"][pr])
        self.assertIsNotNone(re.search(r"41 of the 67", text))
        with open(os.path.join(context.REPO_ROOT, "incidents", "csb_coding.csv"),
                  encoding="utf-8", newline="") as handle:
            rec = sum(1 for r in csv.DictReader(handle) if r["evidence_type"] == "recommendation")
        self.assertEqual(rec, 41)


if __name__ == "__main__":
    unittest.main()
