#!/usr/bin/env python3
"""Data expectations and declared pipeline lineage for the committed ontology data (stdlib only).

A plain-Python take on the Foundry practice of named data expectations and pipeline lineage,
applied to this repository's public data: the ontology, the crosswalk, the suggester rules, the
CSB incident coding and the co-occurrence tables. It reads only committed files and is
independent of and not affiliated with Palantir.

Two parts.

* ``run_checks``: named expectations (referential integrity across files, value domains, dates,
  counts that must agree between files, null-rate ceilings, recomputed co-occurrence counts),
  each with an observed value, a limit and a pass/warn/fail status.
* ``validate_lineage``: ``tools/lineage.json`` declares stages (script, function, inputs, outputs).
  The check confirms paths exist, functions are defined (via ast, nothing imported), every
  committed generated file is placed in the graph, no artifact has two producers and there is no
  cycle.

Usage::

    python3 tools/health.py            # print a summary
    python3 tools/health.py --write    # refresh health/*.csv, docs/health.md, docs/health.svg
    python3 tools/health.py --check    # exit 1 if a check fails, lineage is broken or outputs are stale
"""

from __future__ import annotations

import ast
import csv
import glob
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from typing import Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ehs_hfo.ontology import Ontology  # noqa: E402

SPEC = os.path.join(ROOT, "tools", "lineage.json")
OUT_DIR = os.path.join(ROOT, "health")
DOC = os.path.join(ROOT, "docs", "health.md")
SVG = os.path.join(ROOT, "docs", "health.svg")
CHECKS_CSV = os.path.join(OUT_DIR, "health_checks.csv")
LINEAGE_CSV = os.path.join(OUT_DIR, "lineage_stages.csv")
COLUMNS_CSV = os.path.join(OUT_DIR, "health_columns.csv")

ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DAY_OR_MONTH = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
STRENGTHS = ("close", "partial", "broader", "none")
EVIDENCE = ("finding", "recommendation")
COHORTS = ("development", "held_out")
# Data as-of date; a later date cannot be a real event or report date for the committed files.
LAST_PLAUSIBLE_DATE = "2026-11-09"

# Ceilings on the share of empty values, with the reason each is allowed.
NULL_LIMITS = {
    ("crosswalk", "note"): (85.0, "a note is only written where a match needs explaining"),
    ("crosswalk", "source_refs"): (7.0, "only asserted-absence rows carry no source"),
    ("crosswalk", "external_curie"): (7.0, "only asserted-absence rows have no external factor"),
    ("investigations", "final_report_date"): (10.0, "a few investigations have no final report yet"),
}
MUST_BE_COMPLETE = {
    "crosswalk": ("dimension", "factor_curie", "framework", "match_strength"),
    "rules": ("rule_id", "factor_curie", "phrase", "external_curie", "rationale"),
    "coding": ("investigation_id", "factor_curie", "evidence_type", "quoted_text"),
    "investigations": ("investigation_id", "name", "incident_date", "source_url", "coded", "cohort"),
}


