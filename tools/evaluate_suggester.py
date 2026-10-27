"""Evaluate the PIF suggester against the hand-coded CSB incidents.

Unit of analysis: one (investigation, PIF) pair. The "narrative" for an
investigation is the concatenation of its quoted passages in
``incidents/csb_coding.csv`` (the only incident text in the repository). The
gold label set is the PIFs coded for that investigation. See the generated
report and ``docs/suggester.html`` for the caveats, which are substantial.

    python3 tools/evaluate_suggester.py          # print the report
    python3 tools/evaluate_suggester.py --write  # refresh incidents/suggester_eval.md
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
sys.path.insert(0, _REPO_ROOT)

from ehs_hfo.ontology import Ontology  # noqa: E402
from ehs_hfo.suggest import Rule, build_baseline, load_curated, suggest  # noqa: E402
from tools.build_csb_coding import CODING, INC_DIR, INVESTIGATIONS, read  # noqa: E402

OUTPUT = os.path.join(INC_DIR, "suggester_eval.md")


def cohorts() -> Dict[str, str]:
    """investigation_id -> 'development' (read before the rules were written) or 'held_out'."""
    return {r["investigation_id"]: r["cohort"] for r in read(INVESTIGATIONS)}


def narratives_and_gold(cohort: Optional[str] = None) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    texts: Dict[str, List[str]] = defaultdict(list)
    gold: Dict[str, Set[str]] = defaultdict(set)
    which = cohorts()
    for r in read(CODING):
        if cohort is not None and which[r["investigation_id"]] != cohort:
            continue
        texts[r["investigation_id"]].append(r["quoted_text"])
        gold[r["investigation_id"]].add(r["factor_curie"])
    return {k: "\n".join(v) for k, v in texts.items()}, dict(gold)


def predict(rules: Sequence[Rule], texts: Dict[str, str]) -> Dict[str, Set[str]]:
    return {k: set(suggest(t, rules)) for k, t in texts.items()}


def counts(pred: Dict[str, Set[str]], gold: Dict[str, Set[str]]) -> Dict[str, Counter]:
    per: Dict[str, Counter] = defaultdict(Counter)
    for inv in gold:
        p = pred.get(inv, set())
        for f in p | gold[inv]:
            if f in p and f in gold[inv]:
                per[f]["tp"] += 1
            elif f in p:
                per[f]["fp"] += 1
            else:
                per[f]["fn"] += 1
    return per


def ratio(num: int, den: int) -> str:
    return "n/a" if den == 0 else f"{num / den:.2f}"


def summarise(per: Dict[str, Counter]) -> Tuple[int, int, int]:
    return (sum(c["tp"] for c in per.values()), sum(c["fp"] for c in per.values()),
            sum(c["fn"] for c in per.values()))


def macro_recall(per: Dict[str, Counter]) -> str:
    vals = [c["tp"] / (c["tp"] + c["fn"]) for c in per.values() if c["tp"] + c["fn"] > 0]
    return "n/a" if not vals else f"{sum(vals) / len(vals):.2f}"


def evaluate(ont: Ontology, cohort: Optional[str] = None):
    """Return (n_inv, n_pairs, gold_count, results, nrules), results keyed by rule-set name.

    ``cohort`` restricts to 'development' or 'held_out' investigations; None uses all.
    The majority-class control always predicts the most frequent PIF of the development
    cohort, so it is fixed before the held-out cohort is looked at.
    """
    texts, gold = narratives_and_gold(cohort)
    n_pairs = sum(len(v) for v in gold.values())
    curated = load_curated()
    sets = {
        "baseline (words unique to a PIF's ontology labels; not tuned)": build_baseline(ont),
        "curated (crosswalk/pif_rules.csv; written after reading the development quotes)": curated,
        "curated without the rules whose phrase was taken from the development quotes": [
            r for r in curated if not r.seen_in_set],
    }
    gold_count = Counter(f for v in gold.values() for f in v)
    dev_gold = Counter(f for v in narratives_and_gold("development")[1].values() for f in v)
    majority = dev_gold.most_common(1)[0][0]
    results = {name: counts(predict(r, texts), gold) for name, r in sets.items()}
    maj_name = f"majority-class control (always predict {ont.factor(majority).label})"
    results[maj_name] = counts({k: {majority} for k in gold}, gold)
    nrules = {name: len(r) for name, r in sets.items()}
    nrules[maj_name] = 1
    return len(gold), n_pairs, gold_count, results, nrules


OVERALL_HEAD = ["| Rule set | Rules | TP | FP | FN | Precision | Recall | Macro recall over coded PIFs |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]


def overall_table(results, nrules) -> List[str]:
    out = list(OVERALL_HEAD)
    for name, per in results.items():
        tp, fp, fn = summarise(per)
        out.append(f"| {name} | {nrules[name]} | {tp} | {fp} | {fn} | {ratio(tp, tp + fp)} | "
                   f"{ratio(tp, tp + fn)} | {macro_recall(per)} |")
    return out


def per_pif_tables(ont: Ontology, results, gold_count, only: Optional[str] = None) -> List[str]:
    out: List[str] = []
    for name, per in results.items():
        if only is not None and not name.startswith(only):
            continue
        out += ["", f"### Per PIF: {name}", "",
                "| PIF | Gold (support) | TP | FP | FN | Precision | Recall |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for f in sorted(set(per) | set(gold_count), key=lambda x: (-gold_count[x], x)):
            c = per.get(f, Counter())
            out.append(f"| {ont.factor(f).label} | {gold_count[f]} | {c['tp']} | {c['fp']} | {c['fn']} | "
                       f"{ratio(c['tp'], c['tp'] + c['fp'])} | {ratio(c['tp'], c['tp'] + c['fn'])} |")
    return out


def render(ont: Ontology) -> str:
    n_inv, n_pairs, gold_count, results, nrules = evaluate(ont)
    d_inv, d_pairs, d_gold, d_res, d_rules = evaluate(ont, "development")
    h_inv, h_pairs, h_gold, h_res, h_rules = evaluate(ont, "held_out")
    out = [
        "# PIF suggester: evaluation against the hand-coded CSB incidents",
        "",
        "Generated by `tools/evaluate_suggester.py`; do not hand-edit. Method, rules and caveats: `docs/suggester.html`.",
        "",
        f"Data: {n_inv} coded investigations, {n_pairs} (investigation, PIF) gold pairs over "
        f"{len(gold_count)} distinct PIFs, split into two cohorts by `cohort` in "
        f"`csb_investigations.csv`: **development** ({d_inv} investigations, {d_pairs} pairs, coded before "
        f"the rules were written, so the rule author had read these quotes) and **held-out** ({h_inv} "
        f"investigations, {h_pairs} pairs, coded after the rules in `crosswalk/pif_rules.csv` were "
        "committed; the rules were not changed afterwards). The narrative for each investigation is the "
        "concatenation of the quoted CSB passages used to code it.",
        "",
        "**Read this first.** The input text is the evidence the gold labels were coded from, so recall "
        "measures whether the rules' vocabulary reaches the words a coder already pointed at, not "
        "whether the suggester finds PIFs in a free-running narrative. Precision is measured against an "
        "incomplete gold standard (only PIFs with a quoted passage are coded), so some false positives "
        "may be real conditions nobody coded. The held-out cohort is a genuine out-of-sample test of the "
        "rules for these incidents; the development cohort is resubstitution (optimistic). The same "
        "person coded both cohorts and wrote the rules, and the held-out quotes are mostly CSB "
        "recommendation wording from summary pages, which differs in register from the development "
        "findings. The held-out passages were also chosen by looking for text on each factor's topic (training, procedures, alarms and so on), so their vocabulary is likely to be closer to the rules' keywords than a whole report would be; this inflates recall. Nothing here is an estimate of performance on other incidents; the held-out cohort is the closest thing to one and it is small, so one pair moves a PIF's precision or recall by many points.",
        "",
        f"## Held-out cohort ({h_inv} investigations, {h_pairs} pairs, rules not fit to these)",
        "",
    ]
    out += overall_table(h_res, h_rules)
    out += ["", f"## Development cohort ({d_inv} investigations, {d_pairs} pairs, resubstitution)", ""]
    out += overall_table(d_res, d_rules)
    out += ["", f"## All coded investigations ({n_inv} investigations, {n_pairs} pairs)", ""]
    out += overall_table(results, nrules)
    out += ["", "## Per PIF, held-out cohort"]
    out += per_pif_tables(ont, h_res, h_gold)
    out += ["", "## Per PIF, all coded investigations"]
    out += per_pif_tables(ont, results, gold_count)
    out += ["", "n/a = undefined (no predictions, or no gold cases). PIFs with no gold coding can only score false positives.", ""]
    return "\n".join(out)


def main(argv: Sequence[str]) -> int:
    text = render(Ontology.load())
    if "--write" in argv:
        with open(OUTPUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
