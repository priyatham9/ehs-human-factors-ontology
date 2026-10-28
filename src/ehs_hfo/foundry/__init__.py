"""Foundry-style ontology over the human-factors ontology, crosswalk, rules and CSB evidence.

An independent design in the style of a Palantir Foundry Ontology, built only
on files committed in this repository. It is not affiliated with Palantir.

``spec.json``     declarative object types, link types, action types, functions
``spec``          load and validate the spec
``runtime``       object store, object sets, link traversal, actions, action log
``functions``     pure ontology functions (framework coverage, rules triggered, ...)
``materialise``   build a store from ontology/ehs-hfo.ttl, crosswalk/, incidents/
``export``        write a store to SQLite and JSON

Named ``foundry`` because ``ehs_hfo.ontology`` is the existing OWL/Turtle loader.
See docs/ontology.md. Run ``python3 -m ehs_hfo.foundry --out DIR``.
"""
from .runtime import ActionRejected, ObjectSet, ObjectStore, OntologyObject
from .spec import OntologySpec, SpecError, load_spec

__all__ = ["ActionRejected", "ObjectSet", "ObjectStore", "OntologyObject", "OntologySpec",
           "SpecError", "load_spec"]