def read_csv(rel: str) -> List[Dict[str, str]]:
    with open(os.path.join(ROOT, rel), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load() -> Dict[str, object]:
    with open(os.path.join(ROOT, "CITATIONS.md"), encoding="utf-8") as fh:
        cit = fh.read()
    return {
        "ont": Ontology.load(),
        "crosswalk": read_csv("crosswalk/crosswalk.csv"),
        "rules": read_csv("crosswalk/pif_rules.csv"),
        "coding": read_csv("incidents/csb_coding.csv"),
        "investigations": read_csv("incidents/csb_investigations.csv"),
        "pairs": read_csv("incidents/pif_cooccurrence_pairs.csv"),
        "pifs": read_csv("incidents/pif_cooccurrence_pifs.csv"),
        "citation_keys": set(re.findall(r"^### `([^`]+)`", cit, flags=re.M)),
    }


def is_empty(v) -> bool:
    return v is None or str(v).strip() == ""


def column_profile(rows, dataset):
    out = []
    n = len(rows)
    for c in rows[0].keys():
        vals = [r[c] for r in rows]
        empty = sum(1 for v in vals if is_empty(v))
        out.append({"dataset": dataset, "column": c, "rows": n, "empty": empty,
                    "empty_pct": round(100.0 * empty / n, 2),
                    "distinct": len({v for v in vals if not is_empty(v)})})
    return out


def profiles(data) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for name in ("crosswalk", "rules", "coding", "investigations"):
        out += column_profile(data[name], name)
    return out


def _row(cid, dataset, rule, observed, limit, ok, severity="error"):
    return {"id": cid, "dataset": dataset, "rule": rule, "observed": observed, "limit": limit,
            "status": "pass" if ok else ("fail" if severity == "error" else "warn"), "severity": severity}


def run_checks(data) -> List[Dict[str, object]]:
    ont = data["ont"]
    cw, rules, coding, invs = data["crosswalk"], data["rules"], data["coding"], data["investigations"]
    pairs, pifs = data["pairs"], data["pifs"]
    out: List[Dict[str, object]] = []

    def add(*a, **k):
        out.append(_row("H%02d" % (len(out) + 1), *a, **k))

    def zero(dataset, rule, bad, severity="error"):
        add(dataset, rule, bad, 0, bad == 0, severity)

    factor_ids = set(ont.factors)
    dim_ids = set(ont.dimensions)
    fw_ids = set(ont.frameworks)
    ext_ids = set(ont.external_factors)

    # --- ontology
    zero("ontology", "every factor sits in a declared dimension",
         sum(1 for f in ont.factors.values() if f.dimension not in dim_ids))
    zero("ontology", "every alignment names a local factor and an external factor in the ontology",
         sum(1 for a in ont.alignments.values()
             if a.local_factor not in factor_ids or a.external_factor not in ext_ids))
    zero("ontology", "every external factor belongs to a declared framework",
         sum(1 for e in ont.external_factors.values() if e.framework not in fw_ids))
    noref = sum(1 for a in ont.alignments.values() if not a.source_refs)
    zero("ontology", "every alignment cites at least one source key", noref)
    undoc = sorted(k for k in ont.all_source_refs() if k not in data["citation_keys"])
    zero("ontology", "every source key used in the ontology has an entry in CITATIONS.md", len(undoc))
    pair_dup = len(ont.alignments) - len({(a.local_factor, a.external_factor) for a in ont.alignments.values()})
    zero("ontology", "no local factor is aligned twice to the same external factor", pair_dup)

    # --- crosswalk.csv against the ontology
    n_none = sum(len(v) for v in ont.no_counterpart.values())
    exp = len(ont.alignments) + n_none
    add("crosswalk", "row count equals alignments plus asserted absences in the ontology", len(cw), exp, len(cw) == exp)
    zero("crosswalk", "match_strength is close, partial, broader or none",
         sum(1 for r in cw if r["match_strength"] not in STRENGTHS))
    zero("crosswalk", "factor_curie is a factor and dimension is its declared dimension",
         sum(1 for r in cw if r["factor_curie"] not in factor_ids
             or r["dimension"] != ont.factors[r["factor_curie"]].dimension))
    zero("crosswalk", "framework is a declared framework", sum(1 for r in cw if r["framework"] not in fw_ids))
    zero("crosswalk", "external_curie is an external factor of the same framework",
         sum(1 for r in cw if r["external_curie"] and (r["external_curie"] not in ext_ids
             or ont.external_factors[r["external_curie"]].framework != r["framework"])))
    zero("crosswalk", "external_curie is empty exactly when match_strength is none",
         sum(1 for r in cw if bool(r["external_curie"]) == (r["match_strength"] == "none")))
    keys = [(r["factor_curie"], r["framework"], r["external_curie"]) for r in cw]
    zero("crosswalk", "no duplicate (factor, framework, external factor) rows", len(keys) - len(set(keys)))
    cw_strength = Counter(r["match_strength"] for r in cw)
    onto_strength = Counter(a.match_strength.split("Match", 1)[-1].lower() for a in ont.alignments.values())
    onto_strength["none"] = n_none
    mism = sum(abs(cw_strength[s] - onto_strength[s]) for s in STRENGTHS)
    zero("crosswalk", "strength counts agree with the ontology alignments", mism)
    refs = {x for r in cw for x in r["source_refs"].replace(";", ",").split(",") if x.strip()}
    refs = {x.strip() for x in refs}
    zero("crosswalk", "every source key in the CSV has an entry in CITATIONS.md",
         len(sorted(k for k in refs if k not in data["citation_keys"])))
    per_pair = Counter((r["factor_curie"], r["framework"]) for r in cw)
    full = len(factor_ids) * len(fw_ids - {f for f in fw_ids if not any(r["framework"] == f for r in cw)})
    covered = len(per_pair)
    add("crosswalk", "every factor has a row (match or asserted absence) for every framework used",
        covered, full, covered >= full, "warn")

    # --- rules
    rule_ids = [r["rule_id"] for r in rules]
    zero("rules", "rule_id is unique", len(rule_ids) - len(set(rule_ids)))
    zero("rules", "factor_curie is a factor", sum(1 for r in rules if r["factor_curie"] not in factor_ids))
    zero("rules", "external_curie is an external factor", sum(1 for r in rules if r["external_curie"] not in ext_ids))
    aligned = {(a.local_factor, a.external_factor) for a in ont.alignments.values()}
    zero("rules", "each rule's external factor is aligned to the rule's factor in the ontology (traceability)",
         sum(1 for r in rules if (r["factor_curie"], r["external_curie"]) not in aligned))
    zero("rules", "phrase_seen_in_incident_set is yes or no",
         sum(1 for r in rules if r["phrase_seen_in_incident_set"] not in ("yes", "no")))
    dup_phr = len(rules) - len({(r["factor_curie"], r["phrase"].lower()) for r in rules})
    zero("rules", "no factor carries the same phrase twice", dup_phr)
    uncovered = len(factor_ids) - len({r["factor_curie"] for r in rules})
    add("rules", "factors with no suggester rule (the suggester cannot propose them)", uncovered, 0, uncovered == 0,
        "warn")

    # --- investigations and coding
    inv_ids = [r["investigation_id"] for r in invs]
    zero("investigations", "investigation_id is unique", len(inv_ids) - len(set(inv_ids)))
    zero("investigations", "incident_date is yyyy-mm-dd or yyyy-mm",
         sum(1 for r in invs if not ISO_DAY_OR_MONTH.match(r["incident_date"])))
    zero("investigations", "final_report_date is empty or yyyy-mm-dd",
         sum(1 for r in invs if r["final_report_date"] and not ISO_DAY.match(r["final_report_date"])))
    late = sum(1 for r in invs if r["incident_date"] > LAST_PLAUSIBLE_DATE
               or (r["final_report_date"] and r["final_report_date"] > LAST_PLAUSIBLE_DATE))
    zero("investigations", "no date after " + LAST_PLAUSIBLE_DATE, late)
    zero("investigations", "final report is not before the incident",
         sum(1 for r in invs if r["final_report_date"] and r["final_report_date"] < r["incident_date"][:10]))
    zero("investigations", "fatalities, where recorded, is a non-negative integer",
         sum(1 for r in invs if r["fatalities"] and not r["fatalities"].isdigit()))
    nofat = sum(1 for r in invs if not r["fatalities"])
    add("investigations", "investigations with no fatality count recorded (left empty, not zero)", nofat, 0, nofat == 0, "warn")
    zero("investigations", "source_url is https", sum(1 for r in invs if not r["source_url"].startswith("https://")))
    zero("investigations", "coded is yes or no", sum(1 for r in invs if r["coded"] not in ("yes", "no")))
    zero("investigations", "cohort is development or held_out", sum(1 for r in invs if r["cohort"] not in COHORTS))
    coded_ids = {r["investigation_id"] for r in invs if r["coded"] == "yes"}
    coding_ids = {r["investigation_id"] for r in coding}
    zero("coding", "every coding row points at an investigation marked coded",
         len(coding_ids - coded_ids))
    zero("coding", "every investigation marked coded has at least one coding row", len(coded_ids - coding_ids))
    zero("coding", "factor_curie is a factor in the ontology", sum(1 for r in coding if r["factor_curie"] not in factor_ids))
    zero("coding", "evidence_type is finding or recommendation", sum(1 for r in coding if r["evidence_type"] not in EVIDENCE))
    zero("coding", "no investigation is coded twice to the same factor and passage",
         len(coding) - len({(r["investigation_id"], r["factor_curie"], r["quoted_text"]) for r in coding}))
    zero("coding", "quoted passages are at least 20 characters", sum(1 for r in coding if len(r["quoted_text"].strip()) < 20))
    dup_q = len(coding) - len({r["quoted_text"] for r in coding})
    add("coding", "the same passage is not reused for different factors or investigations", dup_q, 0, dup_q == 0, "warn")
    unused = len(factor_ids - {r["factor_curie"] for r in coding})
    add("coding", "factors never coded in any investigation (the incident set cannot test them)", unused, 0, unused == 0,
        "warn")
    n_held = sum(1 for r in invs if r["cohort"] == "held_out")
    add("investigations", "held-out cohort is the larger share of listed investigations (it was added later)",
        "%d of %d" % (n_held, len(invs)), "> 50%", n_held * 2 > len(invs), "warn")

    # --- co-occurrence tables recomputed from the coding file
    sets = defaultdict(set)
    for r in coding:
        sets[r["investigation_id"]].add(r["factor_curie"].split(":", 1)[1])
    counts = Counter()
    for s in sets.values():
        for pr in combinations(sorted(s), 2):
            counts[pr] += 1
    pair_bad = sum(1 for r in pairs if counts.get((r["pif_a"], r["pif_b"]), 0) != int(r["observed"]))
    zero("cooccurrence", "observed pair counts equal a recount from csb_coding.csv", pair_bad)
    listed = {(r["pif_a"], r["pif_b"]) for r in pairs}
    zero("cooccurrence", "pair table lists every pair observed at least once", len(set(counts) - listed))
    k = len(pifs)
    add("cooccurrence", "pair table has one row per pair of the PIFs that appear in the coding", len(pairs), k * (k - 1) // 2,
        len(pairs) == k * (k - 1) // 2)
    prev = Counter(p for s in sets.values() for p in s)
    prev_bad = sum(1 for r in pifs if prev[r["pif"]] != int(r["investigations"]))
    zero("cooccurrence", "PIF investigation counts equal a recount from csb_coding.csv", prev_bad)
    holm_bad = sum(1 for r in pairs if float(r["holm_p_two_sided"]) < min(float(r["p_upper"]), float(r["p_lower"])) - 1e-9)
    zero("cooccurrence", "Holm-adjusted p is never below the smaller one-sided p", holm_bad)
    ci_bad = sum(1 for r in pifs if not float(r["prev_ci_low"]) <= float(r["prevalence"]) <= float(r["prev_ci_high"]))
    zero("cooccurrence", "prevalence lies inside its Wilson interval", ci_bad)

    # --- null-rate expectations
    for ds in ("crosswalk", "rules", "coding", "investigations"):
        prof = {r["column"]: r for r in column_profile(data[ds], ds)}
        for c in MUST_BE_COMPLETE[ds]:
            add(ds, "column %s has no empty values" % c, prof[c]["empty"], 0, prof[c]["empty"] == 0)
        for (d2, c), (cap, _why) in sorted(NULL_LIMITS.items()):
            if d2 == ds:
                add(ds, "column %s is empty in at most %.1f%% of rows" % (c, cap), prof[c]["empty_pct"], cap,
                    prof[c]["empty_pct"] <= cap)
    return out


# ---------------------------------------------------------------- lineage

def load_spec(path: str = SPEC):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _top_level_names(path: str):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _matches(root: str, pattern: str):
    return sorted(os.path.relpath(p, root).replace(os.sep, "/") for p in glob.glob(os.path.join(root, pattern)))


def validate_lineage(spec, root: str = ROOT) -> List[str]:
    problems: List[str] = []
    arts, stages = spec["artifacts"], spec["stages"]
    declared = set()
    for aid, a in arts.items():
        if a["kind"] == "file":
            for pat in a["paths"]:
                hits = _matches(root, pat)
                if not hits:
                    problems.append("artifact %s: nothing matches %s" % (aid, pat))
                declared.update(hits)
    producer, seen = {}, set()
    for st in stages:
        sid = st["id"]
        if sid in seen:
            problems.append("duplicate stage id: " + sid)
        seen.add(sid)
        f = os.path.join(root, st["script"])
        if not os.path.exists(f):
            problems.append("stage %s: script not found: %s" % (sid, st["script"]))
        elif st["function"] not in _top_level_names(f):
            problems.append("stage %s: function %s not defined in %s" % (sid, st["function"], st["script"]))
        for ref in st["inputs"] + st["outputs"]:
            if ref not in arts:
                problems.append("stage %s: undeclared artifact %s" % (sid, ref))
        for o in st["outputs"]:
            if o in producer:
                problems.append("artifact %s produced by both %s and %s" % (o, producer[o], sid))
            producer[o] = sid
    deps = {s["id"]: {producer[a] for a in s["inputs"] if a in producer} for s in stages}
    rem = dict(deps)
    while rem:
        ready = [s for s, d in rem.items() if not (d & set(rem))]
        if not ready:
            problems.append("cycle among stages: " + ", ".join(sorted(rem)))
            break
        for s in ready:
            del rem[s]
    for aid, a in arts.items():
        if a["kind"] == "file" and aid not in producer and not a.get("source", False):
            problems.append("artifact %s: committed file with no producing stage and not marked source" % aid)
    for pat in spec["must_be_declared"]:
        for rel in _matches(root, pat):
            if rel not in declared:
                problems.append("committed file not declared in lineage: " + rel)
    return problems


def topo(stages):
    producer = {a: s["id"] for s in stages for a in s["outputs"]}
    by_id = {s["id"]: s for s in stages}
    deps = {i: {producer[a] for a in s["inputs"] if a in producer} for i, s in by_id.items()}
    order, done = [], set()
    while len(done) < len(by_id):
        for i in by_id:
            if i not in done and deps[i] <= done:
                order.append(by_id[i])
                done.add(i)
                break
        else:
            break
    return order


def lineage_rows(spec):
    producer = {a: s["id"] for s in spec["stages"] for a in s["outputs"]}
    rows = []
    for n, st in enumerate(topo(spec["stages"]), 1):
        ups = sorted({producer[a] for a in st["inputs"] if a in producer})
        rows.append({"order": n, "stage": st["id"], "label": st["label"], "script": st["script"],
                     "command": st["command"], "inputs": ";".join(st["inputs"]),
                     "outputs": ";".join(st["outputs"]), "upstream_stages": ";".join(ups)})
    return rows


# ---------------------------------------------------------------- rendering

def csv_text(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def render_svg(checks) -> str:
    order = ["ontology", "crosswalk", "rules", "investigations", "coding", "cooccurrence"]
    colour = {"pass": "#2f855a", "warn": "#b7791f", "fail": "#c53030"}
    W, left, right, top, rh = 760, 150, 60, 70, 30
    H = top + rh * len(order) + 56
    mx = max(Counter(c["dataset"] for c in checks).values())
    sx = lambda v: left + (W - left - right) * v / mx  # noqa: E731
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
         'aria-labelledby="t d" font-family="system-ui, sans-serif" font-size="12">' % (W, H, W, H),
         '<title id="t">Data expectations by dataset in the human-factors ontology repository</title>',
         '<desc id="d">Stacked horizontal bars: number of named expectations per dataset, split into pass, warn and fail.</desc>',
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H),
         '<text x="16" y="24" font-size="15" font-weight="600" fill="#1a1a1a">Named data expectations by dataset</text>',
         '<text x="16" y="42" fill="#555">Green passes, amber warns (reported, not blocking), red fails. Committed files only.</text>']
    for i, ds in enumerate(order):
        y = top + rh * i
        o.append('<text x="%d" y="%.1f" text-anchor="end" fill="#1a1a1a">%s</text>' % (left - 8, y + 17, ds))
        x = left
        for st in ("pass", "warn", "fail"):
            n = sum(1 for c in checks if c["dataset"] == ds and c["status"] == st)
            if n:
                w = sx(n) - left
                o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="20" fill="%s"/>' % (x, y + 4, w, colour[st]))
                o.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#ffffff" font-weight="600">%d</text>'
                         % (x + w / 2, y + 18, n))
                x += w
        tot = sum(1 for c in checks if c["dataset"] == ds)
        o.append('<text x="%.1f" y="%.1f" fill="#1a1a1a">%d</text>' % (x + 6, y + 18, tot))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def render_doc(checks, spec, prof) -> str:
    n = len(checks)
    npass = sum(1 for c in checks if c["status"] == "pass")
    warns = [c for c in checks if c["status"] == "warn"]
    fails = [c for c in checks if c["status"] == "fail"]
    arts, stages = spec["artifacts"], topo(spec["stages"])
    L = ["# Data health and pipeline lineage", "",
         "Generated by `python3 tools/health.py --write`; do not edit by hand. `tests/test_health.py` fails if this file, "
         "`docs/health.svg` or `health/*.csv` differ from the generator output.", "",
         "A Foundry-style practice in plain Python on public data: every rule below is a named expectation over a committed "
         "file with an observed value, a limit and a status, and the build pipeline is declared as stages with inputs and "
         "outputs and checked against the repository. Independent of and not affiliated with Palantir.", "",
         "## Result", "",
         "%d expectations: %d pass, %d warn, %d fail. Rows: `health/health_checks.csv`. Empty-value profile of every column: "
         "`health/health_columns.csv`." % (n, npass, len(warns), len(fails)), "",
         "![Expectations by dataset](health.svg)", "",
         "| Dataset | Expectations | Pass | Warn | Fail |", "|---|---|---|---|---|"]
    for ds in ("ontology", "crosswalk", "rules", "investigations", "coding", "cooccurrence"):
        cs = [c for c in checks if c["dataset"] == ds]
        L.append("| %s | %d | %d | %d | %d |" % (ds, len(cs), sum(c["status"] == "pass" for c in cs),
                                                   sum(c["status"] == "warn" for c in cs),
                                                   sum(c["status"] == "fail" for c in cs)))
    L += ["", "## What the warnings say", ""]
    if warns:
        for c in warns:
            L.append("- %s `%s`: %s. Observed %s, limit %s." % (c["id"], c["dataset"], c["rule"], c["observed"], c["limit"]))
    else:
        L.append("None.")
    if fails:
        L += ["", "## Failures", ""]
        for c in fails:
            L.append("- %s `%s`: %s. Observed %s, limit %s." % (c["id"], c["dataset"], c["rule"], c["observed"], c["limit"]))
    L += ["", "Warnings describe the data as it is: they are reported so a reader knows the limit, and they do not block CI. "
          "A new error-severity failure does.", "",
          "## What this does and does not show", "",
          "- The expectations check consistency between the committed files (ontology, crosswalk, rules, coding, tables) and value "
          "domains. They do not check that a quoted CSB passage says what the coding claims, or that an alignment is right: "
          "that is `docs/PROVENANCE.md` and the second-coder protocol.",
          "- Null ceilings are judgement, set a little above the committed value so a regression shows.",
          "- The lineage is declared, then validated (paths, functions via ast, undeclared outputs, double producers, cycles); "
          "it is not discovered by tracing execution.", "",
          "## Pipeline lineage", "",
          "%d stages, %d artifacts. Hexagons are hand-curated sources, rectangles are committed files." % (len(stages), len(arts)),
          "", "```mermaid", "flowchart LR"]
    for aid, a in arts.items():
        lab = a["label"].replace('"', "'")
        wrap = '{{"%s"}}' if a.get("source") else '["%s"]'
        L.append("  A_%s%s" % (aid, wrap % lab))
    for s in stages:
        L.append('  S_%s("%s")' % (s["id"], s["label"].replace('"', "'")))
    for s in stages:
        for a in s["inputs"]:
            L.append("  A_%s --> S_%s" % (a, s["id"]))
        for a in s["outputs"]:
            L.append("  S_%s --> A_%s" % (s["id"], a))
    L += ["```", "", "| # | Stage | Command | Reads | Writes |", "|---|---|---|---|---|"]
    for i, s in enumerate(stages, 1):
        L.append("| %d | %s | `%s` | %s | %s |" % (i, s["label"], s["command"],
                                                   ", ".join(arts[a]["label"] for a in s["inputs"]) or "none",
                                                   ", ".join(arts[a]["label"] for a in s["outputs"])))
    L += ["", "## Reproduce", "", "```", "python3 tools/health.py --write   # or: make health", "python3 tools/health.py --check", "```", ""]
    return "\n".join(L)


