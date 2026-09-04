"""Tests for the command line interface.

Every command the README advertises is exercised here, so a documented command
cannot quietly stop working. Output is captured rather than inspected in
detail — the substance is tested elsewhere; what matters here is that the
entry points exist, exit cleanly, and print something.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import List, Tuple

from tests import context

from ehs_hfo.cli import main

REACTOR = os.path.join(context.EXAMPLES_DIR, "reactor_startup_nonroutine.json")


def _run(argv: List[str]) -> Tuple[int, str, str]:
    """Run the CLI, returning (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestDocumentedCommands(unittest.TestCase):
    """Each command shown in the README must run."""

    def test_assess(self) -> None:
        code, out, _ = _run(["assess", REACTOR])
        self.assertEqual(code, 0)
        self.assertIn("Screening band", out)

    def test_factors(self) -> None:
        code, out, _ = _run(["factors"])
        self.assertEqual(code, 0)
        self.assertIn("Scenario familiarity", out)

    def test_crosswalk(self) -> None:
        code, out, _ = _run(["crosswalk"])
        self.assertEqual(code, 0)
        self.assertGreater(len(out.splitlines()), 50)

    def test_crosswalk_filtered_by_framework(self) -> None:
        code, out, _ = _run(["crosswalk", "--framework", "xw:fw-SPARH"])
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())

    def test_gaps(self) -> None:
        code, out, _ = _run(["gaps"])
        self.assertEqual(code, 0)
        self.assertTrue(out.strip())

    def test_rules(self) -> None:
        code, out, _ = _run(["rules"])
        self.assertEqual(code, 0)
        self.assertIn("stratum", out.lower())
        self.assertIn("convention", out)


class TestAssessOutput(unittest.TestCase):
    """The report must carry its caveats wherever it is produced."""

    def test_report_names_its_provenance_and_disclaims_probability(self) -> None:
        _, out, _ = _run(["assess", REACTOR])
        self.assertIn("NUREG-2198", out)
        self.assertIn("not a probability", out.lower())

    def test_synthetic_input_is_flagged_in_the_output(self) -> None:
        path = sorted(
            os.path.join(context.SYNTHETIC_SCENARIO_DIR, n)
            for n in os.listdir(context.SYNTHETIC_SCENARIO_DIR)
            if n.endswith(".json")
        )[0]
        _, out, _ = _run(["assess", path])
        self.assertIn("SYNTHETIC", out.upper())

    def test_json_output_is_valid_json(self) -> None:
        code, out, _ = _run(["assess", REACTOR, "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["scenario_id"], "reactor-startup-nonroutine")


class TestErrorHandling(unittest.TestCase):
    """Bad input must fail cleanly rather than traceback."""

    def test_missing_scenario_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope.json")
            with self.assertRaises((SystemExit, OSError, ValueError)):
                _run(["assess", missing])

    def test_scenario_with_unknown_factor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "scenario_id": "bad",
                        "factor_levels": {"ehs:Nonexistent": "ehs:LevelNominal"},
                    },
                    handle,
                )
            with self.assertRaises((SystemExit, ValueError)):
                _run(["assess", path])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
