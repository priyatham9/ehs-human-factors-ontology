"""The blinded second-coder tool must hide the first coder's codes and compute agreement correctly.

Test sheets here are built in code to exercise the arithmetic. They are not
second-coder data and are never written to the repository.
"""

from __future__ import annotations

import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from tests import context

from tools import build_csb_coding as b
from tools import second_coder as sc


class TestBlinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.text = sc.sheet_csv()
        cls.rows = list(csv.DictReader(io.StringIO(cls.text)))

    def test_every_quote_is_one_excerpt(self) -> None:
        quotes = {(r["investigation_id"], r["quoted_text"]) for r in b.read(b.CODING)}
        self.assertEqual(len(self.rows), len(quotes))
        self.assertEqual(len({r["excerpt_id"] for r in self.rows}), len(self.rows))

    def test_sheet_has_no_codes_or_codebook_fields(self) -> None:
        self.assertEqual(list(self.rows[0]), sc.SHEET_FIELDS)
        for r in self.rows:
            self.assertEqual(r["pifs"], "")
        self.assertNotIn("ehs:", self.text)
        for forbidden in ("evidence_type", "factor_curie", "cohort", "coded"):
            self.assertNotIn(forbidden, self.rows[0])

    def test_sheet_excerpts_match_quotes(self) -> None:
        quotes = {r["quoted_text"] for r in b.read(b.CODING)}
        self.assertEqual({r["excerpt"] for r in self.rows}, quotes)

    def test_order_is_not_investigation_order(self) -> None:
        names = [r["investigation"] for r in self.rows]
        runs = sum(1 for i in range(1, len(names)) if names[i] != names[i - 1])
        self.assertGreater(runs, len({*names}))

    def test_export_is_deterministic(self) -> None:
        self.assertEqual(self.text, sc.sheet_csv())

    def test_codebook_lists_every_factor(self) -> None:
        rows = list(csv.DictReader(io.StringIO(sc.codebook_csv(self.ont))))
        self.assertEqual({r["factor_curie"] for r in rows}, set(self.ont.factors))


class TestKappa(unittest.TestCase):
    def test_known_values(self) -> None:
        # Cohen (1960)-style hand calculation: po = 0.8, pe = 0.5*0.5 + 0.5*0.5 = 0.5.
        self.assertAlmostEqual(sc.cohen_kappa(40, 10, 10, 40), 0.6)
        self.assertAlmostEqual(sc.cohen_kappa(5, 0, 0, 5), 1.0)
        self.assertAlmostEqual(sc.cohen_kappa(0, 5, 5, 0), -1.0)

    def test_undefined_when_one_category(self) -> None:
        self.assertIsNone(sc.cohen_kappa(0, 0, 0, 10))
        self.assertIsNone(sc.cohen_kappa(0, 0, 0, 0))


class TestAgreement(unittest.TestCase):
    def test_per_pif_table(self) -> None:
        first = {"e1": {"A", "B"}, "e2": {"A"}, "e3": {"B"}, "e4": {"A"}}
        second = {"e1": {"A"}, "e2": {"A", "B"}, "e3": set()}  # e4 not rated
        rows = {r["factor"]: r for r in sc.agreement(first, second, ["A", "B", "C"])}
        self.assertEqual(set(rows), {"A", "B"})  # C unused by either coder
        a = rows["A"]
        self.assertEqual((a["both"], a["only_coder1"], a["only_coder2"], a["neither"]), (2, 0, 0, 1))
        self.assertEqual(a["n"], 3)
        self.assertAlmostEqual(a["percent_agreement"], 100.0)
        self.assertAlmostEqual(a["kappa"], 1.0)  # po 1, pe 5/9
        b_ = rows["B"]
        self.assertEqual(
            (b_["both"], b_["only_coder1"], b_["only_coder2"], b_["neither"]), (0, 2, 1, 0)
        )
        self.assertAlmostEqual(b_["percent_agreement"], 0.0)
        self.assertAlmostEqual(b_["kappa"], -0.8)  # po 0, pe (2*1+1*2)/9 = 4/9
        p = sc.pooled(list(rows.values()))
        self.assertEqual(p["decisions"], 6)
        self.assertAlmostEqual(p["percent_agreement"], 100 * 3 / 6)


class TestParse(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.ids = [e["excerpt_id"] for e in sc.excerpts()]

    def sheet(self, cells: dict) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["excerpt_id", "pifs"])
        for k, v in cells.items():
            w.writerow([k, v])
        return buf.getvalue()

    def test_curie_local_name_none_and_blank(self) -> None:
        text = self.sheet(
            {self.ids[0]: "ehs:Staffing; MentalFatigue", self.ids[1]: "NONE", self.ids[2]: ""}
        )
        got = sc.parse_sheet(text, self.ont)
        self.assertEqual(got[self.ids[0]], {"ehs:Staffing", "ehs:MentalFatigue"})
        self.assertEqual(got[self.ids[1]], set())
        self.assertNotIn(self.ids[2], got)

    def test_rejects_bad_input(self) -> None:
        for cells in (
            {"nope": "ehs:Staffing"},
            {self.ids[0]: "ehs:NotAFactor"},
            {self.ids[0]: "NONE;ehs:Staffing"},
        ):
            with self.assertRaises(sc.SheetError):
                sc.parse_sheet(self.sheet(cells), self.ont)
        with self.assertRaises(sc.SheetError):
            sc.parse_sheet("excerpt_id,other\nx,y\n", self.ont)
        dup = f"excerpt_id,pifs\n{self.ids[0]},NONE\n{self.ids[0]},NONE\n"
        with self.assertRaises(sc.SheetError):
            sc.parse_sheet(dup, self.ont)


class TestCli(unittest.TestCase):
    def test_round_trip_report_when_coder_two_copies_coder_one(self) -> None:
        # Mechanical check only: a sheet filled from coder 1's own codes must give kappa 1.
        ont = context.ontology()
        first = sc.first_coder_sets()
        lines = ["excerpt_id,pifs"] + [f"{e},{';'.join(sorted(f))}" for e, f in first.items()]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "copy.csv")
            with open(path, "w", encoding="utf-8") as h:
                h.write("\n".join(lines) + "\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(sc.main(["report", path, "--markdown"]), 0)
        out = buf.getvalue()
        self.assertIn(f"{len(first)} excerpts rated", out)
        self.assertIn("All PIFs pooled", out)
        self.assertNotIn("| 0.0 |", out)
        self.assertEqual(
            {r["factor"] for r in sc.agreement(first, first, ont.factors)},
            {f for s in first.values() for f in s},
        )
        for r in sc.agreement(first, first, ont.factors):
            self.assertEqual(r["percent_agreement"], 100.0)
            self.assertEqual(r["kappa"], 1.0)


if __name__ == "__main__":
    unittest.main()
