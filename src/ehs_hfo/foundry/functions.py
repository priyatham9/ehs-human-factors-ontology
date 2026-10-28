"""Pure ontology functions over an :class:`ObjectStore`.

Nothing here writes to the store or computes a human error probability. Every
count is derived from the objects, which are read from committed files.
Rejected crosswalk entries and rejected excerpts are ignored, so action-log
writeback reaches the numbers; retired rules are not triggered.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .. import suggest
from .runtime import ObjectStore, OntologyObject

STRENGTH_RANK = {"broader": 1, "partial": 2, "close": 3}


def _live_entries(store: ObjectStore, framework: Optional[str] = None,
                  min_strength: str = "broader") -> List[OntologyObject]:
    floor = STRENGTH_RANK[min_strength]
    return [e for e in store.objects("CrosswalkEntry")
            if e["review_status"] != "rejected" and STRENGTH_RANK[e["match_strength"]] >= floor
            and (framework is None or e["framework_curie"] == framework)]


def framework_coverage(store: ObjectStore, framework: str,
                       pif_curies: Optional[Iterable[str]] = None,
                       min_strength: str = "broader") -> Dict[str, Any]:
    """Coverage of one framework by a set of PIFs (default: every PIF).

    ``items_reached`` counts framework items that at least one PIF in the set
    reaches through a non-rejected entry at or above ``min_strength``.
    ``pifs_with_counterpart`` / ``pifs_asserted_absent`` / ``pifs_unaddressed``
    describe what the crosswalk says about each PIF in the set for this
    framework. Items bound at dimension level (IDHEAS-G categories) have no
    entries and are reported as ``items_dimension_level``.
    """
    store.get("Framework", framework)
    if min_strength not in STRENGTH_RANK:
        raise ValueError(f"min_strength must be one of {sorted(STRENGTH_RANK)}")
    all_pifs = set(store.objects("Pif").primary_keys())
    pifs = all_pifs if pif_curies is None else set(pif_curies)
    if pifs - all_pifs:
        raise KeyError(f"unknown PIFs {sorted(pifs - all_pifs)}")
    items = [i for i in store.objects("FrameworkItem") if i["framework_curie"] == framework]
    entries = [e for e in _live_entries(store, framework, min_strength) if e["factor_curie"] in pifs]
    reached = {e["external_curie"] for e in entries}
    anyentry = {e["factor_curie"] for e in _live_entries(store, framework) if e["factor_curie"] in pifs}
    absent = {a["factor_curie"] for a in store.objects("AssertedAbsence")
              if a["framework_curie"] == framework and a["factor_curie"] in pifs}
    dim_level = ({d["idheas_item_curie"] for d in store.objects("ContextDimension")
                  if d["idheas_item_curie"]} & {i.primary_key for i in items})
    by_strength: Dict[str, int] = {}
    for e in entries:
        by_strength[e["match_strength"]] = by_strength.get(e["match_strength"], 0) + 1
    return {
        "framework": framework, "min_strength": min_strength, "pifs_in_set": len(pifs),
        "items_total": len(items), "items_reached": len(reached),
        "items_unreached": sorted(i.primary_key for i in items if i.primary_key not in reached),
        "items_dimension_level": len(dim_level),
        "entries": len(entries), "entries_by_strength": dict(sorted(by_strength.items())),
        "pifs_with_counterpart": len(anyentry), "pifs_asserted_absent": len(absent),
        "pifs_unaddressed": sorted(pifs - anyentry - absent),
    }


def rules_triggered(store: ObjectStore, pif_curies: Iterable[str]) -> List[OntologyObject]:
    """Active suggester rules whose PIF is in the given set, in rule-id order."""
    pifs = set(pif_curies)
    return sorted((r for r in store.objects("Rule")
                   if r["status"] == "active" and r["factor_curie"] in pifs),
                  key=lambda r: r.primary_key)


def rules_triggered_by_text(store: ObjectStore, text: str) -> Dict[str, List[str]]:
    """PIF -> matched strings, using the suggester's own phrase matcher on active rules."""
    rules = [suggest.Rule(r.primary_key, r["factor_curie"], r["phrase"], r["external_curie"],
                          r["rationale"], suggest.compile_phrase(r["phrase"]))
             for r in store.objects("Rule") if r["status"] == "active"]
    return {f: [h.matched_text for h in hits] for f, hits in suggest.suggest(text, rules).items()}


def pif_evidence(store: ObjectStore, pif_curie: str) -> Dict[str, Any]:
    """Non-rejected excerpts and distinct investigations coded to one PIF."""
    pif = store.get("Pif", pif_curie)
    ex = [e for e in store.linked(pif, "excerpts") if e["review_status"] != "rejected"]
    return {"pif": pif_curie, "excerpts": len(ex),
            "findings": sum(e["evidence_type"] == "finding" for e in ex),
            "recommendations": sum(e["evidence_type"] == "recommendation" for e in ex),
            "investigations": sorted({e["investigation_id"] for e in ex})}


def coverage_table(store: ObjectStore) -> Dict[str, Any]:
    """Counts behind docs/ontology-coverage.md: one row per framework and one per PIF."""
    frameworks = []
    for fw in sorted(store.objects("Framework"), key=lambda f: f["label"]):
        c = framework_coverage(store, fw.primary_key)
        frameworks.append({
            "framework": fw["label"], "framework_curie": fw.primary_key, "items": c["items_total"],
            "items_reached": c["items_reached"], "entries": c["entries"],
            "close": c["entries_by_strength"].get("close", 0),
            "partial": c["entries_by_strength"].get("partial", 0),
            "broader": c["entries_by_strength"].get("broader", 0),
            "pifs_with_counterpart": c["pifs_with_counterpart"],
            "pifs_asserted_absent": c["pifs_asserted_absent"],
            "pifs_unaddressed": len(c["pifs_unaddressed"]),
            "dimension_level_items": c["items_dimension_level"],
            "rules": sum(1 for r in store.objects("Rule") if r["status"] == "active"
                         and store.linked(r, "item").one()["framework_curie"] == fw.primary_key)})
    pifs = []
    for p in sorted(store.objects("Pif"), key=lambda p: (p["dimension_curie"], p["label"])):
        ev = pif_evidence(store, p.primary_key)
        live = [e for e in store.linked(p, "crosswalk_entries") if e["review_status"] != "rejected"]
        pifs.append({
            "pif": p["label"], "factor_curie": p.primary_key,
            "dimension": store.linked(p, "dimension").one()["label"],
            "frameworks_with_counterpart": len({e["framework_curie"] for e in live}),
            "entries": len(live), "rules": len(rules_triggered(store, [p.primary_key])),
            "excerpts": ev["excerpts"], "investigations": len(ev["investigations"])})
    inv = list(store.objects("Investigation"))
    return {"frameworks": frameworks, "pifs": pifs,
            "investigations": len(inv), "investigations_coded": sum(i["coded"] for i in inv),
            "excerpts": len(store.objects("EvidenceExcerpt")),
            "rules": len(store.objects("Rule"))}
