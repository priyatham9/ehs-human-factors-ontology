"""Path setup and shared fixtures for the test suite.

Importing this module puts ``src/`` and the repository root on ``sys.path``, so
tests run against the working tree without an install step. It also caches the
parsed ontology and the stratified program, both of which are immutable once
built and are slow enough to be worth building once.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
ONTOLOGY_PATH = os.path.join(REPO_ROOT, "ontology", "ehs-hfo.ttl")
EXAMPLES_DIR = os.path.join(REPO_ROOT, "examples")
SYNTHETIC_DIR = os.path.join(REPO_ROOT, "synthetic")
SYNTHETIC_SCENARIO_DIR = os.path.join(SYNTHETIC_DIR, "scenarios")
CROSSWALK_DIR = os.path.join(REPO_ROOT, "crosswalk")
CITATIONS_PATH = os.path.join(REPO_ROOT, "CITATIONS.md")

for _path in (SRC_DIR, REPO_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from ehs_hfo.engine import Program  # noqa: E402
from ehs_hfo.ontology import Ontology  # noqa: E402
from ehs_hfo.rules import build_program  # noqa: E402

__all__ = [
    "REPO_ROOT",
    "SRC_DIR",
    "ONTOLOGY_PATH",
    "EXAMPLES_DIR",
    "SYNTHETIC_DIR",
    "SYNTHETIC_SCENARIO_DIR",
    "CROSSWALK_DIR",
    "CITATIONS_PATH",
    "ontology",
    "program",
]

_ONTOLOGY: Optional[Ontology] = None
_PROGRAM: Optional[Program] = None


def ontology() -> Ontology:
    """The parsed ontology, built once per process."""
    global _ONTOLOGY
    if _ONTOLOGY is None:
        _ONTOLOGY = Ontology.load(ONTOLOGY_PATH)
    return _ONTOLOGY


def program() -> Program:
    """The stratified rule program, built once per process."""
    global _PROGRAM
    if _PROGRAM is None:
        _PROGRAM = build_program()
    return _PROGRAM
