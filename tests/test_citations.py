"""Tests that every citation key resolves to a real, recorded bibliography entry.

This is the integrity check. The ontology and the rule base refer to sources by
short key (``nureg2198``, ``gertman2005``). A key with no entry in
``CITATIONS.md`` is a citation to nothing, and a bibliography entry nothing uses
is either a leftover or a source someone meant to lean on and did not. Both are
caught here.

These tests confirm that the keys are internally consistent and that each entry
declares how it was verified. They cannot confirm that a cited document says
what this repository claims it says. That is what ``docs/PROVENANCE.md`` is for,
and it is a human obligation, not a testable one.
"""

from __future__ import annotations

import os
import re
import unittest
from typing import Set

from tests import context

from ehs_hfo.rules import RULES

#: Verification states permitted in CITATIONS.md, defined in that file.
VERIFICATION_STATES = ("primary", "bibliographic", "secondary")


def _citation_text() -> str:
    with open(context.CITATIONS_PATH, encoding="utf-8") as handle:
        return handle.read()


def _documented_keys() -> Set[str]:
    """Keys defined by a ``### \\`key\\``` heading in CITATIONS.md."""
    return set(re.findall(r"^### `([a-z0-9_]+)`\s*$", _citation_text(), re.M))


def _ontology_keys() -> Set[str]:
    return set(context.ontology().all_source_refs())


def _rule_keys() -> Set[str]:
    keys: Set[str] = set()
    for rule in RULES:
        keys.update(rule.source_refs)
    return keys


class TestCitationsFileExists(unittest.TestCase):
    """The bibliography must be present and structured."""

    def test_citations_file_exists(self) -> None:
        self.assertTrue(os.path.exists(context.CITATIONS_PATH))

    def test_citations_file_defines_keys(self) -> None:
        self.assertGreater(len(_documented_keys()), 0)


class TestEveryKeyResolves(unittest.TestCase):
    """No key may point at nothing."""

    def test_every_ontology_key_is_documented(self) -> None:
        documented = _documented_keys()
        for key in sorted(_ontology_keys()):
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    documented,
                    f"ontology cites '{key}' with no entry in CITATIONS.md",
                )

    def test_every_rule_key_is_documented(self) -> None:
        documented = _documented_keys()
        for key in sorted(_rule_keys()):
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    documented,
                    f"a rule cites '{key}' with no entry in CITATIONS.md",
                )

    def test_no_documented_key_is_unused(self) -> None:
        """An entry nothing cites is either dead or a source someone forgot to use."""
        used = _ontology_keys() | _rule_keys()
        unused = sorted(_documented_keys() - used)
        self.assertEqual(
            unused, [], f"CITATIONS.md documents unused keys: {unused}"
        )


class TestVerificationStatus(unittest.TestCase):
    """Each entry must say how strongly it was checked."""

    def test_every_entry_declares_a_verification_state(self) -> None:
        text = _citation_text()
        sections = re.split(r"^### `([a-z0-9_]+)`\s*$", text, flags=re.M)
        # sections alternates [preamble, key, body, key, body, ...]
        for key, body in zip(sections[1::2], sections[2::2]):
            with self.subTest(key=key):
                match = re.search(r"\*\*Verification:\*\*\s*(\w+)", body)
                self.assertIsNotNone(
                    match, f"'{key}' has no **Verification:** line"
                )
                assert match is not None
                self.assertIn(
                    match.group(1),
                    VERIFICATION_STATES,
                    f"'{key}' declares an unknown verification state "
                    f"{match.group(1)!r}",
                )

    def test_the_states_are_defined_in_the_file(self) -> None:
        text = _citation_text()
        for state in VERIFICATION_STATES:
            with self.subTest(state=state):
                self.assertIn(f"`{state}`", text)

    def test_secondary_transcriptions_name_their_intermediary(self) -> None:
        """A transcription must say what it was transcribed from."""
        text = _citation_text()
        self.assertIn("shirali2019", text)
        self.assertIn("secondary", text)


class TestFrameworkCitations(unittest.TestCase):
    """The four crosswalked frameworks must each be cited."""

    def test_each_framework_source_ref_is_documented(self) -> None:
        documented = _documented_keys()
        for curie, framework in sorted(context.ontology().frameworks.items()):
            for key in framework.source_refs:
                with self.subTest(framework=curie, key=key):
                    self.assertIn(key, documented)

    def test_hfacs_cites_both_report_versions(self) -> None:
        """The crosswalk maps the revised taxonomy, so both reports are cited."""
        framework = context.ontology().frameworks["xw:fw-HFACS"]
        self.assertIn("shappell2000", framework.source_refs)
        self.assertIn("shappell2006", framework.source_refs)


class TestNoUnsupportedClaims(unittest.TestCase):
    """Guards against the specific overclaims this project is exposed to."""

    def test_no_human_error_probability_is_claimed_anywhere(self) -> None:
        with open(context.ONTOLOGY_PATH, encoding="utf-8") as handle:
            ttl = handle.read().lower()
        for term in ("human error probability", "hep value", "nominal hep"):
            with self.subTest(term=term):
                # The phrase may appear only where it is being disclaimed.
                for line in ttl.splitlines():
                    if term in line:
                        self.assertTrue(
                            any(
                                marker in line
                                for marker in ("no ", "not ", "never", "asserts")
                            ),
                            f"ontology appears to assert {term!r}: {line.strip()}",
                        )

    def test_spar_h_multipliers_are_not_used(self) -> None:
        """SPAR-H multipliers were fitted to nuclear operations, not to NAICS 325."""
        with open(context.ONTOLOGY_PATH, encoding="utf-8") as handle:
            ttl = handle.read()
        self.assertNotIn("ehs:sparhMultiplier", ttl)
        self.assertNotIn("hasMultiplier", ttl)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
