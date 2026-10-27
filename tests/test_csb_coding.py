"""The CSB coding tables must be well formed, sourced and in sync with the ontology."""

from __future__ import annotations

import unittest

from tests import context

from tools import build_csb_coding as b


class TestCsbCoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ont = context.ontology()
        cls.inv = b.read(b.INVESTIGATIONS)
        cls.rows = b.read(b.CODING)

    def test_factors_exist(self) -> None:
        for r in self.rows:
            self.ont.factor(r["factor_curie"])

    def test_sources_are_csb(self) -> None:
        for r in self.inv:
            self.assertTrue(r["source_url"].startswith("https://www.csb.gov/"), r["name"])

    def test_every_coding_has_quote_and_known_type(self) -> None:
        ids = {r["investigation_id"] for r in self.inv}
        for r in self.rows:
            self.assertIn(r["investigation_id"], ids)
            self.assertIn(r["evidence_type"], {"finding", "recommendation"})
            self.assertGreater(len(r["quoted_text"]), 20)

    def test_coded_flag_matches_codings(self) -> None:
        with_rows = {r["investigation_id"] for r in self.rows}
        for r in self.inv:
            self.assertEqual(r["coded"] == "yes", r["investigation_id"] in with_rows, r["name"])

    def test_no_duplicate_codings(self) -> None:
        keys = [(r["investigation_id"], r["factor_curie"], r["quoted_text"]) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_markdown_is_current(self) -> None:
        with open(b.OUTPUT, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), b.render(self.ont))


if __name__ == "__main__":
    unittest.main()
