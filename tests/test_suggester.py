"""The PIF suggester must be traceable to the crosswalk and its evaluation must be reproducible."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from tests import context

from ehs_hfo import cli
from ehs_hfo import suggest as sg
from tools import build_suggester_page as page
from tools import evaluate_suggester as ev


class TestRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.rules = sg.load_curated()

    def test_ids_unique_and_nonempty(self) -> None:
        ids = [r.rule_id for r in self.rules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 50)

    def test_every_rule_traces_to_an_aligned_external_factor(self) -> None:
        aligned = {(a.local_factor, a.external_factor) for a in self.ont.alignments.values()}
        for r in self.rules:
            self.ont.factor(r.factor_curie)
            self.assertIn((r.factor_curie, r.external_curie), aligned, r.rule_id)
            self.assertTrue(r.rationale.strip(), r.rule_id)

    def test_baseline_rules_are_unique_to_one_pif(self) -> None:
        base = sg.build_baseline(self.ont)
        self.assertGreater(len(base), 20)
        owner = {}
        for r in base:
            self.assertEqual(owner.setdefault(r.phrase, r.factor_curie), r.factor_curie)
            self.ont.factor(r.factor_curie)


class TestMatching(unittest.TestCase):
    def test_whole_word_and_wildcard(self) -> None:
        pat = sg.compile_phrase("train*")
        self.assertTrue(pat.search("Operators were not trained"))
        self.assertFalse(pat.search("constrained"))
        self.assertFalse(sg.compile_phrase("noise").search("noises"))

    def test_phrase_and_hyphen(self) -> None:
        self.assertTrue(sg.compile_phrase("12-hour shift*").search("12-hour shifts for 29 days"))
        self.assertTrue(sg.compile_phrase("shift turnover").search("no shift   turnover policy"))

    def test_suggest_reports_rule_and_text(self) -> None:
        rules = sg.load_curated()
        found = sg.suggest("The operators had no refresher training and the alarm failed.", rules)
        self.assertIn("ehs:Training", found)
        self.assertIn("ehs:HumanSystemInterface", found)
        hit = found["ehs:HumanSystemInterface"][0]
        self.assertEqual(hit.matched_text.lower(), "alarm")
        self.assertEqual(hit.rule.external_curie, "xw:cream-AdequacyOfMMI")

    def test_no_text_no_suggestion(self) -> None:
        self.assertEqual(sg.suggest("", sg.load_curated()), {})
        self.assertIn("not evidence", sg.render({}, context.ontology()))


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            status = cli.main(argv)
        return status, buf.getvalue()

    def test_text_output(self) -> None:
        import os
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Staffing was cut and fatigue followed from overtime.")
            path = f.name
        try:
            status, out = self._run(["suggest", path])
            self.assertEqual(status, 0)
            self.assertIn("ehs:Staffing", out)
            self.assertIn("ehs:MentalFatigue", out)
            self.assertIn("not codings", out)
            status, out = self._run(["suggest", path, "--json"])
            data = json.loads(out)
            self.assertEqual(data["rule_set"], "curated")
            self.assertTrue(all(h["crosswalk_source"] for s in data["suggestions"] for h in s["hits"]))
            status, out = self._run(["suggest", path, "--rules", "baseline"])
            self.assertEqual(status, 0)
        finally:
            os.unlink(path)


class TestEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()

    def test_counts_identity(self) -> None:
        n_inv, n_pairs, gold, results, _ = ev.evaluate(self.ont)
        self.assertEqual(n_pairs, sum(gold.values()))
        for name, per in results.items():
            tp, _, fn = ev.summarise(per)
            self.assertEqual(tp + fn, n_pairs, name)

    def test_curated_is_not_reported_as_unbiased(self) -> None:
        text = ev.render(self.ont)
        self.assertIn("resubstitution", text)
        self.assertIn("Nothing here is an estimate of performance on other incidents", text)

    def test_page_claims_match_numbers(self) -> None:
        _, _, _, results, _ = ev.evaluate(self.ont)
        by = {}
        for name, per in results.items():
            tp, _, fn = ev.summarise(per)
            by[name] = tp / (tp + fn)
        base = next(v for k, v in by.items() if k.startswith("baseline"))
        cur = next(v for k, v in by.items() if k.startswith("curated ("))
        cut = next(v for k, v in by.items() if k.startswith("curated without"))
        self.assertLess(base, 0.5)  # page says "a minority"
        self.assertGreater(cur, 0.5)  # page says "most"
        self.assertLess(cut, cur)  # page says "clearly fewer"

    def test_methods_note_quotes_current_figures(self) -> None:
        with open(context.REPO_ROOT + "/docs/methods-note.md", encoding="utf-8") as handle:
            note = " ".join(handle.read().split())
        expect = [
            "the untuned baseline recovered {tp} of {n} pairs (precision {p})",
            "the curated set recovered {tp} of {n} (precision {p}, recall {r})",
            "without the quote-derived phrases recovered {tp} of {n} (precision {p}, recall {r})",
        ]
        _, _, _, dev, _ = ev.evaluate(self.ont, "development")
        for name, template in zip(list(dev), expect):
            tp, fp, fn = ev.summarise(dev[name])
            text = template.format(tp=tp, n=tp + fn, p=ev.ratio(tp, tp + fp), r=ev.ratio(tp, tp + fn))
            self.assertIn(text, note)
        _, _, _, held, _ = ev.evaluate(self.ont, "held_out")
        names = list(held)
        tp, fp, fn = ev.summarise(held[names[0]])
        self.assertIn(f"the baseline recovered {tp} of {tp + fn} pairs (precision {ev.ratio(tp, tp + fp)})", note)
        tp, fp, fn = ev.summarise(held[names[1]])
        self.assertIn(f"the curated set recovered {tp} of {tp + fn} (precision {ev.ratio(tp, tp + fp)}, "
                      f"recall {ev.ratio(tp, tp + fn)})", note)

    def test_cohorts_partition_the_data(self) -> None:
        a = ev.evaluate(self.ont)
        d = ev.evaluate(self.ont, "development")
        h = ev.evaluate(self.ont, "held_out")
        self.assertEqual(a[0], d[0] + h[0])
        self.assertEqual(a[1], d[1] + h[1])
        self.assertGreaterEqual(h[0], 10)

    def test_reports_are_current(self) -> None:
        with open(ev.OUTPUT, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), ev.render(self.ont), "run tools/evaluate_suggester.py --write")
        with open(page.OUTPUT, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), page.render(self.ont), "run tools/build_suggester_page.py --write")


if __name__ == "__main__":
    unittest.main()
