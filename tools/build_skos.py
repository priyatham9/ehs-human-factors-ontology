#!/usr/bin/env python3
"""Export the PIF ontology and crosswalk as SKOS (Turtle and JSON-LD).

Everything is derived from ``ontology/ehs-hfo.ttl`` through the repository's own
loader, so the SKOS files are never hand-edited. Standard library only.

What is exported
----------------
* one ``skos:ConceptScheme`` for the EHS-HFO (4 context dimensions as top
  concepts, 20 PIFs as their narrower concepts);
* one ``skos:ConceptScheme`` per external framework in the ontology (IDHEAS-G,
  SPAR-H, CREAM, HFACS, HSE PIF list) holding that framework's factors;
* the crosswalk as SKOS mapping properties from each PIF to the external factor
  (see ``MATCH_PROPERTY``), and each dimension's IDHEAS-G category as
  ``skos:closeMatch``.

What is not exported
--------------------
The reified alignment resources (per-row source keys and comments), the
"no counterpart" assertions, factor levels, macrocognitive functions, failure
modes and observable proxies. Those stay in the OWL/Turtle source. SKOS has no
way to say "this PIF has no counterpart in framework X", so absences are simply
absent mappings.

Concept URIs are the ontology's existing identifiers, so the SKOS files and the
OWL file talk about the same resources. They are identifiers; this project does
not run a resolver.

Usage::

    python3 tools/build_skos.py           # write docs/skos/
    python3 tools/build_skos.py --check   # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Set, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from ehs_hfo.ontology import Ontology  # noqa: E402
from ehs_hfo.turtle import IRI  # noqa: E402

__all__ = ["build_triples", "to_turtle", "to_jsonld", "SKOS_DIR", "MATCH_PROPERTY"]

SKOS_DIR = os.path.join(_REPO_ROOT, "docs", "skos")
TTL_NAME = "ehs-hfo-skos.ttl"
JSONLD_NAME = "ehs-hfo-skos.jsonld"

BASE = "https://priyatham9.github.io/ehs-human-factors-ontology/"
HFO_SCHEME = BASE + "ehs-hfo#PIFConceptScheme"
RAW_BASE = "https://raw.githubusercontent.com/priyatham9/ehs-human-factors-ontology/main/"

PREFIXES: Dict[str, str] = {
    "dcterms": "http://purl.org/dc/terms/",
    "ehs": BASE + "ehs-hfo#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xw": BASE + "xwalk#",
}
SKOS = PREFIXES["skos"]
DCT = PREFIXES["dcterms"]
RDF_TYPE = PREFIXES["rdf"] + "type"

#: Ontology match strength -> SKOS mapping property, read from the PIF (subject)
#: to the external factor (object).
#:   exact   same construct and scope      -> skos:exactMatch
#:   close   same construct, scope differs  -> skos:closeMatch
#:   broader external subsumes the PIF      -> skos:broadMatch
#:   narrower external covers part of PIF   -> skos:narrowMatch
#:   partial overlapping, non-nested        -> skos:relatedMatch
MATCH_PROPERTY: Dict[str, str] = {
    "ehs:MatchExact": SKOS + "exactMatch",
    "ehs:MatchClose": SKOS + "closeMatch",
    "ehs:MatchBroader": SKOS + "broadMatch",
    "ehs:MatchNarrower": SKOS + "narrowMatch",
    "ehs:MatchPartial": SKOS + "relatedMatch",
}

# An object is ("iri", value) or ("lit", text, lang).
Obj = Tuple[str, ...]
Triple = Tuple[str, str, Obj]


def _iri(curie: str) -> str:
    prefix, local = curie.split(":", 1)
    return PREFIXES[prefix] + local


def _l(text: str) -> Obj:
    return ("lit", text, "en")


def build_triples(ont: Ontology) -> List[Triple]:
    """The SKOS graph as a sorted, de-duplicated list of triples."""
    out: Set[Triple] = set()

    def add(s: str, p: str, o: Obj) -> None:
        out.add((s, p, o))

    graph = ont.graph
    onto_node = IRI(BASE + "ehs-hfo")
    version = graph.literal(onto_node, "owl:versionInfo") or ""

    add(HFO_SCHEME, RDF_TYPE, ("iri", SKOS + "ConceptScheme"))
    add(HFO_SCHEME, DCT + "title", _l("EHS Human Factors Ontology: performance-influencing factors"))
    add(HFO_SCHEME, DCT + "creator", ("lit", "Priyatham Chimmani", ""))
    add(HFO_SCHEME, DCT + "license", ("iri", "https://opensource.org/licenses/MIT"))
    if version:
        add(HFO_SCHEME, DCT + "hasVersion", ("lit", version, ""))
    add(
        HFO_SCHEME,
        DCT + "description",
        _l(
            "SKOS rendering of the four context dimensions and twenty performance-"
            "influencing factors of IDHEAS-G (NUREG-2198), with analyst-judged mappings to "
            "SPAR-H, CREAM, HFACS and the HSE PIF list. Generated from ontology/ehs-hfo.ttl. "
            "Not endorsed by any standards body."
        ),
    )
    add(HFO_SCHEME, DCT + "source", ("iri", RAW_BASE + "ontology/ehs-hfo.ttl"))

    # Context dimensions: top concepts.
    for d in ont.dimensions.values():
        di = _iri(d.curie)
        add(di, RDF_TYPE, ("iri", SKOS + "Concept"))
        add(di, SKOS + "inScheme", ("iri", HFO_SCHEME))
        add(di, SKOS + "topConceptOf", ("iri", HFO_SCHEME))
        add(HFO_SCHEME, SKOS + "hasTopConcept", ("iri", di))
        add(di, SKOS + "prefLabel", _l(d.label))
        if d.definition:
            add(di, SKOS + "definition", _l(d.definition))
        if d.comment:
            add(di, SKOS + "note", _l(d.comment))
        if d.idheas_category:
            add(di, SKOS + "closeMatch", ("iri", _iri(d.idheas_category)))

    # PIFs.
    for f in ont.factors.values():
        fi, di = _iri(f.curie), _iri(f.dimension)
        add(fi, RDF_TYPE, ("iri", SKOS + "Concept"))
        add(fi, SKOS + "inScheme", ("iri", HFO_SCHEME))
        add(fi, SKOS + "prefLabel", _l(f.label))
        if f.verbatim_label and f.verbatim_label != f.label:
            add(fi, SKOS + "altLabel", _l(f.verbatim_label))
        add(fi, SKOS + "broader", ("iri", di))
        add(di, SKOS + "narrower", ("iri", fi))
        for note in f.boundary_notes:
            if note.startswith("Function assignment"):
                continue  # about macrocognitive functions, which are not exported
            add(fi, SKOS + "scopeNote", _l(note))
        if f.comment:
            add(fi, SKOS + "note", _l(f.comment))

    # External frameworks.
    for fw in ont.frameworks.values():
        si = _iri(fw.curie)
        add(si, RDF_TYPE, ("iri", SKOS + "ConceptScheme"))
        add(si, DCT + "title", _l(fw.label))
        if fw.citation:
            add(si, DCT + "bibliographicCitation", ("lit", fw.citation, ""))
        if fw.comment:
            add(si, SKOS + "note", _l(fw.comment))
    for ef in ont.external_factors.values():
        if ef.framework is None:
            continue
        ei, si = _iri(ef.curie), _iri(ef.framework)
        add(ei, RDF_TYPE, ("iri", SKOS + "Concept"))
        add(ei, SKOS + "inScheme", ("iri", si))
        add(ei, SKOS + "prefLabel", _l(ef.label))
        if ef.verbatim_label and ef.verbatim_label != ef.label:
            add(ei, SKOS + "altLabel", _l(ef.verbatim_label))
        if ef.parent:
            add(ei, SKOS + "broader", ("iri", _iri(ef.parent)))
            add(_iri(ef.parent), SKOS + "narrower", ("iri", ei))
        if ef.out_of_scope_note:
            add(ei, SKOS + "scopeNote", _l(ef.out_of_scope_note))

    # Crosswalk.
    for a in ont.alignments.values():
        add(
            _iri(a.local_factor),
            MATCH_PROPERTY[a.match_strength],
            ("iri", _iri(a.external_factor)),
        )

    return sorted(out)


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #


def _esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _compact(iri: str) -> str:
    """Prefixed name if the local part is a plain name, else ``<iri>``."""
    for prefix, ns in PREFIXES.items():
        if iri.startswith(ns):
            local = iri[len(ns):]
            if local and all(c.isalnum() or c in "-_" for c in local) and not local[0] in "-":
                return f"{prefix}:{local}"
    return f"<{iri}>"


def _ttl_obj(o: Obj) -> str:
    if o[0] == "iri":
        return _compact(o[1])
    text = f'"{_esc(o[1])}"'
    return f"{text}@{o[2]}" if o[2] else text


def to_turtle(triples: List[Triple]) -> str:
    lines = [
        "# ehs-hfo-skos.ttl -- SKOS rendering of the EHS-HFO PIF structure and crosswalk.",
        "# GENERATED by tools/build_skos.py from ontology/ehs-hfo.ttl. Do not edit by hand.",
        "# Mapping direction: from a PIF (subject) to the external factor (object).",
        "# Licence: MIT. Not endorsed by any standards body.",
        "",
    ]
    for prefix in sorted(PREFIXES):
        lines.append(f"@prefix {prefix}: <{PREFIXES[prefix]}> .")
    lines.append("")
    by_subject: Dict[str, List[Tuple[str, Obj]]] = {}
    for s, p, o in triples:
        by_subject.setdefault(s, []).append((p, o))
    for s in sorted(by_subject):
        pairs = by_subject[s]
        # rdf:type first, then by predicate name.
        pairs.sort(key=lambda po: (po[0] != RDF_TYPE, po[0], po[1]))
        lines.append(_compact(s))
        for i, (p, o) in enumerate(pairs):
            pred = "a" if p == RDF_TYPE else _compact(p)
            end = " ." if i == len(pairs) - 1 else " ;"
            lines.append(f"    {pred} {_ttl_obj(o)}{end}")
        lines.append("")
    return "\n".join(lines)


def to_jsonld(triples: List[Triple]) -> str:
    def key(iri: str) -> str:
        return _compact(iri) if not _compact(iri).startswith("<") else iri

    nodes: Dict[str, Dict[str, object]] = {}
    for s, p, o in triples:
        node = nodes.setdefault(s, {"@id": key(s)})
        if p == RDF_TYPE:
            node.setdefault("@type", [])
            node["@type"].append(key(o[1]))  # type: ignore[union-attr]
            continue
        if o[0] == "iri":
            val: object = {"@id": key(o[1])}
        elif o[2]:
            val = {"@value": o[1], "@language": o[2]}
        else:
            val = {"@value": o[1]}
        node.setdefault(key(p), [])
        node[key(p)].append(val)  # type: ignore[union-attr]
    doc = {
        "@context": {k: PREFIXES[k] for k in sorted(PREFIXES)},
        "@graph": [nodes[k] for k in sorted(nodes)],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build_all(ont: Ontology) -> Dict[str, str]:
    triples = build_triples(ont)
    return {TTL_NAME: to_turtle(triples), JSONLD_NAME: to_jsonld(triples)}


def main(argv: List[str] = None) -> int:  # type: ignore[assignment]
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if files are out of date")
    args = ap.parse_args(argv)
    files = build_all(Ontology.load(os.path.join(_REPO_ROOT, "ontology", "ehs-hfo.ttl")))
    stale = []
    for name, text in files.items():
        path = os.path.join(SKOS_DIR, name)
        current = None
        if os.path.exists(path):
            with open(path, encoding="utf-8", newline="") as fh:
                current = fh.read()
        if current != text:
            stale.append(name)
            if not args.check:
                os.makedirs(SKOS_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
    if args.check and stale:
        print("out of date: " + ", ".join(stale) + "; run python3 tools/build_skos.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