def outputs():
    data = load()
    checks = run_checks(data)
    spec = load_spec()
    prof = profiles(data)
    return {
        CHECKS_CSV: csv_text(checks),
        COLUMNS_CSV: csv_text(prof),
        LINEAGE_CSV: csv_text(lineage_rows(spec)),
        SVG: render_svg(checks),
        DOC: render_doc(checks, spec, prof),
    }, checks, validate_lineage(spec)


def main(argv) -> int:
    outs, checks, problems = outputs()
    errors = [c for c in checks if c["status"] == "fail"]
    warns = [c for c in checks if c["status"] == "warn"]
    print("%d expectations, %d fail, %d warn; lineage problems: %d" % (len(checks), len(errors), len(warns), len(problems)))
    for c in errors + warns:
        print("  %s %s %s: %s (observed %s, limit %s)" % (c["status"], c["id"], c["dataset"], c["rule"], c["observed"], c["limit"]))
    for p in problems:
        print("  lineage:", p)
    if "--write" in argv:
        os.makedirs(OUT_DIR, exist_ok=True)
        for path, text in outs.items():
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        print("wrote %d files" % len(outs))
    if "--check" in argv:
        stale = []
        for path, text in outs.items():
            if not os.path.exists(path) or open(path, encoding="utf-8", newline="").read() != text:
                stale.append(os.path.relpath(path, ROOT))
        for s in stale:
            print("  stale:", s)
        return 1 if errors or problems or stale else 0
    return 1 if errors or problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
