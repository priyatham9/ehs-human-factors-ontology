"""Build an :class:`ObjectStore` from the files committed in this repository.

Sources: ``ontology/ehs-hfo.ttl`` (dimensions, PIFs, frameworks, framework
items), ``crosswalk/crosswalk.csv`` (entries and asserted absences),
``crosswalk/pif_rules.csv`` (suggester rules), ``incidents/csb_investigations.csv``
and ``incidents/csb_coding.csv`` (CSB investigations and quoted excerpts).
Nothing is added that is not in those files.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from ..ontology import Ontology
from .runtime import ObjectStore
from .spec import OntologySpec

REPO_ROOT = Path(__file__).resolve().parents[3]
TTL = REPO_ROOT / "ontology" / "ehs-hfo.ttl"
CROSSWALK = REPO_ROOT / "crosswalk" / "crosswalk.csv"
RULES = REPO_ROOT / "crosswalk" / "pif_rules.csv"
INVESTIGATIONS = REPO_ROOT / "incidents" / "csb_investigations.csv"
CODING = REPO_ROOT / "incidents" / "csb_coding.csv"


def _read(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _s(value: str) -> Optional[str]:
    return value if value != "" else None


def build_store(spec: Optional[OntologySpec] = None, clock=None) -> ObjectStore:
    """Load every committed source into a fresh store (raises on any inconsistency)."""
    store = ObjectStore(spec, clock=clock)
    ont = Ontology.load(str(TTL))
    ttl, cw, rules = "ontology/ehs-hfo.ttl", "crosswalk/crosswalk.csv", "crosswalk/pif_rules.csv"
    store.add_objects("ContextDimension", [
        {"dimension_curie": d.curie, "label": d.label, "definition": d.definition or None,
         "idheas_item_curie": d.idheas_category, "source": ttl} for d in ont.dimensions.values()])
    store.add_objects("Pif", [
        {"factor_curie": f.curie, "label": f.label, "verbatim_label": f.verbatim_label,
         "dimension_curie": f.dimension, "source_refs": list(f.source_refs), "comment": f.comment,
         "source": ttl} for f in ont.factors.values()])
    store.add_objects("Framework", [
        {"framework_curie": f.curie, "label": f.label, "citation": f.citation, "source": ttl}
        for f in ont.frameworks.values()])
    store.add_objects("FrameworkItem", [
        {"external_curie": e.curie, "label": e.label, "verbatim_label": e.verbatim_label,
         "framework_curie": e.framework, "out_of_scope_note": e.out_of_scope_note, "source": ttl}
        for e in ont.external_factors.values()])
    entries, absences = [], []
    for r in _read(CROSSWALK):
        if r["match_strength"] == "none":
            absences.append({"absence_key": f"{r['factor_curie']}|{r['framework']}",
                             "factor_curie": r["factor_curie"], "framework_curie": r["framework"],
                             "note": _s(r["note"]), "source": cw})
        else:
            entries.append({"entry_key": f"{r['factor_curie']}|{r['external_curie']}",
                            "factor_curie": r["factor_curie"], "external_curie": r["external_curie"],
                            "framework_curie": r["framework"], "match_strength": r["match_strength"],
                            "source_refs": [r["source_refs"]] if r["source_refs"] else [],
                            "note": _s(r["note"]), "source": cw})
    store.add_objects("CrosswalkEntry", entries)
    store.add_objects("AssertedAbsence", absences)
    store.add_objects("Rule", [
        {"rule_id": r["rule_id"], "factor_curie": r["factor_curie"], "external_curie": r["external_curie"],
         "phrase": r["phrase"], "rationale": r["rationale"],
         "phrase_seen_in_incident_set": r["phrase_seen_in_incident_set"] == "yes", "source": rules}
        for r in _read(RULES)])
    store.add_objects("Investigation", [
        {"investigation_id": r["investigation_id"], "name": r["name"],
         "incident_date": _s(r["incident_date"]), "location": _s(r["location"]),
         "fatalities": int(r["fatalities"]) if r["fatalities"] != "" else None,
         "final_report_date": _s(r["final_report_date"]), "source_url": r["source_url"],
         "coded": r["coded"] == "yes", "cohort": r["cohort"],
         "source": "incidents/csb_investigations.csv"} for r in _read(INVESTIGATIONS)])
    store.add_objects("EvidenceExcerpt", [
        {"evidence_key": f"E{i:03d}", "investigation_id": r["investigation_id"],
         "factor_curie": r["factor_curie"], "evidence_type": r["evidence_type"],
         "quoted_text": r["quoted_text"], "source": "incidents/csb_coding.csv"}
        for i, r in enumerate(_read(CODING), start=1)])
    return store
