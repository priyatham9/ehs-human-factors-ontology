"""EHS human-factors ontology, crosswalk and forward-chaining rule engine.

The package deliberately keeps three things separate:

* :mod:`ehs_hfo.turtle` and :mod:`ehs_hfo.ontology` -- the vocabulary,
  parsed from ``ontology/ehs-hfo.ttl``.
* :mod:`ehs_hfo.rules` -- domain propositions taken from published human-factors
  literature, each carrying its own citation.
* :mod:`ehs_hfo.engine` -- a stratified Datalog evaluator that applies the rules
  to a scenario and records why every conclusion holds.

Nothing in this package computes a human error probability.
"""

__version__ = "0.1.0"

from .ontology import Ontology, OntologyError  # noqa: F401
from .turtle import Graph, TurtleSyntaxError, parse, parse_file  # noqa: F401

__all__ = [
    "Ontology",
    "OntologyError",
    "Graph",
    "TurtleSyntaxError",
    "parse",
    "parse_file",
    "__version__",
]
