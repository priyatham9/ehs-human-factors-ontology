"""Every figure in docs/manuscript/manuscript.md must trace to a repository file.

Appendix A of the manuscript is a register: id, value, source file, search string.
These tests check that each search string occurs in its source file, that every
[Nxx] tag in the text has a register row (and vice versa), that the headline
numbers are written exactly as the repository reports them, and that the
register's figures are recomputed from the data files where possible.
"""

from __future__ import annotations

import csv
import os
import re
import unittest

from tests import context

from tools import evaluate_suggester as ev
from tools import methods_note_stats as stats
from tools import second_coder as sc

PATH = os.path.join(context.REPO_ROOT, "docs", "manuscript", "manuscript.md")
APPENDIX_HEAD = "## Appendix A. Numbers register"


def _read(rel: str) -> str:
    with open(os.path.join(context.REPO_ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


def _csv(rel: str):
    with open(os.path.join(context.REPO_ROOT, rel), encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _split_row(line: str):
    cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
    return [c.replace("\\|", "|") for c in cells]


class TestManuscript(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read("docs/manuscript/manuscript.md")
        cls.body, cls.appendix = cls.text.split(APPENDIX_HEAD)
        cls.register = {}
        for line in cls.appendix.splitlines():
            if line.startswith("| N"):
                ident, value, source, pattern, recomputed = _split_row(line)
                pattern = pattern.strip("`")
                cls.register[ident] = (value, source, pattern, recomputed)
        cls.ont = context.ontology()

    # --- structure and honesty of the header ---------------------------------
    def test_header_states_unsubmitted_draft(self) -> None:
        head = self.text[:600]
        self.assertIn("UNSUBMITTED DRAFT", head)
        self.assertIn("has not been submitted", head)
        self.assertIn("Priyatham Chimmani", head)

    def test_imrad_sections_present(self) -> None:
        for heading in ("## Abstract", "## 1 Introduction", "## 2 Methods", "## 3 Results",
                        "## 4 Discussion", "## 7 References", "## 8 TODO"):
            self.assertIn(heading, self.text)

    def test_caveats_precede_the_abstract(self) -> None:
        head = self.text.split("## Abstract")[0]
        for phrase in ("Same-coder caveat", "Excerpt-sourcing caveat", "incomplete"):
            self.assertIn(phrase, head)

    def test_no_second_coder_data_is_stated_and_true(self) -> None:
        self.assertIn("No second coder has contributed", self.text)
        self.assertIn("no agreement statistic", self.text)
        sheets = os.listdir(os.path.join(context.REPO_ROOT, "incidents", "second_coder"))
        self.assertEqual([s for s in sheets if s.endswith(".csv")], [])

    def test_no_em_dashes(self) -> None:
        self.assertNotIn("—", self.text)

    # --- register mechanics ------------------------------------------------------
    def test_register_has_rows(self) -> None:
        self.assertGreaterEqual(len(self.register), 20)

    def test_every_search_string_is_in_its_source_file(self) -> None:
        for ident, (_value, source, pattern, _re) in self.register.items():
            path = os.path.join(context.REPO_ROOT, source)
            self.assertTrue(os.path.isfile(path), f"{ident}: {source} missing")
            self.assertIn(pattern, _read(source), f"{ident}: not found in {source}")

    def test_tags_and_register_agree(self) -> None:
        tags = set(re.findall(r"\[(N\d{2})\]", self.body))
        self.assertEqual(tags, set(self.register))

    def test_register_values_appear_in_body(self) -> None:
        # the leading figure of each value, as written, must be in the text
        for ident, (value, _s, _p, _r) in self.register.items():
            lead = re.match(r"[^;,]*", value).group(0).strip()
            self.assertIn(lead, self.body, f"{ident}: {lead!r}")

    def test_headline_numbers_exact(self) -> None:
        self.assertIn("precision 0.74 and recall 0.80", self.body)
        self.assertIn("precision 0.86 and recall 0.71", self.body)
        self.assertIn("| Development (resubstitution) | 10 | 25 | 20 | 7 | 5 | 0.74 | 0.80 |", self.body)
        self.assertIn("| Held-out | 13 | 42 | 30 | 5 | 12 | 0.86 | 0.71 |", self.body)

    # --- recomputation ----------------------------------------------------------
    def test_ontology_counts(self) -> None:
        f = stats.compute(self.ont)
        self.assertEqual((f["factors"], f["dimensions"], f["alignments"]), (20, 4, 90))
        self.assertEqual(f["external_factors"], 78)
        self.assertEqual(sum(len(v) for v in [f["no_counterpart"]]), 6)
        self.assertEqual((f["reach"][4], f["reach"][3]), (14, 6))
        self.assertEqual(f["rules"], 24)
        tot = {k: sum(c[k] for c in f["by_fw_strength"].values())
               for k in ("close", "broader", "narrower", "partial", "exact")}
        self.assertEqual(tot, {"close": 34, "broader": 23, "narrower": 0, "partial": 33, "exact": 0})
        per_fw = sorted(sum(c[k] for k in tot) for c in f["by_fw_strength"].values())
        self.assertEqual(per_fw, [16, 22, 23, 29])

    def test_cohort_counts_from_csv(self) -> None:
        inv = _csv("incidents/csb_investigations.csv")
        self.assertEqual(len(inv), 28)
        dev = [r for r in inv if r["cohort"] == "development"]
        held = [r for r in inv if r["cohort"] == "held_out"]
        self.assertEqual((len(dev), len(held)), (13, 15))
        self.assertEqual(sum(r["coded"] == "yes" for r in dev), 10)
        self.assertEqual(sum(r["coded"] == "yes" for r in held), 13)
        coding = _csv("incidents/csb_coding.csv")
        self.assertEqual(len(coding), 67)
        self.assertEqual(len({r["factor_curie"] for r in coding}), 10)

    def test_suggester_numbers_recomputed(self) -> None:
        def row(cohort, prefix):
            _n, pairs, _g, results, nrules = ev.evaluate(self.ont, cohort)
            for name, per in results.items():
                if name.startswith(prefix):
                    tp, fp, fn = ev.summarise(per)
                    return (pairs, nrules[name], tp, fp, fn,
                            ev.ratio(tp, tp + fp), ev.ratio(tp, tp + fn))
            self.fail(prefix)

        self.assertEqual(row("development", "curated ("), (25, 97, 20, 7, 5, "0.74", "0.80"))
        self.assertEqual(row("held_out", "curated ("), (42, 97, 30, 5, 12, "0.86", "0.71"))
        self.assertEqual(row("development", "curated without"), (25, 86, 14, 5, 11, "0.74", "0.56"))
        self.assertEqual(row("development", "baseline")[2], 5)
        self.assertEqual(row("held_out", "baseline")[2:], (10, 14, 32, "0.42", "0.24"))
        self.assertEqual(row("held_out", "majority")[2:], (9, 4, 33, "0.69", "0.21"))
        self.assertEqual(row("development", "baseline")[5], "0.31")
        self.assertEqual(97 - 86, 11)
        self.assertEqual(round(100 / 42, 1), 2.4)

    def test_time_pressure_missed_and_ten_pifs_tested(self) -> None:
        _n, _p, gold, results, _r = ev.evaluate(self.ont, "held_out")
        name = next(n for n in results if n.startswith("curated ("))
        c = results[name]["ehs:TimePressureAndStress"]
        self.assertEqual((gold["ehs:TimePressureAndStress"], c["tp"], c["fn"]), (2, 0, 2))
        _n, _p, gold_all, _r, _nr = ev.evaluate(self.ont, None)
        self.assertEqual(len(gold_all), 10)

    def test_second_coder_sheet_size(self) -> None:
        self.assertEqual(len(sc.excerpts()), 67)

    def test_skos_counts(self) -> None:
        ttl = _read("docs/skos/ehs-hfo-skos.ttl")
        self.assertEqual(len(re.findall(r"skos:closeMatch", ttl)), 38)
        self.assertIn("34 + 23 + 33", _read("docs/skos.md"))

    def test_readme_links_manuscript(self) -> None:
        self.assertIn("docs/manuscript/manuscript.md", _read("README.md"))


if __name__ == "__main__":
    unittest.main()
